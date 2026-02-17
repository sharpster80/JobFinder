import pytest
from unittest.mock import patch, MagicMock
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.base import ScrapedJob

SAMPLE_HTML = """
<html><body>
<section class="jobs">
  <ul>
    <li>
      <a href="/jobs/123-staff-engineer-at-acme">
        <span class="company">Acme Corp</span>
        <span class="title">Staff Software Engineer</span>
        <span class="region">USA Only</span>
      </a>
    </li>
  </ul>
</section>
</body></html>
"""

def test_wwr_returns_jobs():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=SAMPLE_HTML)
        scraper = WeWorkRemotelyScraper()
        jobs = scraper.scrape()
    assert len(jobs) == 1
    assert isinstance(jobs[0], ScrapedJob)

def test_wwr_maps_source():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text=SAMPLE_HTML)
        jobs = WeWorkRemotelyScraper().scrape()
    assert jobs[0].source == "weworkremotely"
    assert jobs[0].is_remote is True
