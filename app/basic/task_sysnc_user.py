# app/client/tasks_sync_user.py  (bot project)
from celery import shared_task
import requests
import logging
import os
from dotenv import load_dotenv
import asyncio
from functools import partial

log = logging.getLogger(__name__)
load_dotenv()
API = os.getenv("API")
DJANGO_SYNC_TOKEN = os.getenv("DJANGO_SYNC_TOKEN")


def _headers():
    h = {"Content-Type": "application/json"}
    if DJANGO_SYNC_TOKEN:
        h["Authorization"] = f"Token {DJANGO_SYNC_TOKEN}"
    return h


@shared_task(name="sync_user_to_django", autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 5})
def sync_user_to_django(payload: dict):
    """
    payload = {
      "telegram_id": int,
      "first_name": str|None,
      "last_name": str|None,
      "role": "user"|"barber"|"admin",
      "username": str|None
    }
    """
    url = f"{API.rstrip('/')}/api/v1/user/sync/user/"
    r = requests.post(url, json=payload, headers=_headers(), timeout=15)
    if r.status_code != 200:
        log.error("User sync failed %s -> %s %s", url, r.status_code, r.text[:300])
        r.raise_for_status()
    return r.json()


async def _enqueue_user_sync(payload: dict) -> None:
    # avoid blocking the event loop with Celery's network I/O
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(sync_user_to_django.delay, payload))


@shared_task(
    name="sync_client_to_django",
    ignore_result=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=5,
    retry_jitter=True,
    max_retries=5,
)
def sync_client_to_django(telegram_id: int, first_name: str = None,
                        last_name: str = None, lang: str = None, role: str = "client",client_id=None):
    """
    Fire-and-forget upsert of a user in the Django app by telegram_id.
    """
    payload = {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
        "lang": lang,
        "role": role or "client",
        "username": str(telegram_id),
        "client_id": client_id,
    }

    url = f"{API.rstrip('/')}/api/v1/client/add/"
    r = requests.post(url, json=payload, headers=_headers(), timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        log.error("POST %s -> %s %s", url, r.status_code, r.text[:500])
        raise
