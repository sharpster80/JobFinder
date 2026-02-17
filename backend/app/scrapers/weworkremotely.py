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
