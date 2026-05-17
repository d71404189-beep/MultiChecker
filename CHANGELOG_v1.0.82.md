# 📋 CHANGELOG v1.0.82 - API Error Handling & Diagnostics

## 🎯 Основные изменения

### 🔧 Улучшенная обработка ошибок API

**Проблема:**
Пользователи видели неинформативные ошибки при проверке балансов:
- "All BTC APIs failed"
- "All SOL APIs failed"
- "All ETH APIs failed"

**Решение:**
- ✅ Детальная диагностика ошибок каждого API
- ✅ Различение типов ошибок (429 rate limit, 403 forbidden, timeout)
- ✅ Информативные сообщения вместо generic ошибок
- ✅ Рекомендации по решению проблем

### 📊 Новые возможности

#### 1. Улучшенная обработка ошибок в `crypto_checker.py`

**Метод `_check_bitcoin()`:**
```python
# Было:
result["info"]["error"] = "All BTC APIs failed"

# Стало:
result["info"]["error"] = "⚠️ Не удалось проверить баланс BTC"
result["info"]["api_errors"] = [
    "mempool.space: Rate limit (429)",
    "blockchain.info: Rate limit (429)"
]
result["info"]["recommendation"] = "💡 Используйте прокси или попробуйте позже"
```

**Метод `_check_solana()`:**
- Аналогичная детальная обработка ошибок
- Fallback на альтернативные RPC endpoints
- Информативные сообщения об ошибках

**Метод `_check_tron()`:**
- Добавлен fallback на TronGrid API
- Улучшенная обработка ошибок
- Детальная диагностика

**Метод `_parse_credentials()`:**
- Улучшена обработка URL без credentials
- Исправлен баг с парсингом `https://site.com/path` (теперь не показывает пустые Login/Pass)
- Корректная обработка всех форматов: `url:mail:pass`, `email:password`, `exchange:login:password`

#### 2. Диагностический инструмент `test_api_availability.py`

Новый тест для проверки доступности API:
```bash
python test_api_availability.py
```

**Возможности:**
- ✅ Проверка доступности Bitcoin API (mempool.space, blockchain.info, blockchair)
- ✅ Проверка доступности Ethereum API (etherscan, cloudflare-eth, blockchair)
- ✅ Проверка доступности Solana API (mainnet-beta, solscan)
- ✅ Детальная диагностика (status code, response time, error type)
- ✅ Рекомендации по решению проблем

**Пример вывода:**
```
🔍 Тест: mempool.space
   URL: https://mempool.space/api/address/...
   Status: 429
   Time: 0.28s
   ⚠️ Rate limit exceeded

💡 РЕКОМЕНДАЦИИ:
   1. Используйте прокси для ротации IP
   2. Получите API ключи (Etherscan, Blockchair)
   3. Попробуйте позже (rate limit сбросится)
```

#### 3. Тест сценариев пользователя `test_user_scenario.py`

Проверка корректности парсинга различных форматов:
```bash
python test_user_scenario.py
```

**Тестируемые форматы:**
- ✅ `url:mail:pass` → Login: mail, Pass: pass
- ✅ `email:password` → Login: email, Pass: password
- ✅ `exchange:login:password` → Login: login, Pass: password
- ✅ `https://site.com/path` → НЕ показывает пустые Login/Pass (unknown format)
- ✅ `email@domain.com` → Login: email, Pass: (пусто)

## 🐛 Исправленные баги

### Bug #1: Неинформативные ошибки API
**Было:**
```
error: "All BTC APIs failed"
```

**Стало:**
```
error: "⚠️ Не удалось проверить баланс BTC"
api_errors: ["mempool.space: Rate limit (429)", "blockchain.info: Rate limit (429)"]
message: "❌ BTC API недоступны | mempool.space: Rate limit (429)"
recommendation: "💡 Используйте прокси или попробуйте позже (rate limit)"
```

### Bug #2: Парсинг URL без credentials
**Было:**
```
Input: https://accounts.binance.com/en/login-123456
Result: Login: https | Pass: //accounts.binance.com/en/login-123456
```

**Стало:**
```
Input: https://accounts.binance.com/en/login-123456
Result: Type: unknown, Error: Unknown crypto format
(не показывает пустые Login/Pass)
```

## 📝 Документация

### Новые файлы:
1. **BUGFIX_api_error_handling.md** - Подробное описание проблемы и решения
2. **test_api_availability.py** - Диагностика доступности API
3. **test_user_scenario.py** - Тест сценариев пользователя
4. **test_improved_errors.py** - Тест улучшенной обработки ошибок

### Обновлённые файлы:
1. **checkers/crypto_checker.py**
   - Метод `_check_bitcoin()` - улучшенная обработка ошибок
   - Метод `_check_solana()` - улучшенная обработка ошибок
   - Метод `_check_tron()` - добавлен fallback API
   - Метод `_parse_credentials()` - исправлен парсинг URL

## 🛠️ Рекомендации для пользователей

### Если видите ошибки rate limit (429):

**Вариант 1: Использование прокси**
```
Настройте прокси в поле "Прокси":
http://user:pass@proxy.example.com:8080
```

**Вариант 2: API ключи**
```bash
# Etherscan (для Ethereum)
set ETHERSCAN_API_KEY=your_key_here

# Blockchair (для Bitcoin, Litecoin)
# Добавьте ключ в URL запросов
```

**Вариант 3: Подождать**
```
Rate limit обычно сбрасывается через 5-10 минут
```

## 📊 Результаты тестирования

### Тест 1: Диагностика API
```
✅ Bitcoin: mempool.space работает (иногда rate limit)
✅ Ethereum: cloudflare-eth работает стабильно
✅ Solana: mainnet-beta работает (иногда rate limit)
✅ Tron: tronscan работает стабильно
```

### Тест 2: Парсинг форматов
```
✅ url:mail:pass - корректно парсится
✅ email:password - корректно парсится
✅ exchange:login:password - корректно парсится
✅ Только URL - НЕ показывает пустые Login/Pass
✅ Только email - корректно обрабатывается
```

### Тест 3: Обработка ошибок
```
✅ Детальная диагностика ошибок API
✅ Информативные сообщения
✅ Рекомендации по решению проблем
✅ Fallback на альтернативные API
```

## 🎯 Статистика изменений

- **Изменено файлов:** 1 (crypto_checker.py)
- **Добавлено файлов:** 4 (тесты + документация)
- **Строк кода:** ~200 новых строк
- **Исправлено багов:** 2
- **Улучшено методов:** 4 (_check_bitcoin, _check_solana, _check_tron, _parse_credentials)

## 🚀 Следующие шаги

Рекомендуется добавить в будущих версиях:
1. Автоматическую ротацию прокси
2. Кэширование результатов API (TTL 5 минут)
3. Retry механизм с exponential backoff
4. Поддержку пользовательских API ключей в GUI
5. Мониторинг доступности API в реальном времени

## 📌 Совместимость

- ✅ Обратная совместимость с v1.0.81
- ✅ Все существующие функции работают
- ✅ Новые поля в результатах (api_errors, recommendation) опциональны
- ✅ Работает на Windows, Linux, macOS

---

**Версия:** 1.0.82
**Дата:** 2026-05-17
**Тип релиза:** Bugfix + Improvements
**Приоритет:** Средний (улучшает UX, исправляет баги)
