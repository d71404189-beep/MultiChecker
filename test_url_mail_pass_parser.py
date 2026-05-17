# -*- coding: utf-8 -*-
"""
Тест парсера для формата url:mail:pass
"""

from checkers.dump_parser import DumpParser


def test_url_mail_pass_format():
    """Тест парсинга формата url:mail:pass"""
    
    print("="*70)
    print("🧪 ТЕСТ ПАРСЕРА: url:mail:pass формат")
    print("="*70)
    
    # Тестовые данные в формате url:mail:pass
    test_dump = """
https://example.com:user1@mail.com:password123
https://site.org:test@gmail.com:mypass456
https://service.net:admin@yahoo.com:secret789
http://domain.com:info@test.ru:qwerty
https://api.example.com:support@company.com:pass1234
"""
    
    parser = DumpParser()
    parsed = parser.parse_dump(test_dump)
    
    print(f"\n📊 Результаты парсинга:")
    print(f"   Всего строк: {parser.stats['total_lines']}")
    print(f"   Распарсено: {parser.stats['parsed_lines']}")
    print(f"   Не удалось: {parser.stats['failed_lines']}")
    print(f"   Найдено credentials: {parser.stats['found_credentials']}")
    
    print(f"\n📝 Распарсенные данные:")
    for i, item in enumerate(parsed, 1):
        print(f"\n   Запись #{i}:")
        if item.get("url"):
            print(f"      🌐 URL: {item['url']}")
        if item.get("email"):
            print(f"      📧 Email: {item['email']}")
        if item.get("password"):
            print(f"      🔒 Password: {item['password']}")
    
    # Извлекаем для email чекера
    print(f"\n📤 Данные для Email Checker:")
    for_checker = parser.extract_for_checker(parsed, checker_type="email")
    for item in for_checker:
        print(f"   {item}")
    
    # Проверяем что всё корректно распарсилось
    print(f"\n✅ Тест завершен!")
    
    if parser.stats['parsed_lines'] == 5 and parser.stats['found_credentials'] == 5:
        print(f"   ✅ Все 5 записей успешно распарсены!")
        return True
    else:
        print(f"   ❌ Ошибка: ожидалось 5 записей, получено {parser.stats['parsed_lines']}")
        return False


if __name__ == "__main__":
    success = test_url_mail_pass_format()
    exit(0 if success else 1)
