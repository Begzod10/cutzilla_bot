import asyncio
from src.core.database import AsyncSessionLocal
from src.models import Barber, User
from sqlalchemy import select

async def debug_barbers():
    async with AsyncSessionLocal() as session:
        # Check all barbers
        stmt = select(Barber.id, User.name, User.city_id, User.role).join(User, Barber.user_id == User.id)
        result = await session.execute(stmt)
        barbers = result.all()
        
        print("--- Barbers in DB ---")
        if not barbers:
            print("No barbers found in database linked to users.")
        for b in barbers:
            print(f"ID: {b.id}, Name: {b.name}, City ID: {b.city_id}, Role: {b.role}")
        
        # Check Users who are barbers but maybe no Barber record?
        stmt_u = select(User.id, User.name, User.city_id, User.role).where(User.role == 'barber')
        result_u = await session.execute(stmt_u)
        users = result_u.all()
        print("\n--- Users with role 'barber' ---")
        for u in users:
            print(f"ID: {u.id}, Name: {u.name}, City ID: {u.city_id}")

if __name__ == '__main__':
    asyncio.run(debug_barbers())
