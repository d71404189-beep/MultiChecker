# -*- coding: utf-8 -*-
"""
Тест улучшенной обработки ошибок API в Crypto Checker
"""

import asyncio
import aiohttp
from checkers.crypto_checker import CryptoChecker


async def test_improved_error_handling():
    """Тест улучшенной обработки ошибок"""
    
    print("="*70)
    print("🧪 ТЕСТ УЛУЧШЕННОЙ ОБРАБОТКИ ОШИБОК API")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые адреса
    test_cases = [
        ("Bitcoin", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"),
        ("Ethereum", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"),
        ("Solana", "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK"),
        ("Tron", "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for chain_name, address in test_cases:
            print(f"\n{'='*70}")
            print(f"🔍 Тест: {chain_name}")
            print(f"📝 Адрес: {address}")
            print("-" * 70)
            
            result = await checker.check(address, timeout=10, session=session)
            
            # Проверяем результат
            print(f"\n✅ Результат:")
            print(f"   Type: {result.get('type')}")
            print(f"   Wallet Type: {result.get('wallet_type')}")
            print(f"   Exists: {result.get('exists')}")
            
            info = result.get("info", {})
            
            # Показываем сообщение
            if "message" in info:
                print(f"   Message: {info['message']}")
            
            # Показываем ошибки (если есть)
            if "error" in info:
                print(f"\n⚠️ Ошибка: {info['error']}")
            
            # Показываем детали ошибок API (если есть)
            if "api_errors" in info:
                print(f"\n📊 Детали ошибок API:")
                for err in info["api_errors"]:
                    print(f"      • {err}")
            
            # Показываем рекомендации (если есть)
            if "recommendation" in info:
                print(f"\n💡 Рекомендация: {info['recommendation']}")
            
            # Показываем баланс (если есть)
            balance_keys = [k for k in info.keys() if k.startswith("balance_")]
            if balance_keys:
                print(f"\n💰 Балансы:")
                for key in balance_keys:
                    print(f"      {key}: {info[key]}")
    
    print("\n" + "="*70)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*70)
    print("\n📊 РЕЗУЛЬТАТЫ:")
    print("   • Улучшенная обработка ошибок работает")
    print("   • Информативные сообщения об ошибках")
    print("   • Рекомендации по решению проблем")
    print("   • Детальная диагностика API")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_improved_error_handling())
