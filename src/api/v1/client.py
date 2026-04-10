from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import List
from src.core.database import get_db
from src.models.client import Client
from src.models.users import User
from src.schemas.client import ClientResponse, SyncClientSchema
from src.core.security import get_password_hash

router = APIRouter()

@router.get("/", response_model=List[ClientResponse])
async def read_clients(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).offset(skip).limit(limit))
    clients = result.scalars().all()
    return clients

@router.post("/sync")
async def sync_client_view(data: SyncClientSchema, db: AsyncSession = Depends(get_db)):
    username = data.username or str(data.telegram_id)
    
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalars().first()
    
    user_created = False
    if not user:
        try:
            new_user = User(
                telegram_id=data.telegram_id,
                username=username,
                first_name=data.first_name,
                last_name=data.last_name,
                role=data.role,
                password=get_password_hash("12345678")
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user = new_user
            user_created = True
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
            user = result.scalars().first()

    if not user_created and user:
        updates = {}
        if data.first_name is not None and getattr(user, "first_name") != data.first_name:
            updates["first_name"] = data.first_name
        if data.last_name is not None and getattr(user, "last_name") != data.last_name:
            updates["last_name"] = data.last_name
        if data.role is not None and getattr(user, "role") != data.role:
            updates["role"] = data.role
        if username is not None and getattr(user, "username") != username:
            updates["username"] = username

        if updates:
            await db.execute(update(User).where(User.id == user.id).values(**updates))
            await db.commit()
            await db.refresh(user)

    client_res = await db.execute(select(Client).where(Client.user_id == user.id))
    client = client_res.scalars().first()
    client_created = False
    
    if not client:
        try:
            new_client = Client(
                user_id=user.id,
                external_id=data.client_id
            )
            db.add(new_client)
            await db.commit()
            client_created = True
        except IntegrityError:
            await db.rollback()

    return {"id": user.id, "created": user_created or client_created}
