# -*- coding: utf-8 -*-
"""Тест v1.0.89 — полезные фичи"""
import asyncio
import aiohttp
import os
from checkers.sol_staking import SOL_LIQUID_STAKING, format_staking_message
from checkers.wallet_exporter import WalletExporter, _estimate_usd

# ── 1. Тест списка Solana staking токенов ─────────────────────────────────
print("=" * 60)
print("1. SOLANA LIQUID STAKING ТОКЕНЫ")
print("=" * 60)
print(f"  Токенов: {len(SOL_LIQUID_STAKING)}")
for mint, info in SOL_LIQUID_STAKING.items():
    print(f"  {info['symbol']:10} {info['protocol']:15} decimals={info['decimals']}")

# Тест format_staking_message
staking_mock = {"mSOL": 5.0, "jitoSOL": 2.5, "bSOL": 1.0}
msg = format_staking_message(staking_mock, sol_price=150.0)
print(f"\n  Сообщение: {msg}")
assert "mSOL" in msg and "jitoSOL" in msg
print("  [OK] format_staking_message работает")

# ── 2. Тест WalletExporter ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. WALLET EXPORTER")
print("=" * 60)

exporter = WalletExporter(min_usd=0.0)

# Тестовые результаты
results = [
    {
        "type": "wallet", "wallet_type": "bitcoin", "exists": True,
        "input": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na",
        "info": {
            "balance_btc": 0.001,
            "message": "Balance: 0.001 BTC (~$78.00)",
            "auth": {"auth_type": "Приватный ключ", "wallets": "Electrum", "how": "Импортируй ключ"}
        }
    },
    {
        "type": "seed", "wallet_type": "seed", "exists": True,
        "input": "abandon abandon abandon...",
        "info": {
            "mnemonic": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            "total_usd": 1500.0,
            "message": "Seed: 12 слов | Баланс: ~$1,500.00",
            "auth": {"auth_type": "Сид-фраза", "wallets": "MetaMask", "how": "Импортируй seed"}
        }
    },
    {
        "type": "wallet", "wallet_type": "ethereum", "exists": False,
        "input": "0x0000000000000000000000000000000000000000",
        "info": {"balance_eth": 0.0, "message": "Balance: 0 ETH (empty)"}
    },
]

added = exporter.add_all(results)
print(f"  Добавлено: {added}/3 (ожидалось 2 — только с exists=True)")
assert added == 2
assert exporter.count == 2
print(f"  [OK] count = {exporter.count}")
print(f"  [OK] total_usd = ${exporter.total_usd:,.2f}")
print(f"  [OK] summary: {exporter.summary()}")

# Тест экспорта
import tempfile, os
with tempfile.TemporaryDirectory() as tmpdir:
    fn_txt  = os.path.join(tmpdir, "test.txt")
    fn_csv  = os.path.join(tmpdir, "test.csv")
    fn_json = os.path.join(tmpdir, "test.json")
    fn_seed = os.path.join(tmpdir, "seeds.txt")

    cnt_txt  = exporter.export_txt(fn_txt)
    cnt_csv  = exporter.export_csv(fn_csv)
    cnt_json = exporter.export_json(fn_json)
    cnt_seed = exporter.export_seeds_only(fn_seed)

    assert cnt_txt  == 2, f"TXT: {cnt_txt}"
    assert cnt_csv  == 2, f"CSV: {cnt_csv}"
    assert cnt_json == 2, f"JSON: {cnt_json}"
    assert cnt_seed == 1, f"Seeds: {cnt_seed}"

    # Проверяем содержимое TXT
    with open(fn_txt, encoding="utf-8") as f:
        content = f.read()
    assert "bitcoin" in content.lower() or "Bitcoin" in content
    assert "seed" in content.lower() or "Seed" in content

    print(f"  [OK] TXT: {cnt_txt} записей")
    print(f"  [OK] CSV: {cnt_csv} записей")
    print(f"  [OK] JSON: {cnt_json} записей")
    print(f"  [OK] Seeds: {cnt_seed} записей")

# ── 3. Тест _estimate_usd ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. ESTIMATE USD")
print("=" * 60)

r1 = {"info": {"total_usd": 1500.0}}
r2 = {"info": {"balance_btc": 0.001}}
r3 = {"info": {"balance_eth": 1.0, "token_usd": 500.0}}

assert _estimate_usd(r1) == 1500.0
assert _estimate_usd(r2) == 78.0, f"BTC: {_estimate_usd(r2)}"
assert _estimate_usd(r3) == 3000.0, f"ETH+tokens: {_estimate_usd(r3)}"
print("  [OK] total_usd прямое поле")
print(f"  [OK] balance_btc: ${_estimate_usd(r2):.2f}")
print(f"  [OK] balance_eth + token_usd: ${_estimate_usd(r3):.2f}")

# ── 4. Реальный тест Solana staking (быстрый) ─────────────────────────────
print("\n" + "=" * 60)
print("4. РЕАЛЬНЫЙ ЗАПРОС SOLANA STAKING")
print("=" * 60)

async def test_sol_staking():
    from checkers.sol_staking import check_sol_staking
    # Адрес с известными staking позициями (публичный)
    address = "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK"
    async with aiohttp.ClientSession() as session:
        result = await check_sol_staking(address, timeout=8, proxy=None, session=session)
    print(f"  Staking токены: {result if result else 'нет (пустой кошелёк)'}")
    print(f"  [OK] Запрос выполнен без ошибок")

asyncio.run(test_sol_staking())

print("\n" + "=" * 60)
print("ИТОГ: все полезные фичи v1.0.89 работают")
print("=" * 60)
