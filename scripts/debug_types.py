import asyncio
import datetime
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models import User, Barber

async def debug():
    # Check hasattr behavior
    t = datetime.time(10, 0)
    print(f"DEBUG: time object: {t}")
    print(f"DEBUG: hasattr(t, 'time'): {hasattr(t, 'time')}")
    
    dt = datetime.datetime.now()
    print(f"DEBUG: datetime object: {dt}")
    print(f"DEBUG: hasattr(dt, 'time'): {hasattr(dt, 'time')}")
    
    async with AsyncSessionLocal() as session:
        # Check users and barbers
        users = (await session.execute(select(User))).scalars().all()
        print(f"\nDEBUG: Total users: {len(users)}")
        for u in users:
            print(f"  User: id={u.id}, tg_id={u.telegram_id}, role={u.role}, login={u.platform_login}")
            
        barbers = (await session.execute(select(Barber))).scalars().all()
        print(f"\nDEBUG: Total barbers: {len(barbers)}")
        for b in barbers:
            print(f"  Barber: id={b.id}, user_id={b.user_id}, login={b.login}")

if __name__ == "__main__":
    asyncio.run(debug())
