# 🐛 BUGFIX: Поддержка формата url:mail:pass в парсере

**Дата:** 17 мая 2026  
**Версия:** v1.0.81 (hotfix)  
**Приоритет:** High

---

## 📋 ОПИСАНИЕ ПРОБЛЕМЫ

При загрузке данных в формате `url:mail:pass` парсер показывал ошибки "Not a valid email format", потому что не мог корректно обработать URL с двоеточиями в начале строки.

**Пример проблемных данных:**
```
https://example.com:user@mail.com:password123
https://site.org:test@gmail.com:mypass456
```

**Ошибка:**
```
[ChatGPT] 5054554 - Not a valid email format
[ChatGPT] 5054554 - Not a valid email format
```

---

## ✅ РЕШЕНИЕ

Добавлена специальная обработка формата `url:mail:pass` в методе `_parse_line()`:

### Изменения в `dump_parser.py`:

1. **Определение URL в начале строки**
   ```python
   url_pattern = re.compile(r'^(https?://[^\s:]+):')
   url_match = url_pattern.match(line)
   ```

2. **Извлечение URL и парсинг оставшейся части**
   ```python
   if url_match:
       result["url"] = url_match.group(1)
       remaining = line[len(result["url"]) + 1:]
       parts = remaining.split(':', 2)
       # Парсим как mail:pass
   ```

3. **Обновлен метод `extract_for_checker()`**
   - Добавлен параметр `checker_type` (auto, email, crypto)
   - Для email чекера возвращает `email:password`
   - Для crypto чекера возвращает seed/privkey/address

---

## 🧪 ТЕСТИРОВАНИЕ

### Тестовые данные:
```
https://example.com:user1@mail.com:password123
https://site.org:test@gmail.com:mypass456
https://service.net:admin@yahoo.com:secret789
http://domain.com:info@test.ru:qwerty
https://api.example.com:support@company.com:pass1234
```

### Результаты:
```
✅ Всего строк: 5
✅ Распарсено: 5
✅ Не удалось: 0
✅ Найдено credentials: 5
```

### Извлеченные данные для Email Checker:
```
user1@mail.com:password123
test@gmail.com:mypass456
admin@yahoo.com:secret789
info@test.ru:qwerty
support@company.com:pass1234
```

---

## 📊 ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ

После исправления парсер поддерживает:

1. ✅ `url:mail:pass` - **НОВОЕ**
2. ✅ `email:password`
3. ✅ `email:password:seed`
4. ✅ `email|password|privkey`
5. ✅ `seed phrase (12-24 words)`
6. ✅ `privkey (hex 64 chars)`
7. ✅ `address (ETH/BTC)`

---

## 🔧 ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Изменения в коде:

**Файл:** `checkers/dump_parser.py`

**Метод:** `_parse_line()`
- Добавлена проверка URL в начале строки
- Добавлено извлечение URL
- Добавлен парсинг оставшейся части как `mail:pass`

**Метод:** `extract_for_checker()`
- Добавлен параметр `checker_type`
- Добавлена логика для разных типов чекеров
- Для email чекера возвращает `email:password`

**Новое поле в результате:**
```python
result = {
    "original": line,
    "email": None,
    "password": None,
    "url": None,  # НОВОЕ
    "seed": None,
    "privkey": None,
    "address": None,
    "extra": [],
}
```

---

## 📝 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Пример 1: Парсинг url:mail:pass
```python
from checkers.dump_parser import DumpParser

parser = DumpParser()
dump = """
https://example.com:user@mail.com:password123
https://site.org:test@gmail.com:mypass456
"""

parsed = parser.parse_dump(dump)

# Результат:
# [
#   {
#     "url": "https://example.com",
#     "email": "user@mail.com",
#     "password": "password123"
#   },
#   {
#     "url": "https://site.org",
#     "email": "test@gmail.com",
#     "password": "mypass456"
#   }
# ]
```

### Пример 2: Извлечение для Email Checker
```python
for_checker = parser.extract_for_checker(parsed, checker_type="email")

# Результат:
# [
#   "user@mail.com:password123",
#   "test@gmail.com:mypass456"
# ]
```

---

## ✅ ПРОВЕРКА

### До исправления:
```
❌ [ChatGPT] 5054554 - Not a valid email format
❌ [ChatGPT] 5054554 - Not a valid email format
```

### После исправления:
```
✅ user@mail.com:password123 - корректно распарсено
✅ test@gmail.com:mypass456 - корректно распарсено
```

---

## 🎯 ВЛИЯНИЕ

**Затронутые модули:**
- `checkers/dump_parser.py`

**Обратная совместимость:**
- ✅ Полная обратная совместимость
- ✅ Все старые форматы работают как прежде
- ✅ Добавлена поддержка нового формата

**Производительность:**
- ✅ Без изменений
- ✅ Дополнительная проверка только для строк начинающихся с `http://` или `https://`

---

## 📦 ФАЙЛЫ

**Изменено:**
- `checkers/dump_parser.py` (+30 строк)

**Создано:**
- `test_url_mail_pass_parser.py` (тестовый файл)
- `BUGFIX_url_mail_pass_parser.md` (этот файл)

---

## 🔄 СТАТУС

✅ **ИСПРАВЛЕНО**

- [x] Проблема идентифицирована
- [x] Решение реализовано
- [x] Тесты пройдены (5/5)
- [x] Документация создана
- [x] Обратная совместимость проверена

---

**Автор:** Bes Bits  
**Дата:** 17 мая 2026  
**Версия:** v1.0.81 (hotfix)
