# -*- coding: utf-8 -*-
"""Тест v1.0.88 — важные улучшения"""
import asyncio
import aiohttp
from checkers.balance_cache import BalanceCache
from checkers.evm_multichain import EVM_NETWORKS, format_multichain_message
from checkers.ton_checker import KNOWN_JETTONS

# ── 1. Тест кэша балансов ─────────────────────────────────────────────────
print("=" * 60)
print("1. КЭШ БАЛАНСОВ")
print("=" * 60)

async def test_cache():
    cache = BalanceCache(ttl=5.0)
    fake_result = {"exists": True, "info": {"balance_eth": 1.5}}

    # Сохраняем
    await cache.set("0xABC", "ethereum", fake_result)
    assert cache.size() == 1

    # Получаем
    r = await cache.get("0xABC", "ethereum")
    assert r == fake_result
    print("  [OK] set/get работает")

    # Другой адрес — None
    r2 = await cache.get("0xDEF", "ethereum")
    assert r2 is None
    print("  [OK] miss возвращает None")

    # Другая сеть — None
    r3 = await cache.get("0xABC", "bitcoin")
    assert r3 is None
    print("  [OK] разные сети не пересекаются")

    # Cleanup
    removed = await cache.cleanup_expired()
    assert removed == 0
    print(f"  [OK] cleanup: {removed} устаревших (ожидалось 0)")

    print(f"  [OK] Кэш работает корректно")

asyncio.run(test_cache())

# ── 2. Тест конфигурации EVM сетей ───────────────────────────────────────
print("\n" + "=" * 60)
print("2. EVM МУЛЬТИЧЕЙН КОНФИГУРАЦИЯ")
print("=" * 60)
print(f"  Сетей в конфиге: {len(EVM_NETWORKS)}")
for net in EVM_NETWORKS:
    print(f"  {net['id']:12} {net['name']:15} {net['symbol']:6} {net['rpc'][:40]}")

# ── 3. Тест format_multichain_message ─────────────────────────────────────
print("\n" + "=" * 60)
print("3. FORMAT MULTICHAIN MESSAGE")
print("=" * 60)

chains_mock = {
    "ethereum": {"balance": 1.5,  "symbol": "ETH",  "usd": 3750.0, "has_balance": True,  "name": "Ethereum", "explorer": ""},
    "bsc":      {"balance": 0.0,  "symbol": "BNB",  "usd": 0.0,    "has_balance": False, "name": "BNB Chain","explorer": ""},
    "arbitrum": {"balance": 0.05, "symbol": "ETH",  "usd": 125.0,  "has_balance": True,  "name": "Arbitrum", "explorer": ""},
    "polygon":  {"balance": 0.0,  "symbol": "MATIC","usd": 0.0,    "has_balance": False, "name": "Polygon",  "explorer": ""},
}
msg = format_multichain_message(chains_mock)
print(f"  Сообщение: {msg}")
assert "Ethereum" in msg
assert "Arbitrum" in msg
assert "BNB" not in msg  # пустой не показываем
print("  [OK] Только сети с балансом показываются")

# ── 4. Тест TON Jetton списка ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. TON JETTON СПИСОК")
print("=" * 60)
print(f"  Известных Jetton: {len(KNOWN_JETTONS)}")
symbols = [v["symbol"] for v in KNOWN_JETTONS.values()]
print(f"  Символы: {', '.join(symbols)}")
assert "USDT" in symbols
assert "NOT" in symbols
assert "DOGS" in symbols
print("  [OK] Основные токены присутствуют")

# ── 5. Реальный тест мультичейн (быстрый) ────────────────────────────────
print("\n" + "=" * 60)
print("5. РЕАЛЬНЫЙ МУЛЬТИЧЕЙН ЗАПРОС (ETH адрес)")
print("=" * 60)

async def test_multichain():
    from checkers.evm_multichain import check_evm_all_chains
    # Тестовый адрес Vitalik Buterin
    address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    prices = {"ethereum": {"price": 2500, "change": 0}, "bnb": {"price": 300, "change": 0},
              "polygon": {"price": 0.8, "change": 0}, "avalanche": {"price": 20, "change": 0},
              "fantom": {"price": 0.5, "change": 0}}
    async with aiohttp.ClientSession() as session:
        result = await check_evm_all_chains(
            address, timeout=8, proxy=None, session=session, prices=prices,
            networks=["ethereum", "bsc"]  # только 2 сети для скорости
        )
    for net_id, data in result.items():
        status = "OK" if data["balance"] >= 0 else "FAIL"
        print(f"  [{status}] {net_id:12}: {data['balance']:.6f} {data['symbol']} (~${data['usd']:,.2f})")
    print(f"  [OK] Мультичейн запрос выполнен для {len(result)} сетей")

asyncio.run(test_multichain())

print("\n" + "=" * 60)
print("ИТОГ: все важные улучшения v1.0.88 работают")
print("=" * 60)
