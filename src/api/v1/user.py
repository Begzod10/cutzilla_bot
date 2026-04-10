from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import List
from src.core.database import get_db
from src.models.users import User
from src.schemas.user import UserResponse, SyncUserSchema
from src.api.deps import get_current_user
from src.core.security import get_password_hash

router = APIRouter()

VALID_ROLES = {"user", "barber", "admin"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/", response_model=List[UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users

@router.post("/sync")
async def sync_user_view(data: SyncUserSchema, db: AsyncSession = Depends(get_db)):
    role = data.role if data.role in VALID_ROLES else "user"
    username = data.username or str(data.telegram_id)[:150]

    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalars().first()
    
    created = False
    if not user:
        try:
            new_user = User(
                telegram_id=data.telegram_id,
                first_name=data.first_name,
                last_name=data.last_name,
                username=username,
                role=role,
                password=get_password_hash("12345678")
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user = new_user
            created = True
        except IntegrityError:
            await db.rollback()
            # Handle race condition
            result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
            user = result.scalars().first()

    if not created and user:
        # Update fields if different
        updates = {}
        if data.first_name and user.first_name != data.first_name:
            updates["first_name"] = data.first_name
        if data.last_name and user.last_name != data.last_name:
            updates["last_name"] = data.last_name
        if role and user.role != role:
            updates["role"] = role

        if updates:
            await db.execute(update(User).where(User.id == user.id).values(**updates))
            await db.commit()
            await db.refresh(user)

    return {"id": user.id if user else None, "created": created}
