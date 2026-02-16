# JobFinder Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal job search aggregator that scrapes multiple job boards, scores matches against configurable criteria, and surfaces results via a web dashboard with email and browser push notifications.

**Architecture:** Python FastAPI backend with Celery workers for scheduled scraping, Next.js frontend dashboard, PostgreSQL for storage, Redis as the Celery broker. All services run locally via Docker Compose.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis, Playwright, httpx, BeautifulSoup4, Next.js 14, Tailwind CSS, shadcn/ui, PostgreSQL 16, Resend (email), Web Push API, Docker Compose

---

## Task 1: Project Scaffolding

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `frontend/package.json` (via Next.js init)

**Step 1: Create directory structure**

```bash
mkdir -p backend/app/{api,models,scrapers,workers,notifications}
mkdir -p backend/tests/{api,scrapers,workers}
mkdir -p backend/alembic/versions
```

**Step 2: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
node_modules/
.next/
*.egg-info/
dist/
.DS_Store
postgres_data/
redis_data/
```

**Step 3: Create `.env.example`**

```
DATABASE_URL=postgresql://jobfinder:jobfinder@localhost:5432/jobfinder
REDIS_URL=redis://localhost:6379/0
RESEND_API_KEY=re_your_key_here
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_SUBJECT=mailto:you@example.com
NOTIFICATION_SCORE_THRESHOLD=90
DIGEST_HOUR=8
```

**Step 4: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: jobfinder
      POSTGRES_PASSWORD: jobfinder
      POSTGRES_DB: jobfinder
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app

  beat:
    build: ./backend
    command: celery -A app.workers.celery_app beat --loglevel=info
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    command: npm run dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
  redis_data:
```

**Step 5: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "jobfinder"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "psycopg2-binary>=2.9",
    "celery[redis]>=5.4",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "playwright>=1.49",
    "resend>=2.0",
    "pywebpush>=2.0",
    "python-dotenv>=1.0",
    "pydantic-settings>=2.6",
    "rapidfuzz>=3.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.35",
    "httpx>=0.27",
    "factory-boy>=3.3",
]
```

**Step 6: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install -e ".[dev]"
RUN playwright install chromium --with-deps

COPY . .
```

**Step 7: Bootstrap Next.js frontend**

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react
npx shadcn@latest init -y
npx shadcn@latest add table button badge card input select dialog toast
```

**Step 8: Commit**

```bash
git add .
git commit -m "feat: project scaffolding, docker-compose, frontend bootstrap"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/job.py`
- Create: `backend/app/models/criteria.py`
- Create: `backend/app/models/notification.py`
- Create: `backend/app/database.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

**Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    resend_api_key: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""
    notification_score_threshold: int = 90
    digest_hour: int = 8

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 3: Create `backend/app/models/job.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ARRAY, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tech_tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    matches: Mapped[list["JobMatch"]] = relationship("JobMatch", back_populates="job")

    __table_args__ = (
        {"schema": None},
    )

class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    criteria_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("search_criteria.id"))
    match_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="new")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="matches")
    criteria: Mapped["SearchCriteria"] = relationship("SearchCriteria", back_populates="matches")

class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=True)
```

**Step 4: Create `backend/app/models/criteria.py`**

```python
import uuid
from sqlalchemy import String, Integer, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class SearchCriteria(Base):
    __tablename__ = "search_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    titles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_salary: Mapped[int] = mapped_column(Integer, default=0)
    exclude_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company_blacklist: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company_whitelist: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    matches: Mapped[list["JobMatch"]] = relationship("JobMatch", back_populates="criteria")
```

**Step 5: Create `backend/app/models/notification.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    channel: Mapped[str] = mapped_column(String(20))
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    subscription_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 6: Create `backend/app/models/__init__.py`**

```python
from app.models.job import Job, JobMatch, ScrapeRun
from app.models.criteria import SearchCriteria
from app.models.notification import Notification, PushSubscription

__all__ = ["Job", "JobMatch", "ScrapeRun", "SearchCriteria", "Notification", "PushSubscription"]
```

**Step 7: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

**Step 8: Update `backend/alembic/env.py`** — replace the `target_metadata` line:

```python
# Add at top of file after imports:
import sys
sys.path.insert(0, "/app")
from app.database import Base
from app import models  # noqa: F401 — ensures models are registered

# Replace:
target_metadata = Base.metadata
```

**Step 9: Generate and run first migration**

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Expected: migration file created in `alembic/versions/`, tables created in DB.

**Step 10: Commit**

```bash
git add backend/
git commit -m "feat: database models and alembic migrations"
```

---

## Task 3: Matching Pipeline

> Build and test this before the scrapers — it's pure logic with no external dependencies.

**Files:**
- Create: `backend/app/matching.py`
- Create: `backend/tests/test_matching.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_matching.py
import pytest
from app.matching import score_job

def make_criteria(
    titles=None, tech_stack=None, min_salary=0,
    exclude_keywords=None, company_blacklist=None, company_whitelist=None
):
    return {
        "titles": titles or ["Staff Software Engineer"],
        "tech_stack": tech_stack or ["Python"],
        "min_salary": min_salary,
        "exclude_keywords": exclude_keywords or [],
        "company_blacklist": company_blacklist or [],
        "company_whitelist": company_whitelist or [],
    }

def make_job(**kwargs):
    defaults = {
        "title": "Staff Software Engineer",
        "company": "Acme Corp",
        "description": "We use Python and Kubernetes",
        "salary_min": 130000,
        "salary_max": 160000,
        "is_remote": True,
        "tech_tags": ["Python", "Kubernetes"],
    }
    return {**defaults, **kwargs}

def test_perfect_match_scores_high():
    score = score_job(make_job(), make_criteria())
    assert score >= 80

def test_title_mismatch_lowers_score():
    score = score_job(make_job(title="Junior Developer"), make_criteria())
    assert score < 40

def test_salary_below_minimum_returns_zero():
    score = score_job(make_job(salary_max=100000), make_criteria(min_salary=125000))
    assert score == 0

def test_blacklisted_company_returns_zero():
    score = score_job(make_job(company="Bad Corp"), make_criteria(company_blacklist=["Bad Corp"]))
    assert score == 0

def test_excluded_keyword_in_description_returns_zero():
    score = score_job(
        make_job(description="This role requires relocation to NYC"),
        make_criteria(exclude_keywords=["relocation"])
    )
    assert score == 0

def test_tech_stack_match_boosts_score():
    score_with_match = score_job(make_job(), make_criteria(tech_stack=["Python"]))
    score_without = score_job(make_job(tech_tags=[]), make_criteria(tech_stack=["Python"]))
    assert score_with_match > score_without

def test_whitelisted_company_boosts_score():
    score_whitelist = score_job(make_job(company="Dream Co"), make_criteria(company_whitelist=["Dream Co"]))
    score_normal = score_job(make_job(company="Dream Co"), make_criteria())
    assert score_whitelist > score_normal

def test_no_salary_listed_does_not_disqualify():
    score = score_job(make_job(salary_min=None, salary_max=None), make_criteria(min_salary=125000))
    assert score > 0

def test_non_remote_job_scores_lower():
    score_remote = score_job(make_job(is_remote=True), make_criteria())
    score_onsite = score_job(make_job(is_remote=False), make_criteria())
    assert score_remote > score_onsite
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_matching.py -v
```

Expected: `ImportError: cannot import name 'score_job' from 'app.matching'`

**Step 3: Implement `backend/app/matching.py`**

```python
from rapidfuzz import fuzz

WEIGHTS = {
    "title": 40,
    "tech_stack": 25,
    "remote": 15,
    "salary": 10,
    "whitelist": 10,
}

def score_job(job: dict, criteria: dict) -> int:
    """Score a job against criteria. Returns 0-100. Returns 0 if hard disqualifiers hit."""

    # Hard disqualifiers
    company = (job.get("company") or "").lower()
    description = (job.get("description") or "").lower()

    if criteria["company_blacklist"]:
        if any(b.lower() == company for b in criteria["company_blacklist"]):
            return 0

    if criteria["exclude_keywords"]:
        if any(kw.lower() in description for kw in criteria["exclude_keywords"]):
            return 0

    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if criteria["min_salary"] and salary_max is not None:
        if salary_max < criteria["min_salary"]:
            return 0

    score = 0

    # Title match (fuzzy)
    title = job.get("title") or ""
    title_scores = [fuzz.partial_ratio(t.lower(), title.lower()) for t in criteria["titles"]]
    best_title = max(title_scores) if title_scores else 0
    score += int((best_title / 100) * WEIGHTS["title"])

    # Tech stack match
    job_tags = {t.lower() for t in (job.get("tech_tags") or [])}
    if criteria["tech_stack"] and job_tags:
        matched = sum(1 for t in criteria["tech_stack"] if t.lower() in job_tags)
        ratio = matched / len(criteria["tech_stack"])
        score += int(ratio * WEIGHTS["tech_stack"])

    # Remote bonus
    if job.get("is_remote"):
        score += WEIGHTS["remote"]

    # Salary bonus (salary listed and above threshold)
    if salary_min and criteria["min_salary"] and salary_min >= criteria["min_salary"]:
        score += WEIGHTS["salary"]

    # Company whitelist bonus
    if criteria["company_whitelist"]:
        if any(w.lower() == company for w in criteria["company_whitelist"]):
            score += WEIGHTS["whitelist"]

    return min(score, 100)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_matching.py -v
```

Expected: all 9 tests PASS

**Step 5: Commit**

```bash
git add backend/app/matching.py backend/tests/test_matching.py
git commit -m "feat: job matching/scoring pipeline with tests"
```

---

## Task 4: Scraper Base + RemoteOK Scraper

**Files:**
- Create: `backend/app/scrapers/base.py`
- Create: `backend/app/scrapers/remoteok.py`
- Create: `backend/app/scrapers/__init__.py`
- Create: `backend/tests/scrapers/test_remoteok.py`

**Step 1: Create `backend/app/scrapers/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ScrapedJob:
    source: str
    external_id: str
    url: str
    title: str
    company: str
    location: str = ""
    is_remote: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    description: str = ""
    tech_tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None

class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    def scrape(self) -> list[ScrapedJob]:
        """Fetch and return a list of ScrapedJob objects."""
        ...
```

**Step 2: Write failing tests for RemoteOK scraper**

```python
# backend/tests/scrapers/test_remoteok.py
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
```

**Step 3: Run tests to verify they fail**

```bash
pytest tests/scrapers/test_remoteok.py -v
```

Expected: `ImportError` — module doesn't exist yet

**Step 4: Create `backend/app/scrapers/remoteok.py`**

```python
from datetime import datetime
import httpx
from app.scrapers.base import BaseScraper, ScrapedJob

REMOTEOK_API = "https://remoteok.com/api"

class RemoteOKScraper(BaseScraper):
    source_name = "remoteok"

    def scrape(self) -> list[ScrapedJob]:
        response = httpx.get(REMOTEOK_API, headers={"User-Agent": "JobFinder/1.0"}, timeout=30)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for item in data:
            if "id" not in item:
                continue  # skip legal header
            jobs.append(self._parse(item))
        return jobs

    def _parse(self, item: dict) -> ScrapedJob:
        posted_at = None
        if item.get("date"):
            try:
                posted_at = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
            except ValueError:
                pass

        return ScrapedJob(
            source=self.source_name,
            external_id=str(item["id"]),
            url=item.get("url", f"https://remoteok.com/jobs/{item['id']}"),
            title=item.get("position", ""),
            company=item.get("company", ""),
            location=item.get("location", "Worldwide"),
            is_remote=True,
            salary_min=item.get("salary_min") or None,
            salary_max=item.get("salary_max") or None,
            description=item.get("description", ""),
            tech_tags=item.get("tags", []),
            posted_at=posted_at,
        )
```

**Step 5: Create `backend/app/scrapers/__init__.py`**

```python
from app.scrapers.remoteok import RemoteOKScraper

ALL_SCRAPERS = [RemoteOKScraper]
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/scrapers/test_remoteok.py -v
```

Expected: all 4 tests PASS

**Step 7: Commit**

```bash
git add backend/app/scrapers/ backend/tests/scrapers/
git commit -m "feat: scraper base interface and RemoteOK scraper"
```

---

## Task 5: Simple HTML Scrapers (We Work Remotely + Dice)

**Files:**
- Create: `backend/app/scrapers/weworkremotely.py`
- Create: `backend/app/scrapers/dice.py`
- Create: `backend/tests/scrapers/test_weworkremotely.py`

**Step 1: Write failing test for WWR scraper**

```python
# backend/tests/scrapers/test_weworkremotely.py
import pytest
from unittest.mock import patch, MagicMock
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.base import ScrapedJob

SAMPLE_HTML = """
<html><body>
<section class="jobs">
  <ul>
    <li class="feature">
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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/scrapers/test_weworkremotely.py -v
```

Expected: `ImportError`

**Step 3: Create `backend/app/scrapers/weworkremotely.py`**

```python
import hashlib
import httpx
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob

WWR_URL = "https://weworkremotely.com/categories/remote-programming-jobs"

class WeWorkRemotelyScraper(BaseScraper):
    source_name = "weworkremotely"

    def scrape(self) -> list[ScrapedJob]:
        response = httpx.get(WWR_URL, headers={"User-Agent": "JobFinder/1.0"}, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for li in soup.select("section.jobs ul li"):
            if "feature" in li.get("class", []):
                continue
            a = li.find("a")
            if not a:
                continue

            company = a.find(class_="company")
            title = a.find(class_="title")
            region = a.find(class_="region")
            href = a.get("href", "")

            if not title:
                continue

            external_id = hashlib.md5(href.encode()).hexdigest()
            jobs.append(ScrapedJob(
                source=self.source_name,
                external_id=external_id,
                url=f"https://weworkremotely.com{href}",
                title=title.text.strip(),
                company=company.text.strip() if company else "",
                location=region.text.strip() if region else "Remote",
                is_remote=True,
            ))
        return jobs
```

**Step 4: Create `backend/app/scrapers/dice.py`**

```python
import httpx
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob

DICE_URL = "https://www.dice.com/jobs?q=staff+software+engineer&filters.workplaceTypes=Remote&pageSize=50"

class DiceScraper(BaseScraper):
    source_name = "dice"

    def scrape(self) -> list[ScrapedJob]:
        # Dice uses a JS-rendered search but has a JSON API endpoint
        api_url = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"
        params = {
            "q": "staff software engineer",
            "filters.workplaceTypes": "Remote",
            "pageSize": "50",
            "page": "1",
        }
        headers = {
            "User-Agent": "JobFinder/1.0",
            "x-api-key": "1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8",  # public API key from Dice JS
        }
        response = httpx.get(api_url, params=params, headers=headers, timeout=30)
        if response.status_code != 200:
            return []

        data = response.json()
        jobs = []
        for item in data.get("data", []):
            salary_min = salary_max = None
            if item.get("salary"):
                # Salary comes as "$100K - $150K" — extract if possible
                pass  # Leave for later, salary not always present

            jobs.append(ScrapedJob(
                source=self.source_name,
                external_id=item.get("id", ""),
                url=f"https://www.dice.com/job-detail/{item.get('id', '')}",
                title=item.get("title", ""),
                company=item.get("companyPageUrl", item.get("advertiser", {}).get("name", "")),
                location=item.get("location", ""),
                is_remote="remote" in item.get("workplaceTypes", "").lower(),
                description=item.get("descriptionFragment", ""),
                tech_tags=item.get("skills", []),
            ))
        return jobs
```

**Step 5: Update `backend/app/scrapers/__init__.py`**

```python
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.dice import DiceScraper

ALL_SCRAPERS = [RemoteOKScraper, WeWorkRemotelyScraper, DiceScraper]
```

**Step 6: Run all scraper tests**

```bash
pytest tests/scrapers/ -v
```

Expected: all tests PASS

**Step 7: Commit**

```bash
git add backend/app/scrapers/ backend/tests/scrapers/
git commit -m "feat: add WeWorkRemotely and Dice scrapers"
```

---

## Task 6: Playwright Scrapers (LinkedIn + Indeed)

**Files:**
- Create: `backend/app/scrapers/linkedin.py`
- Create: `backend/app/scrapers/indeed.py`

> Note: Playwright scrapers can't be unit tested with mocks easily. These are integration-tested manually by running them. Focus on correctness of parsing logic.

**Step 1: Create `backend/app/scrapers/linkedin.py`**

```python
import hashlib
import re
from playwright.sync_api import sync_playwright
from app.scrapers.base import BaseScraper, ScrapedJob

LINKEDIN_URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords=staff+software+engineer"
    "&f_WT=2"           # remote
    "&f_E=5"            # director / staff level
    "&sortBy=DD"        # date descending
)

class LinkedInScraper(BaseScraper):
    source_name = "linkedin"

    def scrape(self) -> list[ScrapedJob]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (compatible; JobFinder/1.0)"})

            page.goto(LINKEDIN_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            cards = page.query_selector_all("div.base-card")
            for card in cards[:25]:
                try:
                    title_el = card.query_selector(".base-search-card__title")
                    company_el = card.query_selector(".base-search-card__subtitle a")
                    location_el = card.query_selector(".job-search-card__location")
                    link_el = card.query_selector("a.base-card__full-link")

                    title = title_el.inner_text().strip() if title_el else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    location = location_el.inner_text().strip() if location_el else ""
                    url = link_el.get_attribute("href") if link_el else ""
                    external_id = hashlib.md5(url.encode()).hexdigest() if url else ""

                    if not title:
                        continue

                    jobs.append(ScrapedJob(
                        source=self.source_name,
                        external_id=external_id,
                        url=url,
                        title=title,
                        company=company,
                        location=location,
                        is_remote="remote" in location.lower(),
                    ))
                except Exception:
                    continue

            browser.close()
        return jobs
```

**Step 2: Create `backend/app/scrapers/indeed.py`**

```python
import hashlib
import httpx
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedJob

INDEED_URL = "https://www.indeed.com/jobs?q=staff+software+engineer&l=Remote&fromage=7"

class IndeedScraper(BaseScraper):
    source_name = "indeed"

    def scrape(self) -> list[ScrapedJob]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = httpx.get(INDEED_URL, headers=headers, timeout=30, follow_redirects=True)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = []

        for card in soup.select("div.job_seen_beacon"):
            try:
                title_el = card.select_one("h2.jobTitle a")
                company_el = card.select_one("[data-testid='company-name']")
                location_el = card.select_one("[data-testid='text-location']")
                salary_el = card.select_one("[data-testid='attribute_snippet_testid']")

                title = title_el.text.strip() if title_el else ""
                company = company_el.text.strip() if company_el else ""
                location = location_el.text.strip() if location_el else ""
                href = title_el.get("href", "") if title_el else ""
                url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                external_id = hashlib.md5(url.encode()).hexdigest()

                if not title:
                    continue

                jobs.append(ScrapedJob(
                    source=self.source_name,
                    external_id=external_id,
                    url=url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote="remote" in location.lower(),
                    description=salary_el.text.strip() if salary_el else "",
                ))
            except Exception:
                continue

        return jobs
```

**Step 3: Update `backend/app/scrapers/__init__.py`**

```python
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.weworkremotely import WeWorkRemotelyScraper
from app.scrapers.dice import DiceScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.indeed import IndeedScraper

ALL_SCRAPERS = [RemoteOKScraper, WeWorkRemotelyScraper, DiceScraper, LinkedInScraper, IndeedScraper]
```

**Step 4: Commit**

```bash
git add backend/app/scrapers/
git commit -m "feat: add LinkedIn and Indeed Playwright scrapers"
```

---

## Task 7: Scrape Service (DB Persistence + Matching)

**Files:**
- Create: `backend/app/services/scrape_service.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/tests/test_scrape_service.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_scrape_service.py
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
```

**Step 2: Create `conftest.py` for test DB session**

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models  # noqa

TEST_DB_URL = "sqlite:///./test.db"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

**Step 3: Run tests to verify they fail**

```bash
pytest tests/test_scrape_service.py -v
```

Expected: `ImportError`

**Step 4: Create `backend/app/services/scrape_service.py`**

```python
from datetime import datetime
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
            existing.scraped_at = datetime.utcnow()
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
    run = ScrapeRun(source=scraper_class.source_name, started_at=datetime.utcnow())
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
        run.finished_at = datetime.utcnow()
        db.commit()

    return run
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_scrape_service.py -v
```

Expected: all 3 tests PASS

**Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: scrape service with dedup, persistence, and matching"
```

---

## Task 8: Celery Workers

**Files:**
- Create: `backend/app/workers/celery_app.py`
- Create: `backend/app/workers/tasks.py`

**Step 1: Create `backend/app/workers/celery_app.py`**

```python
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "jobfinder",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "scrape-all-every-6-hours": {
        "task": "app.workers.tasks.scrape_all",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "send-daily-digest": {
        "task": "app.workers.tasks.send_daily_digest",
        "schedule": crontab(minute=0, hour=str(settings.digest_hour)),
    },
}

celery_app.conf.timezone = "America/New_York"
```

**Step 2: Create `backend/app/workers/tasks.py`**

```python
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
```

**Step 3: Commit**

```bash
git add backend/app/workers/
git commit -m "feat: celery workers and beat schedule"
```

---

## Task 9: FastAPI REST API

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/jobs.py`
- Create: `backend/app/api/criteria.py`
- Create: `backend/app/api/scrapes.py`
- Create: `backend/app/api/notifications.py`
- Create: `backend/tests/api/test_jobs_api.py`

**Step 1: Write failing API tests**

```python
# backend/tests/api/test_jobs_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_get_jobs_returns_list():
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_jobs_filters_by_status():
    response = client.get("/api/jobs?status=new")
    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/api/test_jobs_api.py -v
```

Expected: `ImportError` or connection error

**Step 3: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import jobs, criteria, scrapes, notifications

app = FastAPI(title="JobFinder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(criteria.router, prefix="/api/criteria", tags=["criteria"])
app.include_router(scrapes.router, prefix="/api/scrapes", tags=["scrapes"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 4: Create `backend/app/api/jobs.py`**

```python
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, Query
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Match not found")
    match.status = status
    db.commit()
    return {"id": str(match_id), "status": status}
```

**Step 5: Create `backend/app/api/criteria.py`**

```python
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
    return {"id": str(c.id), **data.model_dump()}

@router.put("/{criteria_id}")
def update_criteria(criteria_id: uuid.UUID, data: CriteriaCreate, db: Session = Depends(get_db)):
    c = db.query(SearchCriteria).filter_by(id=criteria_id).first()
    if not c:
        raise HTTPException(status_code=404)
    for key, val in data.model_dump().items():
        setattr(c, key, val)
    db.commit()
    return {"id": str(criteria_id), **data.model_dump()}

@router.delete("/{criteria_id}", status_code=204)
def delete_criteria(criteria_id: uuid.UUID, db: Session = Depends(get_db)):
    c = db.query(SearchCriteria).filter_by(id=criteria_id).first()
    if not c:
        raise HTTPException(status_code=404)
    db.delete(c)
    db.commit()
```

**Step 6: Create `backend/app/api/scrapes.py`**

```python
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
        {"id": str(r.id), "source": r.source, "started_at": r.started_at.isoformat(),
         "finished_at": r.finished_at.isoformat() if r.finished_at else None,
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
```

**Step 7: Create `backend/app/api/notifications.py`**

```python
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
```

**Step 8: Run API tests**

```bash
pytest tests/api/ -v
```

Expected: all tests PASS

**Step 9: Commit**

```bash
git add backend/app/main.py backend/app/api/ backend/tests/api/
git commit -m "feat: FastAPI REST endpoints for jobs, criteria, scrapes, notifications"
```

---

## Task 10: Email Notifications

**Files:**
- Create: `backend/app/notifications/email.py`
- Create: `backend/app/notifications/__init__.py`
- Create: `backend/tests/test_email_notifications.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_email_notifications.py
import pytest
from unittest.mock import patch, MagicMock
from app.notifications.email import format_digest_html, should_send_immediate

def test_format_digest_html_contains_job_title():
    jobs = [{"title": "Staff Engineer", "company": "Acme", "match_score": 85,
             "salary_min": 130000, "salary_max": 160000, "url": "https://example.com"}]
    html = format_digest_html(jobs)
    assert "Staff Engineer" in html
    assert "Acme" in html

def test_format_digest_html_empty_returns_string():
    html = format_digest_html([])
    assert isinstance(html, str)

def test_should_send_immediate_above_threshold():
    assert should_send_immediate(95, threshold=90) is True

def test_should_send_immediate_below_threshold():
    assert should_send_immediate(85, threshold=90) is False
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_email_notifications.py -v
```

**Step 3: Create `backend/app/notifications/email.py`**

```python
import resend
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Job, JobMatch, Notification

def format_digest_html(jobs: list[dict]) -> str:
    if not jobs:
        return "<p>No new matches in the past 24 hours.</p>"

    rows = ""
    for job in sorted(jobs, key=lambda j: j["match_score"], reverse=True):
        salary = ""
        if job.get("salary_min"):
            salary = f"${job['salary_min']//1000}K"
            if job.get("salary_max"):
                salary += f" – ${job['salary_max']//1000}K"

        rows += f"""
        <tr>
          <td><a href="{job['url']}">{job['title']}</a></td>
          <td>{job['company']}</td>
          <td>{salary}</td>
          <td>{job['match_score']}</td>
        </tr>"""

    return f"""
    <html><body>
    <h2>JobFinder Daily Digest — {datetime.now().strftime('%B %d, %Y')}</h2>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead><tr><th>Title</th><th>Company</th><th>Salary</th><th>Score</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </body></html>
    """

def should_send_immediate(score: int, threshold: int = None) -> bool:
    threshold = threshold or settings.notification_score_threshold
    return score >= threshold

def send_digest(db: Session, to_email: str = None):
    if not settings.resend_api_key:
        return

    since = datetime.utcnow() - timedelta(hours=24)
    results = (
        db.query(Job, JobMatch)
        .join(JobMatch, Job.id == JobMatch.job_id)
        .filter(JobMatch.status == "new")
        .filter(Job.scraped_at >= since)
        .order_by(JobMatch.match_score.desc())
        .limit(50)
        .all()
    )

    if not results:
        return

    jobs_data = [
        {"title": j.title, "company": j.company, "url": j.url,
         "salary_min": j.salary_min, "salary_max": j.salary_max,
         "match_score": m.match_score}
        for j, m in results
    ]

    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": "JobFinder <notifications@yourdomain.com>",
        "to": to_email or "you@example.com",
        "subject": f"JobFinder Digest — {len(jobs_data)} new matches",
        "html": format_digest_html(jobs_data),
    })

    for _, match in results:
        notif = Notification(job_id=match.job_id, channel="email")
        db.add(notif)
    db.commit()
```

**Step 4: Run tests**

```bash
pytest tests/test_email_notifications.py -v
```

Expected: all 4 tests PASS

**Step 5: Commit**

```bash
git add backend/app/notifications/ backend/tests/test_email_notifications.py
git commit -m "feat: email digest notifications via Resend"
```

---

## Task 11: Browser Push Notifications

**Files:**
- Create: `backend/app/notifications/push.py`

**Step 1: Create `backend/app/notifications/push.py`**

```python
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
```

**Step 2: Wire push notifications into `run_matching` in scrape_service.py**

In `backend/app/services/scrape_service.py`, after creating a high-score match, send a push:

```python
# Add after the match insert inside run_matching():
if score >= settings.notification_score_threshold:
    from app.notifications.push import send_push_notification
    send_push_notification(
        db, job.id,
        title=f"New match: {job.title}",
        body=f"{job.company} — Score: {score}",
        url=job.url,
    )
```

**Step 3: Add VAPID key generation instructions to README**

```bash
# Generate VAPID keys (run once):
python -c "from pywebpush import Vapid; v = Vapid(); v.generate_keys(); print('PUBLIC:', v.public_key); print('PRIVATE:', v.private_key)"
```

Copy keys into `.env`.

**Step 4: Commit**

```bash
git add backend/app/notifications/ backend/app/services/scrape_service.py
git commit -m "feat: browser push notifications via Web Push API"
```

---

## Task 12: Next.js Frontend — Job Board

**Files:**
- Modify: `frontend/app/page.tsx`
- Create: `frontend/app/components/JobTable.tsx`
- Create: `frontend/app/components/FilterBar.tsx`
- Create: `frontend/lib/api.ts`

**Step 1: Create `frontend/lib/api.ts`**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getJobs(params: {
  status?: string;
  min_score?: number;
  criteria_id?: string;
} = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.min_score) query.set("min_score", String(params.min_score));
  if (params.criteria_id) query.set("criteria_id", params.criteria_id);
  const res = await fetch(`${API_URL}/api/jobs?${query}`, { cache: "no-store" });
  return res.json();
}

export async function updateJobStatus(matchId: string, status: string) {
  const res = await fetch(`${API_URL}/api/jobs/${matchId}/status?status=${status}`, {
    method: "PATCH",
  });
  return res.json();
}

export async function getCriteria() {
  const res = await fetch(`${API_URL}/api/criteria`, { cache: "no-store" });
  return res.json();
}

export async function triggerScrape(source?: string) {
  const query = source ? `?source=${source}` : "";
  const res = await fetch(`${API_URL}/api/scrapes/trigger${query}`, { method: "POST" });
  return res.json();
}

export async function getScrapeRuns() {
  const res = await fetch(`${API_URL}/api/scrapes`, { cache: "no-store" });
  return res.json();
}
```

**Step 2: Create `frontend/app/components/JobTable.tsx`**

```tsx
"use client";
import { useState } from "react";
import { updateJobStatus } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Job = {
  id: string; match_id: string; title: string; company: string;
  source: string; salary_min: number | null; salary_max: number | null;
  match_score: number; status: string; url: string; posted_at: string | null;
  is_remote: boolean;
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  saved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  applied: "bg-purple-100 text-purple-800",
  reviewed: "bg-gray-100 text-gray-800",
};

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return "—";
  if (min && max) return `$${Math.round(min / 1000)}K – $${Math.round(max / 1000)}K`;
  if (min) return `$${Math.round(min / 1000)}K+`;
  return `Up to $${Math.round((max as number) / 1000)}K`;
}

export default function JobTable({ initialJobs }: { initialJobs: Job[] }) {
  const [jobs, setJobs] = useState(initialJobs);

  async function changeStatus(matchId: string, status: string) {
    await updateJobStatus(matchId, status);
    setJobs(jobs.map(j => j.match_id === matchId ? { ...j, status } : j));
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            <th className="px-4 py-3 text-left">Title</th>
            <th className="px-4 py-3 text-left">Company</th>
            <th className="px-4 py-3 text-left">Source</th>
            <th className="px-4 py-3 text-left">Salary</th>
            <th className="px-4 py-3 text-center">Score</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs.map(job => (
            <tr key={job.match_id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <a href={job.url} target="_blank" className="font-medium text-blue-600 hover:underline">
                  {job.title}
                </a>
              </td>
              <td className="px-4 py-3 text-gray-700">{job.company}</td>
              <td className="px-4 py-3">
                <Badge variant="outline">{job.source}</Badge>
              </td>
              <td className="px-4 py-3 text-gray-700">{formatSalary(job.salary_min, job.salary_max)}</td>
              <td className="px-4 py-3 text-center">
                <span className={`font-bold ${job.match_score >= 80 ? "text-green-600" : job.match_score >= 60 ? "text-yellow-600" : "text-gray-500"}`}>
                  {job.match_score}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[job.status] || ""}`}>
                  {job.status}
                </span>
              </td>
              <td className="px-4 py-3 flex gap-1">
                <Button size="sm" variant="outline" onClick={() => changeStatus(job.match_id, "saved")}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => changeStatus(job.match_id, "applied")}>Applied</Button>
                <Button size="sm" variant="ghost" onClick={() => changeStatus(job.match_id, "rejected")}>✕</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && (
        <p className="text-center py-12 text-gray-400">No matches yet. Trigger a scrape to get started.</p>
      )}
    </div>
  );
}
```

**Step 3: Update `frontend/app/page.tsx`**

```tsx
import { getJobs, getCriteria, triggerScrape } from "@/lib/api";
import JobTable from "./components/JobTable";
import { Button } from "@/components/ui/button";

export default async function Home({
  searchParams,
}: {
  searchParams: { status?: string; min_score?: string; criteria_id?: string };
}) {
  const jobs = await getJobs({
    status: searchParams.status,
    min_score: searchParams.min_score ? Number(searchParams.min_score) : undefined,
    criteria_id: searchParams.criteria_id,
  });

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Job Matches</h1>
        <form action={async () => { "use server"; await triggerScrape(); }}>
          <Button type="submit">Refresh Now</Button>
        </form>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        {["new", "saved", "applied", "rejected"].map(s => (
          <a key={s} href={`?status=${s}`}
            className="px-3 py-1 rounded-full text-sm border hover:bg-gray-100 capitalize">
            {s}
          </a>
        ))}
        <a href="/" className="px-3 py-1 rounded-full text-sm border hover:bg-gray-100">All</a>
      </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <JobTable initialJobs={jobs} />
      </div>
    </main>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: frontend job board with filtering and status actions"
```

---

## Task 13: Frontend — Criteria Manager

**Files:**
- Create: `frontend/app/criteria/page.tsx`
- Create: `frontend/app/criteria/CriteriaForm.tsx`
- Create: `frontend/app/components/Nav.tsx`

**Step 1: Create `frontend/app/components/Nav.tsx`**

```tsx
import Link from "next/link";

export default function Nav() {
  return (
    <nav className="border-b bg-white px-6 py-4 flex gap-6 items-center">
      <span className="font-bold text-lg">JobFinder</span>
      <Link href="/" className="text-sm text-gray-600 hover:text-black">Jobs</Link>
      <Link href="/criteria" className="text-sm text-gray-600 hover:text-black">Criteria</Link>
      <Link href="/settings" className="text-sm text-gray-600 hover:text-black">Settings</Link>
    </nav>
  );
}
```

**Step 2: Create `frontend/app/criteria/page.tsx`**

```tsx
import { getCriteria } from "@/lib/api";
import CriteriaForm from "./CriteriaForm";

export default async function CriteriaPage() {
  const criteria = await getCriteria();
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Search Criteria</h1>
      <CriteriaForm existing={criteria} />
    </main>
  );
}
```

**Step 3: Create `frontend/app/criteria/CriteriaForm.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Criteria = {
  id?: string; name: string; titles: string[]; tech_stack: string[];
  min_salary: number; exclude_keywords: string[]; company_blacklist: string[];
  company_whitelist: string[]; is_active: boolean;
};

const empty: Criteria = {
  name: "", titles: [], tech_stack: [], min_salary: 125000,
  exclude_keywords: [], company_blacklist: [], company_whitelist: [], is_active: true,
};

function TagInput({ label, value, onChange }: { label: string; value: string[]; onChange: (v: string[]) => void }) {
  const [input, setInput] = useState("");
  return (
    <div>
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex gap-2 mt-1">
        <Input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && input.trim()) { onChange([...value, input.trim()]); setInput(""); e.preventDefault(); }}}
          placeholder="Type and press Enter" />
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {value.map(v => (
          <span key={v} className="bg-gray-100 px-2 py-0.5 rounded text-sm flex items-center gap-1">
            {v}
            <button onClick={() => onChange(value.filter(x => x !== v))} className="text-gray-400 hover:text-red-500">×</button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function CriteriaForm({ existing }: { existing: Criteria[] }) {
  const [list, setList] = useState<Criteria[]>(existing);
  const [editing, setEditing] = useState<Criteria | null>(null);

  async function save(c: Criteria) {
    const method = c.id ? "PUT" : "POST";
    const url = c.id ? `${API_URL}/api/criteria/${c.id}` : `${API_URL}/api/criteria`;
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(c) });
    const saved = await res.json();
    if (c.id) setList(list.map(x => x.id === c.id ? saved : x));
    else setList([...list, saved]);
    setEditing(null);
  }

  async function remove(id: string) {
    await fetch(`${API_URL}/api/criteria/${id}`, { method: "DELETE" });
    setList(list.filter(x => x.id !== id));
  }

  const form = editing || empty;

  return (
    <div className="grid grid-cols-2 gap-8">
      <div>
        <h2 className="font-semibold mb-3">Active Criteria Sets</h2>
        {list.map(c => (
          <div key={c.id} className="border rounded p-3 mb-2 flex justify-between items-start">
            <div>
              <div className="font-medium">{c.name}</div>
              <div className="text-sm text-gray-500">{c.titles.join(", ")} · ${c.min_salary.toLocaleString()}+</div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setEditing(c)}>Edit</Button>
              <Button size="sm" variant="ghost" onClick={() => c.id && remove(c.id)}>Delete</Button>
            </div>
          </div>
        ))}
        <Button onClick={() => setEditing({...empty})} className="mt-2">+ New Criteria Set</Button>
      </div>

      {editing && (
        <div className="border rounded p-4">
          <h2 className="font-semibold mb-4">{editing.id ? "Edit" : "New"} Criteria Set</h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input value={form.name} onChange={e => setEditing({...form, name: e.target.value})} className="mt-1" />
            </div>
            <TagInput label="Target Titles" value={form.titles} onChange={v => setEditing({...form, titles: v})} />
            <TagInput label="Tech Stack" value={form.tech_stack} onChange={v => setEditing({...form, tech_stack: v})} />
            <div>
              <label className="text-sm font-medium">Min Salary ($)</label>
              <Input type="number" value={form.min_salary} onChange={e => setEditing({...form, min_salary: Number(e.target.value)})} className="mt-1" />
            </div>
            <TagInput label="Exclude Keywords" value={form.exclude_keywords} onChange={v => setEditing({...form, exclude_keywords: v})} />
            <TagInput label="Company Blacklist" value={form.company_blacklist} onChange={v => setEditing({...form, company_blacklist: v})} />
            <TagInput label="Company Whitelist" value={form.company_whitelist} onChange={v => setEditing({...form, company_whitelist: v})} />
            <div className="flex gap-2 pt-2">
              <Button onClick={() => save(form)}>Save</Button>
              <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/app/criteria/ frontend/app/components/Nav.tsx
git commit -m "feat: criteria manager UI"
```

---

## Task 14: Frontend — Settings & Scrape History

**Files:**
- Create: `frontend/app/settings/page.tsx`

**Step 1: Create `frontend/app/settings/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { getScrapeRuns } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [subscribed, setSubscribed] = useState(false);

  useEffect(() => {
    getScrapeRuns().then(setRuns);
  }, []);

  async function subscribePush() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      alert("Push notifications not supported in this browser.");
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidKey,
    });
    await fetch(`${API_URL}/api/notifications/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: sub.endpoint, subscription_json: sub.toJSON() }),
    });
    setSubscribed(true);
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <section className="mb-8">
        <h2 className="font-semibold mb-3">Browser Notifications</h2>
        {subscribed
          ? <p className="text-green-600 text-sm">✓ Subscribed to push notifications</p>
          : <button onClick={subscribePush} className="px-4 py-2 bg-blue-600 text-white rounded text-sm">
              Enable Push Notifications
            </button>
        }
      </section>

      <section>
        <h2 className="font-semibold mb-3">Scrape History</h2>
        <table className="w-full text-sm border rounded">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">Source</th>
              <th className="px-4 py-2 text-left">Time</th>
              <th className="px-4 py-2 text-right">Found</th>
              <th className="px-4 py-2 text-right">New</th>
              <th className="px-4 py-2 text-left">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {runs.map(r => (
              <tr key={r.id} className={r.error ? "bg-red-50" : ""}>
                <td className="px-4 py-2">{r.source}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(r.started_at).toLocaleString()}</td>
                <td className="px-4 py-2 text-right">{r.jobs_found}</td>
                <td className="px-4 py-2 text-right font-medium">{r.jobs_new}</td>
                <td className="px-4 py-2 text-red-500 text-xs">{r.error || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
```

**Step 2: Add service worker for push notifications**

Create `frontend/public/sw.js`:

```javascript
self.addEventListener("push", function(event) {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || "JobFinder", {
      body: data.body || "New job match!",
      icon: "/icon.png",
      data: { url: data.url },
    })
  );
});

self.addEventListener("notificationclick", function(event) {
  event.notification.close();
  if (event.notification.data?.url) {
    clients.openWindow(event.notification.data.url);
  }
});
```

**Step 3: Register service worker in `frontend/app/layout.tsx`**

Add to the `<body>` or a client component:

```tsx
// Add in a "use client" component:
useEffect(() => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
  }
}, []);
```

**Step 4: Commit**

```bash
git add frontend/app/settings/ frontend/public/sw.js
git commit -m "feat: settings page with push subscription and scrape history"
```

---

## Task 15: Add Nav to Layout + Final Wiring

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/notifications/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/services/__init__.py`

**Step 1: Update `frontend/app/layout.tsx` to include Nav**

```tsx
import Nav from "./components/Nav";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <Nav />
        {children}
      </body>
    </html>
  );
}
```

**Step 2: Create all empty `__init__.py` files**

```bash
touch backend/app/workers/__init__.py
touch backend/app/notifications/__init__.py
touch backend/app/api/__init__.py
touch backend/app/services/__init__.py
touch backend/tests/__init__.py
touch backend/tests/api/__init__.py
touch backend/tests/scrapers/__init__.py
```

**Step 3: Create root `README.md`**

```markdown
# JobFinder

Personal job search aggregator. Scrapes multiple job boards, scores matches against your criteria, and surfaces results via a dashboard.

## Quick Start

1. Copy `.env.example` to `.env` and fill in your values (at minimum: leave DB/Redis as-is for local dev)
2. `docker-compose up`
3. Open http://localhost:3000
4. Go to **Criteria** and create your first search criteria set
5. Click **Refresh Now** to run your first scrape

## Generating VAPID Keys (for push notifications)

```bash
python -c "from pywebpush import Vapid; v = Vapid(); v.generate_keys(); print('PUBLIC:', v.public_key); print('PRIVATE:', v.private_key)"
```

## Architecture

See `docs/plans/2026-02-16-jobfinder-design.md`
```

**Step 4: Run full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: complete JobFinder MVP — dashboard, scrapers, notifications, docker-compose"
```

**Step 6: Start the stack**

```bash
docker-compose up --build
```

Verify:
- http://localhost:3000 — frontend loads
- http://localhost:8000/health — returns `{"status": "ok"}`
- http://localhost:8000/docs — FastAPI interactive docs

---

## Summary

| Task | What it builds |
|---|---|
| 1 | Project scaffold, Docker Compose, Next.js bootstrap |
| 2 | PostgreSQL models and Alembic migrations |
| 3 | Matching/scoring pipeline (TDD) |
| 4 | RemoteOK scraper (TDD) |
| 5 | WeWorkRemotely + Dice scrapers |
| 6 | LinkedIn + Indeed Playwright scrapers |
| 7 | Scrape service: dedup, persistence, matching integration |
| 8 | Celery workers + Beat schedule |
| 9 | FastAPI REST API (all endpoints) |
| 10 | Email digest via Resend |
| 11 | Browser push notifications |
| 12 | Job Board frontend |
| 13 | Criteria Manager frontend |
| 14 | Settings + scrape history frontend |
| 15 | Nav, layout, final wiring, README |
