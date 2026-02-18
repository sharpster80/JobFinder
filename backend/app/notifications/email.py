import resend
from datetime import datetime, timedelta, timezone
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

    since = datetime.now(timezone.utc) - timedelta(hours=24)
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
