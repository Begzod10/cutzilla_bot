import asyncio
from src.core.database import AsyncSessionLocal
from src.models import User, Barber
from sqlalchemy import select

async def add_barber():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Create a NEW User for barber
            # check if it exists
            res = await session.execute(select(User).where(User.username == 'test_barber_sardor'))
            u = res.scalar_one_or_none()
            
            if not u:
                u = User(
                    username='test_barber_sardor', 
                    name='Sardor', 
                    role='barber', 
                    city_id=1, 
                    region_id=1, 
                    country_id=1, 
                    is_active=True
                )
                session.add(u)
                await session.flush()
                print(f"User created: {u.id}")
            
            # 2. Link to Barber table
            res_b = await session.execute(select(Barber).where(Barber.user_id == u.id))
            b = res_b.scalar_one_or_none()
            
            if not b:
                b = Barber(
                    user_id=u.id,
                    per_hour=50000,
                    score=5,
                    login='sardor_login'
                )
                session.add(b)
                print(f"Barber created for User: {u.id}")
            
            await session.commit()
            print("✅ Sardor ismli sartarosh (Test uchun) muvaffaqiyatli qo'shildi!")

if __name__ == '__main__':
    asyncio.run(add_barber())
