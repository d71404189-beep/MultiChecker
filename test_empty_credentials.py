# -*- coding: utf-8 -*-
"""
Тест обработки данных без credentials
"""

import asyncio
from checkers.crypto_checker import CryptoChecker


async def test_empty_credentials():
    """Тест обработки URL без credentials"""
    
    print("="*70)
    print("🧪 ТЕСТ: URL БЕЗ CREDENTIALS")
    print("="*70)
    
    checker = CryptoChecker()
    
    test_data = {
        "URL без credentials": "accounts.binance.com/en/login-5195504007181936",
        "URL с credentials": "https://binance.com:user@binance.com:password123",
        "Email с password": "user@binance.com:password123",
        "Только email": "user@binance.com",
    }
    
    print("\n📝 Тестируем обработку:")
    print("-" * 70)
    
    for name, data in test_data.items():
        print(f"\n🔍 Тест: {name}")
        print(f"   Данные: {data}")
        
        result = await checker.check(data, timeout=5)
        
        result_type = result.get("type")
        exchange = result.get("exchange")
        login = result.get("info", {}).get("login", "")
        password = result.get("info", {}).get("password", "")
        message = result.get("info", {}).get("message", "")
        error = result.get("info", {}).get("error", "")
        
        print(f"   Type: {result_type}")
        print(f"   Exchange: {exchange}")
        print(f"   Login: '{login}'")
        print(f"   Password: '{password}'")
        
        if result_type == "exchange":
            if login or password:
                print(f"   ✅ Обработано как exchange с credentials")
            else:
                print(f"   ❌ ПРОБЛЕМА: Exchange без credentials!")
        elif result_type == "unknown":
            print(f"   ✅ Корректно определено как unknown (нет credentials)")
            if error:
                print(f"   Error: {error}")
        else:
            print(f"   ℹ️ Определено как: {result_type}")


async def main():
    await test_empty_credentials()


if __name__ == "__main__":
    asyncio.run(main())
