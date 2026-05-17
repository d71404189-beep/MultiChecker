# -*- coding: utf-8 -*-
"""
Exchange Checker v1.0.85
Проверка балансов на биржах через API ключи + экспорт аккаунтов
Форматы входных данных:
  binance:API_KEY:SECRET_KEY
  bybit:API_KEY:SECRET_KEY
  okx:API_KEY:SECRET_KEY:PASSPHRASE
  kucoin:API_KEY:SECRET_KEY:PASSPHRASE
  gate:API_KEY:SECRET_KEY
  mexc:API_KEY:SECRET_KEY
  bitget:API_KEY:SECRET_KEY:PASSPHRASE
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time
import base64
import json
import csv
import re
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlencode
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
#  ПАТТЕРНЫ РАСПОЗНАВАНИЯ
# ═══════════════════════════════════════════════════════════════════════════

# API ключи обычно 32-64 символа hex/alphanumeric
_API_KEY_RE = re.compile(r'^[a-zA-Z0-9\-_]{20,80}$')

EXCHANGE_NAMES = {
    "binance": "Binance",
    "bybit": "Bybit",
    "okx": "OKX",
    "kucoin": "KuCoin",
    "gate": "Gate.io",
    "mexc": "MEXC",
    "bitget": "Bitget",
    "huobi": "Huobi",
    "kraken": "Kraken",
    "coinbase": "Coinbase",
}


def detect_api_format(data: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Определить формат API ключа.
    Возвращает (exchange, api_key, api_secret, passphrase) или None.

    Поддерживаемые форматы:
      binance:KEY:SECRET
      okx:KEY:SECRET:PASSPHRASE
      kucoin:KEY:SECRET:PASSPHRASE
      bitget:KEY:SECRET:PASSPHRASE
    """
    s = data.strip()
    parts = s.split(":")

    if len(parts) < 3:
        return None

    exchange = parts[0].lower().strip()
    if exchange not in EXCHANGE_NAMES:
        return None

    api_key    = parts[1].strip()
    api_secret = parts[2].strip()
    passphrase = parts[3].strip() if len(parts) > 3 else ""

    # Минимальная валидация — ключи не пустые и похожи на API ключи
    if not api_key or not api_secret:
        return None
    if len(api_key) < 10 or len(api_secret) < 10:
        return None

    return (exchange, api_key, api_secret, passphrase)


# ═══════════════════════════════════════════════════════════════════════════
#  BINANCE
# ═══════════════════════════════════════════════════════════════════════════

async def _check_binance(api_key: str, api_secret: str, session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "binance", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = int(time.time() * 1000)
        params = f"timestamp={ts}"
        sig = hmac.new(api_secret.encode(), params.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/api/v3/account?{params}&signature={sig}"
        headers = {"X-MBX-APIKEY": api_key}

        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            data = await resp.json()
            if resp.status == 200:
                result["valid"] = True
                result["permissions"] = data.get("permissions", [])
                for b in data.get("balances", []):
                    total = float(b["free"]) + float(b["locked"])
                    if total > 0:
                        result["balances"][b["asset"]] = total

                # Цены для расчёта USD
                prices = await _get_binance_prices(session, timeout)
                for asset, amt in result["balances"].items():
                    if asset in ("USDT", "USDC", "BUSD", "FDUSD"):
                        result["total_usd"] += amt
                    elif f"{asset}USDT" in prices:
                        result["total_usd"] += amt * prices[f"{asset}USDT"]

                # Futures баланс
                ts2 = int(time.time() * 1000)
                p2 = f"timestamp={ts2}"
                s2 = hmac.new(api_secret.encode(), p2.encode(), hashlib.sha256).hexdigest()
                fut_url = f"https://fapi.binance.com/fapi/v2/balance?{p2}&signature={s2}"
                try:
                    async with session.get(fut_url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as fr:
                        if fr.status == 200:
                            fut_data = await fr.json()
                            futures = {}
                            for fb in fut_data:
                                bal = float(fb.get("balance", 0))
                                if bal > 0:
                                    futures[fb["asset"]] = bal
                                    if fb["asset"] in ("USDT", "USDC", "BUSD"):
                                        result["total_usd"] += bal
                            result["futures"] = futures
                except Exception:
                    pass

            elif resp.status == 401:
                result["error"] = "Неверный API ключ или подпись"
            elif resp.status == 403:
                result["error"] = "Нет прав доступа (проверьте разрешения ключа)"
            else:
                result["error"] = f"HTTP {resp.status}: {data.get('msg', '')}"
    except Exception as e:
        result["error"] = str(e)
    return result


async def _get_binance_prices(session: aiohttp.ClientSession, timeout: int) -> Dict[str, float]:
    try:
        async with session.get("https://api.binance.com/api/v3/ticker/price",
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {item["symbol"]: float(item["price"]) for item in data}
    except Exception:
        pass
    return {}


# ═══════════════════════════════════════════════════════════════════════════
#  BYBIT
# ═══════════════════════════════════════════════════════════════════════════

async def _check_bybit(api_key: str, api_secret: str, session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "bybit", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = str(int(time.time() * 1000))
        recv_window = "5000"
        query = f"accountType=UNIFIED"
        sign_str = ts + api_key + recv_window + query
        sig = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": recv_window,
        }
        url = f"https://api.bybit.com/v5/account/wallet-balance?{query}"
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            data = await resp.json()
            if resp.status == 200 and data.get("retCode") == 0:
                result["valid"] = True
                for wallet in data.get("result", {}).get("list", []):
                    for coin in wallet.get("coin", []):
                        amt = float(coin.get("walletBalance", 0))
                        usd = float(coin.get("usdValue", 0))
                        if amt > 0:
                            result["balances"][coin["coin"]] = amt
                            result["total_usd"] += usd
            else:
                result["error"] = data.get("retMsg", f"HTTP {resp.status}")
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  OKX
# ═══════════════════════════════════════════════════════════════════════════

async def _check_okx(api_key: str, api_secret: str, passphrase: str,
                     session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "okx", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        path = "/api/v5/account/balance"
        prehash = ts + "GET" + path
        sig = base64.b64encode(
            hmac.new(api_secret.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
        }
        async with session.get(f"https://www.okx.com{path}", headers=headers,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            data = await resp.json()
            if resp.status == 200 and data.get("code") == "0":
                result["valid"] = True
                for account in data.get("data", []):
                    for detail in account.get("details", []):
                        amt = float(detail.get("cashBal", 0))
                        usd = float(detail.get("eqUsd", 0))
                        if amt > 0:
                            result["balances"][detail["ccy"]] = amt
                            result["total_usd"] += usd
            else:
                result["error"] = data.get("msg", f"HTTP {resp.status}")
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  KUCOIN
# ═══════════════════════════════════════════════════════════════════════════

async def _check_kucoin(api_key: str, api_secret: str, passphrase: str,
                        session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "kucoin", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = str(int(time.time() * 1000))
        endpoint = "/api/v1/accounts"
        sign_str = ts + "GET" + endpoint
        sig = base64.b64encode(
            hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha256).digest()
        ).decode()
        pp_sig = base64.b64encode(
            hmac.new(api_secret.encode(), passphrase.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": sig,
            "KC-API-TIMESTAMP": ts,
            "KC-API-PASSPHRASE": pp_sig,
            "KC-API-KEY-VERSION": "2",
        }
        async with session.get(f"https://api.kucoin.com{endpoint}", headers=headers,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            data = await resp.json()
            if resp.status == 200 and data.get("code") == "200000":
                result["valid"] = True
                for acc in data.get("data", []):
                    amt = float(acc.get("balance", 0))
                    if amt > 0:
                        cur = acc["currency"]
                        result["balances"][cur] = result["balances"].get(cur, 0) + amt
                        if cur in ("USDT", "USDC"):
                            result["total_usd"] += amt
            else:
                result["error"] = data.get("msg", f"HTTP {resp.status}")
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  GATE.IO
# ═══════════════════════════════════════════════════════════════════════════

async def _check_gate(api_key: str, api_secret: str, session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "gate", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = str(int(time.time()))
        path = "/api/v4/spot/accounts"
        body_hash = hashlib.sha512(b"").hexdigest()
        sign_str = f"GET\n{path}\n\n{body_hash}\n{ts}"
        sig = hmac.new(api_secret.encode(), sign_str.encode(), hashlib.sha512).hexdigest()
        headers = {"KEY": api_key, "SIGN": sig, "Timestamp": ts, "Content-Type": "application/json"}
        async with session.get(f"https://api.gateio.ws{path}", headers=headers,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json()
                result["valid"] = True
                for acc in data:
                    amt = float(acc.get("available", 0)) + float(acc.get("locked", 0))
                    if amt > 0:
                        cur = acc["currency"]
                        result["balances"][cur] = amt
                        if cur in ("USDT", "USDC"):
                            result["total_usd"] += amt
            else:
                result["error"] = f"HTTP {resp.status}"
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  MEXC
# ═══════════════════════════════════════════════════════════════════════════

async def _check_mexc(api_key: str, api_secret: str, session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "mexc", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = str(int(time.time() * 1000))
        params = f"timestamp={ts}"
        sig = hmac.new(api_secret.encode(), params.encode(), hashlib.sha256).hexdigest()
        url = f"https://api.mexc.com/api/v3/account?{params}&signature={sig}"
        headers = {"X-MEXC-APIKEY": api_key}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json()
                result["valid"] = True
                for b in data.get("balances", []):
                    total = float(b["free"]) + float(b["locked"])
                    if total > 0:
                        result["balances"][b["asset"]] = total
                        if b["asset"] in ("USDT", "USDC"):
                            result["total_usd"] += total
            else:
                result["error"] = f"HTTP {resp.status}"
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  BITGET
# ═══════════════════════════════════════════════════════════════════════════

async def _check_bitget(api_key: str, api_secret: str, passphrase: str,
                        session: aiohttp.ClientSession, timeout: int) -> Dict:
    result = {"exchange": "bitget", "valid": False, "balances": {}, "total_usd": 0.0, "error": None}
    try:
        ts = str(int(time.time() * 1000))
        path = "/api/spot/v1/account/assets"
        prehash = ts + "GET" + path
        sig = base64.b64encode(
            hmac.new(api_secret.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "ACCESS-KEY": api_key,
            "ACCESS-SIGN": sig,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
        }
        async with session.get(f"https://api.bitget.com{path}", headers=headers,
                               timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            data = await resp.json()
            if resp.status == 200 and data.get("code") == "00000":
                result["valid"] = True
                for asset in data.get("data", []):
                    amt = float(asset.get("available", 0)) + float(asset.get("frozen", 0))
                    if amt > 0:
                        cur = asset["coinName"]
                        result["balances"][cur] = amt
                        if cur in ("USDT", "USDC"):
                            result["total_usd"] += amt
            else:
                result["error"] = data.get("msg", f"HTTP {resp.status}")
    except Exception as e:
        result["error"] = str(e)
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ЧЕКЕР
# ═══════════════════════════════════════════════════════════════════════════

async def check_exchange_api(
    exchange: str,
    api_key: str,
    api_secret: str,
    passphrase: str = "",
    session: Optional[aiohttp.ClientSession] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Универсальная проверка API ключа биржи.
    Возвращает стандартный результат совместимый с crypto_checker.
    """
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()

    try:
        ex = exchange.lower()
        if ex == "binance":
            raw = await _check_binance(api_key, api_secret, session, timeout)
        elif ex == "bybit":
            raw = await _check_bybit(api_key, api_secret, session, timeout)
        elif ex == "okx":
            raw = await _check_okx(api_key, api_secret, passphrase, session, timeout)
        elif ex == "kucoin":
            raw = await _check_kucoin(api_key, api_secret, passphrase, session, timeout)
        elif ex == "gate":
            raw = await _check_gate(api_key, api_secret, session, timeout)
        elif ex == "mexc":
            raw = await _check_mexc(api_key, api_secret, session, timeout)
        elif ex == "bitget":
            raw = await _check_bitget(api_key, api_secret, passphrase, session, timeout)
        else:
            raw = {"exchange": ex, "valid": False, "error": f"Биржа {ex} не поддерживается"}

        # Формируем стандартный результат
        result = {
            "input": f"{ex}:{api_key[:8]}...:{api_secret[:8]}...",
            "type": "exchange_api",
            "exchange": EXCHANGE_NAMES.get(ex, ex.upper()),
            "platform": ex,
            "valid": raw.get("valid", False),
            "exists": raw.get("valid", False) and raw.get("total_usd", 0) > 0,
            "info": {
                "exchange": EXCHANGE_NAMES.get(ex, ex.upper()),
                "api_key": api_key,
                "api_secret": api_secret,
                "passphrase": passphrase,
                "balances": raw.get("balances", {}),
                "futures": raw.get("futures", {}),
                "total_usd": raw.get("total_usd", 0.0),
                "permissions": raw.get("permissions", []),
            }
        }

        if raw.get("error"):
            result["info"]["error"] = raw["error"]
            result["info"]["message"] = f"❌ {EXCHANGE_NAMES.get(ex, ex.upper())}: {raw['error']}"
        else:
            total = raw.get("total_usd", 0.0)
            balances = raw.get("balances", {})
            bal_str = ", ".join(
                f"{amt:.4g} {asset}"
                for asset, amt in sorted(balances.items(), key=lambda x: -x[1])[:8]
            )
            whale = " | 🐋 КИТ" if total >= 10000 else (" | 💰 Высокий баланс" if total >= 1000 else "")
            result["info"]["message"] = (
                f"✅ {EXCHANGE_NAMES.get(ex, ex.upper())} | "
                f"Баланс: ~${total:,.2f}{whale} | "
                f"Активы: {bal_str or 'пусто'} | "
                f"API: {api_key[:12]}..."
            )
            # Добавляем auth инструкцию
            result["info"]["auth"] = {
                "auth_type": "API Key + Secret",
                "wallets": EXCHANGE_NAMES.get(ex, ex.upper()),
                "how": f"Войди на {EXCHANGE_NAMES.get(ex, ex.upper())} → Профиль → API Management → используй ключ {api_key[:12]}..."
            }

        return result

    finally:
        if own_session:
            await session.close()


# ═══════════════════════════════════════════════════════════════════════════
#  ЭКСПОРТ АККАУНТОВ
# ═══════════════════════════════════════════════════════════════════════════

class ExchangeAccountExporter:
    """Экспорт аккаунтов бирж с балансами"""

    def __init__(self):
        self.accounts: List[Dict] = []

    def add(self, result: Dict):
        """Добавить результат проверки"""
        if result.get("valid") or result.get("exists"):
            self.accounts.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "exchange":   result.get("exchange", ""),
                "platform":   result.get("platform", ""),
                "api_key":    result.get("info", {}).get("api_key", ""),
                "api_secret": result.get("info", {}).get("api_secret", ""),
                "passphrase": result.get("info", {}).get("passphrase", ""),
                "total_usd":  result.get("info", {}).get("total_usd", 0.0),
                "balances":   result.get("info", {}).get("balances", {}),
                "futures":    result.get("info", {}).get("futures", {}),
                "message":    result.get("info", {}).get("message", ""),
            })

    def export_txt(self, path: str, min_usd: float = 0.0) -> int:
        """Экспорт в TXT. Возвращает количество записей."""
        accounts = [a for a in self.accounts if a["total_usd"] >= min_usd]
        if not accounts:
            return 0
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("БИРЖЕВЫЕ АККАУНТЫ С БАЛАНСОМ\n")
            f.write(f"Экспорт: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего: {len(accounts)} | Мин. баланс: ${min_usd:,.2f}\n")
            total = sum(a["total_usd"] for a in accounts)
            f.write(f"Суммарный баланс: ~${total:,.2f}\n")
            f.write("=" * 70 + "\n\n")
            for i, acc in enumerate(sorted(accounts, key=lambda x: -x["total_usd"]), 1):
                f.write(f"{'─'*70}\n")
                f.write(f"#{i} {acc['exchange']} | ${acc['total_usd']:,.2f}\n")
                f.write(f"API Key:    {acc['api_key']}\n")
                f.write(f"API Secret: {acc['api_secret']}\n")
                if acc["passphrase"]:
                    f.write(f"Passphrase: {acc['passphrase']}\n")
                if acc["balances"]:
                    bal = ", ".join(f"{v:.4g} {k}" for k, v in
                                   sorted(acc["balances"].items(), key=lambda x: -x[1])[:10])
                    f.write(f"Балансы:    {bal}\n")
                if acc["futures"]:
                    fut = ", ".join(f"{v:.4g} {k}" for k, v in acc["futures"].items())
                    f.write(f"Futures:    {fut}\n")
                f.write(f"Дата:       {acc['timestamp']}\n")
                f.write("\n")
        return len(accounts)

    def export_csv(self, path: str, min_usd: float = 0.0) -> int:
        """Экспорт в CSV."""
        accounts = [a for a in self.accounts if a["total_usd"] >= min_usd]
        if not accounts:
            return 0
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Exchange", "API Key", "API Secret", "Passphrase",
                        "Total USD", "Balances", "Timestamp"])
            for acc in sorted(accounts, key=lambda x: -x["total_usd"]):
                bal_str = json.dumps(acc["balances"], ensure_ascii=False)
                w.writerow([
                    acc["exchange"], acc["api_key"], acc["api_secret"],
                    acc["passphrase"], f"{acc['total_usd']:.2f}", bal_str, acc["timestamp"]
                ])
        return len(accounts)

    def export_json(self, path: str, min_usd: float = 0.0) -> int:
        """Экспорт в JSON."""
        accounts = [a for a in self.accounts if a["total_usd"] >= min_usd]
        if not accounts:
            return 0
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_accounts": len(accounts),
            "total_usd": sum(a["total_usd"] for a in accounts),
            "accounts": sorted(accounts, key=lambda x: -x["total_usd"]),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(accounts)

    def summary(self) -> str:
        if not self.accounts:
            return "Нет аккаунтов для экспорта"
        total_usd = sum(a["total_usd"] for a in self.accounts)
        by_ex = {}
        for a in self.accounts:
            by_ex[a["exchange"]] = by_ex.get(a["exchange"], 0) + 1
        ex_str = ", ".join(f"{k}: {v}" for k, v in by_ex.items())
        return (f"📊 Аккаунтов: {len(self.accounts)} | "
                f"Суммарно: ~${total_usd:,.2f} | {ex_str}")


# Глобальный экспортер (используется из main.py)
global_exchange_exporter = ExchangeAccountExporter()
