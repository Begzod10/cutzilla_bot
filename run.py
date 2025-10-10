from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
import asyncio
import os
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
import redis.asyncio as redis

# Routers

# Basic
from app.basic.handlers import router

# Barber
from app.barber.handlers import barber_router
from app.barber.photo_profile import barber_photo_router
from app.barber.resume import barber_resume
from app.barber.barber_service import barber_service
from app.barber.working_time import barber_working_time
from app.barber.barber_location import barber_location
from app.barber.working_days import barber_working_days_route
from app.barber.barber_requests import barber_requests
from app.barber.schedule.barber_schedule import barber_schedule
from app.barber.barber_scores import barber_scores

# Client
from app.client.client_location import client_basic
from app.client.barber_selection import client_barber_selection
from app.client.barber_profile import barber_profile
from app.client.client_request import client_request_router
from app.client.client_request_info import client_request_info_router
from app.client.client_request_history import client_request_history_router
from app.client.client_barber_list import client_barber_list_router

load_dotenv()

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("Missing bot TOKEN in environment variables.")

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB_BOT', '3')
REDIS_DB_APP = os.getenv('REDIS_DB_APP', '4')


async def main():
    bot = Bot(token=TOKEN)

    # ✅ Aiogram FSM Storage (independent from our redis client)
    storage = RedisStorage.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        key_builder=DefaultKeyBuilder(with_bot_id=True)  # ensures unique keys
    )
    dp = Dispatcher(storage=storage)

    # ✅ Our shared redis pool for business logic
    redis_pool = redis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_APP}",
        decode_responses=True
    )
    bot.redis = redis_pool  # attach for use inside handlers

    # Routers
    dp.include_router(router)
    dp.include_router(barber_router)
    dp.include_router(barber_photo_router)
    dp.include_router(barber_resume)
    dp.include_router(barber_service)
    dp.include_router(barber_working_time)
    dp.include_router(barber_location)
    dp.include_router(barber_working_days_route)
    dp.include_router(barber_requests)
    dp.include_router(barber_schedule)
    dp.include_router(barber_scores)

    dp.include_router(client_basic)
    dp.include_router(client_barber_selection)
    dp.include_router(barber_profile)
    dp.include_router(client_request_router)
    dp.include_router(client_request_info_router)
    dp.include_router(client_request_history_router)
    dp.include_router(client_barber_list_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")
