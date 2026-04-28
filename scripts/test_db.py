import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.users import User
from src.models.barber import Barber
from src.models.client import Client
from src.models.service import Service
from src.models.region import Region

async def test_models():
    models = [User, Barber, Client, Service, Region]
    async with AsyncSessionLocal() as session:
        for m in models:
            try:
                # Execute a simple select query
                result = await session.execute(select(m).limit(1))
                row = result.scalars().first()
                print(f"SUCCESS: {m.__tablename__} -> Found: {row.id if row else 'No rows'}")
            except Exception as e:
                print(f"ERROR: {m.__tablename__} -> {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_models())
