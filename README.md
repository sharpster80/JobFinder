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
