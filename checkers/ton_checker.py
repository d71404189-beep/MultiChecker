# -*- coding: utf-8 -*-
"""
TON Checker v1.0.88
Проверка TON кошелька: нативный баланс + Jetton токены.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from checkers.api_utils import fetch_with_retry


# ── Известные Jetton контракты (master address → symbol) ──────────────────
KNOWN_JETTONS: Dict[str, Dict[str, Any]] = {
    # Стейблкоины
    "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs": {"symbol": "USDT",  "decimals": 6},
    "EQB-MPwrd1G6WKNkLz_VnV6WqBDd142KMQv-g1O-8QUA3728": {"symbol": "USDC",  "decimals": 6},
    "EQDo_ZJyQ_YqBzBwbVpMmhbRMfefhIYLGMFBBMBBBBBBBBBB": {"symbol": "DAI",   "decimals": 18},

    # Wrapped токены
    "EQCM3B12QK1e4yZSf8GtBRT0aLMNyEsBc_9Qsof7cs_4IgBB": {"symbol": "wTON",  "decimals": 9},
    "EQBynBO23ywHy_CgarY9NK9FTz0yDsG82PtcbSTQgGoXwiuA": {"symbol": "jUSDT", "decimals": 6},
    "EQB3ncyBUTjZUA5EnFKR5_EnOMI9V1tTEAAPaiU71gc4TiUt": {"symbol": "jUSDC", "decimals": 6},

    # DeFi / DEX токены
    "EQBlqsm144Dq6SjbPI4jjZvA1hqTIP3CvHovbIfW_t-SCALE": {"symbol": "SCALE", "decimals": 9},
    "EQDQoc5M3Bh8eWFepahi9bScGqDfgopPkNGsfu2MO3BJ-STON": {"symbol": "STON",  "decimals": 9},
    "EQA2kCVNwVsil2EM2mB0SkXytxCqQjS4mttjDpnXmwG9T6bO": {"symbol": "BOLT",  "decimals": 9},
    "EQCvxJy4eG8hyHBFsZ7eePxrRsUQSFE_jpptRAYBmcG_DOGS": {"symbol": "DOGS",  "decimals": 0},
    "EQAvlWFDxGF2lXm67y4yzC17wYKD9A0guwPkMs1gOsM__NOT": {"symbol": "NOT",   "decimals": 9},
    "EQD-cvR0Nz6XAyRBvdBkMZmHmnT6L_ymsgmQwjTNkgkjR4Nz": {"symbol": "GRAM",  "decimals": 9},
    "EQCqC6EhRJ_tpWngKxL6dV0k6DSnRUrs9GSVkLbfdCqsj9mo": {"symbol": "KINGY", "decimals": 9},
    "EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3l": {"symbol": "JETTON","decimals": 9},

    # Meme токены
    "EQBl3gg6AAdjgjO2ZoNU5Q5EZWH9YQBkHBBBBBBBBBBBBBBB": {"symbol": "PEPE",  "decimals": 9},
    "EQCbooAHOszo5oABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB": {"symbol": "SHIB",  "decimals": 9},
}


async def check_ton_jettons(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession
) -> Dict[str, float]:
    """
    Проверяет Jetton токены TON кошелька через TonAPI и TonCenter.
    Возвращает {symbol: amount}.
    """
    jettons: Dict[str, float] = {}

    # ── Метод 1: TonAPI v2 (лучший, возвращает все Jetton) ────────────────
    try:
        url = f"https://tonapi.io/v2/accounts/{address}/jettons?currencies=usd"
        resp = await fetch_with_retry(
            session, "GET", url,
            timeout=timeout, proxy=proxy,
            retries=2, base_delay=1.0
        )
        if resp and resp.status == 200:
            data = await resp.json()
            for item in data.get("balances", []):
                balance_raw = int(item.get("balance", 0))
                if balance_raw <= 0:
                    continue
                jetton_info = item.get("jetton", {})
                symbol   = jetton_info.get("symbol", "")
                decimals = int(jetton_info.get("decimals", 9))
                if not symbol:
                    # Пробуем найти по адресу контракта
                    master = jetton_info.get("address", "")
                    known  = KNOWN_JETTONS.get(master, {})
                    symbol   = known.get("symbol", master[:8] + "…") if master else "UNKNOWN"
                    decimals = known.get("decimals", decimals)
                amount = balance_raw / (10 ** decimals)
                if amount > 0:
                    jettons[symbol] = round(amount, 6)
            return jettons
    except Exception:
        pass

    # ── Метод 2: TonCenter v3 (fallback) ──────────────────────────────────
    try:
        url = f"https://toncenter.com/api/v3/jetton/wallets?owner_address={address}&limit=50"
        resp = await fetch_with_retry(
            session, "GET", url,
            timeout=timeout, proxy=proxy,
            retries=2, base_delay=1.0
        )
        if resp and resp.status == 200:
            data = await resp.json()
            for item in data.get("jetton_wallets", []):
                balance_raw = int(item.get("balance", 0))
                if balance_raw <= 0:
                    continue
                master = item.get("jetton", "")
                known  = KNOWN_JETTONS.get(master, {})
                symbol   = known.get("symbol", master[:8] + "…") if master else "UNKNOWN"
                decimals = known.get("decimals", 9)
                amount = balance_raw / (10 ** decimals)
                if amount > 0:
                    jettons[symbol] = round(amount, 6)
    except Exception:
        pass

    return jettons


async def check_ton_full(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession,
    prices: dict
) -> dict:
    """
    Полная проверка TON кошелька: нативный баланс + Jetton токены.
    Возвращает стандартный result dict.
    """
    result = {
        "input": address,
        "type": "wallet",
        "wallet_type": "ton",
        "valid": True,
        "exists": False,
        "info": {
            "balance_ton": 0.0,
            "jettons": {},
            "message": "",
        }
    }

    # ── Нативный баланс ────────────────────────────────────────────────────
    balance = 0.0
    for url in [
        f"https://toncenter.com/api/v2/getAddressInformation?address={address}",
        f"https://tonapi.io/v2/accounts/{address}",
    ]:
        try:
            resp = await fetch_with_retry(
                session, "GET", url,
                timeout=timeout, proxy=proxy,
                retries=3, base_delay=1.0
            )
            if resp and resp.status == 200:
                data = await resp.json()
                # TonCenter формат
                if data.get("ok"):
                    balance = int(data["result"].get("balance", 0)) / 1e9
                    break
                # TonAPI формат
                elif "balance" in data:
                    balance = int(data.get("balance", 0)) / 1e9
                    break
        except Exception:
            continue

    result["info"]["balance_ton"] = balance
    result["exists"] = balance > 0

    # ── Jetton токены ──────────────────────────────────────────────────────
    jettons = await check_ton_jettons(address, timeout, proxy, session)
    result["info"]["jettons"] = jettons
    if jettons:
        result["exists"] = True

    # ── Формируем message ──────────────────────────────────────────────────
    ton_price = prices.get("ton", {}).get("price", 0) if isinstance(prices.get("ton"), dict) else prices.get("ton", 0)
    ton_usd   = balance * ton_price

    if balance > 0:
        change = prices.get("ton", {}).get("change", 0) if isinstance(prices.get("ton"), dict) else 0
        change_str = f" ({change:+.1f}%)" if change else ""
        msg = f"Balance: {balance:.4f} TON (~${ton_usd:,.2f}{change_str})"
    else:
        msg = "Balance: 0 TON"

    if jettons:
        top = sorted(jettons.items(), key=lambda x: -x[1])[:6]
        jetton_str = ", ".join(f"{v:.4g} {k}" for k, v in top)
        if len(jettons) > 6:
            jetton_str += f" +{len(jettons)-6} ещё"
        msg += f" | Jetton: {jetton_str}"

    if not result["exists"]:
        msg += " (empty)"

    # Whale label
    if ton_usd >= 10000:
        msg += " | 🐋 КИТ"
    elif ton_usd >= 1000:
        msg += " | 💰 Высокий баланс"

    result["info"]["message"] = msg
    result["info"]["total_usd"] = ton_usd
    result["info"]["auth"] = {
        "auth_type": "Сид-фраза (24 слова)",
        "wallets": "Tonkeeper, MyTonWallet",
        "how": "Установи Tonkeeper, нажми 'Восстановить кошелек' и введи 24 слова сид-фразы."
    }

    return result
