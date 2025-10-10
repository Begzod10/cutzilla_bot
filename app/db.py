import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
load_dotenv()

raw_url = os.getenv("SQLALCHEMY_DATABASE_URI", "")
# Convert sync → async only if needed
if raw_url.startswith("postgresql://"):
    DATABASE_URL = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_url  # already async or custom

# Tune your engine
async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    # ⚠️ If you're on SQLAlchemy 2.x, drop future=True
    # future=True,  # keep only if you're on SQLAlchemy 1.4.x
    pool_size=10,
    max_overflow=20,
    pool_timeout=5,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            # asyncpg expects strings; value is in milliseconds
            "statement_timeout": "3000",
            # "idle_in_transaction_session_timeout": "60000",
            # "lock_timeout": "3000",
        }
    },
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)

Base = declarative_base()
