# -*- coding: utf-8 -*-
"""
Тест поддержки форматов url:mail:pass и email:password в Crypto Checker
"""

import asyncio
from checkers.crypto_checker import CryptoChecker


async def test_crypto_email_formats():
    """Тест форматов url:mail:pass и email:password для Crypto Checker"""
    
    print("="*70)
    print("🧪 ТЕСТ: url:mail:pass и email:password для CRYPTO CHECKER")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые данные
    test_data = {
        "url:mail:pass (Binance)": "https://binance.com:user@binance.com:password123",
        "url:mail:pass (Bybit)": "https://bybit.com:trader@bybit.com:mypass456",
        "email:password (Binance)": "user@binance.com:password123",
        "email:password (OKX)": "trader@okx.com:mypass456",
        "email:password (Coinbase)": "user@coinbase.com:secret789",
        "login:password (generic)": "binance:mylogin:mypassword",
        "email:password (generic)": "user@example.com:password123",
    }
    
    print("\n📝 Тестируем форматы:")
    print("-" * 70)
    
    results = {}
    
    for format_name, data in test_data.items():
        print(f"\n🔍 Тест: {format_name}")
        print(f"   Данные: {data}")
        
        try:
            result = await checker.check(data, timeout=5)
            
            # Проверяем результат
            result_type = result.get("type")
            exchange = result.get("exchange") or result.get("platform")
            login = result.get("info", {}).get("login", "")
            password = result.get("info", {}).get("password", "")
            
            print(f"   Type: {result_type}")
            print(f"   Exchange: {exchange}")
            print(f"   Login: {login}")
            print(f"   Password: {password}")
            
            if result_type == "exchange" and login and password:
                print(f"   ✅ Формат распознан корректно!")
                results[format_name] = "✅ Поддерживается"
            else:
                print(f"   ❌ Формат НЕ распознан")
                results[format_name] = "❌ Не поддерживается"
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            results[format_name] = f"❌ Ошибка: {str(e)[:50]}"
    
    # Итоговая таблица
    print("\n" + "="*70)
    print("📊 ИТОГОВАЯ ТАБЛИЦА ПОДДЕРЖКИ ФОРМАТОВ")
    print("="*70)
    
    for format_name, status in results.items():
        print(f"{format_name:40} {status}")
    
    print("\n" + "="*70)
    
    # Подсчет статистики
    supported = sum(1 for s in results.values() if "✅" in s)
    total = len(results)
    
    print(f"\n📈 Статистика:")
    print(f"   Поддерживается: {supported}/{total}")
    print(f"   Не поддерживается: {total - supported}/{total}")
    print(f"   Процент поддержки: {(supported/total)*100:.1f}%")
    
    return supported == total


async def test_parse_credentials():
    """Тест метода _parse_credentials"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ: Метод _parse_credentials")
    print("="*70)
    
    checker = CryptoChecker()
    
    test_cases = [
        ("https://binance.com:user@binance.com:password123", ("user@binance.com", "password123")),
        ("https://bybit.com:trader@bybit.com:mypass456", ("trader@bybit.com", "mypass456")),
        ("user@binance.com:password123", ("user@binance.com", "password123")),
        ("trader@okx.com:mypass456", ("trader@okx.com", "mypass456")),
        ("binance:mylogin:mypassword", ("mylogin", "mypassword")),
        ("user@example.com:password123", ("user@example.com", "password123")),
    ]
    
    print("\n📝 Тестируем парсинг:")
    print("-" * 70)
    
    all_passed = True
    
    for data, expected in test_cases:
        login, password = checker._parse_credentials(data)
        
        if (login, password) == expected:
            print(f"✅ {data[:50]:50} → ({login}, {password})")
        else:
            print(f"❌ {data[:50]:50}")
            print(f"   Ожидалось: {expected}")
            print(f"   Получено: ({login}, {password})")
            all_passed = False
    
    print("\n" + "="*70)
    
    if all_passed:
        print("✅ Все тесты парсинга пройдены!")
    else:
        print("❌ Некоторые тесты парсинга провалены")
    
    return all_passed


async def test_detect_exchange():
    """Тест метода _detect_exchange"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ: Метод _detect_exchange")
    print("="*70)
    
    checker = CryptoChecker()
    
    test_cases = [
        ("https://binance.com:user@binance.com:password123", "binance"),
        ("https://bybit.com:trader@bybit.com:mypass456", "bybit"),
        ("user@binance.com:password123", "binance"),
        ("trader@okx.com:mypass456", "okx"),
        ("user@coinbase.com:secret789", "coinbase"),
        ("binance:mylogin:mypassword", "binance"),
        ("user@example.com:password123", "exchange"),  # generic
    ]
    
    print("\n📝 Тестируем определение биржи:")
    print("-" * 70)
    
    all_passed = True
    
    for data, expected in test_cases:
        detected = checker._detect_exchange(data)
        
        if detected == expected:
            print(f"✅ {data[:50]:50} → {detected}")
        else:
            print(f"❌ {data[:50]:50}")
            print(f"   Ожидалось: {expected}")
            print(f"   Получено: {detected}")
            all_passed = False
    
    print("\n" + "="*70)
    
    if all_passed:
        print("✅ Все тесты определения биржи пройдены!")
    else:
        print("❌ Некоторые тесты определения биржи провалены")
    
    return all_passed


async def main():
    """Запуск всех тестов"""
    
    print("\n" + "="*70)
    print("🚀 ЗАПУСК ТЕСТОВ CRYPTO CHECKER - EMAIL FORMATS")
    print("="*70)
    
    test1 = await test_parse_credentials()
    test2 = await test_detect_exchange()
    test3 = await test_crypto_email_formats()
    
    print("\n" + "="*70)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*70)
    
    print(f"test_parse_credentials: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"test_detect_exchange: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"test_crypto_email_formats: {'✅ PASSED' if test3 else '❌ FAILED'}")
    
    if test1 and test2 and test3:
        print("\n🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("\n✅ Crypto Checker теперь поддерживает:")
        print("   • url:mail:pass")
        print("   • email:password")
        print("   • login:password")
        return True
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
