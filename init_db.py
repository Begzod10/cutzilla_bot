import asyncio
from src.core.database import engine, Base
from src.models import users, barber, client, service, region

async def init_models():
    async with engine.begin() as conn:
        print("Barcha jadvallarni o'chirish...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Tarkibiy jadvallar yaratilmoqda...")
        await conn.run_sync(Base.metadata.create_all)
        print("Barcha jadvallar yaratildi!")

if __name__ == "__main__":
    asyncio.run(init_models())
