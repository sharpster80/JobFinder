from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ScrapedJob:
    source: str
    external_id: str
    url: str
    title: str
    company: str
    location: str = ""
    is_remote: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    description: str = ""
    tech_tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None

class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    def scrape(self) -> list[ScrapedJob]:
        """Fetch and return a list of ScrapedJob objects."""
        ...
