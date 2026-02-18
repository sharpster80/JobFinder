import uuid
from typing import Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, JobMatch

router = APIRouter()

@router.get("")
def list_jobs(
    status: str | None = Query(None),
    min_score: int = Query(0),
    criteria_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Job, JobMatch).join(JobMatch, Job.id == JobMatch.job_id)
    if status:
        query = query.filter(JobMatch.status == status)
    if min_score:
        query = query.filter(JobMatch.match_score >= min_score)
    if criteria_id:
        query = query.filter(JobMatch.criteria_id == criteria_id)

    results = []
    for job, match in query.order_by(JobMatch.match_score.desc()).limit(200).all():
        results.append({
            "id": str(job.id),
            "match_id": str(match.id),
            "source": job.source,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "is_remote": job.is_remote,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "url": job.url,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
            "match_score": match.match_score,
            "status": match.status,
        })
    return results

@router.patch("/{match_id}/status")
def update_job_status(
    match_id: uuid.UUID,
    status: Literal["new", "reviewed", "saved", "rejected", "applied"],
    db: Session = Depends(get_db),
):
    match = db.query(JobMatch).filter_by(id=match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    match.status = status
    db.commit()
    return {"id": str(match_id), "status": status}
