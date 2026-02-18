import json
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from app.config import settings
from app.models.notification import PushSubscription, Notification

def send_push_notification(db: Session, job_id, title: str, body: str, url: str):
    if not settings.vapid_private_key:
        return

    subscriptions = db.query(PushSubscription).all()
    payload = json.dumps({"title": title, "body": body, "url": url})

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.subscription_json,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            notif = Notification(job_id=job_id, channel="browser")
            db.add(notif)
        except WebPushException as e:
            if "410" in str(e) or "404" in str(e):
                # Subscription expired, remove it
                db.delete(sub)
    db.commit()
