from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "jobfinder",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "scrape-all-every-6-hours": {
        "task": "app.workers.tasks.scrape_all",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "send-daily-digest": {
        "task": "app.workers.tasks.send_daily_digest",
        "schedule": crontab(minute=0, hour=str(settings.digest_hour)),
    },
}

celery_app.conf.timezone = "America/New_York"
