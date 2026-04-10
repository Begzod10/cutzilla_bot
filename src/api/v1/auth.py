from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from src.core.database import get_db
from src.models.users import User
from src.models.barber import Barber
from src.core.security import verify_password, create_access_token
from src.schemas.auth import LoginRequest
from passlib.hash import django_pbkdf2_sha256
from src.core.config import settings
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/login")
async def login_api_view(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.login))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid login or password")

    # Verify password (only if user.password is set)
    is_valid_pwd = False
    if not user.password:
        is_valid_pwd = True  # allow login without password if not set in DB
    elif user.password.startswith("pbkdf2_sha256$"):
        is_valid_pwd = django_pbkdf2_sha256.verify(request.password, user.password)
    else:
        is_valid_pwd = verify_password(request.password, user.password)

    if not is_valid_pwd:
        raise HTTPException(status_code=400, detail="Invalid login or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled.")

    telegram_id = request.telegram_id
    if telegram_id is not None:
        # Free telegram_id from any other user
        await db.execute(
            update(User).where(User.telegram_id == telegram_id, User.id != user.id).values(telegram_id=None)
        )
        # Bind telegram_id to current user
        await db.execute(update(User).where(User.id == user.id).values(telegram_id=telegram_id))
        await db.commit()
        await db.refresh(user)

    # Issue refresh / access tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_access_token(data={"sub": user.username, "type": "refresh"}, expires_delta=timedelta(days=30))

    payload = {
        "access": access_token,
        "refresh": refresh_token,
        "login": user.username,
        "role": user.role
    }

    if user.role == 'barber':
        barber_res = await db.execute(select(Barber).options(selectinload(Barber.barber_services)).where(Barber.user_id == user.id))
        barber = barber_res.scalars().first()
        if barber:
            payload["barber"] = {
                "per_hour": barber.per_hour,
                "start_time": barber.start_time,
                "end_time": barber.end_time,
                "score": barber.score,
                "working_days": barber.working_days,
                "img": barber.img,
                "midnight_price": barber.midnight_price,
                "barber_services": [
                    {
                        "id": svc.id,
                        "barber_id": svc.barber_id,
                        "service_id": svc.service_id,
                        "price": svc.price,
                        "duration": svc.duration,
                    } for svc in barber.barber_services
                ]
            }
            payload["user_id"] = user.id

    return payload
