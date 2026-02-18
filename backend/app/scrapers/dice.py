import hashlib
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
                # Parse "USD 166,500.00 - 291,400.00 per year"
                import re
                salary_str = item["salary"]
                numbers = re.findall(r'[\d,]+\.?\d*', salary_str)
                if len(numbers) >= 2:
                    salary_min = int(float(numbers[0].replace(',', '')))
                    salary_max = int(float(numbers[1].replace(',', '')))
                elif len(numbers) == 1:
                    salary_min = int(float(numbers[0].replace(',', '')))

            # workplaceTypes can be null, but we're filtering for Remote in params
            # so if we get results, they should be remote
            is_remote = True  # We filter for Remote in the API params

            # skills can be null, handle it
            skills = item.get("skills") or []

            # Generate deterministic external_id to deduplicate same job with different Dice IDs
            title = item.get("title", "")
            company = item.get("companyName", item.get("employerName", ""))
            # Create hash from title + company + salary range to identify unique positions
            dedupe_key = f"{title}|{company}|{salary_min}|{salary_max}"
            external_id = hashlib.md5(dedupe_key.encode()).hexdigest()

            job = ScrapedJob(
                source=self.source_name,
                external_id=external_id,
                url=item.get("detailsPageUrl", ""),
                title=title,
                company=company,
                location=item.get("location", ""),
                is_remote=is_remote,
                salary_min=salary_min,
                salary_max=salary_max,
                description=item.get("descriptionFragment", ""),
                tech_tags=skills,
            )
            # Deduplicate within scrape results (Dice returns same job multiple times)
            if not any(j.external_id == external_id for j in jobs):
                jobs.append(job)

        return jobs
