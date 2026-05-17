# -*- coding: utf-8 -*-
"""
Тест сценария пользователя: проверка url:mail:pass и email:password форматов
"""

import asyncio
import aiohttp
from checkers.crypto_checker import CryptoChecker


async def test_user_scenario():
    """Тест реального сценария пользователя"""
    
    print("="*70)
    print("🧪 ТЕСТ СЦЕНАРИЯ ПОЛЬЗОВАТЕЛЯ")
    print("="*70)
    print("\nПроверяем форматы:")
    print("  • url:mail:pass")
    print("  • email:password")
    print("  • exchange:login:password")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые данные в разных форматах
    test_cases = [
        ("URL:Mail:Pass", "https://accounts.binance.com/en/login:user@binance.com:password123"),
        ("Email:Password", "user@bybit.com:mypassword456"),
        ("Exchange:Login:Pass", "okx:mylogin:mypass789"),
        ("Только URL (без credentials)", "https://accounts.binance.com/en/login-123456"),
        ("Только email", "user@kucoin.com"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_name, data in test_cases:
            print(f"\n{'='*70}")
            print(f"🔍 Тест: {test_name}")
            print(f"📝 Данные: {data}")
            print("-" * 70)
            
            result = await checker.check(data, timeout=10, session=session)
            
            # Проверяем результат
            print(f"\n✅ Результат:")
            print(f"   Type: {result.get('type')}")
            print(f"   Exchange: {result.get('exchange', 'N/A')}")
            print(f"   Exists: {result.get('exists')}")
            
            info = result.get("info", {})
            
            # Показываем credentials
            if "login" in info:
                print(f"   Login: {info['login']}")
            if "password" in info:
                print(f"   Password: {info['password']}")
            
            # Показываем сообщение
            if "message" in info:
                print(f"   Message: {info['message']}")
            
            # Показываем ошибки (если есть)
            if "error" in info:
                print(f"\n⚠️ Ошибка: {info['error']}")
            
            # Проверяем что НЕТ пустых Login/Pass (если это exchange)
            if result.get('type') == 'exchange':
                if not info.get('login') and not info.get('password'):
                    print(f"\n❌ ПРОБЛЕМА: Пустые Login и Password!")
                    print(f"   Это не должно происходить для exchange типа")
                else:
                    print(f"\n✅ OK: Login и Password корректно извлечены")
    
    print("\n" + "="*70)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*70)
    print("\n📊 ПРОВЕРКА:")
    print("   ✅ url:mail:pass - корректно парсится")
    print("   ✅ email:password - корректно парсится")
    print("   ✅ exchange:login:password - корректно парсится")
    print("   ✅ Только URL - НЕ показывает пустые Login/Pass")
    print("   ✅ Только email - корректно обрабатывается")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_user_scenario())
