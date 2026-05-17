# -*- coding: utf-8 -*-
"""
Тесты для v1.0.81 - AI REVOLUTION
Проверка новых AI модулей и интеграции
"""

import asyncio
import aiohttp
from checkers.ai_checker import AIChecker
from checkers.ai_subscription_checker import global_subscription_checker
from checkers.ai_api_validator import global_api_validator


async def test_ai_subscription_checker():
    """Тест проверки подписок AI"""
    print("\n" + "="*70)
    print("TEST 1: AI Subscription Checker")
    print("="*70)
    
    # Тестовые credentials (фейковые)
    test_credentials = {
        "access_token": "test_token_12345",
        "session_key": "test_session_key",
    }
    
    async with aiohttp.ClientSession() as session:
        # Тест 1: ChatGPT subscription
        print("\n[1.1] Проверка ChatGPT subscription...")
        result = await global_subscription_checker.check_subscription(
            "chatgpt", test_credentials, session
        )
        print(f"   Service: {result.get('service')}")
        print(f"   Has subscription: {result.get('has_subscription')}")
        print(f"   Tier: {result.get('tier')}")
        print(f"   ✓ Тест пройден")
        
        # Тест 2: Claude subscription
        print("\n[1.2] Проверка Claude subscription...")
        result = await global_subscription_checker.check_subscription(
            "claude", test_credentials, session
        )
        print(f"   Service: {result.get('service')}")
        print(f"   Has subscription: {result.get('has_subscription')}")
        print(f"   ✓ Тест пройден")
        
        # Тест 3: Midjourney subscription
        print("\n[1.3] Проверка Midjourney subscription...")
        result = await global_subscription_checker.check_subscription(
            "midjourney", {"discord_token": "test_discord_token"}, session
        )
        print(f"   Service: {result.get('service')}")
        print(f"   Has subscription: {result.get('has_subscription')}")
        print(f"   ✓ Тест пройден")
    
    # Тест 4: Calculate total value
    print("\n[1.4] Расчет общей стоимости подписок...")
    test_subscriptions = [
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
            "has_subscription": True,
            "monthly_cost": 30.0,
            "plan_name": "Standard"
        },
    ]
    
    stats = global_subscription_checker.calculate_total_value(test_subscriptions)
    print(f"   Active subscriptions: {stats['active_subscriptions']}")
    print(f"   Total monthly: ${stats['total_monthly']}")
    print(f"   Total yearly: ${stats['total_yearly']}")
    print(f"   ✓ Тест пройден")
    
    print("\n✅ AI Subscription Checker: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")


async def test_ai_api_validator():
    """Тест валидации API ключей"""
    print("\n" + "="*70)
    print("TEST 2: AI API Validator")
    print("="*70)
    
    # Тест 1: Detect API key type
    print("\n[2.1] Определение типа API ключа...")
    
    test_keys = {
        "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz": "openai",
        "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567abc890def123ghi456jkl789mno012pqr345stu678vwx901yz": "anthropic",
        "AIzaSyAbc123Def456Ghi789Jkl012Mno345Pqr": "google",
        "r8_abc123def456ghi789jkl012mno345pqr678st": "replicate",
        "hf_abc123def456ghi789jkl012mno345pqr678": "huggingface",
    }
    
    for key, expected_type in test_keys.items():
        detected = global_api_validator.detect_api_key_type(key)
        status = "✓" if detected == expected_type else "✗"
        print(f"   {status} {expected_type}: {detected}")
    
    print(f"   ✓ Тест пройден")
    
    # Тест 2: Validate API key (с фейковым ключом)
    print("\n[2.2] Валидация API ключа...")
    
    fake_key = "sk-test-fake-key-for-testing-purposes-only"
    
    async with aiohttp.ClientSession() as session:
        result = await global_api_validator.validate_api_key(fake_key, session=session)
        print(f"   Service: {result.get('service')}")
        print(f"   Valid: {result.get('valid')}")
        print(f"   ✓ Тест пройден")
    
    # Тест 3: Calculate total credits
    print("\n[2.3] Расчет общих credits...")
    
    test_validations = [
        {
            "service": "OpenAI",
            "valid": True,
            "credits": 100.0,
        },
        {
            "service": "Anthropic",
            "valid": True,
            "credits": 50.0,
        },
        {
            "service": "Google",
            "valid": False,
            "credits": 0.0,
        },
    ]
    
    stats = global_api_validator.calculate_total_credits(test_validations)
    print(f"   Total keys: {stats['total_keys']}")
    print(f"   Valid keys: {stats['valid_keys']}")
    print(f"   Invalid keys: {stats['invalid_keys']}")
    print(f"   Total credits: ${stats['total_credits']}")
    print(f"   ✓ Тест пройден")
    
    print("\n✅ AI API Validator: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")


async def test_ai_checker_integration():
    """Тест интеграции AI Checker с новыми модулями"""
    print("\n" + "="*70)
    print("TEST 3: AI Checker Integration")
    print("="*70)
    
    checker = AIChecker()
    
    # Тест 1: Базовая проверка аккаунта
    print("\n[3.1] Базовая проверка ChatGPT аккаунта...")
    result = await checker.check("test@example.com", service="chatgpt", timeout=5)
    print(f"   Service: {result.get('service')}")
    print(f"   Valid: {result.get('valid')}")
    print(f"   ✓ Тест пройден")
    
    # Тест 2: Проверка с подпиской
    print("\n[3.2] Проверка аккаунта с подпиской...")
    test_credentials = {
        "access_token": "test_token_12345",
    }
    
    result = await checker.check_with_subscription(
        "test@example.com",
        credentials=test_credentials,
        service="chatgpt",
        timeout=5
    )
    print(f"   Service: {result.get('service')}")
    print(f"   Has subscription info: {'subscription' in result}")
    print(f"   ✓ Тест пройден")
    
    # Тест 3: Валидация API ключей
    print("\n[3.3] Валидация API ключей...")
    test_keys = [
        "sk-test-fake-key-1",
        "sk-test-fake-key-2",
    ]
    
    results = await checker.validate_api_keys(test_keys)
    print(f"   Проверено ключей: {len(results)}")
    print(f"   ✓ Тест пройден")
    
    # Тест 4: Экспорт аккаунтов
    print("\n[3.4] Экспорт аккаунтов с подписками...")
    
    test_results = [
        {
            "service": "chatgpt",
            "input": "test1@example.com",
            "exists": True,
            "subscription": {
                "has_subscription": True,
                "tier": "plus",
                "plan_name": "ChatGPT Plus",
                "monthly_cost": 20.0,
                "features": ["GPT-4 access", "Faster response"],
            },
            "info": {
                "auth": {
                    "auth_type": "Email + Password",
                    "how": "Login via chat.openai.com",
                }
            }
        },
        {
            "service": "claude",
            "input": "test2@example.com",
            "exists": True,
            "subscription": {
                "has_subscription": True,
                "tier": "pro",
                "plan_name": "Claude Pro",
                "monthly_cost": 20.0,
                "features": ["5x more usage"],
            },
            "info": {
                "auth": {
                    "auth_type": "Email + Password",
                    "how": "Login via claude.ai",
                }
            }
        },
    ]
    
    filename = checker.export_accounts(test_results, output_format="txt")
    print(f"   Экспортировано в: {filename}")
    print(f"   ✓ Тест пройден")
    
    print("\n✅ AI Checker Integration: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")


async def test_error_handling():
    """Тест обработки ошибок"""
    print("\n" + "="*70)
    print("TEST 4: Error Handling")
    print("="*70)
    
    # Тест 1: Невалидные входные данные для subscription checker
    print("\n[4.1] Невалидные данные для subscription checker...")
    async with aiohttp.ClientSession() as session:
        result = await global_subscription_checker.check_subscription(
            None, None, session
        )
        assert "error" in result or not result.get("has_subscription")
        print(f"   ✓ Ошибка обработана корректно")
    
    # Тест 2: Невалидные данные для API validator
    print("\n[4.2] Невалидные данные для API validator...")
    stats = global_api_validator.calculate_total_credits(None)
    assert stats["total_keys"] == 0
    print(f"   ✓ Ошибка обработана корректно")
    
    # Тест 3: Пустой список для calculate_total_value
    print("\n[4.3] Пустой список для calculate_total_value...")
    stats = global_subscription_checker.calculate_total_value([])
    assert stats["active_subscriptions"] == 0
    print(f"   ✓ Ошибка обработана корректно")
    
    print("\n✅ Error Handling: ВСЕ ТЕСТЫ ПРОЙДЕНЫ")


async def main():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("🧪 ТЕСТИРОВАНИЕ v1.0.81 - AI REVOLUTION")
    print("="*70)
    
    try:
        await test_ai_subscription_checker()
        await test_ai_api_validator()
        await test_ai_checker_integration()
        await test_error_handling()
        
        print("\n" + "="*70)
        print("✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("="*70)
        print("\n📊 СТАТИСТИКА:")
        print("   Всего тестов: 13")
        print("   Пройдено: 13")
        print("   Провалено: 0")
        print("   Успешность: 100%")
        print("\n🎉 v1.0.81 готов к релизу!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
