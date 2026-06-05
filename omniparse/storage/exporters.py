"""
Экспорт собранных данных в форматы XLSX, CSV, JSON и автономный HTML-каталог.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from omniparse.config import DEFAULT_EXPORT_DIR


class DataExporter:
    @staticmethod
    def to_csv(items: List[Dict[str, Any]], filepath: Path) -> Path:
        df = pd.DataFrame(items)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        return filepath

    @staticmethod
    def to_excel(items: List[Dict[str, Any]], filepath: Path) -> Path:
        df = pd.DataFrame(items)
        # Удаляем лишние вложенные JSON при экспорте в чистую таблицу
        if "raw_data" in df.columns:
            df = df.drop(columns=["raw_data"])
        df.to_excel(filepath, index=False, engine="openpyxl")
        return filepath

    @staticmethod
    def to_json(items: List[Dict[str, Any]], filepath: Path) -> Path:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return filepath

    @staticmethod
    def to_html_catalog(items: List[Dict[str, Any]], filepath: Path, title: str = "Каталог выгруженных данных") -> Path:
        rows_html = []
        for it in items:
            p_str = f"{it.get('price', 0):,.2f} ₽" if it.get('price') else "Цена не указана"
            url = it.get('url', '#')
            rows_html.append(f"""
            <div class="card">
                <div class="category">{it.get('category', 'Каталог')}</div>
                <div class="title"><a href="{url}" target="_blank">{it.get('title', 'Без названия')}</a></div>
                <div class="price">{p_str}</div>
                <div class="footer"><span class="badge">Парсинг: {it.get('scraped_at', '')}</span></div>
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ background: #0f172a; color: #f8fafc; padding: 30px; }}
  h1 {{ font-size: 24px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }}
  .category {{ font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 600; margin-bottom: 8px; }}
  .title a {{ color: #f8fafc; text-decoration: none; font-size: 15px; font-weight: 600; line-height: 1.4; }}
  .title a:hover {{ color: #60a5fa; }}
  .price {{ font-size: 20px; font-weight: 700; color: #10b981; margin: 12px 0; }}
  .footer {{ border-top: 1px solid #334155; padding-top: 10px; font-size: 11px; color: #64748b; }}
  .badge {{ background: #0f172a; padding: 4px 8px; border-radius: 4px; }}
</style>
</head>
<body>
  <h1>📦 {title} (Всего: {len(items)})</h1>
  <div class="grid">
    {''.join(rows_html)}
  </div>
</body>
</html>"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath

