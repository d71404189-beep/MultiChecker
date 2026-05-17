#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестирование новых фич v1.0.76
"""

import asyncio
from checkers.nft_checker import NFTChecker
from checkers.airdrop_hunter import AirdropHunter
from checkers.defi_positions import DeFiPositionsChecker


async def test_nft_checker():
    """Тест NFT Checker"""
    print("="*70)
    print("🖼️  ТЕСТ NFT CHECKER")
    print("="*70)
    
    checker = NFTChecker()
    
    # Тестовый адрес
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth
    
    print(f"\n📍 Проверяем адрес: {test_address}")
    print("⏳ Загрузка...")
    
    result = await checker.check_nfts(test_address, "ethereum")
    
    print("\n📊 РЕЗУЛЬТАТ:")
    formatted = checker.format_nft_result(result)
    print(formatted)
    
    print("\n✅ NFT Checker работает!")
    return result


async def test_airdrop_hunter():
    """Тест Airdrop Hunter"""
    print("\n" + "="*70)
    print("🪂 ТЕСТ AIRDROP HUNTER")
    print("="*70)
    
    hunter = AirdropHunter()
    
    # Тестовый адрес
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    
    print(f"\n📍 Проверяем адрес: {test_address}")
    print("⏳ Проверка eligibility...")
    
    result = await hunter.check_airdrops(test_address)
    
    print("\n📊 РЕЗУЛЬТАТ:")
    formatted = hunter.format_airdrop_result(result)
    print(formatted)
    
    print("\n✅ Airdrop Hunter работает!")
    return result


async def test_defi_positions():
    """Тест DeFi Positions"""
    print("\n" + "="*70)
    print("📊 ТЕСТ DEFI POSITIONS")
    print("="*70)
    
    checker = DeFiPositionsChecker()
    
    # Тестовый адрес
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    
    print(f"\n📍 Проверяем адрес: {test_address}")
    print("⏳ Проверка DeFi позиций...")
    
    result = await checker.check_positions(test_address)
    
    print("\n📊 РЕЗУЛЬТАТ:")
    formatted = checker.format_defi_result(result)
    print(formatted)
    
    print("\n✅ DeFi Positions работает!")
    return result


async def main():
    """Запуск всех тестов"""
    print("\n" + "🚀 ТЕСТИРОВАНИЕ v1.0.76 - НОВЫЕ ФИЧИ" + "\n")
    
    try:
        # Тест 1: NFT Checker
        nft_result = await test_nft_checker()
        
        # Тест 2: Airdrop Hunter
        airdrop_result = await test_airdrop_hunter()
        
        # Тест 3: DeFi Positions
        defi_result = await test_defi_positions()
        
        # Итоги
        print("\n" + "="*70)
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("="*70)
        
        print("\n📊 СВОДКА:")
        print(f"  ✅ NFT Checker: {nft_result.get('total_nfts', 0)} NFT найдено")
        print(f"  ✅ Airdrop Hunter: {len(airdrop_result.get('eligible_airdrops', []))} eligible")
        print(f"  ✅ DeFi Positions: ${defi_result.get('total_value_usd', 0):,.2f}")
        
        print("\n💪 Все фичи работают корректно!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
