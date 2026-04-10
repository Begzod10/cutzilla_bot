import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.users import User
from src.models.barber import Barber, BarberWorkingDays, BarberService
from src.models.service import Service
from datetime import time

async def fix_database():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. User
            res = await session.execute(select(User).where(User.platform_login == 'thesob1rov'))
            user = res.scalar_one_or_none()
            if not user:
                res = await session.execute(select(User).order_by(User.id.desc()).limit(1))
                user = res.scalar_one_or_none()
            
            if not user:
                print("Xatolik: Foydalanuvchi topilmadi!")
                return

            print(f"DEBUG: Foydalanuvchi topildi: {user.platform_login} (ID: {user.id})")
            user.role = 'barber'

            # 2. Barber
            res = await session.execute(select(Barber).where(Barber.user_id == user.id))
            barber = res.scalar_one_or_none()
            if not barber:
                barber = Barber(user_id=user.id, login='thesob1rov', start_time=time(9,0), end_time=time(20,0))
                session.add(barber)
                await session.flush()
            
            # 3. Service (Main Category)
            res = await session.execute(select(Service).where(Service.name_uz == "Soch olish"))
            svc = res.scalar_one_or_none()
            if not svc:
                svc = Service(name_uz="Soch olish", name_ru="Стрижка")
                session.add(svc)
                await session.flush()
            
            # 4. Link Barber to Service
            res = await session.execute(select(BarberService).where(BarberService.barber_id == barber.id))
            bs_list = res.scalars().all()
            
            if not bs_list:
                session.add(BarberService(
                    barber_id=barber.id,
                    service_id=svc.id,
                    price=50000,
                    duration=30,
                    is_active=True
                ))
                print("DEBUG: Yangi xizmat bog'landi.")
            else:
                for b in bs_list:
                    b.price = 50000
                    b.duration = 30
                    b.is_active = True
                print("DEBUG: Mavjud xizmatlar yangilandi.")

            # 5. Seed days
            res = await session.execute(select(BarberWorkingDays).where(BarberWorkingDays.barber_id == barber.id))
            if not res.scalars().all():
                for d in ['Dushanba','Seshanba','Chorshanba','Payshanba','Juma','Shanba','Yakshanba']:
                    session.add(BarberWorkingDays(barber_id=barber.id, name_uz=d, name_ru=d, is_working=True))
                print("DEBUG: Ish kunlari tiklandi.")

            print("MUVAFFAQIYAT: Hammasi soatday sozlandi!")

if __name__ == "__main__":
    asyncio.run(fix_database())
