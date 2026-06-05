"""
Слой персистентности и работы с базой данных SQLite.
"""

from datetime import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional
from omniparse.config import DB_PATH
from omniparse.storage.models import ScrapedItem, ScrapeJob


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    total_items INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    price REAL,
                    url TEXT,
                    category TEXT,
                    raw_data TEXT,
                    scraped_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_job ON items(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_title ON items(title)")
            conn.commit()

    def create_job(self, name: str, target_url: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (name, target_url, status, started_at)
                VALUES (?, ?, 'RUNNING', ?)
            """, (name, target_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return cursor.lastrowid

    def update_job_progress(self, job_id: int, total_items: int, total_pages: int, status: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status in ["COMPLETED", "FAILED"]:
                cursor.execute("""
                    UPDATE jobs SET total_items = ?, total_pages = ?, status = ?, finished_at = ?
                    WHERE id = ?
                """, (total_items, total_pages, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_id))
            elif status:
                cursor.execute("""
                    UPDATE jobs SET total_items = ?, total_pages = ?, status = ?
                    WHERE id = ?
                """, (total_items, total_pages, status, job_id))
            else:
                cursor.execute("""
                    UPDATE jobs SET total_items = ?, total_pages = ?
                    WHERE id = ?
                """, (total_items, total_pages, job_id))
            conn.commit()

    def save_items_batch(self, job_id: int, items_data: List[Dict[str, Any]]):
        if not items_data:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = []
        for it in items_data:
            title = it.get("title") or it.get("name") or "Без названия"
            price = it.get("price")
            if isinstance(price, (int, float)):
                p_val = float(price)
            else:
                p_val = None
            url = it.get("url") or it.get("link")
            cat = it.get("category") or "Каталог"
            raw = json.dumps(it, ensure_ascii=False)
            records.append((job_id, title, p_val, url, cat, raw, now_str))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO items (job_id, title, price, url, category, raw_data, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            conn.commit()

    def get_items(self, job_id: Optional[int] = None, search: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM items WHERE 1=1"
            params = []
            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)
            if search:
                query += " AND title LIKE ?"
                params.append(f"%{search}%")
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

