import asyncio
import asyncpg
from src.core.config import settings

async def main():
    print(f"Connecting to: postgresql://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}")
    try:
        # Connect to 'postgres' db first to list databases
        conn = await asyncpg.connect(user=settings.DB_USER, password=settings.DB_PASSWORD,
                                     database='postgres', host=settings.DB_HOST, port=settings.DB_PORT)
        dbs = await conn.fetch('SELECT datname FROM pg_database WHERE datistemplate = false;')
        db_names = [d['datname'] for d in dbs]
        print("Mavjud bazalar ro'yxati:", db_names)
        
        if settings.DB_NAME in db_names:
            print(f"Baza '{settings.DB_NAME}' topildi! Endi shunga ulanishga harakat qilamiz...")
            await conn.close()
            # Try connecting directly
            conn2 = await asyncpg.connect(user=settings.DB_USER, password=settings.DB_PASSWORD,
                                         database=settings.DB_NAME, host=settings.DB_HOST, port=settings.DB_PORT)
            print("Muvaffaqiyatli ulandik!")
            await conn2.close()
        else:
            print(f"XATO: '{settings.DB_NAME}' nomli baza bu portdagi ({settings.DB_PORT}) PostgreSQL ichidan topilmadi.")
            
    except Exception as e:
        print("Xatolik yuz berdi:", e)

asyncio.run(main())
