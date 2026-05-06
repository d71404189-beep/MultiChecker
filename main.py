import customtkinter as ctk
from tkinter import Text
import asyncio
import aiohttp
import threading
import json
from datetime import datetime
import sys
import os

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
        
        self.checkers = {
            "Email": EmailChecker(),
            "Social": SocialChecker(),
            "Crypto": CryptoChecker(),
            "Games": GameChecker(),
            "AI": AIChecker()
        }
        
        self.tab_widgets = {}
        self.setup_ui()
        
    def setup_ui(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(top_frame, text=i18n.t("title"), font=("Arial", 20, "bold")).pack(side="left", padx=10)
        
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
        self.lang_btn.deselect() if i18n.current_lang == "en" else self.lang_btn.select()
    
    def create_tab_content(self, frame, tab_name):
        widgets = {}
        
        header = ctk.CTkLabel(frame, text=f"{i18n.t(tab_name.lower())} Checker", font=("Arial", 18, "bold"))
        header.pack(pady=5)
        
        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(input_frame, text=i18n.t("input_label")).pack(anchor="w", padx=5, pady=2)
        
        widgets["input"] = Text(input_frame, height=6, width=100)
        widgets["input"].pack(pady=5, padx=5)
        
        settings_frame = ctk.CTkFrame(frame)
        settings_frame.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(settings_frame, text=i18n.t("threads")).pack(side="left", padx=5)
        widgets["threads"] = ctk.CTkSlider(settings_frame, from_=1, to=200, number_of_steps=199)
        widgets["threads"].set(50)
        widgets["threads"].pack(side="left", padx=5)
        
        ctk.CTkLabel(settings_frame, text=i18n.t("timeout")).pack(side="left", padx=10)
        widgets["timeout"] = ctk.CTkEntry(settings_frame, width=50)
        widgets["timeout"].insert(0, "10")
        widgets["timeout"].pack(side="left", padx=5)
        
        ctk.CTkLabel(settings_frame, text=i18n.t("proxy")).pack(side="left", padx=10)
        widgets["proxy"] = ctk.CTkEntry(settings_frame, width=150, placeholder_text=i18n.t("proxy_placeholder"))
        widgets["proxy"].pack(side="left", padx=5)
        
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkButton(btn_frame, text=i18n.t("start"), command=lambda: self.start_check(tab_name),
                     fg_color="#2fa572", hover_color="#258e63").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=i18n.t("stop"), command=self.stop_check,
                     fg_color="#c93c3c", hover_color="#a32f2f").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=i18n.t("clear"), command=lambda: self.clear_output(widgets)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=i18n.t("export"), command=lambda: self.export_valid(widgets)).pack(side="left", padx=5)
        
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
    
    def start_check(self, tab_name):
        widgets = self.tab_widgets[tab_name]
        data = widgets["input"].get("1.0", "end").strip().split('\n')
        data = [d.strip() for d in data if d.strip()]
        
        if not data:
            self.log(widgets, i18n.t("no_data"))
            return
        
        threads = int(widgets["threads"].get())
        timeout = int(widgets["timeout"].get())
        proxy = widgets["proxy"].get().strip()
        
        self.is_running = True
        self.results = []
        
        self.log(widgets, i18n.t("starting").format(len(data), threads))
        widgets["progress"].set(0)
        
        thread = threading.Thread(target=self.run_async_check, 
                                  args=(data, tab_name, threads, timeout, proxy, widgets))
        thread.start()
    
    def run_async_check(self, data, tab_name, threads, timeout, proxy, widgets):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.check_all(data, tab_name, threads, timeout, proxy, widgets))
    
    async def check_all(self, data, tab_name, threads, timeout, proxy, widgets):
        semaphore = asyncio.Semaphore(threads)
        total = len(data)
        completed = [0]
        
        proxies = []
        if proxy:
            if os.path.isfile(proxy):
                try:
                    with open(proxy, 'r') as f:
                        proxies = [line.strip() for line in f if line.strip()]
                except:
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
                    
                    progress = completed[0] / total
                    self.after(0, lambda p=progress: widgets["progress"].set(p))
                    
                    return result
            
            tasks = [check_with_sem(item) for item in data]
            results = await asyncio.gather(*tasks)
        
        valid_results = [r for r in results if r and r.get('exists')]
        self.results = valid_results
        
        self.log(widgets, i18n.t("completed").format(len(valid_results), total))
        self.log(widgets, "=" * 50)
        for r in valid_results:
            self.log(widgets, f"[{r.get('platform', r.get('service', r.get('wallet_type', 'unknown')))}] {r.get('input', r.get('email', r.get('data', 'N/A')))} - {r.get('info', {})}")
    
    async def check_item(self, data_item, tab_name, timeout, proxy, session):
        checker = self.checkers.get(tab_name)
        
        try:
            if tab_name == "Email":
                return await checker.check(data_item, timeout)
            elif tab_name == "Social":
                return await checker.check(data_item, timeout=timeout)
            elif tab_name == "Crypto":
                return await checker.check(data_item, timeout)
            elif tab_name == "Games":
                return await checker.check(data_item, timeout=timeout)
            elif tab_name == "AI":
                return await checker.check(data_item, timeout=timeout)
        except Exception as e:
            return {"input": data_item, "error": str(e), "exists": False}
        
        return {"input": data_item, "exists": False}
    
    def stop_check(self):
        self.is_running = False
    
    def clear_output(self, widgets):
        widgets["output"].delete("1.0", "end")
        widgets["progress"].set(0)
    
    def export_valid(self, widgets):
        if not self.results:
            self.log(widgets, i18n.t("no_results"))
            return
        
        filename = f"valid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w') as f:
                for r in self.results:
                    f.write(f"{json.dumps(r)}\n")
            self.log(widgets, i18n.t("exported").format(filename))
        except Exception as e:
            self.log(widgets, f"Export error: {e}")
    
    def log(self, widgets, message):
        widgets["output"].insert("end", f"{message}\n")
        widgets["output"].see("end")

if __name__ == "__main__":
    app = MultiCheckerApp()
    app.mainloop()
