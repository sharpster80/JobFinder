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
