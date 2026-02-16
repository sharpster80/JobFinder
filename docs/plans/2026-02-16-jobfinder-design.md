# JobFinder Design Document
**Date:** 2026-02-16
**Status:** Approved
**Deployment:** Local (Docker Compose)

---

## Problem

Finding remote software engineering work as a Staff Engineer requires monitoring multiple job boards (Indeed, LinkedIn, Dice, RemoteOK, etc.), company career pages, and ATS platforms (Workday, Greenhouse, Lever). The manual process is time-consuming and inconsistent. This tool automates discovery, filtering, and notification so relevant jobs surface without manual searching.

**Constraints:**
- Must support remote-only roles
- Must filter for $125K+ salary
- Based in Gettysburg, PA — remote work is required, not preferred
- Single user, personal tool, local deployment

---

## Architecture Overview

Five services orchestrated via Docker Compose:

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────┐  │
│  │  React   │   │ FastAPI  │   │ Celery Workers  │  │
│  │ Frontend │◄──│ Backend  │◄──│ (Scrapers)      │  │
│  │ (Next.js)│   │          │   │                 │  │
│  └──────────┘   └────┬─────┘   └────────┬────────┘  │
│                      │                  │            │
│                 ┌────▼──────────────────▼────┐       │
│                 │        PostgreSQL           │       │
│                 └────────────────────────────┘       │
│                      │                               │
│                 ┌────▼──────┐                        │
│                 │   Redis   │ (job queue + cache)    │
│                 └───────────┘                        │
└─────────────────────────────────────────────────────┘
         │ email via Resend API (external)
         │ browser push notifications (Web Push API)
```

| Service | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 14 + Tailwind + shadcn/ui | Dashboard UI |
| Backend | Python FastAPI | REST API + business logic |
| Worker | Celery + Celery Beat | Background scraping on schedule |
| Database | PostgreSQL | Persistent storage |
| Cache/Queue | Redis | Celery broker + dedup cache |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) + Tailwind CSS + shadcn/ui |
| Backend API | Python FastAPI |
| Background Jobs | Celery + Celery Beat |
| Message Broker | Redis |
| Database | PostgreSQL |
| Scraping (simple) | httpx + BeautifulSoup |
| Scraping (JS-heavy) | Playwright (headless Chromium) |
| Email | Resend API |
| Push Notifications | Web Push API |
| Dev/Deploy | Docker Compose |

---

## Data Model

### `jobs`
Canonical job posting record. One row per unique posting.

```sql
id              UUID PRIMARY KEY
source          TEXT        -- 'indeed', 'linkedin', 'remoteok', etc.
external_id     TEXT        -- source's own ID for deduplication
url             TEXT
title           TEXT
company         TEXT
location        TEXT
is_remote       BOOLEAN
salary_min      INTEGER
salary_max      INTEGER
description     TEXT
tech_tags       TEXT[]      -- extracted keywords
posted_at       TIMESTAMP
scraped_at      TIMESTAMP
is_active       BOOLEAN     -- false when job is no longer listed

UNIQUE(source, external_id)
```

### `job_matches`
Links jobs to search criteria with a computed score.

```sql
id              UUID PRIMARY KEY
job_id          UUID REFERENCES jobs(id)
criteria_id     UUID REFERENCES search_criteria(id)
match_score     INTEGER     -- 0-100
status          TEXT        -- 'new', 'reviewed', 'saved', 'rejected', 'applied'
reviewed_at     TIMESTAMP
```

### `search_criteria`
User-configurable filter sets. Multiple sets supported.

```sql
id                  UUID PRIMARY KEY
name                TEXT
titles              TEXT[]      -- target job titles (fuzzy matched)
tech_stack          TEXT[]      -- required/preferred technologies
min_salary          INTEGER
exclude_keywords    TEXT[]      -- keywords that disqualify a job
company_blacklist   TEXT[]
company_whitelist   TEXT[]
is_active           BOOLEAN
```

### `notifications`
Tracks sent notifications to prevent duplicates.

```sql
id          UUID PRIMARY KEY
job_id      UUID REFERENCES jobs(id)
channel     TEXT        -- 'email', 'browser'
sent_at     TIMESTAMP
```

### `scrape_runs`
Audit log for every scraper execution.

```sql
id          UUID PRIMARY KEY
source      TEXT
started_at  TIMESTAMP
finished_at TIMESTAMP
jobs_found  INTEGER
jobs_new    INTEGER
error       TEXT
```

---

## Scraper Architecture

### Scraper Types

**Simple scrapers** (httpx + BeautifulSoup) for sites with stable HTML or public APIs:
- RemoteOK — public JSON API, most reliable source
- We Work Remotely
- Dice
- ZipRecruiter

**Playwright scrapers** (headless Chromium) for JavaScript-rendered sites:
- LinkedIn (public job search pages, no login required)
- Indeed
- Workday, Greenhouse, Lever, iCIMS (company ATS platforms)

### Scheduling
- Celery Beat runs all active scrapers every 6 hours
- Manual "Refresh Now" button in the dashboard triggers an on-demand run

### Deduplication
Before inserting: check `(source, external_id)`. If exists, update `is_active` and skip. If new, insert and run matching pipeline.

### Matching Pipeline
After each scrape batch, for each new job:
1. Fuzzy-match title against `titles[]` in each active criteria set
2. Scan description for `tech_stack[]` keywords
3. Check salary range against `min_salary`
4. Check company against `company_blacklist` / `company_whitelist`
5. Compute `match_score` (0–100)
6. Insert into `job_matches` if score ≥ 50

### Known Limitations
LinkedIn and Indeed have ToS restrictions on scraping and actively rate-limit bots. Strategy: scrape public search result pages (no login), respect rate limits with delays, fall back to RSS feeds where available. This is a personal tool — low volume requests are unlikely to trigger blocks.

---

## Frontend Dashboard

Three views:

### 1. Job Board (home)
- Sortable/filterable table of matched jobs
- Columns: title, company, source, salary, match score, posted date, status
- Per-row actions: Save, Reject, Mark Applied, Open Original
- Filter bar: status, criteria set, minimum score
- "Refresh Now" button for on-demand scrape

### 2. Criteria Manager
- Create, edit, delete search criteria sets
- Fields: target titles, tech keywords, min salary, blacklist, whitelist
- Toggle criteria sets active/inactive

### 3. Settings / Notifications
- Email address for digests + notification threshold
- Browser push notification subscription toggle
- Scrape run history log for debugging

**No authentication** — personal tool, local deployment. HTTP Basic Auth can be added at the OS/network level if ever exposed externally.

---

## Notifications

### Email (Resend API)
- Daily digest at a configured time: all new matches from past 24 hours, sorted by score
- Immediate alert for matches scoring above configurable threshold (default: 90)
- HTML email: title, company, salary, score, direct link

### Browser Push (Web Push API)
- User subscribes once from the dashboard
- Backend stores push subscription in DB
- Celery worker sends push when high-score match arrives
- Works with browser open, even if tab is closed

---

## Deployment

Local Docker Compose. Single command: `docker-compose up`.

Services:
- `frontend` — Next.js, port 3000
- `api` — FastAPI, port 8000
- `worker` — Celery worker (no exposed port)
- `beat` — Celery Beat scheduler (no exposed port)
- `db` — PostgreSQL, port 5432 (local only)
- `redis` — Redis, port 6379 (local only)

Environment variables (`.env` file, not committed):
- `DATABASE_URL`
- `REDIS_URL`
- `RESEND_API_KEY`
- `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` (Web Push)

---

## Job Sources (Initial Set)

| Source | Type | Scraper Method |
|---|---|---|
| RemoteOK | Remote board | Public JSON API |
| We Work Remotely | Remote board | Simple HTML |
| Dice | Tech aggregator | Simple HTML |
| ZipRecruiter | Aggregator | Simple HTML |
| LinkedIn | Aggregator | Playwright |
| Indeed | Aggregator | Playwright |
| Workday | ATS platform | Playwright |
| Greenhouse | ATS platform | Playwright |
| Lever | ATS platform | Playwright |

Sources are pluggable — adding a new scraper requires implementing a standard interface and registering it with Celery Beat.

---

## Out of Scope (for now)
- Multi-user support
- Resume parsing / auto-apply
- Interview tracking
- External hosting / cloud deployment
- Mobile app
