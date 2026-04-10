import asyncio
from src.core.database import AsyncSessionLocal
from src.models.users import User
from sqlalchemy import select, func

async def search_users():
    async with AsyncSessionLocal() as session:
        # Search for anything like 'sobirov'
        print("--- Searching for users containing 'sob' ---")
        res = await session.execute(
            select(User).where(func.lower(User.username).like('%sob%'))
        )
        users = res.scalars().all()
        for u in users:
            print(f"ID: {u.id}, Username: {u.username}, Role: {u.role}, UserType: {u.user_type}, TG: {u.telegram_id}")
        
        # Search for all users with role or user_type = barber
        print("\n--- All Barbers in DB ---")
        res = await session.execute(
            select(User).where((User.role == 'barber') | (User.user_type == 'barber'))
        )
        barbers = res.scalars().all()
        for b in barbers:
            print(f"ID: {b.id}, Username: {b.username}, Role: {b.role}, UserType: {b.user_type}, TG: {b.telegram_id}")

if __name__ == "__main__":
    asyncio.run(search_users())
