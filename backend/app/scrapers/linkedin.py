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

                    if not title:
                        continue

                    # We filter for remote in URL params (f_WT=2), so assume remote
                    is_remote = True

                    # Generate deterministic external_id to deduplicate same remote job
                    # posted in multiple locations (LinkedIn posts same remote job with different location tags)
                    dedupe_key = f"{title}|{company}"
                    external_id = hashlib.md5(dedupe_key.encode()).hexdigest()

                    jobs.append(ScrapedJob(
                        source=self.source_name,
                        external_id=external_id,
                        url=url,
                        title=title,
                        company=company,
                        location=location,
                        is_remote=is_remote,
                    ))
                except Exception:
                    continue

            browser.close()
        return jobs
