# -*- coding: utf-8 -*-
"""Тест умного парсера дампов"""
from checkers.dump_crypto_checker import SmartDumpChecker

DUMP = """
# Сид-фразы
abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about
word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24

# Приватные ключи
0xa3f8c2d1e4b5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
5KJvsngHeMpm884wtkJNzQGaCErckhHJBGFsvd3VyK5qMZXj3hS

# Крипто адреса
1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na
0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE
EQD14kgmngE0fNYVs7_9dw78V3rPhNt7_Ee-7X3ykDORQvMp

# Биржевые credentials (url:mail:pass)
accounts.binance.com/en/login:user@gmail.com:MyPass123
https://accounts.binance.com/en/login:test@mail.com:password456
kucoin.com:gececi164@gmail.com:21532456s
gate.io:skuba21@gmail.com:@lencia2020
user@bybit.com:mypassword789

# API ключи
binance:abc123def456ghi789jkl012mno345pqr678stu:xyz987wvu654tsr321qpo098nml765kji432fed

# Дубликаты (должны быть удалены)
accounts.binance.com/en/login:user@gmail.com:MyPass123
0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
"""

checker = SmartDumpChecker()
parsed = checker.parse_dump(DUMP)

print("=" * 60)
print("🧪 ТЕСТ УМНОГО ПАРСЕРА ДАМПОВ")
print("=" * 60)
print()
print(checker.format_stats())
print()
print(f"📋 Крипто ({len(parsed['crypto'])}):")
for item in parsed["crypto"]:
    print(f"   {item[:70]}")

print(f"\n🏦 Биржевые credentials ({len(parsed['exchange'])}):")
for item in parsed["exchange"]:
    print(f"   {item}")

print(f"\n🔐 API ключи ({len(parsed['api_keys'])}):")
for item in parsed["api_keys"]:
    print(f"   {item[:60]}...")

total = len(checker.get_all_for_checker(parsed))
print(f"\n✅ Итого для проверки: {total}")
print("=" * 60)
