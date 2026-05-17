# -*- coding: utf-8 -*-
"""
Тест форматов для Crypto Checker
Проверяем какие форматы данных принимает Crypto Checker
"""

import asyncio
from checkers.crypto_checker import CryptoChecker


async def test_crypto_formats():
    """Тест различных форматов для Crypto Checker"""
    
    print("="*70)
    print("🧪 ТЕСТ ФОРМАТОВ ДЛЯ CRYPTO CHECKER")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые данные в разных форматах
    test_data = {
        "Seed фраза (12 слов)": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        "Seed фраза (24 слова)": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art",
        "Приватный ключ (hex)": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "Приватный ключ (без 0x)": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "Bitcoin адрес": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "Ethereum адрес": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "Tron адрес": "TRX9QAHgjLqN1x6V5o4FHEJZQjqMbZWUAx",
        "Solana адрес": "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK",
    }
    
    print("\n📝 Тестируем форматы:")
    print("-" * 70)
    
    results = {}
    
    for format_name, data in test_data.items():
        print(f"\n🔍 Тест: {format_name}")
        print(f"   Данные: {data[:50]}...")
        
        try:
            result = await checker.check(data, timeout=5)
            
            # Проверяем результат
            if result.get("type") != "unknown":
                print(f"   ✅ Распознан как: {result.get('type')}")
                print(f"   ✅ Wallet type: {result.get('wallet_type', 'N/A')}")
                results[format_name] = "✅ Поддерживается"
            else:
                print(f"   ❌ Не распознан (type: unknown)")
                results[format_name] = "❌ Не поддерживается"
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            results[format_name] = f"❌ Ошибка: {str(e)[:50]}"
    
    # Итоговая таблица
    print("\n" + "="*70)
    print("📊 ИТОГОВАЯ ТАБЛИЦА ПОДДЕРЖКИ ФОРМАТОВ")
    print("="*70)
    
    for format_name, status in results.items():
        print(f"{format_name:30} {status}")
    
    print("\n" + "="*70)
    
    # Подсчет статистики
    supported = sum(1 for s in results.values() if "✅" in s)
    total = len(results)
    
    print(f"\n📈 Статистика:")
    print(f"   Поддерживается: {supported}/{total}")
    print(f"   Не поддерживается: {total - supported}/{total}")
    print(f"   Процент поддержки: {(supported/total)*100:.1f}%")


async def test_url_mail_pass_format():
    """Тест формата url:mail:pass для Crypto Checker"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТ ФОРМАТА url:mail:pass ДЛЯ CRYPTO CHECKER")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые данные в формате url:mail:pass
    test_data = [
        "https://example.com:user@mail.com:password123",
        "https://site.org:test@gmail.com:mypass456",
    ]
    
    print("\n📝 Тестируем url:mail:pass формат:")
    print("-" * 70)
    
    for data in test_data:
        print(f"\n🔍 Данные: {data}")
        
        try:
            result = await checker.check(data, timeout=5)
            
            print(f"   Type: {result.get('type')}")
            print(f"   Wallet type: {result.get('wallet_type', 'N/A')}")
            print(f"   Error: {result.get('info', {}).get('error', 'None')}")
            
            if result.get("type") != "unknown":
                print(f"   ✅ Формат распознан")
            else:
                print(f"   ❌ Формат НЕ распознан")
                print(f"   ℹ️ Crypto Checker не предназначен для email:password")
                print(f"   ℹ️ Используйте Email Checker для этого формата")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "="*70)
    print("💡 ВЫВОД:")
    print("="*70)
    print("Crypto Checker предназначен для:")
    print("  ✅ Seed фраз (12-24 слова)")
    print("  ✅ Приватных ключей (hex)")
    print("  ✅ Адресов кошельков (BTC, ETH, TRX, SOL, и др.)")
    print("  ✅ API ключей бирж (binance:api_key:api_secret)")
    print("\nДля формата url:mail:pass используйте:")
    print("  ✅ Email Checker")
    print("  ✅ Social Checker")
    print("="*70)


async def main():
    """Запуск всех тестов"""
    await test_crypto_formats()
    await test_url_mail_pass_format()


if __name__ == "__main__":
    asyncio.run(main())
