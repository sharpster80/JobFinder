from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ScrapeRun
from app.scrapers import ALL_SCRAPERS

router = APIRouter()

@router.get("")
def list_scrape_runs(db: Session = Depends(get_db)):
    runs = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(50).all()
    return [
        {"id": str(r.id), "source": r.source,
         "started_at": r.started_at.isoformat() + "Z",  # Append Z to indicate UTC
         "finished_at": r.finished_at.isoformat() + "Z" if r.finished_at else None,
         "jobs_found": r.jobs_found, "jobs_new": r.jobs_new, "error": r.error}
        for r in runs
    ]

@router.post("/trigger")
def trigger_scrape(background_tasks: BackgroundTasks, source: str | None = None):
    """Trigger an on-demand scrape. If source is None, runs all scrapers."""
    from app.workers.tasks import scrape_all, scrape_source
    if source:
        scrape_source.delay(source)
    else:
        scrape_all.delay()
    return {"status": "queued", "source": source or "all"}

@router.get("/sources")
def list_sources():
    return [{"name": s.source_name} for s in ALL_SCRAPERS]
