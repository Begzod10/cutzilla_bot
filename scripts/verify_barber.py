import asyncio
from src.core.database import AsyncSessionLocal
from src.models.users import User
from sqlalchemy import select

async def verify():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username.in_(['thesobirov', 'thesob1rov'])))
        users = res.scalars().all()
        if not users:
            # Also check ID 5
            u5 = await session.get(User, 5)
            if u5: users.append(u5)
            
        print("--- Verification Results ---")
        for u in users:
            print(f"ID: {u.id}, Username: {u.username}, Role: {u.role}, UserType: {u.user_type}, TG: {u.telegram_id}")

if __name__ == "__main__":
    asyncio.run(verify())
