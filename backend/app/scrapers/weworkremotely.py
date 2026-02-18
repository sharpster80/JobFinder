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

        # WeWorkRemotely returns RSS/XML, not HTML
        soup = BeautifulSoup(response.text, "xml")

        jobs = []
        for item in soup.find_all("item"):
            try:
                # Parse RSS item
                title_text = item.find("title").text if item.find("title") else ""
                link = item.find("link").text if item.find("link") else ""
                region = item.find("region").text if item.find("region") else "Remote"

                if not title_text or not link:
                    continue

                # Title format: "Company: Job Title"
                if ": " in title_text:
                    company, title = title_text.split(": ", 1)
                else:
                    company = ""
                    title = title_text

                external_id = hashlib.md5(link.encode()).hexdigest()
                jobs.append(ScrapedJob(
                    source=self.source_name,
                    external_id=external_id,
                    url=link,
                    title=title.strip(),
                    company=company.strip(),
                    location=region.strip(),
                    is_remote=True,
                ))
            except Exception:
                continue

        return jobs
