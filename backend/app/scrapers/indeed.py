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
