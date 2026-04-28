import asyncio
from src.core.database import AsyncSessionLocal
from src.models.users import User
from src.models.barber import Barber
from sqlalchemy import select, or_

async def migrate_roles():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Find users who have role 'barber' but user_type is not 'barber' (including None)
            stmt = select(User).where(
                User.role == 'barber',
                or_(User.user_type != 'barber', User.user_type.is_(None))
            )
            res = await session.execute(stmt)
            users_to_fix = res.scalars().all()
            
            if not users_to_fix:
                print("No users found with inconsistent role/user_type.")
                return
            
            for user in users_to_fix:
                print(f"Fixing User ID {user.id} ({user.username}): setting user_type to 'barber'")
                user.user_type = 'barber'
                
                # Also ensure Barber record exists and is linked
                res_b = await session.execute(select(Barber).where(Barber.user_id == user.id))
                barber = res_b.scalar_one_or_none()
                if not barber:
                    print(f"Adding missing Barber record for User ID {user.id}")
                    barber = Barber(user_id=user.id, login=user.username or str(user.telegram_id))
                    session.add(barber)
                else:
                    print(f"Ensuring Barber record (ID: {barber.id}) is correctly linked to user ID {user.id}")
                    barber.user_id = user.id
            
            await session.commit()
            print("\nMigration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate_roles())
