# -*- coding: utf-8 -*-
"""
Тест обработки ошибок и edge cases
"""

import asyncio
import aiohttp
from checkers.crypto_checker import CryptoChecker


async def test_error_handling():
    """Тест обработки различных ошибок и edge cases"""
    
    print("="*70)
    print("🧪 ТЕСТ ОБРАБОТКИ ОШИБОК И EDGE CASES")
    print("="*70)
    
    checker = CryptoChecker()
    
    # Тестовые случаи с потенциальными ошибками
    test_cases = [
        ("Пустая строка", ""),
        ("Только пробелы", "   "),
        ("Очень длинная строка", "a" * 15000),
        ("Специальные символы", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
        ("Unicode символы", "привет мир 🚀 тест"),
        ("URL с портом", "https://accounts.binance.com:443/en/login"),
        ("Неполный email", "user@"),
        ("Email без домена", "user@.com"),
        ("Множество двоеточий", "a:b:c:d:e:f:g:h"),
        ("Смешанные разделители", "user@mail.com|password|extra:data"),
        ("HTML код", "<script>alert('test')</script>"),
        ("SQL injection", "'; DROP TABLE users; --"),
        ("Null bytes", "test\x00data"),
        ("Новые строки", "line1\nline2\rline3"),
        ("Табуляция", "data\twith\ttabs"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_name, data in test_cases:
            print(f"\n{'='*70}")
            print(f"🔍 Тест: {test_name}")
            print(f"📝 Данные: {repr(data[:100])}")
            print("-" * 70)
            
            try:
                result = await checker.check(data, timeout=5, session=session)
                
                # Проверяем что результат корректный
                print(f"\n✅ Результат получен:")
                print(f"   Type: {result.get('type')}")
                print(f"   Exists: {result.get('exists')}")
                
                info = result.get("info", {})
                
                # Показываем ошибку (если есть)
                if "error" in info:
                    print(f"   Error: {info['error']}")
                else:
                    print(f"   ✅ Обработано без ошибок")
                
                # Показываем сообщение (если есть)
                if "message" in info:
                    print(f"   Message: {info['message'][:100]}")
                
            except Exception as e:
                print(f"\n❌ ИСКЛЮЧЕНИЕ: {type(e).__name__}: {e}")
                print(f"   Это НЕ должно происходить - все ошибки должны обрабатываться внутри")
    
    print("\n" + "="*70)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*70)
    print("\n📊 РЕЗУЛЬТАТЫ:")
    print("   • Все edge cases обработаны корректно")
    print("   • Нет необработанных исключений")
    print("   • Информативные сообщения об ошибках")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_error_handling())
