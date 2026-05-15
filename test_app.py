#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работы MultiChecker v1.0.47
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("MultiChecker v1.0.47 - Тест запуска")
print("=" * 60)

# Тест 1: Импорт модулей
print("\n[1/5] Проверка импорта модулей...")
try:
    import customtkinter as ctk
    print("  ✓ customtkinter")
except ImportError as e:
    print(f"  ✗ customtkinter: {e}")
    sys.exit(1)

try:
    import aiohttp
    print("  ✓ aiohttp")
except ImportError as e:
    print(f"  ✗ aiohttp: {e}")
    sys.exit(1)

try:
    from bip_utils import Bip39MnemonicValidator
    print("  ✓ bip_utils")
except ImportError as e:
    print(f"  ✗ bip_utils: {e}")
    sys.exit(1)

try:
    from eth_account import Account
    print("  ✓ eth_account")
except ImportError as e:
    print(f"  ✗ eth_account: {e}")
    sys.exit(1)

try:
    from web3 import Web3
    print("  ✓ web3")
except ImportError as e:
    print(f"  ✗ web3: {e}")
    sys.exit(1)

# Тест 2: Импорт чекеров
print("\n[2/5] Проверка импорта чекеров...")
try:
    from checkers.email_checker import EmailChecker
    print("  ✓ EmailChecker")
except ImportError as e:
    print(f"  ✗ EmailChecker: {e}")
    sys.exit(1)

try:
    from checkers.social_checker import SocialChecker
    print("  ✓ SocialChecker")
except ImportError as e:
    print(f"  ✗ SocialChecker: {e}")
    sys.exit(1)

try:
    from checkers.crypto_checker import CryptoChecker
    print("  ✓ CryptoChecker")
except ImportError as e:
    print(f"  ✗ CryptoChecker: {e}")
    sys.exit(1)

try:
    from checkers.game_checker import GameChecker
    print("  ✓ GameChecker")
except ImportError as e:
    print(f"  ✗ GameChecker: {e}")
    sys.exit(1)

try:
    from checkers.ai_checker import AIChecker
    print("  ✓ AIChecker")
except ImportError as e:
    print(f"  ✗ AIChecker: {e}")
    sys.exit(1)

# Тест 3: Создание экземпляров чекеров
print("\n[3/5] Создание экземпляров чекеров...")
try:
    crypto = CryptoChecker()
    print(f"  ✓ CryptoChecker создан")
    print(f"    - Автовывод: {'включен' if crypto.auto_withdraw_enabled else 'выключен'}")
    print(f"    - Поддержка бирж: {len(crypto.exchanges)} шт")
except Exception as e:
    print(f"  ✗ Ошибка создания CryptoChecker: {e}")
    sys.exit(1)

# Тест 4: Проверка методов автовывода
print("\n[4/5] Проверка методов автовывода...")
try:
    # Проверяем наличие методов
    assert hasattr(crypto, 'enable_auto_withdraw'), "Метод enable_auto_withdraw не найден"
    assert hasattr(crypto, 'disable_auto_withdraw'), "Метод disable_auto_withdraw не найден"
    assert hasattr(crypto, 'get_withdraw_log'), "Метод get_withdraw_log не найден"
    assert hasattr(crypto, 'export_withdraw_log'), "Метод export_withdraw_log не найден"
    print("  ✓ Все методы автовывода присутствуют")
    
    # Проверяем лог
    log = crypto.get_withdraw_log()
    print(f"  ✓ Лог выводов: {len(log)} записей")
except Exception as e:
    print(f"  ✗ Ошибка проверки методов: {e}")
    sys.exit(1)

# Тест 5: Импорт главного приложения
print("\n[5/5] Проверка импорта главного приложения...")
try:
    import main
    print(f"  ✓ main.py импортирован")
    print(f"  ✓ Версия приложения: {main.APP_VERSION}")
except Exception as e:
    print(f"  ✗ Ошибка импорта main.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Финальный результат
print("\n" + "=" * 60)
print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 60)
print("\nMultiChecker v1.0.47 готов к работе!")
print("\nДля запуска GUI выполните:")
print("  python main.py")
print("\n" + "=" * 60)
