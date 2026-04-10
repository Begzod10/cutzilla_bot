import asyncio
from src.core.database import AsyncSessionLocal
from sqlalchemy import select
from src.models.users import User
from src.models.barber import Barber

async def fix_thesobirov():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Try to find by username or id 5
            res = await session.execute(select(User).where(User.username == 'thesob1rov'))
            user = res.scalar_one_or_none()
            
            if not user:
                user = await session.get(User, 5)
            
            if user:
                print(f"User found: ID={user.id}, prev username='{user.username}'")
                user.username = 'thesob1rov'
                user.role = 'barber'
                user.user_type = 'barber'  # Added this for bot consistency
                user.password = None
                
                # Check barber record
                res_b = await session.execute(select(Barber).where(Barber.user_id == user.id))
                barber = res_b.scalar_one_or_none()
                if not barber:
                    barber = Barber(user_id=user.id, login='thesob1rov', per_hour=50000)
                    session.add(barber)
                    print("Barber record created.")
                else:
                    barber.login = 'thesob1rov'
                    barber.user_id = user.id # Ensure it's correctly linked
                    print("Barber record updated.")
                
                print(f"SUCCESS: User '{user.username}' is now a Barber (role and user_type updated).")
            else:
                print("User not found by ID 5 or 'thesob1rov'. Please run the bot /start first.")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(fix_thesobirov())
