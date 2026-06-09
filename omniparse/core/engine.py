"""
Многопоточный движок краулинга и парсинга с поддержкой паузы, остановки и очереди.
"""

from collections import deque
from datetime import datetime
import threading
import time
from typing import Callable, Dict, List, Optional
from omniparse.core.anti_detect import AntiDetectManager
from omniparse.core.extractor import DataExtractor
from omniparse.storage.database import DatabaseManager


class ScrapingEngine:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.anti_detect = AntiDetectManager()

        # Состояния выполнения
        self.is_running = False
        self.is_paused = False
        self._stop_requested = False
        self._worker_thread: Optional[threading.Thread] = None

        # Метрики сессии
        self.scraped_pages = 0
        self.scraped_items_count = 0
        self.errors_count = 0
        self.start_time = 0.0

        # Коллбеки для UI
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_progress: Optional[Callable[[dict], None]] = None
        self.on_item_scraped: Optional[Callable[[dict], None]] = None

    def log(self, message: str, level: str = "INFO"):
        if self.on_log:
            self.on_log(message, level)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {message}")

    def start_job(self,
                  job_name: str,
                  start_urls: List[str],
                  container_selector: str,
                  field_rules: Dict[str, str],
                  next_page_selector: Optional[str] = None,
                  max_pages: int = 20,
                  delay: float = 1.0):
        """Запускает процесс парсинга в фоновом потоке."""
        if self.is_running:
            self.log("Задача уже запущена!", "WARN")
            return

        self.is_running = True
        self.is_paused = False
        self._stop_requested = False
        self.scraped_pages = 0
        self.scraped_items_count = 0
        self.errors_count = 0
        self.start_time = time.time()

        job_id = self.db.create_job(job_name, start_urls[0] if start_urls else "N/A")

        self._worker_thread = threading.Thread(
            target=self._run_crawler,
            args=(job_id, start_urls, container_selector, field_rules, next_page_selector, max_pages, delay),
            daemon=True
        )
        self._worker_thread.start()

    def pause(self):
        self.is_paused = True
        self.log("Парсинг приостановлен пользователем.", "WARN")

    def resume(self):
        self.is_paused = False
        self.log("Парсинг возобновлен.", "INFO")

    def stop(self):
        self._stop_requested = True
        self.is_paused = False
        self.log("Запрос остановки процесса...", "WARN")

    def _run_crawler(self, job_id: int, start_urls: List[str], container_selector: str,
                     field_rules: Dict[str, str], next_page_selector: Optional[str],
                     max_pages: int, delay: float):
        self.log(f"Старт задачи #{job_id}: URL очереди={len(start_urls)}, лимит={max_pages} стр.", "INFO")
        session = self.anti_detect.create_session()
        queue = deque(start_urls)
        visited = set()

        while queue and not self._stop_requested and self.scraped_pages < max_pages:
            while self.is_paused and not self._stop_requested:
                time.sleep(0.5)

            url = queue.popleft()
            if url in visited:
                continue

            visited.add(url)
            self.log(f"Запрос страницы [{self.scraped_pages + 1}/{max_pages}]: {url}", "INFO")

            try:
                headers = self.anti_detect.generate_headers()
                response = session.get(url, headers=headers, timeout=12)

                if response.status_code == 200:
                    html = response.text
                    items = DataExtractor.extract_items(html, container_selector, field_rules, base_url=url)

                    # Если это реальный сайт или тестовый парсинг
                    if items:
                        self.db.save_items_batch(job_id, items)
                        self.scraped_items_count += len(items)
                        self.log(f"Извлечено объектов: {len(items)} (Всего: {self.scraped_items_count})", "SUCCESS")
                        if self.on_item_scraped and items:
                            self.on_item_scraped(items[-1])
                    else:
                        self.log("На странице не найдено элементов по указанному селектору контейнера.", "WARN")

                    self.scraped_pages += 1

                    # Поиск ссылки на следующую страницу (пагинация)
                    if next_page_selector and self.scraped_pages < max_pages:
                        next_url = DataExtractor.extract_next_page(html, next_page_selector, base_url=url)
                        if next_url and next_url not in visited and next_url not in queue:
                            queue.append(next_url)
                            self.log(f"Обнаружена ссылка пагинации: {next_url}", "DEBUG")

                else:
                    self.errors_count += 1
                    self.log(f"Ошибка ответа сервера HTTP {response.status_code} для {url}", "ERROR")

            except Exception as e:
                self.errors_count += 1
                self.log(f"Сетевое исключение при обращении к {url}: {str(e)}", "ERROR")

            # Обновление метрик в БД и UI
            elapsed = max(1.0, time.time() - self.start_time)
            speed = round((self.scraped_pages / elapsed) * 60, 1)

            self.db.update_job_progress(job_id, self.scraped_items_count, self.scraped_pages)
            if self.on_progress:
                self.on_progress({
                    "job_id": job_id,
                    "pages": self.scraped_pages,
                    "items": self.scraped_items_count,
                    "errors": self.errors_count,
                    "speed_ppm": speed,
                    "status": "RUNNING"
                })

            if queue and not self._stop_requested:
                self.anti_detect.sleep_with_jitter(delay)

        final_status = "COMPLETED" if not self._stop_requested else "CANCELLED"
        self.db.update_job_progress(job_id, self.scraped_items_count, self.scraped_pages, status=final_status)
        self.is_running = False
        self.log(f"Парсинг завершен! Статус: {final_status}. Собрано: {self.scraped_items_count} объектов.", "SUCCESS")

