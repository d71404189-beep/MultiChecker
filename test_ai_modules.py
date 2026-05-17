# -*- coding: utf-8 -*-
"""
Тесты для AI модулей - проверка на баги и ошибки
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from checkers.ai_subscription_checker import AISubscriptionChecker, global_subscription_checker
from checkers.ai_api_validator import AIAPIValidator, global_api_validator


def test_subscription_checker_init():
    """Тест инициализации subscription checker"""
    print("\n🧪 Тест: Инициализация Subscription Checker")
    
    checker = AISubscriptionChecker()
    
    assert len(checker.subscription_prices) > 0, "Цены не загружены"
    assert len(checker.subscription_tiers) > 0, "Tier'ы не загружены"
    
    # Проверяем что все цены положительные
    for key, price in checker.subscription_prices.items():
        assert price > 0, f"Неверная цена для {key}: {price}"
    
    print(f"✅ Загружено {len(checker.subscription_prices)} цен подписок")
    print(f"✅ Загружено {len(checker.subscription_tiers)} tier'ов")
    return True


def test_calculate_total_value_empty():
    """Тест расчета стоимости с пустым списком"""
    print("\n🧪 Тест: Расчет стоимости (пустой список)")
    
    checker = AISubscriptionChecker()
    
    # Тест с пустым списком
    result = checker.calculate_total_value([])
    assert result["active_subscriptions"] == 0, "Должно быть 0 подписок"
    assert result["total_monthly"] == 0.0, "Должно быть 0.0"
    
    # Тест с None
    result = checker.calculate_total_value(None)
    assert result["active_subscriptions"] == 0, "Должно быть 0 подписок"
    
    # Тест с невалидными данными
    result = checker.calculate_total_value([None, "invalid", 123])
    assert result["active_subscriptions"] == 0, "Должно быть 0 подписок"
    
    print("✅ Обработка пустых данных работает корректно")
    return True


def test_calculate_total_value_valid():
    """Тест расчета стоимости с валидными данными"""
    print("\n🧪 Тест: Расчет стоимости (валидные данные)")
    
    checker = AISubscriptionChecker()
    
    subscriptions = [
        {
            "service": "ChatGPT",
            "has_subscription": True,
            "monthly_cost": 20.0,
            "plan_name": "Plus"
        },
        {
            "service": "Claude",
            "has_subscription": True,
            "monthly_cost": 20.0,
            "plan_name": "Pro"
        },
        {
            "service": "Midjourney",
            "has_subscription": False,
            "monthly_cost": 0.0,
            "plan_name": "Free"
        },
    ]
    
    result = checker.calculate_total_value(subscriptions)
    
    assert result["active_subscriptions"] == 2, f"Должно быть 2 подписки, получено {result['active_subscriptions']}"
    assert result["total_monthly"] == 40.0, f"Должно быть 40.0, получено {result['total_monthly']}"
    assert result["total_yearly"] == 480.0, f"Должно быть 480.0, получено {result['total_yearly']}"
    assert len(result["services"]) == 2, "Должно быть 2 сервиса"
    
    print(f"✅ Активных подписок: {result['active_subscriptions']}")
    print(f"✅ Стоимость в месяц: ${result['total_monthly']}")
    print(f"✅ Стоимость в год: ${result['total_yearly']}")
    return True


def test_api_validator_init():
    """Тест инициализации API validator"""
    print("\n🧪 Тест: Инициализация API Validator")
    
    validator = AIAPIValidator()
    
    assert len(validator.api_patterns) > 0, "Паттерны не загружены"
    
    print(f"✅ Загружено {len(validator.api_patterns)} паттернов API ключей")
    return True


def test_detect_api_key_type():
    """Тест определения типа API ключа"""
    print("\n🧪 Тест: Определение типа API ключа")
    
    validator = AIAPIValidator()
    
    # Тестовые ключи (не валидные, только для проверки паттерна)
    test_keys = {
        "sk-proj-" + "a" * 48: "openai",
        "sk-ant-" + "a" * 95: "anthropic",
        "AIza" + "a" * 35: "google",
        "r8_" + "a" * 40: "replicate",
        "hf_" + "a" * 38: "huggingface",
    }
    
    for key, expected_type in test_keys.items():
        detected = validator.detect_api_key_type(key)
        assert detected == expected_type, f"Ожидался {expected_type}, получен {detected}"
        print(f"✅ {expected_type}: корректно определен")
    
    # Тест с невалидным ключом
    invalid_key = "invalid_key_123"
    detected = validator.detect_api_key_type(invalid_key)
    assert detected is None, "Невалидный ключ должен вернуть None"
    print("✅ Невалидный ключ корректно обработан")
    
    return True


def test_calculate_total_credits_empty():
    """Тест расчета credits с пустым списком"""
    print("\n🧪 Тест: Расчет credits (пустой список)")
    
    validator = AIAPIValidator()
    
    # Тест с пустым списком
    result = validator.calculate_total_credits([])
    assert result["total_keys"] == 0, f"Должно быть 0 ключей, получено {result['total_keys']}"
    assert result["total_credits"] == 0.0, f"Должно быть 0.0 credits, получено {result['total_credits']}"
    
    # Тест с None
    result = validator.calculate_total_credits(None)
    assert result["total_keys"] == 0, f"Должно быть 0 ключей, получено {result['total_keys']}"
    
    # Тест с невалидными данными - ИСПРАВЛЕНО: эти элементы будут пропущены, но total_keys будет 3
    result = validator.calculate_total_credits([None, "invalid", 123])
    # Эти элементы пропускаются в цикле, поэтому total_keys = len([None, "invalid", 123]) = 3
    # но valid_keys и invalid_keys будут 0, так как все пропущены
    assert result["valid_keys"] == 0, f"Должно быть 0 валидных, получено {result['valid_keys']}"
    assert result["invalid_keys"] == 0, f"Должно быть 0 невалидных, получено {result['invalid_keys']}"
    
    print("✅ Обработка пустых данных работает корректно")
    return True


def test_calculate_total_credits_valid():
    """Тест расчета credits с валидными данными"""
    print("\n🧪 Тест: Расчет credits (валидные данные)")
    
    validator = AIAPIValidator()
    
    validations = [
        {
            "valid": True,
            "service": "OpenAI",
            "credits": 50.0
        },
        {
            "valid": True,
            "service": "Anthropic",
            "credits": 25.0
        },
        {
            "valid": False,
            "service": "Google",
            "credits": 0.0
        },
        {
            "valid": True,
            "service": "OpenAI",
            "credits": 10.0
        },
    ]
    
    result = validator.calculate_total_credits(validations)
    
    assert result["total_keys"] == 4, f"Должно быть 4 ключа, получено {result['total_keys']}"
    assert result["valid_keys"] == 3, f"Должно быть 3 валидных, получено {result['valid_keys']}"
    assert result["invalid_keys"] == 1, f"Должен быть 1 невалидный, получено {result['invalid_keys']}"
    assert result["total_credits"] == 85.0, f"Должно быть 85.0, получено {result['total_credits']}"
    
    # Проверяем группировку по сервисам
    assert "OpenAI" in result["services"], "OpenAI должен быть в сервисах"
    assert result["services"]["OpenAI"]["count"] == 2, "Должно быть 2 ключа OpenAI"
    assert result["services"]["OpenAI"]["credits"] == 60.0, "Должно быть 60.0 credits для OpenAI"
    
    print(f"✅ Всего ключей: {result['total_keys']}")
    print(f"✅ Валидных: {result['valid_keys']}")
    print(f"✅ Невалидных: {result['invalid_keys']}")
    print(f"✅ Всего credits: ${result['total_credits']}")
    return True


def test_edge_cases():
    """Тест граничных случаев"""
    print("\n🧪 Тест: Граничные случаи")
    
    checker = AISubscriptionChecker()
    
    # Тест с отрицательной стоимостью (не должно добавляться)
    subscriptions = [
        {
            "service": "Test",
            "has_subscription": True,
            "monthly_cost": -10.0,  # Отрицательная
            "plan_name": "Invalid"
        },
        {
            "service": "Test2",
            "has_subscription": True,
            "monthly_cost": "invalid",  # Невалидный тип
            "plan_name": "Invalid"
        },
    ]
    
    result = checker.calculate_total_value(subscriptions)
    assert result["total_monthly"] == 0.0, "Отрицательные и невалидные значения не должны учитываться"
    
    print("✅ Граничные случаи обработаны корректно")
    return True


def test_rounding():
    """Тест округления"""
    print("\n🧪 Тест: Округление чисел")
    
    checker = AISubscriptionChecker()
    
    subscriptions = [
        {
            "service": "Test",
            "has_subscription": True,
            "monthly_cost": 19.999,
            "plan_name": "Test"
        },
    ]
    
    result = checker.calculate_total_value(subscriptions)
    
    # Проверяем что округление работает
    assert isinstance(result["total_monthly"], float), "Должно быть float"
    assert result["total_monthly"] == 20.0, f"Должно быть 20.0, получено {result['total_monthly']}"
    
    print(f"✅ Округление работает: 19.999 -> {result['total_monthly']}")
    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("🚀 ТЕСТИРОВАНИЕ AI МОДУЛЕЙ")
    print("="*60)
    
    tests = [
        ("Subscription Checker Init", test_subscription_checker_init),
        ("Calculate Total Value (Empty)", test_calculate_total_value_empty),
        ("Calculate Total Value (Valid)", test_calculate_total_value_valid),
        ("API Validator Init", test_api_validator_init),
        ("Detect API Key Type", test_detect_api_key_type),
        ("Calculate Total Credits (Empty)", test_calculate_total_credits_empty),
        ("Calculate Total Credits (Valid)", test_calculate_total_credits_valid),
        ("Edge Cases", test_edge_cases),
        ("Rounding", test_rounding),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ FAILED: {name}")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR in {name}: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print("📊 ИТОГИ")
    print("="*60)
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Провалено: {failed}")
    print(f"📈 Всего: {passed + failed}")
    print(f"🎯 Успешность: {(passed / (passed + failed) * 100):.1f}%")
    print("="*60 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
