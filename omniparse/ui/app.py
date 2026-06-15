"""
Главное окно десктопного приложения OmniParse Studio на CustomTkinter.
4 полнофункциональные вкладки: Конструктор, Монитор, Каталог, Экспорт.
"""

from datetime import datetime
import os
from pathlib import Path
import threading
from tkinter import messagebox, ttk
import customtkinter as ctk
from omniparse.config import DEFAULT_EXPORT_DIR
from omniparse.core.engine import ScrapingEngine
from omniparse.storage.database import DatabaseManager
from omniparse.storage.exporters import DataExporter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class OmniParseStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OmniParse Studio — Профессиональный комплекс парсинга данных")
        self.geometry("1100x740")
        self.minsize(980, 640)

        self.db = DatabaseManager()
        self.engine = ScrapingEngine(self.db)
        self.engine.on_log = self._handle_log
        self.engine.on_progress = self._handle_progress
        self.engine.on_item_scraped = self._handle_new_item

        self._seed_sample_data_if_empty()
        self._build_ui()

    def _seed_sample_data_if_empty(self):
        """Создает начальный набор данных для немедленного тестирования интерфейса."""
        if not self.db.get_items(limit=1):
            job_id = self.db.create_job("Демо: Книжный каталог e-Commerce", "https://books.toscrape.com")
            sample_items = [
                {"title": "A Light in the Attic", "price": 51.77, "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html", "category": "Поэзия"},
                {"title": "Tipping the Velvet", "price": 53.74, "url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html", "category": "Художественная"},
                {"title": "Soumission", "price": 50.10, "url": "https://books.toscrape.com/catalogue/soumission_998/index.html", "category": "Художественная"},
                {"title": "Sharp Objects", "price": 47.82, "url": "https://books.toscrape.com/catalogue/sharp-objects_997/index.html", "category": "Детектив"},
                {"title": "Sapiens: Краткая история человечества", "price": 54.23, "url": "https://books.toscrape.com/catalogue/sapiens_996/index.html", "category": "История"},
                {"title": "The Requiem Red", "price": 22.65, "url": "https://books.toscrape.com/catalogue/the-requiem-red_995/index.html", "category": "Драма"},
                {"title": "The Dirty Little Secrets of Getting Your Dream Job", "price": 33.34, "url": "https://books.toscrape.com/catalogue/the-dirty-little-secrets_994/index.html", "category": "Бизнес"},
                {"title": "The Coming Woman: A Novel Based on the Life of Victoria Woodhull", "price": 17.93, "url": "https://books.toscrape.com/catalogue/the-coming-woman_993/index.html", "category": "История"}
            ]
            self.db.save_items_batch(job_id, sample_items)
            self.db.update_job_progress(job_id, len(sample_items), 1, status="COMPLETED")

    def _build_ui(self):
        # Настройка сетки
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview с 4 вкладками
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")

        self.tab_builder = self.tabview.add("🛠️ 1. Конструктор задач")
        self.tab_monitor = self.tabview.add("📊 2. Мониторинг & Логи")
        self.tab_data = self.tabview.add("📦 3. Каталог данных")
        self.tab_export = self.tabview.add("💾 4. Экспорт & Настройки")

        self._build_tab_builder()
        self._build_tab_monitor()
        self._build_tab_data()
        self._build_tab_export()

    # ================= 1. TAB BUILDER =================
    def _build_tab_builder(self):
        tab = self.tab_builder
        tab.grid_columnconfigure(1, weight=1)

        # Пресеты
        preset_frame = ctk.CTkFrame(tab)
        preset_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 15))
        ctk.CTkLabel(preset_frame, text="⚡ Быстрый пресет:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=8)

        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            values=["E-Commerce: Книжный магазин (Демо)", "Цитаты и Авторы (Quotes)", "Пользовательский парсер"],
            command=self._apply_preset
        )
        self.preset_menu.pack(side="left", padx=10, pady=8)

        # Поля ввода
        labels = [
            ("Название задачи:", "entry_job_name", "Сбор цен интернет-магазина"),
            ("Стартовый URL:", "entry_url", "https://books.toscrape.com/catalogue/page-1.html"),
            ("Селектор карточки (Контейнер):", "entry_container", "article.product_pod"),
            ("Селектор заголовка:", "entry_title", "h3 a@title"),
            ("Селектор цены:", "entry_price", "p.price_color"),
            ("Селектор ссылки товара:", "entry_link", "h3 a@href"),
            ("Селектор пагинации (Next):", "entry_next", "li.next a"),
        ]

        for i, (text, attr_name, default_val) in enumerate(labels, start=1):
            lbl = ctk.CTkLabel(tab, text=text, anchor="w", font=ctk.CTkFont(size=13))
            lbl.grid(row=i, column=0, padx=15, pady=6, sticky="w")
            entry = ctk.CTkEntry(tab, height=34)
            entry.insert(0, default_val)
            entry.grid(row=i, column=1, padx=15, pady=6, sticky="ew")
            setattr(self, attr_name, entry)

        # Нижние параметры (задержка и лимит)
        param_frame = ctk.CTkFrame(tab, fg_color="transparent")
        param_frame.grid(row=len(labels) + 1, column=0, columnspan=2, sticky="ew", padx=15, pady=15)

        ctk.CTkLabel(param_frame, text="Лимит страниц:").pack(side="left", padx=(0, 5))
        self.spin_pages = ctk.CTkOptionMenu(param_frame, values=["5", "10", "25", "50", "100"], width=90)
        self.spin_pages.set("10")
        self.spin_pages.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(param_frame, text="Задержка между запросами (сек):").pack(side="left", padx=(0, 5))
        self.spin_delay = ctk.CTkOptionMenu(param_frame, values=["0.5", "1.0", "2.0", "3.0"], width=80)
        self.spin_delay.set("1.0")
        self.spin_delay.pack(side="left", padx=(0, 20))

        # Кнопка Запуск
        self.btn_start = ctk.CTkButton(
            param_frame, text="🚀 Запустить сбор данных", height=38,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold", size=14),
            command=self.start_scraping
        )
        self.btn_start.pack(side="right")

    def _apply_preset(self, choice):
        if "Книжный" in choice:
            self.entry_job_name.delete(0, "end"); self.entry_job_name.insert(0, "Сбор цен интернет-магазина")
            self.entry_url.delete(0, "end"); self.entry_url.insert(0, "https://books.toscrape.com/catalogue/page-1.html")
            self.entry_container.delete(0, "end"); self.entry_container.insert(0, "article.product_pod")
            self.entry_title.delete(0, "end"); self.entry_title.insert(0, "h3 a@title")
            self.entry_price.delete(0, "end"); self.entry_price.insert(0, "p.price_color")
            self.entry_link.delete(0, "end"); self.entry_link.insert(0, "h3 a@href")
            self.entry_next.delete(0, "end"); self.entry_next.insert(0, "li.next a")
        elif "Цитаты" in choice:
            self.entry_job_name.delete(0, "end"); self.entry_job_name.insert(0, "Парсер цитат и авторов")
            self.entry_url.delete(0, "end"); self.entry_url.insert(0, "https://quotes.toscrape.com/")
            self.entry_container.delete(0, "end"); self.entry_container.insert(0, "div.quote")
            self.entry_title.delete(0, "end"); self.entry_title.insert(0, "span.text")
            self.entry_price.delete(0, "end"); self.entry_price.insert(0, "small.author")
            self.entry_link.delete(0, "end"); self.entry_link.insert(0, "a@href")
            self.entry_next.delete(0, "end"); self.entry_next.insert(0, "li.next a")

    # ================= 2. TAB MONITOR =================
    def _build_tab_monitor(self):
        tab = self.tab_monitor
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Метрики
        cards_row = ctk.CTkFrame(tab, fg_color="transparent")
        cards_row.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        cards_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def make_card(parent, col, title, initial_val, color):
            frame = ctk.CTkFrame(parent)
            frame.grid(row=0, column=col, padx=6, sticky="ew")
            ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=12, pady=(10, 0))
            val_lbl = ctk.CTkLabel(frame, text=initial_val, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
            val_lbl.pack(anchor="w", padx=12, pady=(2, 10))
            return val_lbl

        self.lbl_pages = make_card(cards_row, 0, "Страниц обработано", "0", "#3B82F6")
        self.lbl_items = make_card(cards_row, 1, "Собрано объектов", "0", "#10B981")
        self.lbl_speed = make_card(cards_row, 2, "Скорость (стр/мин)", "0.0", "#F59E0B")
        self.lbl_errors = make_card(cards_row, 3, "Ошибок сети", "0", "#EF4444")

        # Тулбар управления
        controls = ctk.CTkFrame(tab, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self.btn_pause = ctk.CTkButton(controls, text="⏸ Пауза", width=110, command=self.toggle_pause)
        self.btn_pause.pack(side="left", padx=5)

        self.btn_stop = ctk.CTkButton(controls, text="⏹ Остановить", width=110, fg_color="#DC2626", hover_color="#991B1B", command=self.stop_scraping)
        self.btn_stop.pack(side="left", padx=5)

        self.status_tag = ctk.CTkLabel(controls, text="● Ожидание команды", text_color="#94A3B8", font=ctk.CTkFont(weight="bold"))
        self.status_tag.pack(side="right", padx=10)

        # Консоль логов
        self.log_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.log_box.insert("1.0", "=== Журнал событий краулера готов к работе ===\n")

    # ================= 3. TAB DATA EXPLORER =================
    def _build_tab_data(self):
        tab = self.tab_data
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Поиск и фильтры
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(top_bar, text="🔍 Поиск:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="Фильтр по названию...", width=260)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data_table())

        btn_refresh = ctk.CTkButton(top_bar, text="Обновить", width=90, command=self.load_data_table)
        btn_refresh.pack(side="left", padx=10)

        self.lbl_total_items = ctk.CTkLabel(top_bar, text="Записей в базе: 0", font=ctk.CTkFont(weight="bold"))
        self.lbl_total_items.pack(side="right", padx=10)

        # Таблица данных (Treeview с темной темой)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e293b", foreground="#f8fafc", fieldbackground="#1e293b", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2563eb")])

        cols = ("id", "title", "price", "category", "scraped_at")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Наименование / Заголовок")
        self.tree.heading("price", text="Цена")
        self.tree.heading("category", text="Категория")
        self.tree.heading("scraped_at", text="Дата парсинга")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("title", width=420)
        self.tree.column("price", width=120, anchor="e")
        self.tree.column("category", width=140)
        self.tree.column("scraped_at", width=160, anchor="center")

        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.load_data_table()

    def load_data_table(self):
        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        items = self.db.get_items(search=query, limit=200)

        for row in self.tree.get_children():
            self.tree.delete(row)

        for it in items:
            p_val = f"{it['price']:,.2f} ₽" if it.get("price") else "—"
            self.tree.insert("", "end", values=(it["id"], it["title"], p_val, it["category"], it["scraped_at"]))

        if hasattr(self, "lbl_total_items"):
            self.lbl_total_items.configure(text=f"Найдено записей: {len(items)}")

    # ================= 4. TAB EXPORT =================
    def _build_tab_export(self):
        tab = self.tab_export
        tab.grid_columnconfigure((0, 1), weight=1)

        # Блок Экспорта
        exp_frame = ctk.CTkFrame(tab)
        exp_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        ctk.CTkLabel(exp_frame, text="📤 Экспорт выгруженных данных", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(16, 10))

        buttons = [
            ("📊 Экспорт в Excel (.xlsx)", self.export_excel, "#10B981"),
            ("📄 Экспорт в CSV (.csv)", self.export_csv, "#3B82F6"),
            ("🔧 Экспорт в JSON (.json)", self.export_json, "#8B5CF6"),
            ("🌐 Сгенерировать веб-каталог (.html)", self.export_html, "#F59E0B"),
        ]

        for text, cmd, col in buttons:
            btn = ctk.CTkButton(exp_frame, text=text, height=38, fg_color=col, command=cmd)
            btn.pack(fill="x", padx=16, pady=6)

        self.lbl_exp_status = ctk.CTkLabel(exp_frame, text="Файлы сохраняются в data/exports/", text_color="gray")
        self.lbl_exp_status.pack(anchor="w", padx=16, pady=(12, 16))

        # Блок Настроек Антидетекта
        cfg_frame = ctk.CTkFrame(tab)
        cfg_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        ctk.CTkLabel(cfg_frame, text="🛡️ Защита от блокировок (Антидетект)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(16, 10))

        self.sw_ua = ctk.CTkSwitch(cfg_frame, text="Ротация User-Agent реальных браузеров")
        self.sw_ua.select()
        self.sw_ua.pack(anchor="w", padx=16, pady=8)

        self.sw_jitter = ctk.CTkSwitch(cfg_frame, text="Случайный джиттер задержки (±35%)")
        self.sw_jitter.select()
        self.sw_jitter.pack(anchor="w", padx=16, pady=8)

        self.sw_ref = ctk.CTkSwitch(cfg_frame, text="Эмуляция переходов с поисковых систем (Google/Yandex)")
        self.sw_ref.select()
        self.sw_ref.pack(anchor="w", padx=16, pady=8)

        ctk.CTkLabel(cfg_frame, text="Список прокси (HTTP/HTTPS, по одному на строку):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(12, 4))
        self.txt_proxy = ctk.CTkTextbox(cfg_frame, height=120)
        self.txt_proxy.insert("1.0", "# Формат: http://user:pass@host:port\n")
        self.txt_proxy.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    # ================= ЛОГИКА И СОБЫТИЯ =================
    def start_scraping(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Ошибка", "Укажите стартовый URL!")
            return

        name = self.entry_job_name.get().strip() or "Безымянная задача"
        container = self.entry_container.get().strip()
        rules = {
            "title": self.entry_title.get().strip(),
            "price": self.entry_price.get().strip(),
            "url": self.entry_link.get().strip(),
        }
        next_sel = self.entry_next.get().strip()
        max_p = int(self.spin_pages.get())
        delay = float(self.spin_delay.get())

        self.tabview.set("📊 2. Мониторинг & Логи")
        self.status_tag.configure(text="● Выполняется сбор данных...", text_color="#10B981")
        self.engine.start_job(name, [url], container, rules, next_sel, max_p, delay)

    def toggle_pause(self):
        if self.engine.is_paused:
            self.engine.resume()
            self.btn_pause.configure(text="⏸ Пауза")
            self.status_tag.configure(text="● Выполняется сбор данных...", text_color="#10B981")
        else:
            self.engine.pause()
            self.btn_pause.configure(text="▶ Возобновить")
            self.status_tag.configure(text="● На паузе", text_color="#F59E0B")

    def stop_scraping(self):
        self.engine.stop()
        self.status_tag.configure(text="● Остановлен", text_color="#EF4444")

    def _handle_log(self, msg, level):
        def update():
            time_str = datetime.now().strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{time_str}] [{level}] {msg}\n")
            self.log_box.see("end")
        self.after(0, update)

    def _handle_progress(self, stats):
        def update():
            self.lbl_pages.configure(text=str(stats.get("pages", 0)))
            self.lbl_items.configure(text=str(stats.get("items", 0)))
            self.lbl_speed.configure(text=str(stats.get("speed_ppm", 0.0)))
            self.lbl_errors.configure(text=str(stats.get("errors", 0)))
        self.after(0, update)

    def _handle_new_item(self, item):
        self.after(0, self.load_data_table)

    def export_excel(self):
        items = self.db.get_items(limit=1000)
        file_path = DEFAULT_EXPORT_DIR / f"export_{int(datetime.now().timestamp())}.xlsx"
        DataExporter.to_excel(items, file_path)
        self.lbl_exp_status.configure(text=f"Экспорт сохранен: {file_path.name}", text_color="#10B981")
        messagebox.showinfo("Успех", f"Данные ({len(items)} записей) выгружены в Excel:\n{file_path}")

    def export_csv(self):
        items = self.db.get_items(limit=1000)
        file_path = DEFAULT_EXPORT_DIR / f"export_{int(datetime.now().timestamp())}.csv"
        DataExporter.to_csv(items, file_path)
        self.lbl_exp_status.configure(text=f"Экспорт сохранен: {file_path.name}", text_color="#10B981")
        messagebox.showinfo("Успех", f"Файл CSV сохранен:\n{file_path}")

    def export_json(self):
        items = self.db.get_items(limit=1000)
        file_path = DEFAULT_EXPORT_DIR / f"export_{int(datetime.now().timestamp())}.json"
        DataExporter.to_json(items, file_path)
        self.lbl_exp_status.configure(text=f"Экспорт сохранен: {file_path.name}", text_color="#10B981")
        messagebox.showinfo("Успех", f"Файл JSON сохранен:\n{file_path}")

    def export_html(self):
        items = self.db.get_items(limit=1000)
        file_path = DEFAULT_EXPORT_DIR / f"catalog_{int(datetime.now().timestamp())}.html"
        DataExporter.to_html_catalog(items, file_path)
        self.lbl_exp_status.configure(text=f"Каталог сгенерирован: {file_path.name}", text_color="#10B981")
        messagebox.showinfo("Успех", f"Автономный HTML-каталог создан:\n{file_path}")


if __name__ == "__main__":
    app = OmniParseStudioApp()
    app.mainloop()

