import asyncio
from src.core.database import AsyncSessionLocal
from src.models.users import User
from src.models.barber import Barber
from sqlalchemy import select

async def list_data():
    async with AsyncSessionLocal() as session:
        # List all users
        print("--- All Users ---")
        res = await session.execute(select(User))
        users = res.scalars().all()
        for u in users:
            print(f"User ID: {u.id}, Username: {u.username}, TG ID: {u.telegram_id}, Role: {u.role}, Name: {u.name}")
        
        # List all barbers
        print("\n--- All Barbers ---")
        res = await session.execute(select(Barber))
        barbers = res.scalars().all()
        for b in barbers:
            print(f"Barber ID: {b.id}, User ID: {b.user_id}, Login: {b.login}")

if __name__ == "__main__":
    asyncio.run(list_data())
