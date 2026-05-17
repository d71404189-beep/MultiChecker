# -*- coding: utf-8 -*-
"""
Dump Crypto Checker v1.0.86
Умный парсер дампов для крипто чекера.

Из каждой строки дампа извлекает ВСЕ типы данных:
  - Крипто адреса (BTC, ETH, TRX, SOL, TON, ...)
  - Приватные ключи (HEX, WIF)
  - Сид-фразы (12/24 слова)
  - Биржевые credentials (url:mail:pass, mail:pass, exchange:key:secret)

Затем проверяет балансы по каждому найденному элементу.
"""

import re
import asyncio
import aiohttp
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
#  ПАТТЕРНЫ
# ═══════════════════════════════════════════════════════════════════════════

_RE_ETH_ADDR    = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
_RE_BTC_ADDR    = re.compile(r'\b(bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-zA-HJ-NP-Z0-9]{25,34})\b')
_RE_TRX_ADDR    = re.compile(r'\bT[a-zA-HJ-NP-Z0-9]{33}\b')
_RE_SOL_ADDR    = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
_RE_TON_ADDR    = re.compile(r'\b(EQ|UQ)[a-zA-Z0-9_\-]{46}\b')
_RE_PRIVKEY_HEX = re.compile(r'\b(0x)?[a-fA-F0-9]{64}\b')
_RE_PRIVKEY_WIF = re.compile(r'\b[5KLc][1-9A-HJ-NP-Za-km-z]{50,51}\b')
_RE_SEED        = re.compile(r'\b([a-z]{3,12}\s){11,23}[a-z]{3,12}\b', re.IGNORECASE)
_RE_EMAIL       = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_RE_URL         = re.compile(r'https?://[^\s:]+')

# Биржи для определения по домену/ключевому слову
_EXCHANGE_KEYWORDS = {
    "binance": ["binance", "bnb"],
    "bybit":   ["bybit"],
    "okx":     ["okx"],
    "kucoin":  ["kucoin"],
    "gate":    ["gate.io", "gateio"],
    "mexc":    ["mexc"],
    "bitget":  ["bitget"],
    "huobi":   ["huobi"],
    "coinbase":["coinbase"],
    "kraken":  ["kraken"],
}

_EXCHANGE_DOMAINS = {
    "binance.com": "binance", "accounts.binance.com": "binance",
    "bybit.com": "bybit",
    "okx.com": "okx",
    "kucoin.com": "kucoin",
    "gate.io": "gate",
    "mexc.com": "mexc",
    "bitget.com": "bitget",
    "huobi.com": "huobi",
    "coinbase.com": "coinbase",
    "kraken.com": "kraken",
}


# ═══════════════════════════════════════════════════════════════════════════
#  ПАРСЕР СТРОКИ
# ═══════════════════════════════════════════════════════════════════════════

class DumpLineParser:
    """Парсит одну строку дампа и извлекает все типы данных"""

    @staticmethod
    def parse(line: str) -> Dict[str, Any]:
        """
        Возвращает словарь:
        {
          "original": str,
          "type": "exchange" | "crypto_address" | "privkey" | "seed" | "unknown",
          "exchange": str | None,
          "login": str | None,
          "password": str | None,
          "crypto_items": [{"type": "btc"|"eth"|..., "value": str}, ...]
        }
        """
        s = line.strip()
        if not s:
            return {}

        result = {
            "original": s,
            "type": "unknown",
            "exchange": None,
            "login": None,
            "password": None,
            "crypto_items": [],
        }

        # ── 1. Сид-фраза (12-24 слова)
        seed_m = _RE_SEED.search(s)
        if seed_m:
            words = seed_m.group(0).strip().split()
            if len(words) in (12, 15, 18, 21, 24):
                result["type"] = "seed"
                result["crypto_items"].append({"type": "seed", "value": seed_m.group(0).strip()})
                return result

        # ── 2. Приватный ключ WIF
        wif_m = _RE_PRIVKEY_WIF.search(s)
        if wif_m:
            result["type"] = "privkey"
            result["crypto_items"].append({"type": "privkey_wif", "value": wif_m.group(0)})
            return result

        # ── 3. Приватный ключ HEX (64 hex символа)
        hex_m = _RE_PRIVKEY_HEX.search(s)
        if hex_m:
            val = hex_m.group(0)
            # Убеждаемся что это не просто часть адреса
            if len(val.replace("0x", "")) == 64:
                result["type"] = "privkey"
                result["crypto_items"].append({"type": "privkey_hex", "value": val})
                return result

        # ── 4. Биржевые credentials
        exchange, login, password = DumpLineParser._parse_exchange_line(s)
        if exchange and (login or password):
            result["type"] = "exchange"
            result["exchange"] = exchange
            result["login"] = login
            result["password"] = password
            return result

        # ── 5. Крипто адреса
        items = []

        # TON (проверяем первым — специфичный паттерн)
        for m in _RE_TON_ADDR.finditer(s):
            items.append({"type": "ton", "value": m.group(0)})

        # ETH
        for m in _RE_ETH_ADDR.finditer(s):
            items.append({"type": "ethereum", "value": m.group(0)})

        # TRX
        for m in _RE_TRX_ADDR.finditer(s):
            items.append({"type": "tron", "value": m.group(0)})

        # BTC
        for m in _RE_BTC_ADDR.finditer(s):
            items.append({"type": "bitcoin", "value": m.group(0)})

        if items:
            result["type"] = "crypto_address"
            result["crypto_items"] = items
            return result

        # ── 6. Просто email без пароля — тоже сохраняем
        email_m = _RE_EMAIL.search(s)
        if email_m:
            exchange = DumpLineParser._detect_exchange_by_email(email_m.group(0))
            result["type"] = "exchange"
            result["exchange"] = exchange or "exchange"
            result["login"] = email_m.group(0)
            result["password"] = ""
            return result

        return result

    @staticmethod
    def _parse_exchange_line(s: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Извлекает (exchange, login, password) из строки"""
        norm = s.replace("|", ":")

        # Формат с протоколом: https://site.com:login:pass
        if norm.startswith(("https://", "http://")):
            proto_end = norm.index("://") + 3
            colon = norm.find(":", proto_end)
            if colon == -1:
                return None, None, None
            domain_part = norm[proto_end:colon].split("/")[0]
            exchange = DumpLineParser._detect_exchange_by_domain(domain_part)
            if not exchange:
                exchange = DumpLineParser._detect_exchange_by_keyword(norm)
            after = norm[colon + 1:].lstrip("/")
            parts = after.split(":", 1)
            login = parts[0].strip()
            password = parts[1].strip() if len(parts) > 1 else ""
            if login:
                return exchange or "exchange", login, password
            return None, None, None

        # Формат без протокола: site.com:login:pass или site.com/path:login:pass
        first_colon = norm.find(":")
        if first_colon > 0:
            possible_domain = norm[:first_colon]
            if "." in possible_domain and "@" not in possible_domain:
                domain_clean = possible_domain.split("/")[0]
                exchange = DumpLineParser._detect_exchange_by_domain(domain_clean)
                if not exchange:
                    exchange = DumpLineParser._detect_exchange_by_keyword(norm)
                after = norm[first_colon + 1:].lstrip("/")
                parts = after.split(":", 1)
                login = parts[0].strip()
                password = parts[1].strip() if len(parts) > 1 else ""
                if login:
                    return exchange or "exchange", login, password
                return None, None, None

        # Формат: exchange_name:key:secret (API ключи)
        parts = norm.split(":")
        if len(parts) >= 3:
            ex_name = parts[0].lower().strip()
            from checkers.exchange_checker import EXCHANGE_NAMES
            if ex_name in EXCHANGE_NAMES:
                return ex_name, parts[1].strip(), parts[2].strip()

        # Формат: email:password
        if len(parts) >= 2:
            email_m = _RE_EMAIL.match(parts[0].strip())
            if email_m:
                exchange = DumpLineParser._detect_exchange_by_email(email_m.group(0))
                return exchange or "exchange", parts[0].strip(), ":".join(parts[1:]).strip()

        return None, None, None

    @staticmethod
    def _detect_exchange_by_domain(domain: str) -> Optional[str]:
        dl = domain.lower()
        for d, ex in _EXCHANGE_DOMAINS.items():
            if d in dl:
                return ex
        return None

    @staticmethod
    def _detect_exchange_by_keyword(text: str) -> Optional[str]:
        tl = text.lower()
        for ex, keywords in _EXCHANGE_KEYWORDS.items():
            for kw in keywords:
                if kw in tl:
                    return ex
        return None

    @staticmethod
    def _detect_exchange_by_email(email: str) -> Optional[str]:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        for d, ex in _EXCHANGE_DOMAINS.items():
            if d in domain:
                return ex
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  УМНЫЙ ДАМП ЧЕКЕР
# ═══════════════════════════════════════════════════════════════════════════

class SmartDumpChecker:
    """
    Принимает дамп (список строк), парсит каждую строку,
    определяет тип данных и возвращает список элементов для проверки.
    """

    def __init__(self):
        self.stats = {
            "total": 0,
            "seeds": 0,
            "privkeys": 0,
            "addresses": 0,
            "exchange_creds": 0,
            "exchange_api": 0,
            "unknown": 0,
            "duplicates_removed": 0,
        }

    def parse_dump(self, text: str) -> Dict[str, List]:
        """
        Парсит дамп и возвращает словарь:
        {
          "crypto":   [строки для crypto_checker],
          "exchange": [строки для exchange checker (login:pass)],
          "api_keys": [строки для API key checker (exchange:key:secret)],
          "parsed":   [полные распарсенные объекты],
        }
        """
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        self.stats["total"] = len(lines)

        crypto_items = []
        exchange_items = []
        api_key_items = []
        parsed_all = []

        seen = set()

        for line in lines:
            parsed = DumpLineParser.parse(line)
            if not parsed or parsed["type"] == "unknown":
                self.stats["unknown"] += 1
                continue

            parsed_all.append(parsed)
            t = parsed["type"]

            if t == "seed":
                for item in parsed["crypto_items"]:
                    val = item["value"]
                    if val not in seen:
                        seen.add(val)
                        crypto_items.append(val)
                        self.stats["seeds"] += 1
                    else:
                        self.stats["duplicates_removed"] += 1

            elif t == "privkey":
                for item in parsed["crypto_items"]:
                    val = item["value"]
                    if val not in seen:
                        seen.add(val)
                        crypto_items.append(val)
                        self.stats["privkeys"] += 1
                    else:
                        self.stats["duplicates_removed"] += 1

            elif t == "crypto_address":
                for item in parsed["crypto_items"]:
                    val = item["value"]
                    if val not in seen:
                        seen.add(val)
                        crypto_items.append(val)
                        self.stats["addresses"] += 1
                    else:
                        self.stats["duplicates_removed"] += 1

            elif t == "exchange":
                login    = parsed.get("login", "")
                password = parsed.get("password", "")
                exchange = parsed.get("exchange", "exchange")

                # Определяем — это API ключи или обычные credentials
                from checkers.exchange_checker import EXCHANGE_NAMES, detect_api_format
                api_fmt = detect_api_format(line)
                if api_fmt:
                    if line not in seen:
                        seen.add(line)
                        api_key_items.append(line)
                        self.stats["exchange_api"] += 1
                    else:
                        self.stats["duplicates_removed"] += 1
                else:
                    # Обычные credentials — формируем строку для crypto_checker
                    # Формат: exchange:login:pass или login:pass
                    if login:
                        if exchange and exchange != "exchange":
                            cred_str = f"{exchange}:{login}:{password}" if password else f"{exchange}:{login}"
                        else:
                            cred_str = f"{login}:{password}" if password else login
                        if cred_str not in seen:
                            seen.add(cred_str)
                            exchange_items.append(cred_str)
                            self.stats["exchange_creds"] += 1
                        else:
                            self.stats["duplicates_removed"] += 1

        return {
            "crypto":   crypto_items,
            "exchange": exchange_items,
            "api_keys": api_key_items,
            "parsed":   parsed_all,
        }

    def format_stats(self) -> str:
        s = self.stats
        lines = [
            f"📊 Всего строк:        {s['total']}",
            f"🌱 Сид-фраз:           {s['seeds']}",
            f"🔑 Приватных ключей:   {s['privkeys']}",
            f"📍 Крипто адресов:     {s['addresses']}",
            f"🏦 Биржевых аккаунтов: {s['exchange_creds']}",
            f"🔐 API ключей:         {s['exchange_api']}",
            f"❓ Нераспознано:       {s['unknown']}",
            f"🔁 Дубликатов удалено: {s['duplicates_removed']}",
        ]
        return "\n".join(lines)

    def get_all_for_checker(self, parsed: Dict[str, List]) -> List[str]:
        """Возвращает все элементы для проверки в одном списке"""
        return parsed["crypto"] + parsed["exchange"] + parsed["api_keys"]
