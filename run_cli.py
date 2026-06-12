"""
CLI-режим запуска парсера для планировщика задач (cron, background tasks).
Использование:
  python run_cli.py --url "https://books.toscrape.com" --limit 5
"""

import argparse
import time
from omniparse.core.engine import ScrapingEngine
from omniparse.storage.database import DatabaseManager
from omniparse.storage.exporters import DataExporter
from omniparse.config import DEFAULT_EXPORT_DIR

def main():
    parser = argparse.ArgumentParser(description="OmniParse CLI Runner")
    parser.add_argument("--url", type=str, default="https://books.toscrape.com/catalogue/page-1.html", help="Стартовый URL")
    parser.add_argument("--limit", type=int, default=3, help="Максимальное число страниц")
    parser.add_argument("--delay", type=float, default=1.0, help="Задержка между запросами")
    parser.add_argument("--export", choices=["excel", "csv", "json", "html"], default="excel", help="Формат экспорта")
    args = parser.parse_args()

    db = DatabaseManager()
    engine = ScrapingEngine(db)

    print(f"🚀 Запуск CLI парсинга: {args.url} (Лимит: {args.limit} стр.)")
    
    rules = {
        "title": "h3 a@title",
        "price": "p.price_color",
        "url": "h3 a@href"
    }

    engine.start_job(
        job_name="CLI Batch Run",
        start_urls=[args.url],
        container_selector="article.product_pod",
        field_rules=rules,
        next_page_selector="li.next a",
        max_pages=args.limit,
        delay=args.delay
    )

    # Ожидание окончания работы потока
    while engine.is_running:
        time.sleep(0.5)

    print(f"✅ Готово! Собрано записей: {engine.scraped_items_count}")
    items = db.get_items(limit=1000)

    timestamp = int(time.time())
    if args.export == "excel":
        out = DataExporter.to_excel(items, DEFAULT_EXPORT_DIR / f"cli_export_{timestamp}.xlsx")
    elif args.export == "csv":
        out = DataExporter.to_csv(items, DEFAULT_EXPORT_DIR / f"cli_export_{timestamp}.csv")
    elif args.export == "json":
        out = DataExporter.to_json(items, DEFAULT_EXPORT_DIR / f"cli_export_{timestamp}.json")
    else:
        out = DataExporter.to_html_catalog(items, DEFAULT_EXPORT_DIR / f"cli_catalog_{timestamp}.html")

    print(f"📁 Результаты выгружены в: {out}")

if __name__ == "__main__":
    main()

