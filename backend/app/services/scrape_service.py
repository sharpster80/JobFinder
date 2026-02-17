from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Job, JobMatch, SearchCriteria, ScrapeRun
from app.scrapers.base import ScrapedJob
from app.matching import score_job

MATCH_THRESHOLD = 50

def save_jobs(db: Session, scraped_jobs: list[ScrapedJob]) -> int:
    """Persist scraped jobs. Returns count of new jobs inserted."""
    new_count = 0
    for sj in scraped_jobs:
        existing = db.query(Job).filter_by(source=sj.source, external_id=sj.external_id).first()
        if existing:
            existing.is_active = True
            existing.scraped_at = datetime.now(timezone.utc)
        else:
            job = Job(
                source=sj.source,
                external_id=sj.external_id,
                url=sj.url,
                title=sj.title,
                company=sj.company,
                location=sj.location,
                is_remote=sj.is_remote,
                salary_min=sj.salary_min,
                salary_max=sj.salary_max,
                description=sj.description,
                tech_tags=sj.tech_tags,
                posted_at=sj.posted_at,
            )
            db.add(job)
            new_count += 1
    db.commit()
    return new_count

def run_matching(db: Session, new_only: bool = True) -> int:
    """Score all unmatched jobs against active criteria. Returns count of matches created."""
    criteria_list = db.query(SearchCriteria).filter_by(is_active=True).all()
    if not criteria_list:
        return 0

    jobs_query = db.query(Job).filter_by(is_active=True)
    if new_only:
        matched_job_ids = {m.job_id for m in db.query(JobMatch.job_id).all()}
        jobs_query = jobs_query.filter(Job.id.not_in(matched_job_ids))

    match_count = 0
    for job in jobs_query.all():
        job_dict = {
            "title": job.title, "company": job.company,
            "description": job.description, "salary_min": job.salary_min,
            "salary_max": job.salary_max, "is_remote": job.is_remote,
            "tech_tags": job.tech_tags,
        }
        for criteria in criteria_list:
            criteria_dict = {
                "titles": criteria.titles, "tech_stack": criteria.tech_stack,
                "min_salary": criteria.min_salary,
                "exclude_keywords": criteria.exclude_keywords,
                "company_blacklist": criteria.company_blacklist,
                "company_whitelist": criteria.company_whitelist,
            }
            score = score_job(job_dict, criteria_dict)
            if score >= MATCH_THRESHOLD:
                match = JobMatch(job_id=job.id, criteria_id=criteria.id, match_score=score)
                db.add(match)
                match_count += 1
    db.commit()
    return match_count

def run_scraper(db: Session, scraper_class) -> ScrapeRun:
    """Run one scraper, save results, return ScrapeRun audit record."""
    run = ScrapeRun(source=scraper_class.source_name, started_at=datetime.now(timezone.utc))
    db.add(run)
    db.commit()

    try:
        scraper = scraper_class()
        jobs = scraper.scrape()
        run.jobs_found = len(jobs)
        run.jobs_new = save_jobs(db, jobs)
        run_matching(db)
    except Exception as e:
        run.error = str(e)
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

    return run
