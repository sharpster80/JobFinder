from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.notification import PushSubscription

router = APIRouter()

class PushSubscriptionCreate(BaseModel):
    endpoint: str
    subscription_json: dict

@router.post("/subscribe")
def subscribe_push(data: PushSubscriptionCreate, db: Session = Depends(get_db)):
    existing = db.query(PushSubscription).filter_by(endpoint=data.endpoint).first()
    if not existing:
        sub = PushSubscription(endpoint=data.endpoint, subscription_json=data.subscription_json)
        db.add(sub)
        db.commit()
    return {"status": "subscribed"}

@router.delete("/subscribe")
def unsubscribe_push(endpoint: str, db: Session = Depends(get_db)):
    sub = db.query(PushSubscription).filter_by(endpoint=endpoint).first()
    if sub:
        db.delete(sub)
        db.commit()
    return {"status": "unsubscribed"}
