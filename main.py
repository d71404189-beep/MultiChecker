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

# Fix for Windows: aiohttp requires SelectorEventLoop, not Proactor
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


# Max lines to display in the textbox to keep UI responsive
_TEXTBOX_DISPLAY_LIMIT = 5000
# Batch size for asyncio.gather to avoid scheduling millions of coroutines at once
_GATHER_BATCH_SIZE = 50000
# Max log lines kept in memory per tab (older entries are dropped)
_MAX_LOG_LINES = 50000


class MultiCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(i18n.t("title"))
        self.geometry("1100x750")

        self.is_running = False
        self.results = []
        self.all_results = []
        self._platform_stats = {}
        self._loaded_data = {}  # tab_name -> list of lines loaded from file

        self.checkers = {
            "Email": EmailChecker(),
            "Social": SocialChecker(),
            "Crypto": CryptoChecker(),
            "Games": GameChecker(),
            "AI": AIChecker(),
        }

        self.tab_widgets = {}
        self._translatable = []
        self.setup_ui()

    def setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=5)

        self.title_label = ctk.CTkLabel(top_frame, text=i18n.t("title"), font=("Arial", 20, "bold"))
        self.title_label.pack(side="left", padx=10)

        self.lang_btn = ctk.CTkSwitch(top_frame, text="EN", command=self.toggle_lang)
        self.lang_btn.pack(side="right", padx=10)
        if i18n.current_lang == "ru":
            self.lang_btn.select()

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabview = ctk.CTkTabview(main_frame, width=1080, height=680)
        self.tabview.pack(pady=5, padx=5, fill="both", expand=True)

        tabs = ["All", "Email", "Social", "Crypto", "Games", "AI"]
        for tab in tabs:
            self.tabview.add(tab)
            frame = self.tabview.tab(tab)
            widgets = self.create_tab_content(frame, tab)
            self.tab_widgets[tab] = widgets

    def toggle_lang(self):
        if i18n.current_lang == "ru":
            i18n.set_lang("en")
        else:
            i18n.set_lang("ru")
        self.lang_btn.configure(text="RU" if i18n.current_lang == "en" else "EN")
        if i18n.current_lang == "en":
            self.lang_btn.deselect()
        else:
            self.lang_btn.select()
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        self.title(i18n.t("title"))
        self.title_label.configure(text=i18n.t("title"))
        for widget, key, fmt in self._translatable:
            try:
                text = i18n.t(key)
                if fmt:
                    text = fmt.format(text)
                widget.configure(text=text)
            except Exception:
                pass
        filter_labels = [i18n.t("filter_all"), i18n.t("filter_valid"),
                         i18n.t("filter_invalid"), i18n.t("filter_errors")]
        filter_keys = ["all", "valid", "invalid", "error"]
        for tab_name, widgets in self.tab_widgets.items():
            widgets["status"].configure(text=i18n.t("ready"))
            widgets["filter_seg"].configure(values=filter_labels)
            current = widgets.get("_filter", "all")
            idx = filter_keys.index(current) if current in filter_keys else 0
            widgets["filter_seg"].set(filter_labels[idx])

    def create_tab_content(self, frame, tab_name):
        widgets = {}

        label_key = "all_categories" if tab_name == "All" else tab_name.lower()
        header = ctk.CTkLabel(frame, text=f"{i18n.t(label_key)} Checker", font=("Arial", 18, "bold"))
        header.pack(pady=5)
        self._translatable.append((header, label_key, "{} Checker"))

        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(pady=5, padx=10, fill="x")

        input_label = ctk.CTkLabel(input_frame, text=i18n.t("input_label"))
        input_label.pack(anchor="w", padx=5, pady=2)
        self._translatable.append((input_label, "input_label", None))

        widgets["input"] = ctk.CTkTextbox(input_frame, height=100, width=1000)
        widgets["input"].pack(pady=5, padx=5, fill="x")

        settings_frame = ctk.CTkFrame(frame)
        settings_frame.pack(pady=5, padx=10, fill="x")

        threads_label = ctk.CTkLabel(settings_frame, text=i18n.t("threads"))
        threads_label.pack(side="left", padx=5)
        self._translatable.append((threads_label, "threads", None))

        widgets["threads"] = ctk.CTkSlider(settings_frame, from_=1, to=500, number_of_steps=499)
        widgets["threads"].set(100)
        widgets["threads"].pack(side="left", padx=5)

        timeout_label = ctk.CTkLabel(settings_frame, text=i18n.t("timeout"))
        timeout_label.pack(side="left", padx=10)
        self._translatable.append((timeout_label, "timeout", None))

        widgets["timeout"] = ctk.CTkEntry(settings_frame, width=50)
        widgets["timeout"].insert(0, "10")
        widgets["timeout"].pack(side="left", padx=5)

        proxy_label = ctk.CTkLabel(settings_frame, text=i18n.t("proxy"))
        proxy_label.pack(side="left", padx=10)
        self._translatable.append((proxy_label, "proxy", None))

        widgets["proxy"] = ctk.CTkEntry(settings_frame, width=300, placeholder_text=i18n.t("proxy_placeholder"))
        widgets["proxy"].pack(side="left", padx=5, expand=True, fill="x")

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=5, padx=10, fill="x")

        start_btn = ctk.CTkButton(btn_frame, text=i18n.t("start"),
                                   command=lambda: self.start_check(tab_name),
                                   fg_color="#2fa572", hover_color="#258e63")
        start_btn.pack(side="left", padx=5)
        self._translatable.append((start_btn, "start", None))

        stop_btn = ctk.CTkButton(btn_frame, text=i18n.t("stop"),
                                  command=self.stop_check,
                                  fg_color="#c93c3c", hover_color="#a32f2f")
        stop_btn.pack(side="left", padx=5)
        self._translatable.append((stop_btn, "stop", None))

        clear_btn = ctk.CTkButton(btn_frame, text=i18n.t("clear"),
                                   command=lambda: self.clear_output(widgets))
        clear_btn.pack(side="left", padx=5)
        self._translatable.append((clear_btn, "clear", None))

        import_btn = ctk.CTkButton(btn_frame, text=i18n.t("import_file"),
                                    command=lambda: self.import_file(widgets))
        import_btn.pack(side="left", padx=5)
        self._translatable.append((import_btn, "import_file", None))

        export_txt_btn = ctk.CTkButton(btn_frame, text=i18n.t("export_txt"),
                                        command=lambda: self.export_results(widgets, "txt"))
        export_txt_btn.pack(side="left", padx=5)
        self._translatable.append((export_txt_btn, "export_txt", None))

        export_json_btn = ctk.CTkButton(btn_frame, text=i18n.t("export_json"),
                                         command=lambda: self.export_results(widgets, "json"))
        export_json_btn.pack(side="left", padx=5)
        self._translatable.append((export_json_btn, "export_json", None))

        export_csv_btn = ctk.CTkButton(btn_frame, text=i18n.t("export_csv"),
                                        command=lambda: self.export_results(widgets, "csv"))
        export_csv_btn.pack(side="left", padx=5)
        self._translatable.append((export_csv_btn, "export_csv", None))

        counter_frame = ctk.CTkFrame(frame)
        counter_frame.pack(pady=3, padx=10, fill="x")

        widgets["cnt_valid"] = ctk.CTkLabel(counter_frame, text=f"{i18n.t('valid')}: 0",
                                             font=("Arial", 12, "bold"), text_color="#2fa572")
        widgets["cnt_valid"].pack(side="left", padx=15)
        widgets["cnt_invalid"] = ctk.CTkLabel(counter_frame, text=f"{i18n.t('invalid')}: 0",
                                               font=("Arial", 12, "bold"), text_color="#c93c3c")
        widgets["cnt_invalid"].pack(side="left", padx=15)
        widgets["cnt_errors"] = ctk.CTkLabel(counter_frame, text=f"{i18n.t('errors')}: 0",
                                              font=("Arial", 12, "bold"), text_color="#d4a017")
        widgets["cnt_errors"].pack(side="left", padx=15)
        widgets["cnt_total"] = ctk.CTkLabel(counter_frame, text=f"{i18n.t('total')}: 0",
                                             font=("Arial", 12, "bold"))
        widgets["cnt_total"].pack(side="left", padx=15)

        filter_frame = ctk.CTkFrame(frame)
        filter_frame.pack(pady=3, padx=10, fill="x")

        widgets["_log_lines"] = []
        widgets["_filter"] = "all"

        widgets["filter_seg"] = ctk.CTkSegmentedButton(
            filter_frame,
            values=[i18n.t("filter_all"), i18n.t("filter_valid"),
                    i18n.t("filter_invalid"), i18n.t("filter_errors")],
            command=lambda v: self._on_filter(widgets, v)
        )
        widgets["filter_seg"].set(i18n.t("filter_all"))
        widgets["filter_seg"].pack(side="left", padx=5)

        stats_btn = ctk.CTkButton(filter_frame, text=i18n.t("stats"),
                                   command=lambda: self.show_stats(tab_name),
                                   fg_color="#6c5ce7", hover_color="#5a4bd1", width=100)
        stats_btn.pack(side="right", padx=5)
        self._translatable.append((stats_btn, "stats", None))

        widgets["status"] = ctk.CTkLabel(frame, text=i18n.t("ready"), font=("Arial", 12))
        widgets["status"].pack(pady=2)

        widgets["progress"] = ctk.CTkProgressBar(frame, width=1000)
        widgets["progress"].pack(pady=2, padx=10)
        widgets["progress"].set(0)

        output_frame = ctk.CTkFrame(frame)
        output_frame.pack(pady=5, padx=10, fill="both", expand=True)

        widgets["output"] = ctk.CTkTextbox(output_frame)
        widgets["output"].pack(pady=5, padx=5, fill="both", expand=True)

        return widgets

    def import_file(self, widgets):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filepath:
            try:
                tab_name = self._get_tab_for_widgets(widgets)
                lines = []
                chunk_size = 1_000_000
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        chunk = f.readlines(chunk_size)
                        if not chunk:
                            break
                        for line in chunk:
                            stripped = line.strip()
                            if stripped:
                                lines.append(stripped)
                total = len(lines)
                self._loaded_data[tab_name] = lines
                widgets["input"].delete("1.0", "end")
                if total <= _TEXTBOX_DISPLAY_LIMIT:
                    widgets["input"].insert("1.0", "\n".join(lines))
                else:
                    preview = "\n".join(lines[:_TEXTBOX_DISPLAY_LIMIT])
                    widgets["input"].insert(
                        "1.0",
                        f"{preview}\n\n... [{total - _TEXTBOX_DISPLAY_LIMIT} more lines loaded from file] ..."
                    )
                self.log(widgets, i18n.t("file_loaded").format(total))
            except Exception as e:
                self.log(widgets, f"Import error: {e}")

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
        # Fast path for Crypto: if it looks like a plain wallet address, skip all parsing
        if tab_name == "Crypto" and ":" not in raw and "/" not in raw and "|" not in raw:
            return raw

        if tab_name == "Email":
            email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw)
            if email_match:
                return email_match.group(0)

        url_match = re.search(r"https?://[^\s|:]+(?:/[^\s|]*)?", raw)
        cleaned = raw.replace("|", ":")

        if url_match:
            try:
                parsed = urlparse(url_match.group(0))
                path_bits = [part for part in parsed.path.split("/") if part]
                if tab_name in {"Social", "Games", "AI"} and path_bits:
                    return path_bits[-1]
                if tab_name == "Crypto" and path_bits:
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

        # Use pre-loaded file data if available, otherwise read from textbox
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
        proxy = widgets["proxy"].get().strip()

        self.is_running = True
        self.results = []
        self.all_results = []
        self._platform_stats = {}
        widgets["_log_lines"] = []
        widgets["_filter"] = "all"
        widgets["filter_seg"].set(i18n.t("filter_all"))

        self._update_counters(widgets, 0, 0, 0, 0)
        widgets["output"].delete("1.0", "end")
        widgets["status"].configure(text=i18n.t("checking"))
        widgets["progress"].set(0)
        self.log(widgets, i18n.t("preparing_data"))

        thread = threading.Thread(
            target=self._prepare_and_check,
            args=(raw_lines, tab_name, threads, timeout, proxy, widgets),
            daemon=True,
        )
        thread.start()

    def _prepare_and_check(self, raw_lines, tab_name, threads, timeout, proxy, widgets):
        """Normalize + deduplicate data in background thread, then run checks."""
        try:
            original_count = len(raw_lines)

            if tab_name == "Crypto":
                data = self._fast_crypto_filter(raw_lines, widgets)
            else:
                # Normalize in streaming fashion
                if tab_name == "All":
                    data_iter = (d.strip() for d in raw_lines if d.strip())
                else:
                    data_iter = (self._normalize_input_line(d, tab_name) for d in raw_lines if d.strip())

                # Deduplicate using a set for O(1) lookups while preserving order
                seen = set()
                data = []
                for item in data_iter:
                    if item and item not in seen:
                        seen.add(item)
                        data.append(item)
                del seen

            dupes_removed = original_count - len(data)

            if not data:
                self.after(0, lambda: self.log(widgets, i18n.t("no_data")))
                self.after(0, lambda: widgets["status"].configure(text=i18n.t("ready")))
                return

            if dupes_removed > 0:
                self.after(0, lambda: self.log(widgets, i18n.t("duplicates_removed").format(dupes_removed)))
            if tab_name == "All":
                cats = 5
                self.after(0, lambda: self.log(widgets, i18n.t("starting_all").format(len(data), cats, len(data) * cats, threads)))
            else:
                self.after(0, lambda: self.log(widgets, i18n.t("starting").format(len(data), threads)))

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.check_all(data, tab_name, threads, timeout, proxy, widgets))
        except Exception as e:
            self.after(0, lambda: self.log(widgets, f"Error: {e}"))
            self.after(0, lambda: widgets["status"].configure(text=i18n.t("ready")))
        finally:
            self.is_running = False

    def _fast_crypto_filter(self, raw_lines, widgets):
        """Fast filter for Crypto: scan lines for wallet addresses and exchange URLs."""
        from checkers.crypto_checker import _WALLET_PATTERNS, _WALLET_FIRST_CHARS

        exchanges = ("binance", "bybit", "okx", "huobi", "kucoin", "gate.io", "mexc", "bitget")
        seen = set()
        data = []
        total = len(raw_lines)
        report_interval = max(total // 10, 1_000_000)

        for idx, line in enumerate(raw_lines):
            stripped = line.strip()
            if not stripped:
                continue

            if idx % report_interval == 0 and idx > 0:
                pct = idx * 100 // total
                self.after(0, lambda p=pct, i=idx, t=total: self.log(
                    widgets, f"Scanning... {p}% ({i}/{t})"))

            # Extract domain for exchange check (only look at domain, not user/pass)
            domain = ""
            if "://" in stripped:
                after_scheme = stripped.split("://", 1)[1]
                domain = after_scheme.split("/", 1)[0].split(":", 1)[0].lower()
            elif "." in stripped.split(":", 1)[0]:
                domain = stripped.split(":", 1)[0].split("/", 1)[0].lower()

            # Check for exchange in domain only
            if domain:
                for ex in exchanges:
                    if ex in domain:
                        if stripped not in seen:
                            seen.add(stripped)
                            data.append(stripped)
                        break
                else:
                    # Check tokens for wallet addresses
                    self._scan_line_for_wallets(stripped, _WALLET_FIRST_CHARS, _WALLET_PATTERNS, seen, data)
            else:
                self._scan_line_for_wallets(stripped, _WALLET_FIRST_CHARS, _WALLET_PATTERNS, seen, data)

        del seen
        found = len(data)
        self.after(0, lambda: self.log(
            widgets, f"Scan complete: {found} crypto items in {total} lines"))
        return data

    @staticmethod
    def _scan_line_for_wallets(line, first_chars, patterns, seen, data):
        """Scan tokens in a line for crypto wallet addresses."""
        for token in line.split(":"):
            if len(token) < 25 or len(token) > 95:
                continue
            # Remove URL prefix if present
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
        semaphore = asyncio.Semaphore(threads)
        all_categories = ["Email", "Social", "Crypto", "Games", "AI"]
        total = len(data) * len(all_categories) if tab_name == "All" else len(data)
        completed = [0]
        valid_count = [0]
        invalid_count = [0]
        error_count = [0]
        # Throttle UI updates: update every N completions to avoid flooding Tkinter
        ui_update_interval = max(1, total // 2000)

        proxies = []
        if proxy:
            if os.path.isfile(proxy):
                try:
                    with open(proxy, "r") as f:
                        proxies = [line.strip() for line in f if line.strip()]
                except Exception:
                    pass
            else:
                proxies = [proxy]

        connector = aiohttp.TCPConnector(
            limit=threads * 2,
            limit_per_host=min(threads, 50),
            ttl_dns_cache=300,
            force_close=False,
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            async def check_with_sem(data_item, category=None):
                async with semaphore:
                    if not self.is_running:
                        return None

                    p = proxies[completed[0] % len(proxies)] if proxies else None

                    cat = category or tab_name
                    item = data_item
                    if category:
                        item = self._normalize_input_line(data_item, cat)
                        if not item:
                            completed[0] += 1
                            if completed[0] % ui_update_interval == 0:
                                progress = completed[0] / total
                                self.after(0, lambda p=progress: widgets["progress"].set(p))
                            return None
                    result = await self.check_item(item, cat, timeout, p, session)
                    completed[0] += 1

                    if result:
                        tag = result.get("platform", result.get("service", result.get("wallet_type", "")))
                        inp = result.get("input", result.get("email", ""))

                        if result.get("info", {}).get("error"):
                            error_count[0] += 1
                            err_msg = result.get("info", {}).get("error", "")
                            self.after(0, lambda t=tag, i=inp, m=err_msg: self.log_tagged(
                                widgets, "error", f"[!] [{t}] {i} - {m}"))
                        elif result.get("exists"):
                            valid_count[0] += 1
                            self._platform_stats[tag] = self._platform_stats.get(tag, 0) + 1
                            msg = result.get("info", {}).get("message", "")
                            self.after(0, lambda t=tag, i=inp, m=msg: self.log_tagged(
                                widgets, "valid", f"[+] [{t}] {i} - {m}"))

                            auth = result.get("info", {}).get("auth")
                            if auth:
                                self.after(0, lambda a=auth: self.log_tagged(
                                    widgets, "valid", f"    ↳ {i18n.t('auth_type')}: {a['auth_type']}"))
                                self.after(0, lambda a=auth: self.log_tagged(
                                    widgets, "valid", f"    ↳ {i18n.t('auth_wallets')}: {a['wallets']}"))
                                self.after(0, lambda a=auth: self.log_tagged(
                                    widgets, "valid", f"    ↳ {i18n.t('auth_how')}: {a['how']}"))

                            linked = result.get("info", {}).get("linked_services", [])
                            if linked:
                                svc_names = ", ".join(s["service"] for s in linked)
                                self.after(0, lambda i=inp, s=svc_names: self.log_tagged(
                                    widgets, "valid", f"    ↳ {i18n.t('linked')}: {s}"))
                                for svc in linked:
                                    self.after(0, lambda n=svc["service"], m2=svc.get("message", ""): self.log_tagged(
                                        widgets, "valid", f"      • {n}: {m2}"))
                        else:
                            invalid_count[0] += 1
                            msg = result.get("info", {}).get("message", "Not found")
                            self.after(0, lambda t=tag, i=inp, m=msg: self.log_tagged(
                                widgets, "invalid", f"[-] [{t}] {i} - {m}"))

                    if completed[0] % ui_update_interval == 0 or completed[0] == total:
                        progress = completed[0] / total
                        v, inv, err, comp = valid_count[0], invalid_count[0], error_count[0], completed[0]
                        self.after(0, lambda p=progress: widgets["progress"].set(p))
                        self.after(0, lambda: self._update_counters(widgets, v, inv, err, comp))

                    return result

            # Process in batches to avoid scheduling millions of coroutines at once
            results = []
            batch = []

            def _flush_batch():
                nonlocal batch
                if tab_name == "All":
                    tasks = [check_with_sem(item, cat) for item, cat in batch]
                else:
                    tasks = [check_with_sem(item) for item, _ in batch]
                batch = []
                return tasks

            if tab_name == "All":
                for item in data:
                    for cat in all_categories:
                        batch.append((item, cat))
                        if len(batch) >= _GATHER_BATCH_SIZE:
                            if not self.is_running:
                                break
                            batch_results = await asyncio.gather(*_flush_batch())
                            results.extend(batch_results)
                    if not self.is_running:
                        break
            else:
                for item in data:
                    batch.append((item, None))
                    if len(batch) >= _GATHER_BATCH_SIZE:
                        if not self.is_running:
                            break
                        batch_results = await asyncio.gather(*_flush_batch())
                        results.extend(batch_results)

            # Flush remaining items
            if batch and self.is_running:
                batch_results = await asyncio.gather(*_flush_batch())
                results.extend(batch_results)

        # Filter results efficiently — only keep non-None results
        self.all_results = [r for r in results if r]
        self.results = [r for r in self.all_results if r.get("exists")]
        del results  # free the raw list

        v, inv, err = valid_count[0], invalid_count[0], error_count[0]
        self.after(0, lambda: self._update_counters(widgets, v, inv, err, total))
        self.after(0, lambda: widgets["status"].configure(text=i18n.t("ready")))
        self.log(widgets, i18n.t("completed").format(len(self.results), total))
        self.log(widgets, "=" * 50)

    async def check_item(self, data_item, tab_name, timeout, proxy, session):
        checker = self.checkers.get(tab_name)
        try:
            result = await checker.check(data_item, timeout=timeout, proxy=proxy, session=session)
            if tab_name == "Email" and result.get("exists"):
                linked = await self._cross_check_email(data_item, timeout, proxy, session)
                result["info"]["linked_services"] = linked
            return result
        except Exception as e:
            return {"input": data_item, "error": str(e), "exists": False, "info": {"error": str(e)}}
        return {"input": data_item, "exists": False, "info": {}}

    async def _cross_check_email(self, email, timeout, proxy, session):
        linked = []
        username = email.split("@")[0]

        ai_checks = [
            ("chatgpt", self.checkers["AI"]._check_openai, email),
            ("gemini", self.checkers["AI"]._check_gemini, email),
            ("perplexity", self.checkers["AI"]._check_perplexity, email),
            ("claude", self.checkers["AI"]._check_claude, email),
        ]

        social_checks = [
            ("github", self.checkers["Social"]._check_github, username),
            ("instagram", self.checkers["Social"]._check_instagram, username),
            ("twitter", self.checkers["Social"]._check_twitter, username),
            ("tiktok", self.checkers["Social"]._check_tiktok, username),
            ("reddit", self.checkers["Social"]._check_reddit, username),
            ("vk", self.checkers["Social"]._check_vk, username),
            ("telegram", self.checkers["Social"]._check_telegram, username),
        ]

        game_checks = [
            ("steam", self.checkers["Games"]._check_steam, username),
            ("epic", self.checkers["Games"]._check_epic, username),
            ("xbox", self.checkers["Games"]._check_xbox, username),
            ("playstation", self.checkers["Games"]._check_playstation, username),
        ]

        all_checks = ai_checks + social_checks + game_checks

        async def _run_check(name, handler, data):
            try:
                r = await handler(data, timeout, proxy, session)
                if r.get("exists"):
                    return {"service": name, "found": True, "message": r.get("info", {}).get("message", "")}
            except Exception:
                pass
            return None

        tasks = [_run_check(name, handler, data) for name, handler, data in all_checks]
        results = await asyncio.gather(*tasks)

        for r in results:
            if r:
                linked.append(r)

        return linked

    def _update_counters(self, widgets, valid, invalid, errors, total):
        widgets["cnt_valid"].configure(text=f"{i18n.t('valid')}: {valid}")
        widgets["cnt_invalid"].configure(text=f"{i18n.t('invalid')}: {invalid}")
        widgets["cnt_errors"].configure(text=f"{i18n.t('errors')}: {errors}")
        widgets["cnt_total"].configure(text=f"{i18n.t('total')}: {total}")

    def log_tagged(self, widgets, tag, message):
        log_lines = widgets.setdefault("_log_lines", [])
        log_lines.append((tag, message))
        if len(log_lines) > _MAX_LOG_LINES:
            widgets["_log_lines"] = log_lines[-_MAX_LOG_LINES:]
        current_filter = widgets.get("_filter", "all")
        if current_filter == "all" or current_filter == tag:
            self._log_safe(widgets, message)

    def _on_filter(self, widgets, value):
        mapping = {
            i18n.t("filter_all"): "all",
            i18n.t("filter_valid"): "valid",
            i18n.t("filter_invalid"): "invalid",
            i18n.t("filter_errors"): "error",
        }
        self.apply_filter(widgets, mapping.get(value, "all"))

    def apply_filter(self, widgets, filter_type):
        widgets["_filter"] = filter_type
        widgets["output"].delete("1.0", "end")
        for tag, line in widgets.get("_log_lines", []):
            if filter_type == "all" or tag == filter_type or tag == "system":
                self._log_safe(widgets, line)

    def show_stats(self, tab_name):
        widgets = self.tab_widgets[tab_name]

        if not self.all_results:
            self.log(widgets, i18n.t("stats_no_data"))
            return

        win = ctk.CTkToplevel(self)
        win.title(i18n.t("stats_title"))
        win.geometry("500x450")
        win.attributes("-topmost", True)

        valid = len([r for r in self.all_results if r.get("exists")])
        errors = len([r for r in self.all_results if r.get("info", {}).get("error")])
        invalid = len(self.all_results) - valid - errors
        total = len(self.all_results)

        summary_frame = ctk.CTkFrame(win)
        summary_frame.pack(pady=10, padx=15, fill="x")

        ctk.CTkLabel(summary_frame, text=i18n.t("stats_summary"),
                      font=("Arial", 16, "bold")).pack(pady=5)

        canvas = Canvas(summary_frame, width=460, height=130, bg="#2b2b2b",
                         highlightthickness=0, bd=0)
        canvas.pack(pady=5, padx=10)

        max_val = max(valid, invalid, errors, 1)
        bar_max_w = 300

        bars = [
            (i18n.t("valid"), valid, "#2fa572", 10),
            (i18n.t("invalid"), invalid, "#c93c3c", 50),
            (i18n.t("errors"), errors, "#d4a017", 90),
        ]

        for label, count, color, y in bars:
            w = int((count / max_val) * bar_max_w) if max_val > 0 else 0
            canvas.create_rectangle(120, y, 120 + max(w, 2), y + 25,
                                     fill=color, outline="")
            pct = f"{count * 100 // total}%" if total > 0 else "0%"
            canvas.create_text(10, y + 12, text=f"{label}: {count}",
                                anchor="w", fill="white", font=("Arial", 11))
            canvas.create_text(440, y + 12, text=pct, anchor="w",
                                fill="white", font=("Arial", 11, "bold"))

        platform_frame = ctk.CTkFrame(win)
        platform_frame.pack(pady=10, padx=15, fill="both", expand=True)

        ctk.CTkLabel(platform_frame, text=i18n.t("stats_by_platform"),
                      font=("Arial", 14, "bold")).pack(pady=5)

        scroll = ctk.CTkScrollableFrame(platform_frame, height=180)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        for platform, count in sorted(self._platform_stats.items(), key=lambda x: -x[1]):
            ctk.CTkLabel(scroll, text=f"  {platform}: {count} {i18n.t('stats_found')}",
                          font=("Arial", 12), anchor="w").pack(fill="x", padx=10, pady=1)

        if not self._platform_stats:
            ctk.CTkLabel(scroll, text="  —", font=("Arial", 12)).pack()

    def stop_check(self):
        self.is_running = False

    def clear_output(self, widgets):
        widgets["output"].delete("1.0", "end")
        widgets["input"].delete("1.0", "end")
        widgets["progress"].set(0)
        self._update_counters(widgets, 0, 0, 0, 0)
        widgets["_log_lines"] = []
        widgets["_filter"] = "all"
        widgets["filter_seg"].set(i18n.t("filter_all"))
        tab_name = self._get_tab_for_widgets(widgets)
        self._loaded_data.pop(tab_name, None)

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
                            flat = {}
                            for k, v in r.items():
                                flat[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v
                            writer.writerow(flat)
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    for r in self.results:
                        f.write(f"{json.dumps(r, ensure_ascii=False)}\n")
            self.log(widgets, i18n.t("exported").format(filename))
        except Exception as e:
            self.log(widgets, f"Export error: {e}")

    def log(self, widgets, message):
        widgets.setdefault("_log_lines", []).append(("system", message))
        self.after(0, lambda: self._log_safe(widgets, message))

    def _log_safe(self, widgets, message):
        try:
            widgets["output"].insert("end", f"{message}\n")
            widgets["output"].see("end")
        except Exception:
            pass


if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
