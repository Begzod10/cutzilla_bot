# app/service/tasks.py
from __future__ import annotations

import os
import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path

import requests
from celery import shared_task

# ✅ Make sure ALL models are imported & mappers configured in the right order.
#    Your app/models/__init__.py must import region -> user -> client -> barber -> service, then call configure_mappers()
import app.models  # DO NOT REMOVE

from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.db import AsyncSessionLocal, async_engine
from app.service.models import Service, ServiceImages

log = logging.getLogger(__name__)


# ---------- public Celery entrypoint (sync) ----------
@shared_task(name="app.tasks.update_services")
def update_services() -> None:
    """
    Celery task entrypoint. Runs the async body in a fresh event loop.
    We import app.models above so all mappers (Country/User/...) are registered
    BEFORE the first DB access.
    """
    # Defensive import (no-op if already imported)
    import app.models  # noqa: F401
    asyncio.run(_update_services())


# ---------- async task body ----------
async def _update_services() -> None:
    """
    Fetch services from the platform API and upsert into local DB with images.
    """
    # Defensive import (keeps mapper order guarantees if this module is run standalone)
    import app.models  # noqa: F401

    api = os.getenv("API")
    username = os.getenv("PLATFORM_LOGIN", "rimefara")  # change if needed
    password = os.getenv("PASSWORD")

    if not api or not password:
        log.error("API/PASSWORD environment variables are not set.")
        return

    # ---- 1) Authenticate (sync HTTP is fine in Celery) ----
    try:
        auth_r = requests.post(
            f"{api}/api/v1/auth/login/",
            json={"login": username, "password": password},
            timeout=20,
        )
        auth_r.raise_for_status()
        auth = auth_r.json()
    except Exception as e:
        log.exception("Login failed: %s", e)
        return

    token = auth.get("access")
    if not token:
        log.error("Login response missing 'access': %s", auth)
        return

    headers = {"Authorization": f"Bearer {token}"}

    # ---- 2) Fetch services ----
    try:
        r = requests.get(f"{api}/api/v1/service/services/", headers=headers, timeout=30)
        r.raise_for_status()
        services = r.json() or []
    except Exception as e:
        log.exception("Failed to fetch services: %s", e)
        return

    # Optional debug: peek at payload
    # log.warning("%s", services)

    # ---- 3) Upsert into DB ----
    async with AsyncSessionLocal() as session:
        try:
            for s in services:
                # Upsert Service by platform_id
                service = (await session.scalars(
                    select(Service).where(Service.platform_id == s.get("id"))
                )).first()

                if not service:
                    service = Service(
                        platform_id=s.get("id"),
                        name_uz=s.get("name_uz"),
                        name_ru=s.get("name_ru"),
                        name_en=s.get("name_en"),   # ← no trailing comma!
                        description_uz=s.get("description_uz"),
                        description_ru=s.get("description_ru"),
                        description_en=s.get("description_en"),
                        disabled=bool(s.get("disabled", False)),
                    )
                    session.add(service)
                    # Need service.id for image FK
                    await session.flush()
                else:
                    service.name_uz = s.get("name_uz")
                    service.name_ru = s.get("name_ru")
                    service.name_en = s.get("name_en")
                    service.description_uz = s.get("description_uz")
                    service.description_ru = s.get("description_ru")
                    service.description_en = s.get("description_en")
                    service.disabled = bool(s.get("disabled", False))

                # Upsert images for this service
                for img in s.get("images", []) or []:
                    url = img.get("image")
                    if not url:
                        continue
                    local_path = _download_image(url)
                    if not local_path:
                        continue

                    # Avoid duplicates by (service_id, image_url)
                    exists = (await session.scalars(
                        select(ServiceImages).where(
                            ServiceImages.service_id == service.id,
                            ServiceImages.image_url == local_path,
                        )
                    )).first()
                    if not exists:
                        session.add(ServiceImages(service_id=service.id, image_url=local_path))

            await session.commit()

            # Remove local services that no longer exist on the platform
            platform_ids = [s.get("id") for s in services if s.get("id") is not None]
            if platform_ids:
                await session.execute(
                    delete(Service).where(Service.platform_id.notin_(platform_ids))
                )
                await session.commit()

        except SQLAlchemyError as db_err:
            await session.rollback()
            log.exception("DB error while saving services: %s", db_err)
        except Exception as e:
            await session.rollback()
            log.exception("Unexpected error while saving services: %s", e)

    # ---- 4) Dispose engine before loop closes (prevents asyncpg teardown noise) ----
    try:
        await async_engine.dispose()
    except Exception:
        # best-effort; avoid masking real errors
        pass


# ---------- helpers ----------
def _download_image(url: str) -> Optional[str]:
    """
    Downloads an image to static/images/ and returns the local relative path as string,
    or None on failure.
    """
    try:
        resp = requests.get(url, stream=True, timeout=30)
        if resp.status_code != 200:
            log.warning("Image download failed (%s): %s", resp.status_code, url)
            return None

        filename = os.path.basename(urlparse(url).path) or "image.bin"
        # simple dedup by filename; if collisions are possible, hash the URL
        local_dir = Path("static/images")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(1024 * 64):
                if chunk:
                    f.write(chunk)

        return str(local_path)
    except Exception as e:
        log.warning("Error downloading image %s: %s", url, e)
        return None
