#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест интеграции новых фич с UI
"""

import sys
import os

# Проверяем что все импорты работают
print("🔍 Проверка импортов...")

try:
    from checkers.nft_checker import NFTChecker
    print("  ✅ NFTChecker импортирован")
except Exception as e:
    print(f"  ❌ NFTChecker: {e}")
    sys.exit(1)

try:
    from checkers.airdrop_hunter import AirdropHunter
    print("  ✅ AirdropHunter импортирован")
except Exception as e:
    print(f"  ❌ AirdropHunter: {e}")
    sys.exit(1)

try:
    from checkers.defi_positions import DeFiPositionsChecker
    print("  ✅ DeFiPositionsChecker импортирован")
except Exception as e:
    print(f"  ❌ DeFiPositionsChecker: {e}")
    sys.exit(1)

# Проверяем что main.py компилируется
print("\n🔍 Проверка main.py...")

try:
    import py_compile
    py_compile.compile('main.py', doraise=True)
    print("  ✅ main.py компилируется без ошибок")
except Exception as e:
    print(f"  ❌ main.py: {e}")
    sys.exit(1)

# Проверяем что методы существуют в main.py
print("\n🔍 Проверка методов в main.py...")

try:
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    methods = [
        'check_nfts',
        'check_airdrops', 
        'check_defi_positions'
    ]
    
    for method in methods:
        if f'def {method}(' in content:
            print(f"  ✅ Метод {method} найден")
        else:
            print(f"  ❌ Метод {method} НЕ найден")
            sys.exit(1)

except Exception as e:
    print(f"  ❌ Ошибка чтения main.py: {e}")
    sys.exit(1)

# Проверяем что кнопки добавлены
print("\n🔍 Проверка кнопок в UI...")

buttons = [
    ('🖼️ NFT', 'btn_nft'),
    ('🪂 AIRDROP', 'btn_airdrop'),
    ('📊 DEFI', 'btn_defi')
]

for button_text, button_var in buttons:
    if button_text in content:
        print(f"  ✅ Кнопка '{button_text}' найдена")
    else:
        print(f"  ❌ Кнопка '{button_text}' НЕ найдена")
        sys.exit(1)

# Проверяем версию
print("\n🔍 Проверка версии...")

if 'APP_VERSION = "1.0.76"' in content:
    print("  ✅ Версия 1.0.76 установлена")
else:
    print("  ❌ Версия НЕ обновлена")
    sys.exit(1)

# Проверяем changelog
print("\n🔍 Проверка changelog...")

if os.path.exists('CHANGELOG_v1.0.76.md'):
    print("  ✅ CHANGELOG_v1.0.76.md существует")
else:
    print("  ❌ CHANGELOG_v1.0.76.md НЕ найден")
    sys.exit(1)

# Итоги
print("\n" + "="*70)
print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("="*70)

print("\n✅ Интеграция успешна:")
print("  • Все модули импортируются")
print("  • main.py компилируется")
print("  • Все методы добавлены")
print("  • Все кнопки в UI")
print("  • Версия обновлена")
print("  • Changelog создан")

print("\n🚀 v1.0.76 готов к использованию!")
