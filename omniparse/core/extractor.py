"""
Модуль извлечения и нормализации данных из HTML.
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup


class DataExtractor:
    """Парсинг HTML по CSS-селекторам и нормализация результатов."""

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        # Удаление неразрывных пробелов и лишних переносов
        cleaned = text.replace("\xa0", " ").strip()
        return re.sub(r"\s+", " ", cleaned)

    @staticmethod
    def extract_price(text: Optional[str]) -> Optional[float]:
        """Извлечение числового значения цены из строк вида '12 490 ₽' или '$1,299.50'."""
        if not text:
            return None
        cleaned = text.replace(" ", "").replace("\xa0", "")
        # Если есть и запятая и точка, например 1,299.50 - удаляем запятую
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def parse_item(element, rules: Dict[str, str], base_url: str = "") -> Dict[str, Any]:
        """
        Извлекает поля из одного HTML-элемента (карточки товара/статьи)
        по переданным правилам селекторов.
        """
        result = {}
        for field, selector in rules.items():
            if not selector:
                continue

            # Проверка извлечения атрибута: "a[href]@href" или "img@src"
            attr_target = None
            if "@" in selector:
                selector, attr_target = selector.split("@", 1)

            node = element.select_one(selector.strip())
            if not node:
                result[field] = None
                continue

            if attr_target:
                val = node.get(attr_target.strip(), "")
                if attr_target in ["href", "src"] and base_url and val:
                    val = urljoin(base_url, val)
                result[field] = val
            else:
                raw_text = DataExtractor.clean_text(node.get_text())
                if "price" in field.lower() or "цена" in field.lower():
                    result[field] = DataExtractor.extract_price(raw_text) or raw_text
                else:
                    result[field] = raw_text

        return result

    @staticmethod
    def extract_items(html: str, container_selector: str, rules: Dict[str, str], base_url: str = "") -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(container_selector)
        items = []
        for c in containers:
            parsed = DataExtractor.parse_item(c, rules, base_url)
            if any(parsed.values()):
                items.append(parsed)
        return items

    @staticmethod
    def extract_next_page(html: str, next_selector: str, base_url: str = "") -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.select_one(next_selector)
        if node and node.name == "a":
            href = node.get("href")
            return urljoin(base_url, href) if href else None
        return None
