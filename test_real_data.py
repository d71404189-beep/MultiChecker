# -*- coding: utf-8 -*-
"""
Тест с реальными данными пользователя
"""

from checkers.crypto_checker import CryptoChecker


def test_parse_real_data():
    """Тест парсинга реальных данных"""
    
    print("="*70)
    print("🧪 ТЕСТ ПАРСИНГА РЕАЛЬНЫХ ДАННЫХ")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Примеры данных из скриншота
    test_data = [
        "accounts.binance.com/en/login-5195504007181936",
        "accounts.binance.info/en/login-password2@example.com:password123",
        "https://accounts.binance.com:user@binance.com:password123",
        "user@binance.com:password123",
    ]
    
    print("\n📝 Тестируем парсинг:")
    print("-" * 70)
    
    for data in test_data:
        print(f"\n🔍 Данные: {data}")
        
        # Проверяем определение биржи
        exchange = checker._detect_exchange(data)
        print(f"   Exchange detected: {exchange}")
        
        # Проверяем парсинг credentials
        login, password = checker._parse_credentials(data)
        print(f"   Login: '{login}'")
        print(f"   Password: '{password}'")
        
        if not login and not password:
            print(f"   ❌ ПРОБЛЕМА: Login и Password пустые!")
            print(f"   ℹ️ Возможно данные не содержат email:password")
        elif not login:
            print(f"   ⚠️ Login пустой")
        elif not password:
            print(f"   ⚠️ Password пустой")
        else:
            print(f"   ✅ Данные распарсены корректно")


if __name__ == "__main__":
    test_parse_real_data()
