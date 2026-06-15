"""
Тесты модуля извлечения и нормализации данных.
"""

from omniparse.core.extractor import DataExtractor


def test_extract_price():
    assert DataExtractor.extract_price("12 490 ₽") == 12490.0
    assert DataExtractor.extract_price("$1,299.50") == 1299.5
    assert DataExtractor.extract_price("£51.77") == 51.77
    assert DataExtractor.extract_price("Бесплатно") is None


def test_clean_text():
    raw = "   Привет,\xa0\xa0мир! \n\n Тест   "
    assert DataExtractor.clean_text(raw) == "Привет, мир! Тест"


def test_html_parsing():
    html = """
    <div class="product">
        <h2 class="name"><a href="/item/101">Смартфон Pro Max</a></h2>
        <span class="price">89 990 руб.</span>
    </div>
    """
    rules = {
        "title": "h2.name a",
        "price": "span.price",
        "url": "h2.name a@href"
    }
    items = DataExtractor.extract_items(html, "div.product", rules, base_url="https://shop.example.com")
    assert len(items) == 1
    assert items[0]["title"] == "Смартфон Pro Max"
    assert items[0]["price"] == 89990.0
    assert items[0]["url"] == "https://shop.example.com/item/101"

