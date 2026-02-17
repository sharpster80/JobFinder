from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.services.scrape_service import run_scraper
from app.scrapers import ALL_SCRAPERS

@celery_app.task(name="app.workers.tasks.scrape_all")
def scrape_all():
    db = SessionLocal()
    try:
        results = []
        for scraper_class in ALL_SCRAPERS:
            run = run_scraper(db, scraper_class)
            results.append({
                "source": run.source,
                "found": run.jobs_found,
                "new": run.jobs_new,
                "error": run.error,
            })
        return results
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.scrape_source")
def scrape_source(source_name: str):
    """Scrape a single source by name. Used for manual refresh."""
    db = SessionLocal()
    try:
        scraper_class = next((s for s in ALL_SCRAPERS if s.source_name == source_name), None)
        if not scraper_class:
            return {"error": f"Unknown source: {source_name}"}
        run = run_scraper(db, scraper_class)
        return {"source": run.source, "found": run.jobs_found, "new": run.jobs_new, "error": run.error}
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.send_daily_digest")
def send_daily_digest():
    from app.notifications.email import send_digest
    db = SessionLocal()
    try:
        send_digest(db)
    finally:
        db.close()
