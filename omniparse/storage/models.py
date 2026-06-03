"""
Модели данных и структуры для хранения результатов парсинга.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ScrapedItem:
    id: Optional[int]
    job_id: int
    title: str
    price: Optional[float]
    url: Optional[str]
    category: Optional[str]
    raw_data: str  # JSON dump of all attributes
    scraped_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScrapeJob:
    id: Optional[int]
    name: str
    target_url: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED, PAUSED
    total_items: int
    total_pages: int
    started_at: str
    finished_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

