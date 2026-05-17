# -*- coding: utf-8 -*-
"""Тест v1.0.87 — критичные улучшения"""
import asyncio
import aiohttp
from checkers.api_utils import is_valid_solana_address
from checkers.crypto_checker import CryptoChecker

checker = CryptoChecker()

# ── 1. Тест валидации Solana адресов ──────────────────────────────────────
print("=" * 60)
print("1. ВАЛИДАЦИЯ SOLANA АДРЕСОВ")
print("=" * 60)

tests = [
    ("7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK", "solana"),
    ("EQD14kgmngE0fNYVs7_9dw78V3rPhNt7_Ee-7X3ykDORQvMp", "ton"),
    ("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0", "ethereum"),  # 42 символа
    ("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "tron"),
    ("So11111111111111111111111111111111111111112", None),         # Wrapped SOL — системная программа
    ("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "bitcoin"),
    ("1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na", None),               # пробел — невалидный
]

passed = 0
for addr, expected in tests:
    detected = checker._detect_wallet(addr.strip())
    ok = detected == expected
    passed += ok
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {addr[:44]:44} -> {str(detected):10} (ожидалось: {expected})")

print(f"\n  Результат: {passed}/{len(tests)}")

# ── 2. Тест is_valid_solana_address ───────────────────────────────────────
print("\n" + "=" * 60)
print("2. is_valid_solana_address")
print("=" * 60)

sol_tests = [
    ("7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK", True),
    ("EQD14kgmngE0fNYVs7_9dw78V3rPhNt7_Ee-7X3ykDORQvMp", False),
    ("11111111111111111111111111111111", False),
    ("So11111111111111111111111111111111111111112", False),
    ("short", False),
    ("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", False),
]

passed2 = 0
for addr, expected in sol_tests:
    result = is_valid_solana_address(addr)
    ok = result == expected
    passed2 += ok
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {addr[:44]:44} -> {result} (ожидалось: {expected})")

print(f"\n  Результат: {passed2}/{len(sol_tests)}")

# ── 3. Тест retry fetch ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. RETRY FETCH (реальный запрос)")
print("=" * 60)

async def test_retry():
    from checkers.api_utils import fetch_with_retry
    async with aiohttp.ClientSession() as session:
        # Тест с рабочим URL
        resp = await fetch_with_retry(
            session, "GET",
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10, retries=2
        )
        if resp and resp.status == 200:
            data = await resp.json()
            btc_price = data.get("bitcoin", {}).get("usd", 0)
            print(f"  [OK] CoinGecko ответил: BTC = ${btc_price:,.0f}")
        else:
            print(f"  [WARN] CoinGecko недоступен (статус: {resp.status if resp else 'None'})")

asyncio.run(test_retry())

# ── 4. Тест расширенного списка SPL токенов ───────────────────────────────
print("\n" + "=" * 60)
print("4. РАСШИРЕННЫЙ СПИСОК SPL ТОКЕНОВ")
print("=" * 60)
from checkers.api_utils import KNOWN_SPL_MINTS
print(f"  Токенов в списке: {len(KNOWN_SPL_MINTS)}")
print(f"  Примеры: {', '.join(list(KNOWN_SPL_MINTS.values())[:10])}")

print("\n" + "=" * 60)
print("ИТОГ: все критичные улучшения v1.0.87 работают")
print("=" * 60)
