# -*- coding: utf-8 -*-
"""
Solana Staking Checker v1.0.89
Проверка liquid staking токенов на Solana:
  mSOL (Marinade), jitoSOL (Jito), bSOL (Blaze), hSOL (Helius),
  JSOL (JPOOL), laineSOL, scnSOL, stSOL (Lido)
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from checkers.api_utils import fetch_with_retry


# Liquid staking токены Solana (mint → {symbol, decimals, protocol})
SOL_LIQUID_STAKING: Dict[str, Dict] = {
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So":  {"symbol": "mSOL",     "decimals": 9,  "protocol": "Marinade"},
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn": {"symbol": "jitoSOL",  "decimals": 9,  "protocol": "Jito"},
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1":  {"symbol": "bSOL",     "decimals": 9,  "protocol": "BlazeStake"},
    "he1iusmfkpAdwvxLNGV8Y1iSbj4rUy6yMhEA3fotn9A":  {"symbol": "hSOL",     "decimals": 9,  "protocol": "Helius"},
    "7Q2afV64in6N6SeZsAAB81TJzwDoD6zpqmHkzi9Dcavn": {"symbol": "JSOL",     "decimals": 9,  "protocol": "JPOOL"},
    "LAinEtNLgpmCP9Rvsf5Hn8W6EhNiKLZQti1xfWMLy6X":  {"symbol": "laineSOL", "decimals": 9,  "protocol": "Laine"},
    "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm": {"symbol": "scnSOL",   "decimals": 9,  "protocol": "Socean"},
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": {"symbol": "stSOL",    "decimals": 9,  "protocol": "Lido"},
    "CgnTSoL3DgY9SFHxcLj6CgCgKKoTBr6tp4CPAEWy25DE": {"symbol": "cgntSOL",  "decimals": 9,  "protocol": "Cogent"},
    "picobAEvs6w7QEknPce34wAE4gknZA9v5tTonnmHYdX":  {"symbol": "picoSOL",  "decimals": 9,  "protocol": "Pico"},
}

# Stake pool программа Solana
_STAKE_POOL_PROGRAM = "SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy"


async def check_sol_staking(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession
) -> Dict[str, float]:
    """
    Проверяет liquid staking позиции Solana кошелька.
    Возвращает {symbol: amount} для всех staking токенов с ненулевым балансом.
    """
    staking: Dict[str, float] = {}

    # Получаем все SPL токены одним запросом
    for rpc_url in [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com",
    ]:
        try:
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            resp = await fetch_with_retry(
                session, "POST", rpc_url,
                timeout=timeout, proxy=proxy,
                json=payload,
                headers={"Content-Type": "application/json"},
                retries=2, base_delay=1.0
            )
            if resp and resp.status == 200:
                data = await resp.json()
                accounts = data.get("result", {}).get("value", [])
                for acc in accounts:
                    parsed = acc.get("account", {}).get("data", {}).get("parsed", {})
                    info   = parsed.get("info", {})
                    mint   = info.get("mint", "")
                    amt    = float(info.get("tokenAmount", {}).get("uiAmount", 0) or 0)
                    if amt > 0 and mint in SOL_LIQUID_STAKING:
                        token_info = SOL_LIQUID_STAKING[mint]
                        staking[token_info["symbol"]] = round(amt, 6)
                return staking  # Успех
        except Exception:
            continue

    return staking


def format_staking_message(staking: Dict[str, float], sol_price: float) -> str:
    """Форматирует staking позиции в строку для лога."""
    if not staking:
        return ""
    parts = []
    total_sol = 0.0
    for symbol, amount in sorted(staking.items(), key=lambda x: -x[1]):
        parts.append(f"{amount:.4f} {symbol}")
        total_sol += amount  # ~1:1 к SOL
    total_usd = total_sol * sol_price
    return f" | Staking: {', '.join(parts)} (~${total_usd:,.2f})"
