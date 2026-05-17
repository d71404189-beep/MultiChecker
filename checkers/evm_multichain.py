# -*- coding: utf-8 -*-
"""
EVM Multichain Checker v1.0.88
Один ETH адрес — проверка на всех EVM сетях параллельно.
Сети: Ethereum, BSC, Polygon, Arbitrum, Optimism, Base, Avalanche, zkSync, Linea
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from checkers.api_utils import fetch_with_retry


# ── Конфигурация сетей ─────────────────────────────────────────────────────
EVM_NETWORKS: List[Dict[str, Any]] = [
    {
        "id":       "ethereum",
        "name":     "Ethereum",
        "symbol":   "ETH",
        "rpc":      "https://cloudflare-eth.com",
        "price_key":"ethereum",
        "explorer": "https://etherscan.io",
    },
    {
        "id":       "bsc",
        "name":     "BNB Chain",
        "symbol":   "BNB",
        "rpc":      "https://bsc-dataseed.binance.org/",
        "price_key":"bnb",
        "explorer": "https://bscscan.com",
    },
    {
        "id":       "polygon",
        "name":     "Polygon",
        "symbol":   "MATIC",
        "rpc":      "https://polygon-rpc.com",
        "price_key":"polygon",
        "explorer": "https://polygonscan.com",
    },
    {
        "id":       "arbitrum",
        "name":     "Arbitrum",
        "symbol":   "ETH",
        "rpc":      "https://arb1.arbitrum.io/rpc",
        "price_key":"ethereum",
        "explorer": "https://arbiscan.io",
    },
    {
        "id":       "optimism",
        "name":     "Optimism",
        "symbol":   "ETH",
        "rpc":      "https://mainnet.optimism.io",
        "price_key":"ethereum",
        "explorer": "https://optimistic.etherscan.io",
    },
    {
        "id":       "base",
        "name":     "Base",
        "symbol":   "ETH",
        "rpc":      "https://mainnet.base.org",
        "price_key":"ethereum",
        "explorer": "https://basescan.org",
    },
    {
        "id":       "avalanche",
        "name":     "Avalanche",
        "symbol":   "AVAX",
        "rpc":      "https://api.avax.network/ext/bc/C/rpc",
        "price_key":"avalanche",
        "explorer": "https://snowtrace.io",
    },
    {
        "id":       "zksync",
        "name":     "zkSync Era",
        "symbol":   "ETH",
        "rpc":      "https://mainnet.era.zksync.io",
        "price_key":"ethereum",
        "explorer": "https://explorer.zksync.io",
    },
    {
        "id":       "linea",
        "name":     "Linea",
        "symbol":   "ETH",
        "rpc":      "https://rpc.linea.build",
        "price_key":"ethereum",
        "explorer": "https://lineascan.build",
    },
    {
        "id":       "fantom",
        "name":     "Fantom",
        "symbol":   "FTM",
        "rpc":      "https://rpc.ftm.tools",
        "price_key":"fantom",
        "explorer": "https://ftmscan.com",
    },
]

# Маппинг price_key → CoinGecko ID (для цен которых нет в основном кэше)
_EXTRA_PRICE_IDS = {
    "avalanche": "avalanche-2",
    "fantom":    "fantom",
}


async def _get_evm_balance(
    address: str,
    rpc_url: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession
) -> float:
    """Получить нативный баланс через eth_getBalance RPC."""
    try:
        payload = {
            "jsonrpc": "2.0", "id": 1,
            "method": "eth_getBalance",
            "params": [address, "latest"]
        }
        resp = await fetch_with_retry(
            session, "POST", rpc_url,
            timeout=timeout, proxy=proxy,
            json=payload,
            headers={"Content-Type": "application/json"},
            retries=2, base_delay=0.5
        )
        if resp and resp.status == 200:
            data = await resp.json()
            hex_val = data.get("result", "0x0")
            return int(hex_val, 16) / 1e18
    except Exception:
        pass
    return 0.0


async def check_evm_all_chains(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession,
    prices: dict,
    networks: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Параллельная проверка ETH адреса на всех EVM сетях.

    Args:
        address:  ETH адрес (0x...)
        networks: список ID сетей для проверки (None = все)

    Returns:
        {
          "ethereum": {"balance": 1.5, "symbol": "ETH", "usd": 3750.0, "has_balance": True},
          "bsc":      {"balance": 0.0, "symbol": "BNB", "usd": 0.0,    "has_balance": False},
          ...
        }
    """
    target_nets = [
        n for n in EVM_NETWORKS
        if networks is None or n["id"] in networks
    ]

    async def _check_one(net: dict):
        balance = await _get_evm_balance(address, net["rpc"], timeout, proxy, session)
        price_data = prices.get(net["price_key"], {})
        price = price_data.get("price", 0) if isinstance(price_data, dict) else float(price_data or 0)
        usd = balance * price
        return net["id"], {
            "balance":     balance,
            "symbol":      net["symbol"],
            "usd":         usd,
            "has_balance": balance > 0,
            "name":        net["name"],
            "explorer":    net["explorer"],
        }

    results_list = await asyncio.gather(*[_check_one(n) for n in target_nets], return_exceptions=True)

    out: Dict[str, Dict[str, Any]] = {}
    for item in results_list:
        if isinstance(item, Exception):
            continue
        net_id, data = item
        out[net_id] = data

    return out


def format_multichain_message(chains: Dict[str, Dict[str, Any]]) -> str:
    """
    Форматирует результат мультичейн проверки в строку для лога.
    Показывает только сети с ненулевым балансом.
    """
    active = {k: v for k, v in chains.items() if v.get("has_balance")}
    if not active:
        return ""

    total_usd = sum(v["usd"] for v in active.values())
    parts = []
    for net_id, data in sorted(active.items(), key=lambda x: -x[1]["usd"]):
        parts.append(f"{data['name']}: {data['balance']:.6f} {data['symbol']} (~${data['usd']:,.2f})")

    return f" | Мультичейн [{len(active)} сетей, ~${total_usd:,.2f}]: " + " | ".join(parts)
