import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
from src.core.database import Base
# Barcha modellarni import qilish muhim, shunda Base.metadata ularni bilib oladi
from src.models import *

async def create_db():
    print("PostgreSQL-ga ulanib, baza yaratishga harakat qilinmoqda...")
    try:
        # Default postgres bazasiga ulanish
        conn = await asyncpg.connect(
            user=settings.DB_USER, 
            password=settings.DB_PASSWORD,
            database='template1', 
            host=settings.DB_HOST, 
            port=settings.DB_PORT
        )
        
        # Baza mavjudligini tekshirish
        dbs = await conn.fetch("SELECT datname FROM pg_database WHERE datname='cutzilla';")
        if not dbs:
            # cutzilla bazasini yaratish
            await conn.execute('CREATE DATABASE cutzilla')
            print("✅ 'cutzilla' ma'lumotlar bazasi mufaqqiyatli yaratildi!")
        else:
            print("✅ 'cutzilla' ma'lumotlar bazasi allaqachon mavjud.")
            
        await conn.close()
    except Exception as e:
        print(f"❌ Xato yuz berdi: {e}")
        print("Bunga sabab mahalliy PostgreSQL parolingiz 123 bo'lmasligi mumkin.")
        print(".env fayliga to'g'ri DB_PASSWORD yozib keyin qayta urinib ko'ring.")
        return

async def create_tables():
    print("Modellar bo'yicha jadvallarni (tables) yaratish...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Eski jadvallarni tozalab, yangidan yaratish (barcha yangi ustunlar bilan)
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Barcha jadvallar yaratildi!")

async def main():
    await create_db()
    # Baza yaratilgach yoki mavjud bo'lgach jadvallarni quramiz
    await create_tables()

if __name__ == "__main__":
    asyncio.run(main())
