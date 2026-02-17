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
