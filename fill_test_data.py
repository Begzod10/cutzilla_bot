import asyncio
from src.core.database import AsyncSessionLocal
from src.models import Country, Region, City, Service, User, Barber
from sqlalchemy import select

async def fill_test_data():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Create Country
            country = (await session.execute(select(Country).limit(1))).scalar_one_or_none()
            if not country:
                country = Country(name_uz="O'zbekiston", name_ru="Узбекистан", name_en="Uzbekistan")
                session.add(country)
                await session.flush()
            
            # 2. Create Region
            region = (await session.execute(select(Region).limit(1))).scalar_one_or_none()
            if not region:
                region = Region(name_uz="Toshkent shahri", name_ru="город Ташкент", country_id=country.id)
                session.add(region)
                await session.flush()
            
            # 3. Create City
            city = (await session.execute(select(City).limit(1))).scalar_one_or_none()
            if not city:
                city = City(name_uz="Toshkent", name_ru="Ташкент", region_id=region.id, country_id=country.id)
                session.add(city)
                await session.flush()

            # 4. Create a Sample Service
            service = (await session.execute(select(Service).limit(1))).scalar_one_or_none()
            if not service:
                service = Service(
                    name_uz="Soch kesish (Classic)", 
                    name_ru="Стрижка (Классик)", 
                    description_uz="Eng mashhur xizmat"
                )
                session.add(service)
                await session.flush()

            # 5. Connect ALL existing users and barbers to this test city
            users = (await session.execute(select(User))).scalars().all()
            for u in users:
                u.city_id = city.id
                u.region_id = region.id
                u.country_id = country.id
            
            print(f"✅ Tayyor!")
            print(f"Country ID: {country.id}, Region ID: {region.id}, City ID: {city.id}")
            print(f"Barcha foydalanuvchilar ({len(users)} ta) Toshkentga ulandi.")

if __name__ == '__main__':
    asyncio.run(fill_test_data())
