# app/celery_app.py

import os
from celery import Celery
from dotenv import load_dotenv
from celery.schedules import crontab
from datetime import timedelta

load_dotenv()

celery = Celery(
    'my_tasks',
    broker=os.getenv('CELERY_BROKER_URL'),
    backend=os.getenv('CELERY_RESULT_BACKEND')
)

celery.conf.timezone = 'Asia/Tashkent'

celery.conf.beat_schedule = {
    'update-services-every-minute': {
        'task': 'app.tasks.update_services',
        # 'schedule': timedelta(hours=1),
        'schedule': crontab(minute='*'),
    },
    'create-barber-schedule-every-minute': {
        'task': 'app.tasks.create_barber_schedule',
        'schedule': crontab(minute=0, hour=12),
        # 'schedule': crontab(minute='*'),
    },
    "notify-upcoming-requests": {
        "task": "app.client.tasks.notify_upcoming_requests",
        "schedule": timedelta(minutes=90),
        # 'schedule': crontab(minute='*'),
    }
}

from app import tasks
