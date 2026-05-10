import customtkinter as ctk
from tkinter import filedialog
import asyncio
import aiohttp
import csv
import io
import json
import os
import re
import sys
import threading
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))

from checkers.email_checker import EmailChecker
from checkers.social_checker import SocialChecker
from checkers.crypto_checker import CryptoChecker
from checkers.game_checker import GameChecker
from checkers.ai_checker import AIChecker
import i18n

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MultiCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(i18n.t("title"))
        self.geometry("1100x750")

        self.is_running = False
        self.results = []
        self.all_results = []

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

        tabs = ["Email", "Social", "Crypto", "Games", "AI"]
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
        for tab_name, widgets in self.tab_widgets.items():
            widgets["status"].configure(text=i18n.t("ready"))

    def create_tab_content(self, frame, tab_name):
        widgets = {}

        header = ctk.CTkLabel(frame, text=f"{i18n.t(tab_name.lower())} Checker", font=("Arial", 18, "bold"))
        header.pack(pady=5)
        self._translatable.append((header, tab_name.lower(), "{} Checker"))

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

        widgets["threads"] = ctk.CTkSlider(settings_frame, from_=1, to=200, number_of_steps=199)
        widgets["threads"].set(50)
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
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f if line.strip()]
                widgets["input"].delete("1.0", "end")
                widgets["input"].insert("1.0", "\n".join(lines))
                self.log(widgets, i18n.t("file_loaded").format(len(lines)))
            except Exception as e:
                self.log(widgets, f"Import error: {e}")

    def _safe_int(self, value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_input_line(self, line, tab_name):
        raw = line.strip()
        if not raw:
            return ""

        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw)
        if tab_name == "Email" and email_match:
            return email_match.group(0)

        url_match = re.search(r"https?://[^\s|:]+(?:/[^\s|]*)?", raw)
        cleaned = raw.replace("|", ":")

        if url_match:
            parsed = urlparse(url_match.group(0))
            path_bits = [part for part in parsed.path.split("/") if part]
            if tab_name in {"Social", "Games", "AI"} and path_bits:
                return path_bits[-1]
            if tab_name == "Crypto" and path_bits:
                return path_bits[-1]

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
        raw_data = widgets["input"].get("1.0", "end").strip().split("\n")
        data = [self._normalize_input_line(d, tab_name) for d in raw_data if d.strip()]
        data = [d for d in data if d]

        if not data:
            self.log(widgets, i18n.t("no_data"))
            return

        threads = self._safe_int(widgets["threads"].get(), 50)
        timeout = self._safe_int(widgets["timeout"].get(), 10)
        proxy = widgets["proxy"].get().strip()

        self.is_running = True
        self.results = []
        self.all_results = []

        self._update_counters(widgets, 0, 0, 0, 0)
        widgets["status"].configure(text=i18n.t("checking"))
        self.log(widgets, i18n.t("starting").format(len(data), threads))
        widgets["progress"].set(0)

        thread = threading.Thread(
            target=self.run_async_check,
            args=(data, tab_name, threads, timeout, proxy, widgets),
            daemon=True,
        )
        thread.start()

    def run_async_check(self, data, tab_name, threads, timeout, proxy, widgets):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.check_all(data, tab_name, threads, timeout, proxy, widgets))

    async def check_all(self, data, tab_name, threads, timeout, proxy, widgets):
        semaphore = asyncio.Semaphore(threads)
        total = len(data)
        completed = [0]
        valid_count = [0]
        invalid_count = [0]
        error_count = [0]

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

        connector = aiohttp.TCPConnector(limit=threads, limit_per_host=threads)

        async with aiohttp.ClientSession(connector=connector) as session:
            async def check_with_sem(data_item):
                async with semaphore:
                    if not self.is_running:
                        return None

                    p = proxies[completed[0] % len(proxies)] if proxies else None

                    result = await self.check_item(data_item, tab_name, timeout, p, session)
                    completed[0] += 1

                    if result:
                        if result.get("info", {}).get("error"):
                            error_count[0] += 1
                        elif result.get("exists"):
                            valid_count[0] += 1
                        else:
                            invalid_count[0] += 1

                    progress = completed[0] / total
                    v, inv, err, comp = valid_count[0], invalid_count[0], error_count[0], completed[0]
                    self.after(0, lambda p=progress: widgets["progress"].set(p))
                    self.after(0, lambda: self._update_counters(widgets, v, inv, err, comp))

                    if result and result.get("exists"):
                        tag = result.get("platform", result.get("service", result.get("wallet_type", "")))
                        inp = result.get("input", result.get("email", ""))
                        msg = result.get("info", {}).get("message", "")
                        self.after(0, lambda t=tag, i=inp, m=msg: self.log(
                            widgets, f"[+] [{t}] {i} - {m}"))

                        linked = result.get("info", {}).get("linked_services", [])
                        if linked:
                            svc_names = ", ".join(s["service"] for s in linked)
                            self.after(0, lambda i=inp, s=svc_names: self.log(
                                widgets, f"    ↳ {i18n.t('linked')}: {s}"))
                            for svc in linked:
                                self.after(0, lambda n=svc["service"], m2=svc.get("message", ""): self.log(
                                    widgets, f"      • {n}: {m2}"))

                    return result

            tasks = [check_with_sem(item) for item in data]
            results = await asyncio.gather(*tasks)

        self.all_results = [r for r in results if r]
        self.results = [r for r in results if r and r.get("exists")]

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

    def stop_check(self):
        self.is_running = False

    def clear_output(self, widgets):
        widgets["output"].delete("1.0", "end")
        widgets["progress"].set(0)
        self._update_counters(widgets, 0, 0, 0, 0)

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
