"""
Модуль обхода блокировок и антидетект-эмуляции реального браузера.
"""

import random
import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from omniparse.config import DEFAULT_HEADERS, USER_AGENTS


class AntiDetectManager:
    """Управление заголовками, ротацией User-Agent и защитой от капч/лимитов."""

    def __init__(self, proxies: Optional[list] = None):
        self.proxies = proxies or []
        self._proxy_index = 0

    def get_random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    def generate_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = DEFAULT_HEADERS.copy()
        headers["User-Agent"] = self.get_random_user_agent()
        # Случайный реферер поисковой системы
        referrers = [
            "https://www.google.com/",
            "https://yandex.ru/",
            "https://duckduckgo.com/",
            "https://www.bing.com/",
        ]
        headers["Referer"] = random.choice(referrers)
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None
        proxy = self.proxies[self._proxy_index % len(self.proxies)]
        self._proxy_index += 1
        return {"http": proxy, "https": proxy}

    def sleep_with_jitter(self, base_delay: float):
        """Пауза между запросами с рандомизацией для естественного поведения."""
        jitter = random.uniform(base_delay * 0.7, base_delay * 1.4)
        time.sleep(jitter)

    def create_session(self, retry_count: int = 3) -> requests.Session:
        """Создает requests.Session с автоповтором при сетевых сбоях и таймаутах."""
        session = requests.Session()
        retry_strategy = Retry(
            total=retry_count,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

