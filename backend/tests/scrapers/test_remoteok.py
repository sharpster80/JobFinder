import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.base import ScrapedJob

SAMPLE_RESPONSE = [
    {"legal": "ignore this first item"},
    {
        "id": "123",
        "position": "Staff Software Engineer",
        "company": "Acme Inc",
        "location": "Worldwide",
        "tags": ["python", "django", "postgres"],
        "description": "We are looking for a Staff Engineer",
        "date": "2026-02-10T12:00:00Z",
        "url": "https://remoteok.com/jobs/123",
        "salary_min": 130000,
        "salary_max": 160000,
    }
]

def test_scraper_returns_scraped_jobs():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: SAMPLE_RESPONSE
        )
        scraper = RemoteOKScraper()
        jobs = scraper.scrape()
    assert len(jobs) == 1
    assert isinstance(jobs[0], ScrapedJob)

def test_scraper_maps_fields_correctly():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: SAMPLE_RESPONSE
        )
        scraper = RemoteOKScraper()
        job = scraper.scrape()[0]
    assert job.source == "remoteok"
    assert job.external_id == "123"
    assert job.title == "Staff Software Engineer"
    assert job.company == "Acme Inc"
    assert job.is_remote is True
    assert "python" in job.tech_tags
    assert job.salary_min == 130000

def test_scraper_skips_legal_header():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: SAMPLE_RESPONSE
        )
        scraper = RemoteOKScraper()
        jobs = scraper.scrape()
    # Only 1 real job, legal header skipped
    assert len(jobs) == 1

def test_scraper_handles_missing_salary():
    no_salary = [{**SAMPLE_RESPONSE[1], "salary_min": None, "salary_max": None}]
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"legal": "skip"}, *no_salary]
        )
        scraper = RemoteOKScraper()
        job = scraper.scrape()[0]
    assert job.salary_min is None
    assert job.salary_max is None
