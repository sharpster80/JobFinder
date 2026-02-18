import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import SearchCriteria

router = APIRouter()

class CriteriaCreate(BaseModel):
    name: str
    titles: list[str] = []
    tech_stack: list[str] = []
    min_salary: int = 0
    exclude_keywords: list[str] = []
    company_blacklist: list[str] = []
    company_whitelist: list[str] = []
    is_active: bool = True

@router.get("")
def list_criteria(db: Session = Depends(get_db)):
    return [
        {"id": str(c.id), "name": c.name, "titles": c.titles,
         "tech_stack": c.tech_stack, "min_salary": c.min_salary,
         "exclude_keywords": c.exclude_keywords, "company_blacklist": c.company_blacklist,
         "company_whitelist": c.company_whitelist, "is_active": c.is_active}
        for c in db.query(SearchCriteria).all()
    ]

@router.post("", status_code=201)
def create_criteria(data: CriteriaCreate, db: Session = Depends(get_db)):
    c = SearchCriteria(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    # Re-run matching for all active jobs with new criteria
    from app.services.scrape_service import run_matching
    run_matching(db, new_only=False)
    return {"id": str(c.id), **data.model_dump()}

@router.put("/{criteria_id}")
def update_criteria(criteria_id: uuid.UUID, data: CriteriaCreate, db: Session = Depends(get_db)):
    from app.models import Job, JobMatch
    from app.matching import score_job
    from app.services.scrape_service import MATCH_THRESHOLD

    c = db.query(SearchCriteria).filter_by(id=criteria_id).first()
    if not c:
        raise HTTPException(status_code=404)
    for key, val in data.model_dump().items():
        setattr(c, key, val)
    db.commit()

    # Delete existing matches for this criteria
    db.query(JobMatch).filter_by(criteria_id=criteria_id).delete()
    db.commit()

    # Re-score all active jobs against updated criteria
    criteria_dict = {
        "titles": c.titles, "tech_stack": c.tech_stack,
        "min_salary": c.min_salary, "exclude_keywords": c.exclude_keywords,
        "company_blacklist": c.company_blacklist,
        "company_whitelist": c.company_whitelist,
    }

    for job in db.query(Job).filter_by(is_active=True).all():
        job_dict = {
            "title": job.title, "company": job.company,
            "description": job.description, "salary_min": job.salary_min,
            "salary_max": job.salary_max, "is_remote": job.is_remote,
            "tech_tags": job.tech_tags,
        }
        score = score_job(job_dict, criteria_dict)
        if score >= MATCH_THRESHOLD:
            match = JobMatch(job_id=job.id, criteria_id=criteria_id, match_score=score)
            db.add(match)

    db.commit()
    return {"id": str(criteria_id), **data.model_dump()}

@router.delete("/{criteria_id}", status_code=204)
def delete_criteria(criteria_id: uuid.UUID, db: Session = Depends(get_db)):
    c = db.query(SearchCriteria).filter_by(id=criteria_id).first()
    if not c:
        raise HTTPException(status_code=404)
    db.delete(c)
    db.commit()
