import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.scrape_service import save_jobs, run_matching
from app.scrapers.base import ScrapedJob

def make_scraped_job(**kwargs):
    defaults = dict(
        source="remoteok", external_id="abc123", url="https://example.com/job/1",
        title="Staff Software Engineer", company="Acme", location="Remote",
        is_remote=True, salary_min=130000, salary_max=160000,
        description="Python Kubernetes role", tech_tags=["Python"], posted_at=None
    )
    return ScrapedJob(**{**defaults, **kwargs})

def test_save_jobs_inserts_new_job(db_session):
    jobs = [make_scraped_job()]
    new_count = save_jobs(db_session, jobs)
    assert new_count == 1

def test_save_jobs_deduplicates(db_session):
    jobs = [make_scraped_job()]
    save_jobs(db_session, jobs)
    new_count = save_jobs(db_session, jobs)  # second time, same job
    assert new_count == 0

def test_save_jobs_marks_active(db_session):
    from app.models import Job
    jobs = [make_scraped_job()]
    save_jobs(db_session, jobs)
    job = db_session.query(Job).first()
    assert job.is_active is True
