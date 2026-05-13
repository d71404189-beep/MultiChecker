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

sys.path.insert(0, os.path.dirname(__file__))

APP_VERSION = "1.0.29"

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

# ── Colour palette ─────────────────────────────────────────────────────────────
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
        self.geometry("1320x820")
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
        self._setup_ui()

    # ═══════════════════════════════════════════════════════════════════════════
    #  LAYOUT
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(20, weight=1)

        # Logo block
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.grid(row=0, column=0, padx=18, pady=(22, 6), sticky="ew")
        ctk.CTkLabel(logo, text="◈  MultiChecker",
                     font=("Segoe UI", 16, "bold"), text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(logo, text=f"Pro  ·  v{APP_VERSION}",
                     font=("Segoe UI", 10), text_color=MUTED).pack(anchor="w")

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=1, column=0, padx=14, pady=(6, 10), sticky="ew")

        # Nav
        self._nav_btns = {}
        for row_idx, (tab, (icon, _)) in enumerate(TAB_META.items()):
            btn = ctk.CTkButton(
                sb, text=f"  {icon}   {tab}", anchor="w",
                font=("Segoe UI", 13), height=42,
                fg_color="transparent", hover_color=HOVER,
                text_color=TEXT, corner_radius=8,
                command=lambda t=tab: self._switch_tab(t),
            )
            btn.grid(row=row_idx + 2, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[tab] = btn

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=9, column=0, padx=14, pady=8, sticky="ew")

        # Language
        lang_box = ctk.CTkFrame(sb, fg_color="transparent")
        lang_box.grid(row=10, column=0, padx=14, pady=4, sticky="ew")
        ctk.CTkLabel(lang_box, text="Language", font=("Segoe UI", 10),
                     text_color=MUTED).pack(anchor="w", padx=4)
        self.lang_sw = ctk.CTkSwitch(
            lang_box, text="RU / EN", font=("Segoe UI", 12),
            command=self.toggle_lang,
            button_color=ACCENT, progress_color=ACCENT,
        )
        self.lang_sw.pack(anchor="w", padx=4, pady=4)
        if i18n.current_lang == "ru":
            self.lang_sw.select()

        # Status dot
        self._sb_status = ctk.CTkLabel(
            sb, text="●  Ready", font=("Segoe UI", 11), text_color=GREEN)
        self._sb_status.grid(row=21, column=0, padx=18, pady=(0, 18), sticky="sw")

        self._switch_tab("All")

    def _highlight_nav(self, active):
        for tab, btn in self._nav_btns.items():
            if tab == active:
                btn.configure(fg_color=HOVER, text_color=ACCENT,
                               font=("Segoe UI", 13, "bold"))
            else:
                btn.configure(fg_color="transparent", text_color=TEXT,
                               font=("Segoe UI", 13))

    def _build_content(self):
        wrap = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        wrap.grid(row=0, column=1, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        self._tab_frames = {}
        for tab in TAB_META:
            f = ctk.CTkFrame(wrap, fg_color=BG, corner_radius=0)
            f.grid_columnconfigure(0, weight=1)
            f.grid_rowconfigure(1, weight=1)
            self._tab_frames[tab] = f
            self.tab_widgets[tab] = self._build_tab(f, tab)

    def _switch_tab(self, tab):
        self._highlight_nav(tab)
        for t, f in self._tab_frames.items():
            if t == tab:
                f.grid(row=0, column=0, sticky="nsew")
            else:
                f.grid_remove()

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB BUILDER
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_tab(self, frame, tab_name):
        w = {}
        icon, label_key = TAB_META[tab_name]

        # ── Top bar ──────────────────────────────────────────────────────────
        bar = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=0, height=58)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text=f"{icon}  {i18n.t(label_key)} Checker",
                     font=("Segoe UI", 17, "bold"), text_color=TEXT
                     ).grid(row=0, column=0, padx=22, pady=14, sticky="w")

        w["status_pill"] = ctk.CTkLabel(
            bar, text="●  Ready",
            font=("Segoe UI", 11, "bold"), text_color=GREEN,
            fg_color=CARD2, corner_radius=14, padx=14, pady=5)
        w["status_pill"].grid(row=0, column=2, padx=22, pady=14, sticky="e")

        # ── Scrollable body ──────────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(frame, fg_color=BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        # Input
        in_card = self._card(body, "Input")
        in_card.grid(row=0, column=0, padx=18, pady=(14, 6), sticky="ew")
        in_card.grid_columnconfigure(0, weight=1)
        w["input"] = ctk.CTkTextbox(
            in_card, height=115, font=("Consolas", 12),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8, wrap="none")
        w["input"].grid(row=1, column=0, padx=14, pady=(4, 14), sticky="ew")

        # Settings row
        cfg = self._card(body, "Settings")
        cfg.grid(row=1, column=0, padx=18, pady=6, sticky="ew")
        cfg.grid_columnconfigure(0, weight=1)
        sr = ctk.CTkFrame(cfg, fg_color="transparent")
        sr.grid(row=1, column=0, padx=14, pady=(4, 14), sticky="ew")
        sr.grid_columnconfigure(1, weight=1)
        sr.grid_columnconfigure(6, weight=2)

        def lbl(parent, text, col):
            ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11),
                         text_color=MUTED).grid(row=0, column=col, padx=(0, 6), sticky="w")

        lbl(sr, "Threads", 0)
        w["threads"] = ctk.CTkSlider(
            sr, from_=1, to=500, number_of_steps=499,
            button_color=ACCENT, progress_color=ACCENT, fg_color=BORDER)
        w["threads"].set(100)
        w["threads"].grid(row=0, column=1, padx=(0, 10), sticky="ew")
        w["threads_val"] = ctk.CTkLabel(
            sr, text="100", font=("Segoe UI", 11, "bold"),
            text_color=ACCENT, width=34)
        w["threads_val"].grid(row=0, column=2, padx=(0, 18))
        w["threads"].configure(
            command=lambda v, ww=w: ww["threads_val"].configure(text=str(int(v))))

        lbl(sr, "Timeout (s)", 3)
        w["timeout"] = ctk.CTkEntry(
            sr, width=58, font=("Segoe UI", 11),
            fg_color=CARD2, border_color=BORDER, text_color=TEXT, corner_radius=8)
        w["timeout"].insert(0, "10")
        w["timeout"].grid(row=0, column=4, padx=(0, 18), sticky="w")

        lbl(sr, "Proxy", 5)
        w["proxy"] = ctk.CTkEntry(
            sr, font=("Segoe UI", 11), fg_color=CARD2, border_color=BORDER,
            text_color=TEXT, corner_radius=8,
            placeholder_text="http://ip:port  or  proxy.txt")
        w["proxy"].grid(row=0, column=6, sticky="ew")

        # Action buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=18, pady=6, sticky="ew")

        def mk(parent, txt, fg, hv, cmd, width=None):
            kw = dict(text=txt, fg_color=fg, hover_color=hv,
                      font=("Segoe UI", 12, "bold"), corner_radius=8, height=38, command=cmd)
            if width:
                kw["width"] = width
            return ctk.CTkButton(parent, **kw)

        sb_btn = mk(btn_row, f"▶  {i18n.t('start')}", GREEN, "#2ea043",
                    lambda: self.start_check(tab_name), 155)
        sb_btn.pack(side="left", padx=(0, 6))
        self._translatable.append((sb_btn, "start", "▶  {}"))

        st_btn = mk(btn_row, f"■  {i18n.t('stop')}", RED, "#da3633",
                    self.stop_check, 110)
        st_btn.pack(side="left", padx=(0, 6))
        self._translatable.append((st_btn, "stop", "■  {}"))

        cl_btn = mk(btn_row, f"⌫  {i18n.t('clear')}", CARD, CARD2,
                    lambda: self.clear_output(w), 110)
        cl_btn.pack(side="left", padx=(0, 6))
        self._translatable.append((cl_btn, "clear", "⌫  {}"))

        im_btn = mk(btn_row, f"↑  {i18n.t('import_file')}", CARD, CARD2,
                    lambda: self.import_file(w), 135)
        im_btn.pack(side="left", padx=(0, 6))
        self._translatable.append((im_btn, "import_file", "↑  {}"))

        dd_btn = mk(btn_row, f"⊘  {i18n.t('remove_duplicates')}", "#6e40c9", "#5a32a3",
                    lambda: self.remove_duplicates(w), 175)
        dd_btn.pack(side="left", padx=(0, 6))
        self._translatable.append((dd_btn, "remove_duplicates", "⊘  {}"))

        # Export group
        exp = ctk.CTkFrame(btn_row, fg_color=CARD, corner_radius=8)
        exp.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(exp, text="Export:", font=("Segoe UI", 10),
                     text_color=MUTED).pack(side="left", padx=(12, 4))
        for fmt, lbl_txt in [("txt", "TXT"), ("json", "JSON"), ("csv", "CSV")]:
            ctk.CTkButton(
                exp, text=lbl_txt, fg_color="transparent", hover_color=CARD2,
                font=("Segoe UI", 11, "bold"), text_color=ACCENT,
                corner_radius=6, height=32, width=54,
                command=lambda f=fmt: self.export_results(w, f),
            ).pack(side="left", padx=2, pady=4)

        st_btn2 = mk(btn_row, f"◈  {i18n.t('stats')}", PURPLE, "#a371f7",
                     lambda: self.show_stats(tab_name), 120)
        st_btn2.pack(side="right", padx=(6, 0))
        self._translatable.append((st_btn2, "stats", "◈  {}"))

        # Counter cards
        cnt = ctk.CTkFrame(body, fg_color="transparent")
        cnt.grid(row=3, column=0, padx=18, pady=6, sticky="ew")
        cnt.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def counter(col, label, color):
            c = ctk.CTkFrame(cnt, fg_color=CARD, corner_radius=10)
            c.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(c, text=label, font=("Segoe UI", 10),
                         text_color=MUTED).pack(pady=(10, 0))
            v = ctk.CTkLabel(c, text="0", font=("Segoe UI", 26, "bold"),
                             text_color=color)
            v.pack(pady=(2, 10))
            return v

        w["cnt_valid"]   = counter(0, i18n.t("valid"),   GREEN)
        w["cnt_invalid"] = counter(1, i18n.t("invalid"), RED)
        w["cnt_errors"]  = counter(2, i18n.t("errors"),  YELLOW)
        w["cnt_total"]   = counter(3, i18n.t("total"),   ACCENT)

        # Progress
        pg = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        pg.grid(row=4, column=0, padx=18, pady=6, sticky="ew")
        pg.grid_columnconfigure(0, weight=1)
        w["progress"] = ctk.CTkProgressBar(
            pg, height=8, corner_radius=4,
            progress_color=ACCENT, fg_color=BORDER)
        w["progress"].grid(row=0, column=0, padx=14, pady=12, sticky="ew")
        w["progress"].set(0)

        # Filter bar
        fb = ctk.CTkFrame(body, fg_color="transparent")
        fb.grid(row=5, column=0, padx=18, pady=(4, 0), sticky="ew")
        w["_log_lines"] = []
        w["_filter"]    = "all"
        w["filter_seg"] = ctk.CTkSegmentedButton(
            fb,
            values=[i18n.t("filter_all"), i18n.t("filter_valid"),
                    i18n.t("filter_invalid"), i18n.t("filter_errors")],
            font=("Segoe UI", 12),
            selected_color=ACCENT, selected_hover_color="#4493e0",
            unselected_color=CARD, unselected_hover_color=CARD2,
            fg_color=CARD, text_color=TEXT,
            command=lambda v: self._on_filter(w, v),
        )
        w["filter_seg"].set(i18n.t("filter_all"))
        w["filter_seg"].pack(side="left")

        # Log output
        log_card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        log_card.grid(row=6, column=0, padx=18, pady=(6, 18), sticky="ew")
        log_card.grid_columnconfigure(0, weight=1)
        w["output"] = ctk.CTkTextbox(
            log_card, height=300, font=("Consolas", 12),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8, wrap="none")
        w["output"].grid(row=0, column=0, padx=14, pady=14, sticky="ew")
        w["output"].tag_config("valid",   foreground=GREEN)
        w["output"].tag_config("invalid", foreground=MUTED)
        w["output"].tag_config("error",   foreground=YELLOW)
        w["output"].tag_config("system",  foreground=ACCENT)

        w["status"] = w["status_pill"]
        return w

    def _card(self, parent, title=""):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10)
        if title:
            ctk.CTkLabel(f, text=title, font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=0, padx=14, pady=(10, 2), sticky="w")
        return f


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

    # ═══════════════════════════════════════════════════════════════════════════
    #  LAYOUT
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, fg_color=SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(9, weight=1)
        sb.grid_columnconfigure(0, weight=1)

        # Logo block
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.grid(row=0, column=0, padx=18, pady=(22, 6), sticky="ew")
        ctk.CTkLabel(logo, text="MultiChecker", font=("Segoe UI", 18, "bold"),
                     text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(logo, text=f"Pro  •  v{APP_VERSION}", font=("Segoe UI", 11),
                     text_color=MUTED).pack(anchor="w")

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=1, column=0, padx=14, pady=(6, 10), sticky="ew")

        # Nav
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

        # Language
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

        # Status dot
        self._sb_status = ctk.CTkLabel(
            sb, text="● Готов", font=("Segoe UI", 11), text_color=GREEN)
        self._sb_status.grid(row=11, column=0, padx=18, pady=(8, 18), sticky="sw")

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

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB BUILDER
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_tab(self, frame, tab_name):
        w = {}
        icon, label_key = TAB_META[tab_name]

        # ── Top bar ──────────────────────────────────────────────────────────
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

        # ── Scrollable body ──────────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(frame, fg_color=BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        # ── Input ────────────────────────────────────────────────────────────
        ic = self._card(body, "Входные данные")
        ic.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="ew")
        ic.grid_columnconfigure(0, weight=1)
        w["input"] = ctk.CTkTextbox(
            ic, height=108, font=("Consolas", 12),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8,
        )
        w["input"].grid(row=1, column=0, padx=12, pady=(2, 12), sticky="ew")

        # ── Settings row ─────────────────────────────────────────────────────
        sc = self._card(body, "Настройки")
        sc.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        sc.grid_columnconfigure(0, weight=1)

        sr = ctk.CTkFrame(sc, fg_color="transparent")
        sr.grid(row=1, column=0, padx=12, pady=(2, 12), sticky="ew")
        sr.grid_columnconfigure(1, weight=1)
        sr.grid_columnconfigure(6, weight=2)

        def lbl(parent, text, col):
            ctk.CTkLabel(parent, text=text, font=("Segoe UI", 12),
                         text_color=MUTED).grid(row=0, column=col, padx=(0, 6), sticky="w")

        lbl(sr, "Потоки", 0)
        w["threads"] = ctk.CTkSlider(sr, from_=1, to=500, number_of_steps=499,
                                      button_color=ACCENT, progress_color=ACCENT,
                                      fg_color=BORDER)
        w["threads"].set(100)
        w["threads"].grid(row=0, column=1, padx=(0, 10), sticky="ew")
        w["tval"] = ctk.CTkLabel(sr, text="100", font=("Segoe UI", 12, "bold"),
                                  text_color=ACCENT, width=34)
        w["tval"].grid(row=0, column=2, padx=(0, 18))
        w["threads"].configure(command=lambda v, ww=w: ww["tval"].configure(text=str(int(v))))

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

        # ── Action buttons ───────────────────────────────────────────────────
        bf = ctk.CTkFrame(body, fg_color="transparent")
        bf.grid(row=2, column=0, padx=16, pady=6, sticky="ew")

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
        btn(bf, "⊘  Дубли",   "#6e40c9", "#5a32a3", lambda: self.remove_duplicates(w), 110).pack(side="left", padx=(0,6))

        # Export group
        eg = ctk.CTkFrame(bf, fg_color=CARD, corner_radius=8)
        eg.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(eg, text="Экспорт:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(10, 4))
        for fmt, lbl_text in [("txt","TXT"),("json","JSON"),("csv","CSV")]:
            ctk.CTkButton(eg, text=lbl_text, fg_color="transparent",
                           hover_color=HOVER, font=("Segoe UI", 11, "bold"),
                           text_color=ACCENT, corner_radius=6, height=30, width=54,
                           command=lambda f=fmt: self.export_results(w, f)
                           ).pack(side="left", padx=2, pady=4)

        btn(bf, "◈  Стат", PURPLE, "#a371f7",
            lambda: self.show_stats(tab_name), 110).pack(side="right")

        # ── Counter cards ────────────────────────────────────────────────────
        cr = ctk.CTkFrame(body, fg_color="transparent")
        cr.grid(row=3, column=0, padx=16, pady=6, sticky="ew")
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

        # ── Progress ─────────────────────────────────────────────────────────
        pc = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        pc.grid(row=4, column=0, padx=16, pady=6, sticky="ew")
        pc.grid_columnconfigure(0, weight=1)
        w["progress"] = ctk.CTkProgressBar(pc, height=8, corner_radius=4,
                                            progress_color=ACCENT, fg_color=BORDER)
        w["progress"].grid(row=0, column=0, padx=14, pady=10, sticky="ew")
        w["progress"].set(0)

        # ── Filter bar ───────────────────────────────────────────────────────
        ff = ctk.CTkFrame(body, fg_color="transparent")
        ff.grid(row=5, column=0, padx=16, pady=(4, 0), sticky="ew")
        w["_log_lines"] = []
        w["_filter"]    = "all"
        w["filter_seg"] = ctk.CTkSegmentedButton(
            ff,
            values=[i18n.t("filter_all"), i18n.t("filter_valid"),
                    i18n.t("filter_invalid"), i18n.t("filter_errors")],
            font=("Segoe UI", 12),
            selected_color=ACCENT, selected_hover_color="#4393e4",
            unselected_color=CARD, unselected_hover_color=HOVER,
            fg_color=CARD, text_color=TEXT,
            command=lambda v: self._on_filter(w, v),
        )
        w["filter_seg"].set(i18n.t("filter_all"))
        w["filter_seg"].pack(side="left")

        # ── Log output ───────────────────────────────────────────────────────
        lc = ctk.CTkFrame(body, fg_color=CARD, corner_radius=10)
        lc.grid(row=6, column=0, padx=16, pady=(6, 18), sticky="ew")
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

        # compat alias
        w["status"] = w["pill"]
        return w

    def _card(self, parent, title=""):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10)
        if title:
            ctk.CTkLabel(f, text=title, font=("Segoe UI", 10),
                         text_color=MUTED).grid(row=0, column=0, padx=14,
                                                pady=(10, 2), sticky="w")
        return f

    # ═══════════════════════════════════════════════════════════════════════════
    #  LANGUAGE
    # ═══════════════════════════════════════════════════════════════════════════

    def toggle_lang(self):
        i18n.set_lang("en" if i18n.current_lang == "ru" else "ru")
        self._refresh_text()

    def _refresh_text(self):
        self.title(f"MultiChecker Pro  v{APP_VERSION}")
        fl = [i18n.t("filter_all"), i18n.t("filter_valid"),
              i18n.t("filter_invalid"), i18n.t("filter_errors")]
        fk = ["all", "valid", "invalid", "error"]
        for tab_name, w in self.tab_widgets.items():
            w["pill"].configure(text=f"● {i18n.t('ready')}")
            w["filter_seg"].configure(values=fl)
            cur = w.get("_filter", "all")
            w["filter_seg"].set(fl[fk.index(cur) if cur in fk else 0])

    # ═══════════════════════════════════════════════════════════════════════════
    #  FILE I/O
    # ═══════════════════════════════════════════════════════════════════════════

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
            else:
                with open(fn, "w", encoding="utf-8") as f:
                    for r in self.results:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            self.log(w, i18n.t("exported").format(fn))
        except Exception as e:
            self.log(w, f"Export error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  DEDUP
    # ═══════════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

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

    def _normalize(self, line, tab):
        raw = line.strip()
        if not raw:
            return ""
        try:
            if tab == "Crypto" and ":" not in raw and "/" not in raw and "|" not in raw:
                return raw
            if tab == "Email":
                m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw)
                if m:
                    return m.group(0)
            url_m = re.search(r"https?://[^\s|:]+(?:/[^\s|]*)?", raw)
            cleaned = raw.replace("|", ":")
            if url_m:
                try:
                    parsed = urlparse(url_m.group(0))
                    bits = [p for p in parsed.path.split("/") if p]
                    if tab in {"Social", "Games", "AI", "Crypto"} and bits:
                        return bits[-1]
                except (ValueError, TypeError):
                    pass
            tokens = [t.strip() for t in cleaned.split(":") if t.strip()
                      and t.strip() not in {"http", "https", "//"}]
            if tab == "Email":
                for t in tokens:
                    if "@" in t and "." in t.split("@")[-1]:
                        return t
            if tab in {"Social", "Games", "AI", "Crypto"}:
                cands = [t for t in tokens
                         if not t.lower().startswith("http") and "." not in t]
                if cands:
                    return cands[0] if len(cands) == 1 else cands[-2]
            return tokens[0] if tokens else raw
        except Exception:
            return raw

    # ═══════════════════════════════════════════════════════════════════════════
    #  CRYPTO FILTER
    # ═══════════════════════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════════════════════
    #  CHECK PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    def start_check(self, tab_name):
        w = self.tab_widgets[tab_name]
        if tab_name in self._loaded_data and self._loaded_data[tab_name]:
            raw = self._loaded_data[tab_name]
        else:
            raw = w["input"].get("1.0", "end").strip().split("\n")
        if not raw or (len(raw) == 1 and not raw[0].strip()):
            self.log(w, i18n.t("no_data")); return

        threads = self._safe_int(w["threads"].get(), 50)
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
                    p   = proxies[done[0] % len(proxies)] if proxies else None
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
                        vv,iv,ev = valid[0],inv[0],err[0]
                        self.after(0, lambda p=pv: w["progress"].set(p))
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

    # ═══════════════════════════════════════════════════════════════════════════
    #  UI UPDATES
    # ═══════════════════════════════════════════════════════════════════════════

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
        if w.get("_filter","all") in ("all", tag):
            self._log_safe(w, msg, tag)

    def _on_filter(self, w, value):
        mapping = {
            i18n.t("filter_all"):     "all",
            i18n.t("filter_valid"):   "valid",
            i18n.t("filter_invalid"): "invalid",
            i18n.t("filter_errors"):  "error",
        }
        ft = mapping.get(value, "all")
        w["_filter"] = ft
        w["output"].delete("1.0", "end")
        for tag, line in w.get("_log_lines", []):
            if ft == "all" or tag == ft or tag == "system":
                self._log_safe(w, line, tag)

    def stop_check(self):
        self.is_running = False

    def clear_output(self, w):
        w["output"].delete("1.0", "end")
        w["input"].delete("1.0", "end")
        w["progress"].set(0)
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

    # ═══════════════════════════════════════════════════════════════════════════
    #  STATS WINDOW
    # ═══════════════════════════════════════════════════════════════════════════

    def show_stats(self, tab_name):
        w = self.tab_widgets[tab_name]
        if not self.all_results:
            self.log(w, i18n.t("stats_no_data")); return

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

        # Summary cards
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

        # Bar chart
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

        # Platform list
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


if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
