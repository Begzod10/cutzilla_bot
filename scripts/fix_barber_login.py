import asyncio
from src.core.database import AsyncSessionLocal
from sqlalchemy import select, update, func
from src.models.users import User

async def fix_login():
    async with AsyncSessionLocal() as session:
        # Search case-insensitively
        res = await session.execute(
            select(User).where(func.lower(User.username) == 'thesob1rov')
        )
        user = res.scalar_one_or_none()
        
        if user:
            print(f"Found user: {user.username} (ID: {user.id}). Clearing password...")
            async with session.begin():
                user.password = None
            await session.commit()
            print("Password cleared successfully.")
        else:
            print("User 'thesob1rov' not found case-insensitively.")
            # List all users to help debug
            res = await session.execute(select(User))
            users = res.scalars().all()
            print("\nAll users in DB:")
            for u in users:
                print(f"- '{u.username}' (ID: {u.id}, Role: {u.role}, TG: {u.telegram_id})")

if __name__ == "__main__":
    asyncio.run(fix_login())
