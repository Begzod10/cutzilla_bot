# app/core/redis.py
import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB_BOT', '3')

redis_client = redis.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    decode_responses=True
)
