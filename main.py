import customtkinter as ctk
from tkinter import filedialog, Canvas
import asyncio
import aiohttp
import csv
import io
import json
import os
import platform
import re
import sys
import threading
import traceback
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))

APP_VERSION = "1.0.25"

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

C_BG      = "#0f1117"
C_SIDEBAR = "#161b27"
C_CARD    = "#1a2035"
C_CARD2   = "#1e2640"
C_BORDER  = "#2a3352"
C_ACCENT  = "#4f8ef7"
C_GREEN   = "#22c55e"
C_RED     = "#ef4444"
C_YELLOW  = "#f59e0b"
C_PURPLE  = "#a855f7"
C_TEXT    = "#e2e8f0"
C_MUTED   = "#64748b"

TAB_ICONS = {
    "All":    "⬡",
    "Email":  "✉",
    "Social": "◈",
    "Crypto": "◎",
    "Games":  "◉",
    "AI":     "◆",
}


class MultiCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Multi Checker Pro  v{APP_VERSION}")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=C_BG)
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

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=200, fg_color=C_SIDEBAR, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(20, weight=1)
        logo_frame = ctk.CTkFrame(sb, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")
        ctk.CTkLabel(logo_frame, text="◈ MultiChecker", font=("Segoe UI", 17, "bold"), text_color=C_ACCENT).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text=f"Pro  v{APP_VERSION}", font=("Segoe UI", 11), text_color=C_MUTED).pack(anchor="w")
        ctk.CTkFrame(sb, height=1, fg_color=C_BORDER).grid(row=1, column=0, padx=12, pady=(4, 12), sticky="ew")
        self._nav_buttons = {}
        tabs = ["All", "Email", "Social", "Crypto", "Games", "AI"]
        for idx, tab in enumerate(tabs):
            btn = ctk.CTkButton(
                sb, text=f"  {TAB_ICONS[tab]}  {tab}", anchor="w",
                font=("Segoe UI", 13), fg_color="transparent", hover_color=C_CARD2,
                text_color=C_TEXT, corner_radius=8, height=40,
                command=lambda t=tab: self._switch_tab(t),
            )
            btn.grid(row=idx + 2, column=0, padx=10, pady=2, sticky="ew")
            self._nav_buttons[tab] = btn
        ctk.CTkFrame(sb, height=1, fg_color=C_BORDER).grid(row=9, column=0, padx=12, pady=8, sticky="ew")
        lang_frame = ctk.CTkFrame(sb, fg_color="transparent")
        lang_frame.grid(row=10, column=0, padx=12, pady=4, sticky="ew")
        ctk.CTkLabel(lang_frame, text="Language", font=("Segoe UI", 11), text_color=C_MUTED).pack(anchor="w", padx=4)
        self.lang_btn = ctk.CTkSwitch(lang_frame, text="RU / EN", font=("Segoe UI", 12),
                                       command=self.toggle_lang, button_color=C_ACCENT, progress_color=C_ACCENT)
        self.lang_btn.pack(anchor="w", padx=4, pady=4)
        if i18n.current_lang == "ru":
            self.lang_btn.select()
        self._sidebar_status = ctk.CTkLabel(sb, text="● Ready", font=("Segoe UI", 11), text_color=C_GREEN)
        self._sidebar_status.grid(row=21, column=0, padx=16, pady=(0, 16), sticky="sw")
        self._highlight_nav("All")

    def _highlight_nav(self, active):
        for tab, btn in self._nav_buttons.items():
            if tab == active:
                btn.configure(fg_color=C_CARD2, text_color=C_ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=C_TEXT)

    def _switch_tab(self, tab_name):
        self._active_tab = tab_name
        self._highlight_nav(tab_name)
        for t, frame in self._tab_frames.items():
            if t == tab_name:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color=C_BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)
        self._tab_frames = {}
        for tab in ["All", "Email", "Social", "Crypto", "Games", "AI"]:
            frame = ctk.CTkFrame(main, fg_color=C_BG, corner_radius=0)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(1, weight=1)
            self._tab_frames[tab] = frame
            self.tab_widgets[tab] = self._create_tab_content(frame, tab)
        self._switch_tab("All")

    def _create_tab_content(self, frame, tab_name):
        widgets = {}
        header_bar = ctk.CTkFrame(frame, fg_color=C_CARD, corner_radius=0, height=56)
        header_bar.grid(row=0, column=0, sticky="ew")
        header_bar.grid_propagate(False)
        header_bar.grid_columnconfigure(1, weight=1)
        icon = TAB_ICONS.get(tab_name, "◈")
        label_key = "all_categories" if tab_name == "All" else tab_name.lower()
        header_lbl = ctk.CTkLabel(header_bar, text=f"{icon}  {i18n.t(label_key)} Checker",
                                   font=("Segoe UI", 18, "bold"), text_color=C_TEXT)
        header_lbl.grid(row=0, column=0, padx=20, pady=12, sticky="w")
        self._translatable.append((header_lbl, label_key, f"{icon}  {{}} Checker"))
        widgets["status_pill"] = ctk.CTkLabel(header_bar, text="● Ready",
                                               font=("Segoe UI", 12, "bold"), text_color=C_GREEN,
                                               fg_color=C_CARD2, corner_radius=12, padx=12, pady=4)
        widgets["status_pill"].grid(row=0, column=2, padx=20, pady=12, sticky="e")

        body = ctk.CTkScrollableFrame(frame, fg_color=C_BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        input_card = self._card(body, "Input")
        input_card.grid(row=0, column=0, padx=16, pady=(12, 6), sticky="ew")
        input_card.grid_columnconfigure(0, weight=1)
        widgets["input"] = ctk.CTkTextbox(input_card, height=110, font=("Consolas", 12),
                                           fg_color=C_CARD2, border_color=C_BORDER, border_width=1,
                                           text_color=C_TEXT, corner_radius=8)
        widgets["input"].grid(row=1, column=0, padx=12, pady=(4, 12), sticky="ew")

        settings_card = self._card(body, "Settings")
        settings_card.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        settings_card.grid_columnconfigure(0, weight=1)
        rs = ctk.CTkFrame(settings_card, fg_color="transparent")
        rs.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="ew")
        rs.grid_columnconfigure(1, weight=1)
        rs.grid_columnconfigure(6, weight=2)

        ctk.CTkLabel(rs, text="Threads", font=("Segoe UI", 12), text_color=C_MUTED).grid(row=0, column=0, padx=(0,8), sticky="w")
        widgets["threads"] = ctk.CTkSlider(rs, from_=1, to=500, number_of_steps=499,
                                            button_color=C_ACCENT, progress_color=C_ACCENT, fg_color=C_BORDER)
        widgets["threads"].set(100)
        widgets["threads"].grid(row=0, column=1, padx=(0,16), sticky="ew")
        widgets["threads_val"] = ctk.CTkLabel(rs, text="100", font=("Segoe UI", 12, "bold"), text_color=C_ACCENT, width=36)
        widgets["threads_val"].grid(row=0, column=2, padx=(0,20))
        widgets["threads"].configure(command=lambda v, w=widgets: w["threads_val"].configure(text=str(int(v))))

        ctk.CTkLabel(rs, text="Timeout (s)", font=("Segoe UI", 12), text_color=C_MUTED).grid(row=0, column=3, padx=(0,8), sticky="w")
        widgets["timeout"] = ctk.CTkEntry(rs, width=60, font=("Segoe UI", 12),
                                           fg_color=C_CARD2, border_color=C_BORDER, text_color=C_TEXT, corner_radius=8)
        widgets["timeout"].insert(0, "10")
        widgets["timeout"].grid(row=0, column=4, padx=(0,20), sticky="w")

        ctk.CTkLabel(rs, text="Proxy", font=("Segoe UI", 12), text_color=C_MUTED).grid(row=0, column=5, padx=(0,8), sticky="w")
        widgets["proxy"] = ctk.CTkEntry(rs, font=("Segoe UI", 12), fg_color=C_CARD2, border_color=C_BORDER,
                                         text_color=C_TEXT, corner_radius=8, placeholder_text="http://ip:port  or  proxy.txt")
        widgets["proxy"].grid(row=0, column=6, sticky="ew")

        btn_card = ctk.CTkFrame(body, fg_color="transparent")
        btn_card.grid(row=2, column=0, padx=16, pady=6, sticky="ew")

        def _btn(parent, text, color, hover, cmd, width=130):
            return ctk.CTkButton(parent, text=text, fg_color=color, hover_color=hover,
                                  font=("Segoe UI", 12, "bold"), corner_radius=8, height=36, width=width, command=cmd)

        start_btn = _btn(btn_card, f"▶  {i18n.t('start')}", C_GREEN, "#16a34a", lambda: self.start_check(tab_name), 150)
        start_btn.pack(side="left", padx=(0,6))
        self._translatable.append((start_btn, "start", "▶  {}"))

        stop_btn = _btn(btn_card, f"■  {i18n.t('stop')}", C_RED, "#b91c1c", self.stop_check, 110)
        stop_btn.pack(side="left", padx=(0,6))
        self._translatable.append((stop_btn, "stop", "■  {}"))

        clear_btn = _btn(btn_card, f"⌫  {i18n.t('clear')}", C_CARD, C_CARD2, lambda: self.clear_output(widgets), 110)
        clear_btn.pack(side="left", padx=(0,6))
        self._translatable.append((clear_btn, "clear", "⌫  {}"))

        import_btn = _btn(btn_card, f"↑  {i18n.t('import_file')}", C_CARD, C_CARD2, lambda: self.import_file(widgets), 130)
        import_btn.pack(side="left", padx=(0,6))
        self._translatable.append((import_btn, "import_file", "↑  {}"))

        dedup_btn = _btn(btn_card, f"⊘  {i18n.t('remove_duplicates')}", "#7c3aed", "#6d28d9", lambda: self.remove_duplicates(widgets), 170)
        dedup_btn.pack(side="left", padx=(0,6))
        self._translatable.append((dedup_btn, "remove_duplicates", "⊘  {}"))

        export_frame = ctk.CTkFrame(btn_card, fg_color=C_CARD, corner_radius=8)
        export_frame.pack(side="left", padx=(6,0))
        ctk.CTkLabel(export_frame, text="Export:", font=("Segoe UI", 11), text_color=C_MUTED).pack(side="left", padx=(10,4))
        for fmt, label in [("txt","TXT"),("json","JSON"),("csv","CSV")]:
            ctk.CTkButton(export_frame, text=label, fg_color="transparent", hover_color=C_CARD2,
                           font=("Segoe UI", 11, "bold"), text_color=C_ACCENT, corner_radius=6, height=30, width=52,
                           command=lambda f=fmt: self.export_results(widgets, f)).pack(side="left", padx=2, pady=3)

        stats_btn = _btn(btn_card, f"◈  {i18n.t('stats')}", C_PURPLE, "#9333ea", lambda: self.show_stats(tab_name), 120)
        stats_btn.pack(side="right", padx=(6,0))
        self._translatable.append((stats_btn, "stats", "◈  {}"))

        counters_row = ctk.CTkFrame(body, fg_color="transparent")
        counters_row.grid(row=3, column=0, padx=16, pady=6, sticky="ew")
        counters_row.grid_columnconfigure((0,1,2,3), weight=1)

        def _counter_card(parent, col, label, color):
            card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10)
            card.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 10), text_color=C_MUTED).pack(pady=(8,0))
            val = ctk.CTkLabel(card, text="0", font=("Segoe UI", 22, "bold"), text_color=color)
            val.pack(pady=(0,8))
            return val

        widgets["cnt_valid"]   = _counter_card(counters_row, 0, i18n.t("valid"),   C_GREEN)
        widgets["cnt_invalid"] = _counter_card(counters_row, 1, i18n.t("invalid"), C_RED)
        widgets["cnt_errors"]  = _counter_card(counters_row, 2, i18n.t("errors"),  C_YELLOW)
        widgets["cnt_total"]   = _counter_card(counters_row, 3, i18n.t("total"),   C_ACCENT)

        prog_card = ctk.CTkFrame(body, fg_color=C_CARD, corner_radius=10)
        prog_card.grid(row=4, column=0, padx=16, pady=6, sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)
        widgets["progress"] = ctk.CTkProgressBar(prog_card, height=10, corner_radius=5,
                                                   progress_color=C_ACCENT, fg_color=C_BORDER)
        widgets["progress"].grid(row=0, column=0, padx=12, pady=10, sticky="ew")
        widgets["progress"].set(0)

        filter_bar = ctk.CTkFrame(body, fg_color="transparent")
        filter_bar.grid(row=5, column=0, padx=16, pady=(4,0), sticky="ew")
        widgets["_log_lines"] = []
        widgets["_filter"]    = "all"
        widgets["filter_seg"] = ctk.CTkSegmentedButton(
            filter_bar,
            values=[i18n.t("filter_all"), i18n.t("filter_valid"), i18n.t("filter_invalid"), i18n.t("filter_errors")],
            font=("Segoe UI", 12), selected_color=C_ACCENT, selected_hover_color="#3b7de8",
            unselected_color=C_CARD, unselected_hover_color=C_CARD2, fg_color=C_CARD, text_color=C_TEXT,
            command=lambda v: self._on_filter(widgets, v),
        )
        widgets["filter_seg"].set(i18n.t("filter_all"))
        widgets["filter_seg"].pack(side="left")

        log_card = ctk.CTkFrame(body, fg_color=C_CARD, corner_radius=10)
        log_card.grid(row=6, column=0, padx=16, pady=(6,16), sticky="ew")
        log_card.grid_columnconfigure(0, weight=1)
        widgets["output"] = ctk.CTkTextbox(log_card, height=280, font=("Consolas", 12),
                                            fg_color=C_CARD2, border_color=C_BORDER, border_width=1,
                                            text_color=C_TEXT, corner_radius=8, wrap="none")
        widgets["output"].grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        widgets["output"].tag_config("valid",   foreground=C_GREEN)
        widgets["output"].tag_config("invalid", foreground=C_MUTED)
        widgets["output"].tag_config("error",   foreground=C_YELLOW)
        widgets["output"].tag_config("system",  foreground=C_ACCENT)
        widgets["status"] = widgets["status_pill"]
        return widgets

    def _card(self, parent, title=""):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10)
        if title:
            ctk.CTkLabel(frame, text=title, font=("Segoe UI", 11), text_color=C_MUTED).grid(
                row=0, column=0, padx=14, pady=(10,2), sticky="w")
        return frame

    def toggle_lang(self):
        i18n.set_lang("en" if i18n.current_lang == "ru" else "ru")
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        self.title(f"Multi Checker Pro  v{APP_VERSION}")
        for widget, key, fmt in self._translatable:
            try:
                text = i18n.t(key)
                if fmt:
                    text = fmt.format(text)
                widget.configure(text=text)
            except Exception:
                pass
        filter_labels = [i18n.t("filter_all"), i18n.t("filter_valid"), i18n.t("filter_invalid"), i18n.t("filter_errors")]
        filter_keys   = ["all", "valid", "invalid", "error"]
        for tab_name, widgets in self.tab_widgets.items():
            widgets["status_pill"].configure(text=f"● {i18n.t('ready')}")
            widgets["filter_seg"].configure(values=filter_labels)
            current = widgets.get("_filter", "all")
            idx = filter_keys.index(current) if current in filter_keys else 0
            widgets["filter_seg"].set(filter_labels[idx])

    def import_file(self, widgets):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filepath:
            return
        try:
            tab_name = self._get_tab_for_widgets(widgets)
            lines = []
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                while True:
                    chunk = f.readlines(1_000_000)
                    if not chunk:
                        break
                    for line in chunk:
                        s = line.strip()
                        if s:
                            lines.append(s)
            total = len(lines)
            self._loaded_data[tab_name] = lines
            widgets["input"].delete("1.0", "end")
            if total <= _TEXTBOX_DISPLAY_LIMIT:
                widgets["input"].insert("1.0", "\n".join(lines))
            else:
                widgets["input"].insert("1.0", "\n".join(lines[:_TEXTBOX_DISPLAY_LIMIT]) +
                                        f"\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} more lines loaded] ...")
            self.log(widgets, i18n.t("file_loaded").format(total))
        except Exception as e:
            self.log(widgets, f"Import error: {e}")

    def export_results(self, widgets, fmt="txt"):
        if not self.results:
            self.log(widgets, i18n.t("no_results"))
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"valid_{ts}.{fmt}"
        try:
            if fmt == "json":
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
            elif fmt == "csv":
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    if self.results:
                        writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                        writer.writeheader()
                        for r in self.results:
                            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v for k, v in r.items()})
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    for r in self.results:
                        f.write(f"{json.dumps(r, ensure_ascii=False)}\n")
            self.log(widgets, i18n.t("exported").format(filename))
        except Exception as e:
            self.log(widgets, f"Export error: {e}")

    def remove_duplicates(self, widgets):
        tab_name = self._get_tab_for_widgets(widgets)
        if tab_name in self._loaded_data and self._loaded_data[tab_name]:
            raw_lines = self._loaded_data[tab_name]
        else:
            raw_text = widgets["input"].get("1.0", "end").strip()
            if not raw_text:
                self.log(widgets, i18n.t("no_data_to_dedup"))
                return
            raw_lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        original_count = len(raw_lines)
        if original_count == 0:
            self.log(widgets, i18n.t("no_data_to_dedup"))
            return
        seen, unique = set(), []
        for line in raw_lines:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        del seen
        dupes = original_count - len(unique)
        if dupes > 0:
            self._loaded_data[tab_name] = unique
            widgets["input"].delete("1.0", "end")
            total = len(unique)
            if total <= _TEXTBOX_DISPLAY_LIMIT:
                widgets["input"].insert("1.0", "\n".join(unique))
            else:
                widgets["input"].insert("1.0", "\n".join(unique[:_TEXTBOX_DISPLAY_LIMIT]) +
                                        f"\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} more lines] ...")
            self.log(widgets, i18n.t("dedup_result").format(dupes, len(unique)))
        else:
            self.log(widgets, i18n.t("dedup_no_dupes").format(original_count))

    def _get_tab_for_widgets(self, widgets):
        for tab_name, w in self.tab_widgets.items():
            if w is widgets:
                return tab_name
        return "Unknown"

    def _safe_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_input_line(self, line, tab_name):
        raw = line.strip()
        if not raw:
            return ""
        try:
            return self._do_normalize(raw, tab_name)
        except Exception:
            return raw

    def _do_normalize(self, raw, tab_name):
        if tab_name == "Crypto" and ":" not in raw and "/" not in raw and "|" not in raw:
            return raw
        if tab_name == "Email":
            m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw)
            if m:
                return m.group(0)
        url_match = re.search(r"https?://[^\s|:]+(?:/[^\s|]*)?", raw)
        cleaned = raw.replace("|", ":")
        if url_match:
            try:
                parsed = urlparse(url_match.group(0))
                path_bits = [p for p in parsed.path.split("/") if p]
                if tab_name in {"Social", "Games", "AI", "Crypto"} and path_bits:
                    return path_bits[-1]
            except (ValueError, TypeError):
                pass
        tokens = [t.strip() for t in cleaned.split(":") if t.strip()]
        tokens = [t for t in tokens if t not in {"http", "https", "//"}]
        if tab_name == "Email":
            for token in tokens:
                if "@" in token and "." in token.split("@")[-1]:
                    return token
        if tab_name in {"Social", "Games", "AI", "Crypto"}:
            candidate_tokens = [t for t in tokens if not t.lower().startswith("http") and "." not in t]
            if candidate_tokens:
                return candidate_tokens[0] if len(candidate_tokens) == 1 else candidate_tokens[-2]
        return tokens[0] if tokens else raw

    def start_check(self, tab_name):
        widgets = self.tab_widgets[tab_name]
        if tab_name in self._loaded_data and self._loaded_data[tab_name]:
            raw_lines = self._loaded_data[tab_name]
        else:
            raw_text = widgets["input"].get("1.0", "end").strip()
            raw_lines = raw_text.split("\n")
        if not raw_lines or (len(raw_lines) == 1 and not raw_lines[0].strip()):
            self.log(widgets, i18n.t("no_data"))
            return
        threads = self._safe_int(widgets["threads"].get(), 50)
        timeout = self._safe_int(widgets["timeout"].get(), 10)
        proxy   = widgets["proxy"].get().strip()
        self.is_running = True
        self.results = []
        self.all_results = []
        self._platform_stats = {}
        widgets["_log_lines"] = []
        widgets["_filter"]    = "all"
        widgets["filter_seg"].set(i18n.t("filter_all"))
        self._update_counters(widgets, 0, 0, 0, 0)
        widgets["output"].delete("1.0", "end")
        widgets["status_pill"].configure(text=f"⟳ {i18n.t('checking')}", text_color=C_ACCENT)
        self._sidebar_status.configure(text="⟳ Checking...", text_color=C_ACCENT)
        widgets["progress"].set(0)
        self.log(widgets, i18n.t("preparing_data"))
        threading.Thread(target=self._prepare_and_check,
                         args=(raw_lines, tab_name, threads, timeout, proxy, widgets), daemon=True).start()

    def _prepare_and_check(self, raw_lines, tab_name, threads, timeout, proxy, widgets):
        try:
            original_count = len(raw_lines)
            if tab_name in ("Crypto", "All"):
                seen, data = set(), []
                total = len(raw_lines)
                report_interval = max(total // 10, 1_000_000)
                for idx, line in enumerate(raw_lines):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped not in seen:
                        seen.add(stripped)
                        data.append(stripped)
                    if idx % report_interval == 0 and idx > 0:
                        pct = idx * 100 // total
                        self.after(0, lambda p=pct, i=idx, t=total: self.log(widgets, f"Scanning... {p}% ({i}/{t})"))
                del seen
            else:
                seen, data = set(), []
                for item in (self._normalize_input_line(d, tab_name) for d in raw_lines if d.strip()):
                    if item and item not in seen:
                        seen.add(item)
                        data.append(item)
                del seen
            dupes_removed = original_count - len(data)
            if not data:
                self.after(0, lambda: self.log(widgets, i18n.t("no_data")))
                self.after(0, lambda: widgets["status_pill"].configure(text=f"● {i18n.t('ready')}", text_color=C_GREEN))
                return
            if dupes_removed > 0:
                self.after(0, lambda: self.log(widgets, i18n.t("duplicates_removed").format(dupes_removed)))
            if tab_name == "All":
                self.after(0, lambda: self.log(widgets, i18n.t("starting_all").format(len(data), 5, len(data)*5, threads)))
            else:
                self.after(0, lambda: self.log(widgets, i18n.t("starting").format(len(data), threads)))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.check_all(data, tab_name, threads, timeout, proxy, widgets))
        except Exception as e:
            self.after(0, lambda: self.log(widgets, f"Error: {e}"))
            self.after(0, lambda: widgets["status_pill"].configure(text=f"● {i18n.t('ready')}", text_color=C_GREEN))
        finally:
            self.is_running = False
            self.after(0, lambda: self._sidebar_status.configure(text="● Ready", text_color=C_GREEN))

    @staticmethod
    def _scan_line_for_wallets(line, first_chars, patterns, seen, data):
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
                        seen.add(token)
                        data.append(token)
                    return

    async def check_all(self, data, tab_name, threads, timeout, proxy, widgets):
        semaphore      = asyncio.Semaphore(threads)
        all_categories = ["Email", "Social", "Crypto", "Games", "AI"]
        total          = len(data) * len(all_categories) if tab_name == "All" else len(data)
        completed      = [0]
        valid_count    = [0]
        invalid_count  = [0]
        error_count    = [0]
        ui_update_interval = max(1, total // 2000)
        proxies = []
        if proxy:
            if os.path.isfile(proxy):
                try:
                    with open(proxy, "r") as f:
                        proxies = [l.strip() for l in f if l.strip()]
                except Exception:
                    pass
            else:
                proxies = [proxy]
        connector = aiohttp.TCPConnector(limit=threads*2, limit_per_host=min(threads,50), ttl_dns_cache=300, force_close=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async def check_with_sem(data_item, category=None):
                async with semaphore:
                    if not self.is_running:
                        return None
                    p   = proxies[completed[0] % len(proxies)] if proxies else None
                    cat = category or tab_name
                    item = data_item
                    if category:
                        item = self._normalize_input_line(data_item, cat)
                        if not item:
                            completed[0] += 1
                            if completed[0] % ui_update_interval == 0:
                                pv = completed[0] / total
                                self.after(0, lambda v=pv: widgets["progress"].set(v))
                            return None
                    result = await self.check_item(item, cat, timeout, p, session)
                    completed[0] += 1
                    if result:
                        tag = result.get("platform", result.get("service", result.get("wallet_type", "")))
                        inp = result.get("input", result.get("email", ""))
                        if result.get("info", {}).get("error"):
                            error_count[0] += 1
                            err_msg = result.get("info", {}).get("error", "")
                            self.after(0, lambda t=tag, i=inp, m=err_msg: self.log_tagged(widgets, "error", f"[!] [{t}] {i} - {m}"))
                        elif result.get("exists"):
                            valid_count[0] += 1
                            self._platform_stats[tag] = self._platform_stats.get(tag, 0) + 1
                            msg = result.get("info", {}).get("message", "")
                            self.after(0, lambda t=tag, i=inp, m=msg: self.log_tagged(widgets, "valid", f"[+] [{t}] {i} - {m}"))
                            auth = result.get("info", {}).get("auth")
                            if auth:
                                self.after(0, lambda a=auth: self.log_tagged(widgets, "valid", f"    ↳ {i18n.t('auth_type')}: {a['auth_type']}"))
                                self.after(0, lambda a=auth: self.log_tagged(widgets, "valid", f"    ↳ {i18n.t('auth_wallets')}: {a['wallets']}"))
                                self.after(0, lambda a=auth: self.log_tagged(widgets, "valid", f"    ↳ {i18n.t('auth_how')}: {a['how']}"))
                            linked = result.get("info", {}).get("linked_services", [])
                            if linked:
                                svc_names = ", ".join(s["service"] for s in linked)
                                self.after(0, lambda i=inp, s=svc_names: self.log_tagged(widgets, "valid", f"    ↳ {i18n.t('linked')}: {s}"))
                                for svc in linked:
                                    self.after(0, lambda n=svc["service"], m2=svc.get("message",""): self.log_tagged(widgets, "valid", f"      • {n}: {m2}"))
                        else:
                            invalid_count[0] += 1
                            msg = result.get("info", {}).get("message", "Not found")
                            self.after(0, lambda t=tag, i=inp, m=msg: self.log_tagged(widgets, "invalid", f"[-] [{t}] {i} - {m}"))
                    if completed[0] % ui_update_interval == 0 or completed[0] == total:
                        pv = completed[0] / total
                        v, inv, err = valid_count[0], invalid_count[0], error_count[0]
                        self.after(0, lambda p=pv: widgets["progress"].set(p))
                        self.after(0, lambda: self._update_counters(widgets, v, inv, err, completed[0]))
                    return result

            results, batch = [], []
            def _flush_batch():
                nonlocal batch
                tasks = [check_with_sem(item, cat) for item, cat in batch] if tab_name == "All" else [check_with_sem(item) for item, _ in batch]
                batch = []
                return tasks

            if tab_name == "All":
                for item in data:
                    for cat in all_categories:
                        batch.append((item, cat))
                        if len(batch) >= _GATHER_BATCH_SIZE:
                            if not self.is_running: break
                            results.extend(await asyncio.gather(*_flush_batch()))
                    if not self.is_running: break
            else:
                for item in data:
                    batch.append((item, None))
                    if len(batch) >= _GATHER_BATCH_SIZE:
                        if not self.is_running: break
                        results.extend(await asyncio.gather(*_flush_batch()))
            if batch and self.is_running:
                results.extend(await asyncio.gather(*_flush_batch()))

        self.all_results = [r for r in results if r]
        self.results     = [r for r in self.all_results if r.get("exists")]
        del results
        v, inv, err = valid_count[0], invalid_count[0], error_count[0]
        self.after(0, lambda: self._update_counters(widgets, v, inv, err, total))
        self.after(0, lambda: widgets["status_pill"].configure(text=f"● {i18n.t('ready')}", text_color=C_GREEN))
        self.log(widgets, i18n.t("completed").format(len(self.results), total))
        self.log(widgets, "─" * 60)

    async def check_item(self, data_item, tab_name, timeout, proxy, session):
        checker = self.checkers.get(tab_name)
        try:
            result = await checker.check(data_item, timeout=timeout, proxy=proxy, session=session)
            if tab_name == "Email" and result.get("exists"):
                result["info"]["linked_services"] = await self._cross_check_email(data_item, timeout, proxy, session)
            return result
        except Exception as e:
            return {"input": data_item, "error": str(e), "exists": False, "info": {"error": str(e)}}

    async def _cross_check_email(self, email, timeout, proxy, session):
        username = email.split("@")[0]
        all_checks = [
            ("chatgpt",    self.checkers["AI"]._check_openai,      email),
            ("gemini",     self.checkers["AI"]._check_gemini,      email),
            ("perplexity", self.checkers["AI"]._check_perplexity,  email),
            ("claude",     self.checkers["AI"]._check_claude,      email),
            ("github",     self.checkers["Social"]._check_github,    username),
            ("instagram",  self.checkers["Social"]._check_instagram, username),
            ("twitter",    self.checkers["Social"]._check_twitter,   username),
            ("tiktok",     self.checkers["Social"]._check_tiktok,    username),
            ("reddit",     self.checkers["Social"]._check_reddit,    username),
            ("vk",         self.checkers["Social"]._check_vk,        username),
            ("telegram",   self.checkers["Social"]._check_telegram,  username),
            ("steam",      self.checkers["Games"]._check_steam,       username),
            ("epic",       self.checkers["Games"]._check_epic,        username),
            ("xbox",       self.checkers["Games"]._check_xbox,        username),
            ("playstation",self.checkers["Games"]._check_playstation, username),
        ]
        async def _run(name, handler, data):
            try:
                r = await handler(data, timeout, proxy, session)
                if r.get("exists"):
                    return {"service": name, "found": True, "message": r.get("info", {}).get("message", "")}
            except Exception:
                pass
            return None
        results = await asyncio.gather(*[_run(n, h, d) for n, h, d in all_checks])
        return [r for r in results if r]

    def _update_counters(self, widgets, valid, invalid, errors, total):
        widgets["cnt_valid"].configure(text=str(valid))
        widgets["cnt_invalid"].configure(text=str(invalid))
        widgets["cnt_errors"].configure(text=str(errors))
        widgets["cnt_total"].configure(text=str(total))

    def log_tagged(self, widgets, tag, message):
        log_lines = widgets.setdefault("_log_lines", [])
        log_lines.append((tag, message))
        if len(log_lines) > _MAX_LOG_LINES:
            widgets["_log_lines"] = log_lines[-_MAX_LOG_LINES:]
        current_filter = widgets.get("_filter", "all")
        if current_filter == "all" or current_filter == tag:
            self._log_safe(widgets, message, tag)

    def _on_filter(self, widgets, value):
        mapping = {
            i18n.t("filter_all"):     "all",
            i18n.t("filter_valid"):   "valid",
            i18n.t("filter_invalid"): "invalid",
            i18n.t("filter_errors"):  "error",
        }
        self.apply_filter(widgets, mapping.get(value, "all"))

    def apply_filter(self, widgets, filter_type):
        widgets["_filter"] = filter_type
        widgets["output"].delete("1.0", "end")
        for tag, line in widgets.get("_log_lines", []):
            if filter_type == "all" or tag == filter_type or tag == "system":
                self._log_safe(widgets, line, tag)

    def stop_check(self):
        self.is_running = False

    def clear_output(self, widgets):
        widgets["output"].delete("1.0", "end")
        widgets["input"].delete("1.0", "end")
        widgets["progress"].set(0)
        self._update_counters(widgets, 0, 0, 0, 0)
        widgets["_log_lines"] = []
        widgets["_filter"]    = "all"
        widgets["filter_seg"].set(i18n.t("filter_all"))
        self._loaded_data.pop(self._get_tab_for_widgets(widgets), None)

    def log(self, widgets, message):
        widgets.setdefault("_log_lines", []).append(("system", message))
        self.after(0, lambda: self._log_safe(widgets, message, "system"))

    def _log_safe(self, widgets, message, tag="system"):
        try:
            tb = widgets["output"]
            tb.insert("end", f"{message}\n", tag)
            tb.see("end")
        except Exception:
            pass

    def show_stats(self, tab_name):
        widgets = self.tab_widgets[tab_name]
        if not self.all_results:
            self.log(widgets, i18n.t("stats_no_data"))
            return
        win = ctk.CTkToplevel(self)
        win.title(i18n.t("stats_title"))
        win.geometry("520x500")
        win.configure(fg_color=C_BG)
        win.attributes("-topmost", True)
        valid   = len([r for r in self.all_results if r.get("exists")])
        errors  = len([r for r in self.all_results if r.get("info", {}).get("error")])
        invalid = len(self.all_results) - valid - errors
        total   = len(self.all_results)
        ctk.CTkLabel(win, text=i18n.t("stats_title"), font=("Segoe UI", 18, "bold"), text_color=C_TEXT).pack(pady=(20,10))
        cards_frame = ctk.CTkFrame(win, fg_color="transparent")
        cards_frame.pack(padx=20, fill="x")
        cards_frame.grid_columnconfigure((0,1,2), weight=1)
        for col, (label, count, color) in enumerate([(i18n.t("valid"),valid,C_GREEN),(i18n.t("invalid"),invalid,C_RED),(i18n.t("errors"),errors,C_YELLOW)]):
            card = ctk.CTkFrame(cards_frame, fg_color=C_CARD, corner_radius=10)
            card.grid(row=0, column=col, padx=4, sticky="ew")
            ctk.CTkLabel(card, text=label, font=("Segoe UI", 11), text_color=C_MUTED).pack(pady=(10,0))
            pct = f"{count*100//total}%" if total else "0%"
            ctk.CTkLabel(card, text=str(count), font=("Segoe UI", 24, "bold"), text_color=color).pack()
            ctk.CTkLabel(card, text=pct, font=("Segoe UI", 11), text_color=C_MUTED).pack(pady=(0,10))
        chart_frame = ctk.CTkFrame(win, fg_color=C_CARD, corner_radius=10)
        chart_frame.pack(padx=20, pady=12, fill="x")
        canvas = Canvas(chart_frame, width=460, height=110, bg=C_CARD, highlightthickness=0, bd=0)
        canvas.pack(pady=10, padx=10)
        max_val = max(valid, invalid, errors, 1)
        for label, count, color, y in [(i18n.t("valid"),valid,C_GREEN,10),(i18n.t("invalid"),invalid,C_RED,45),(i18n.t("errors"),errors,C_YELLOW,80)]:
            w   = int((count / max_val) * 280) if max_val > 0 else 0
            pct = f"{count*100//total}%" if total > 0 else "0%"
            canvas.create_rectangle(130, y, 130+max(w,3), y+22, fill=color, outline="")
            canvas.create_text(8,   y+11, text=f"{label}: {count}", anchor="w", fill=C_TEXT, font=("Segoe UI", 11))
            canvas.create_text(430, y+11, text=pct, anchor="e", fill=color, font=("Segoe UI", 11, "bold"))
        ctk.CTkLabel(win, text=i18n.t("stats_by_platform"), font=("Segoe UI", 14, "bold"), text_color=C_TEXT).pack(padx=20, anchor="w")
        scroll = ctk.CTkScrollableFrame(win, fg_color=C_CARD, corner_radius=10, height=160)
        scroll.pack(padx=20, pady=(4,20), fill="both", expand=True)
        if self._platform_stats:
            for plat, count in sorted(self._platform_stats.items(), key=lambda x: -x[1]):
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(row, text=plat, font=("Segoe UI", 12), text_color=C_TEXT).pack(side="left")
                ctk.CTkLabel(row, text=f"{count} {i18n.t('stats_found')}", font=("Segoe UI", 12, "bold"), text_color=C_ACCENT).pack(side="right")
        else:
            ctk.CTkLabel(scroll, text="  —", font=("Segoe UI", 12), text_color=C_MUTED).pack()


if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
