# -*- coding: utf-8 -*-
"""
API Utils v1.0.87
Утилиты для надёжных API запросов:
  - Retry с exponential backoff
  - Умная обработка 429/503
  - Реальная проверка airdrop eligibility
"""

import asyncio
import aiohttp
import time
from typing import Optional, Any, Dict


# ═══════════════════════════════════════════════════════════════════════════
#  RETRY FETCH
# ═══════════════════════════════════════════════════════════════════════════

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    timeout: int = 10,
    proxy: Optional[str] = None,
    **kwargs
) -> Optional[aiohttp.ClientResponse]:
    """
    HTTP запрос с exponential backoff retry.

    При 429 (rate limit) или 503 (service unavailable) ждёт и повторяет.
    При других ошибках — сразу возвращает None.

    Задержки: 1s → 2s → 4s (base_delay * 2^attempt)
    """
    last_resp = None

    for attempt in range(retries):
        try:
            resp = await session.request(
                method, url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                proxy=proxy,
                **kwargs
            )

            # Успех
            if resp.status == 200:
                return resp

            # Rate limit или временная недоступность — ждём и повторяем
            if resp.status in (429, 503, 502):
                await resp.release()
                if attempt < retries - 1:
                    delay = base_delay * (2 ** attempt)
                    # Проверяем Retry-After заголовок
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = min(float(retry_after), 10.0)
                        except ValueError:
                            pass
                    await asyncio.sleep(delay)
                    continue

            # Другой статус — возвращаем как есть
            last_resp = resp
            return resp

        except asyncio.TimeoutError:
            if attempt < retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
            continue
        except aiohttp.ClientConnectorError:
            if attempt < retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
            continue
        except Exception:
            break

    return last_resp


# ═══════════════════════════════════════════════════════════════════════════
#  РЕАЛЬНАЯ ПРОВЕРКА AIRDROP ELIGIBILITY
# ═══════════════════════════════════════════════════════════════════════════

# Известные airdrop контракты и API
_AIRDROP_CHECKS = {
    "arbitrum": {
        "name": "Arbitrum (ARB)",
        "url": "https://api.arbitrum.io/airdrop/check/{address}",
        "method": "GET",
    },
    "optimism": {
        "name": "Optimism (OP)",
        "url": "https://api.optimism.io/airdrop/check/{address}",
        "method": "GET",
    },
    "zksync": {
        "name": "zkSync (ZK)",
        "url": "https://api.zksync.io/api/v0.2/accounts/{address}/transactions",
        "method": "GET",
    },
    "layerzero": {
        "name": "LayerZero (ZRO)",
        "url": "https://layerzero.network/api/airdrop/{address}",
        "method": "GET",
    },
    "starknet": {
        "name": "StarkNet (STRK)",
        "url": "https://provisions.starknet.io/api/eligibility/{address}",
        "method": "GET",
    },
}

# Контракты для on-chain проверки через ETH RPC
_AIRDROP_CONTRACTS = {
    # Uniswap UNI — исторический, но показываем как пример
    "uniswap_v3_nft": {
        "name": "Uniswap V3 LP",
        "contract": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
        "method": "balanceOf",
        "selector": "0x70a08231",
    },
}


async def check_airdrop_eligibility(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession
) -> str:
    """
    Реальная проверка airdrop eligibility через публичные API.
    Возвращает строку с найденными airdrop или пустую строку.
    """
    found = []

    # 1. Проверяем активность в zkSync Era (индикатор ZK airdrop)
    try:
        url = f"https://block-explorer-api.mainnet.zksync.io/api?module=account&action=txlist&address={address}&page=1&offset=1"
        resp = await fetch_with_retry(session, "GET", url, timeout=timeout, proxy=proxy, retries=2)
        if resp and resp.status == 200:
            data = await resp.json()
            txs = data.get("result", [])
            if isinstance(txs, list) and len(txs) > 0:
                found.append("zkSync активен")
    except Exception:
        pass

    # 2. Проверяем активность в Arbitrum (индикатор ARB airdrop)
    try:
        url = f"https://api.arbiscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1"
        resp = await fetch_with_retry(session, "GET", url, timeout=timeout, proxy=proxy, retries=2)
        if resp and resp.status == 200:
            data = await resp.json()
            txs = data.get("result", [])
            if isinstance(txs, list) and len(txs) > 0:
                found.append("Arbitrum активен")
    except Exception:
        pass

    # 3. Проверяем активность в Optimism
    try:
        url = f"https://api-optimistic.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1"
        resp = await fetch_with_retry(session, "GET", url, timeout=timeout, proxy=proxy, retries=2)
        if resp and resp.status == 200:
            data = await resp.json()
            txs = data.get("result", [])
            if isinstance(txs, list) and len(txs) > 0:
                found.append("Optimism активен")
    except Exception:
        pass

    # 4. Проверяем StarkNet eligibility
    try:
        url = f"https://provisions.starknet.io/api/eligibility/{address}"
        resp = await fetch_with_retry(session, "GET", url, timeout=timeout, proxy=proxy, retries=1)
        if resp and resp.status == 200:
            data = await resp.json()
            amount = data.get("amount", 0) or data.get("allocation", 0)
            if amount and float(amount) > 0:
                found.append(f"STRK: {float(amount):,.0f}")
    except Exception:
        pass

    # 5. Проверяем LayerZero ZRO
    try:
        url = f"https://www.layerzero.foundation/api/proof/{address}"
        resp = await fetch_with_retry(session, "GET", url, timeout=timeout, proxy=proxy, retries=1)
        if resp and resp.status == 200:
            data = await resp.json()
            amount = data.get("amount", 0)
            if amount and int(amount) > 0:
                zro_amount = int(amount) / 1e18
                found.append(f"ZRO: {zro_amount:,.2f}")
    except Exception:
        pass

    if found:
        return f" | [Airdrop: {', '.join(found)}]"
    return ""


# ═══════════════════════════════════════════════════════════════════════════
#  РАСШИРЕННЫЙ СПИСОК SPL ТОКЕНОВ (Jupiter Token List)
# ═══════════════════════════════════════════════════════════════════════════

# Топ-50 SPL токенов по ликвидности (mint → symbol)
KNOWN_SPL_MINTS: Dict[str, str] = {
    # Стейблкоины
    "EPjFW3dpEqEU2o194Kzk9GwZ99Q11111111111111111": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11111111111111": "USDT",
    "EjmyN6qEC1Tf1JxiG1ae7UTJhUxSwk1TCWNWqxWV4J6o": "DAI",
    "9mWRABuz2x6koTPCWiCPM49WUbcrNqGTHBV9T9k7y1o7": "USDH",
    "USDH1SM1ojwWUga67PGrgFWUHibbjqMvuMaDkRJTgkX":  "USDH",

    # Wrapped токены
    "So11111111111111111111111111111111111111112":   "wSOL",
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "wETH",
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E": "wBTC",
    "A9mUU4qviSctJVPJdBJWkb28deg915LYJKrzQ19ji3FM":  "USDCet",

    # DeFi токены
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": "RAY",
    "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt":  "SRM",
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE":  "ORCA",
    "MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey":  "MNDE",
    "LFNTYraetVioAPnGJht4yNg2aUZFXR776cMeN9VMjXp":  "LIFINITY",
    "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT":  "STEP",
    "kinXdEcpDQeHPEuQnqmUgtYykqKGVFq6CeVX5iAHJq6": "KIN",

    # Meme токены
    "DezXAZ8z7PnrFcEDUsPR4oFc8C8cH1m1JitEX62G16nn": "BONK",
    "EKpQGSJtjMFqBBm9938CgX9uw96S67beBU8vA5w3pump": "WIF",
    "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5":  "MEW",
    "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82":  "BOME",
    "A3eME5CetyZPBoWbRUwY3tSe25S6tb18ba9ZPbWk9eFJ": "PENG",
    "Gu3LDkn7Vx3bmCzLafYNKcDxv2mH7YN44NJZFXnypump": "POPCAT",
    "8wXtPeU6557ETkp9WHFY1n1EcU6NxDvbAggHGsMYiHsB": "GME",
    "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK31CR8Ada": "FLOKI",

    # Liquid staking
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So":  "mSOL",
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn": "jitoSOL",
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1":  "bSOL",
    "7Q2afV64in6N6SeZsAAB81TJzwDoD6zpqmHkzi9Dcavn": "JSOL",
    "he1iusmfkpAdwvxLNGV8Y1iSbj4rUy6yMhEA3fotn9A":  "hSOL",

    # Gaming / NFT
    "ATLASXmbPQxBUYbxPsV97usA3fPQYEqzQBUHgiFCUsXx": "ATLAS",
    "poLisWXnNRwC6oBu1vHiuKQzFjGL4XDSu4g9qjz9qVk":  "POLIS",
    "AFbX8oGjGpmVFywabs9DVxVJCPanjkFiG18EBnB6ZQKM": "GST",
    "7i5KKsX2weiTkry7jA4ZwSuXGhs5eJBEjY8vVxR4pfRx": "GMT",

    # Infrastructure
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "PYTH",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN":  "JUP",
    "WENWENvqqNya429ubCdR81ZmD69brwQaaBYY6p3LCpk":  "WEN",
    "TNSRxcUxoT9xBG3de7PiJyTDYu7kskLqcpddxnEJAS6":  "TNSR",
    "85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ": "W",
    "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof":  "RENDER",
    "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7":  "NOS",
    "DriFtupJYLTosbwoN8koMbEYSx54aFAVLddWsbksjwg7":  "DRIFT",
    "iotEVVZLEywoTn1QdwNPddxPWszn3zFhEot3MfL9fns":  "IOT",
    "mb1eu7TzEc71KxDpsmsKoucSSuuoGLv1drys1oP2jh6":  "MOBILE",
    "HxhWkVpk5NS4Ltg5nij2G671CKXFRKPK8vy271Ub4uEK": "HXRO",
}


async def fetch_spl_tokens_extended(
    address: str,
    timeout: int,
    proxy: Optional[str],
    session: aiohttp.ClientSession
) -> Dict[str, float]:
    """
    Расширенная проверка SPL токенов с retry и большим списком токенов.
    Возвращает {symbol: amount} для всех токенов с ненулевым балансом.
    """
    tokens: Dict[str, float] = {}

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
                retries=3, base_delay=1.0
            )
            if resp and resp.status == 200:
                data = await resp.json()
                accounts = data.get("result", {}).get("value", [])
                for acc in accounts:
                    parsed = acc.get("account", {}).get("data", {}).get("parsed", {})
                    info = parsed.get("info", {})
                    amt = float(info.get("tokenAmount", {}).get("uiAmount", 0) or 0)
                    mint = info.get("mint", "")
                    if amt > 0 and mint:
                        # Используем расширенный список, иначе сокращаем mint
                        symbol = KNOWN_SPL_MINTS.get(mint, mint[:6] + "…")
                        tokens[symbol] = round(amt, 6)
                return tokens  # Успех — выходим
        except Exception:
            continue

    return tokens


# ═══════════════════════════════════════════════════════════════════════════
#  ВАЛИДАЦИЯ SOLANA АДРЕСА
# ═══════════════════════════════════════════════════════════════════════════

# Base58 алфавит (без 0, O, I, l)
_BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

# Известные НЕ-Solana паттерны которые могут совпасть с regex
_NOT_SOLANA_PREFIXES = (
    "EQ", "UQ",          # TON адреса
    "addr1",             # Cardano
    "bc1", "tb1",        # Bitcoin bech32
    "ltc1",              # Litecoin
)

# Системные программы Solana (не кошельки)
_SOLANA_SYSTEM_PROGRAMS = {
    "11111111111111111111111111111111",           # System Program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJe1bJ",  # Associated Token
    "So11111111111111111111111111111111111111111",    # Native SOL mint
    "So11111111111111111111111111111111111111112",    # Wrapped SOL
    "Sysvar1111111111111111111111111111111111111",    # Sysvar
    "Vote111111111111111111111111111111111111111p",   # Vote Program
    "Stake11111111111111111111111111111111111111",    # Stake Program
    "BPFLoaderUpgradeab1e11111111111111111111111",   # BPF Loader
    "ComputeBudget111111111111111111111111111111",   # Compute Budget
}


def is_valid_solana_address(address: str) -> bool:
    """
    Строгая валидация Solana адреса.
    Проверяет:
    1. Длина 32-44 символа
    2. Только Base58 символы
    3. Не начинается с TON/Cardano/BTC префиксов
    4. Не является системной программой
    5. Декодируется в 32 байта
    """
    s = address.strip()

    # Длина
    if not (32 <= len(s) <= 44):
        return False

    # Только Base58 символы
    if not all(c in _BASE58_ALPHABET for c in s):
        return False

    # Не TON/Cardano/BTC
    for prefix in _NOT_SOLANA_PREFIXES:
        if s.startswith(prefix):
            return False

    # Не системная программа
    if s in _SOLANA_SYSTEM_PROGRAMS:
        return False

    # Декодируем Base58 и проверяем что получается 32 байта
    try:
        n = 0
        for char in s:
            n = n * 58 + "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz".index(char)
        # Конвертируем в байты
        result = []
        while n > 0:
            result.append(n & 0xFF)
            n >>= 8
        # Добавляем ведущие нули
        for char in s:
            if char == '1':
                result.append(0)
            else:
                break
        decoded = bytes(reversed(result))
        return len(decoded) == 32
    except Exception:
        return False
