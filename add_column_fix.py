import asyncio
from sqlalchemy import text
from src.core.database import AsyncSessionLocal

async def add_column():
    async with AsyncSessionLocal() as session:
        try:
            # Check if column exists
            query = text("SELECT column_name FROM information_schema.columns WHERE table_name='barber_services' AND column_name='is_active'")
            res = await session.execute(query)
            if not res.scalar():
                print("Adding is_active column...")
                await session.execute(text("ALTER TABLE barber_services ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                await session.commit()
                print("✅ Column added successfully.")
            else:
                print("ℹ️ Column is_active already exists.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    asyncio.run(add_column())
