# 📋 CHANGELOG v1.0.64

**Дата релиза:** 17 мая 2026  
**Тип:** Major Feature Release  
**Автор:** Bes Bits

---

## 🚀 ОСНОВНЫЕ УЛУЧШЕНИЯ

5 мощных модулей для продвинутого анализа и работы с результатами!

---

## 🎯 НОВЫЕ МОДУЛИ

### 1. 🔗 Related Addresses Finder - Поиск связанных адресов

**Модуль:** `checkers/related_addresses.py`

**Что это?**
Автоматический поиск адресов и аккаунтов, принадлежащих одному владельцу!

**Возможности:**
- ✅ Группировка по seed фразе (один seed = один владелец)
- ✅ Группировка по приватному ключу
- ✅ Группировка по email (один email = один владелец)
- ✅ Группировка по паролю (одинаковые пароли)
- ✅ Группировка по паттернам адресов (похожие префиксы/суффиксы)
- ✅ Группировка по времени создания (созданы одновременно)

**Пример использования:**
```python
from checkers.related_addresses import RelatedAddressFinder

finder = RelatedAddressFinder()
report = finder.analyze_results(results)

# Статистика
print(f"Найдено групп: {report['total_groups']}")
print(f"Всего адресов: {report['total_addresses']}")

# Экспорт
finder.export_to_txt(report, "related_addresses.txt")
finder.export_to_json(report, "related_addresses.json")
```

**Типы связей:**
1. **same_seed** - Одна seed фраза
2. **same_privkey** - Один приватный ключ
3. **same_email** - Один email
4. **same_password** - Одинаковый пароль
5. **same_prefix** - Похожие адреса (префикс)
6. **same_suffix** - Похожие адреса (суффикс)
7. **close_creation_time** - Созданы в одно время

---

### 2. 📧 Email Domain Grouper - Группировка по email доменам

**Модуль:** `checkers/email_grouper.py`

**Что это?**
Группировка аккаунтов по email доменам с детальной статистикой!

**Возможности:**
- ✅ Автоматическая группировка по доменам
- ✅ Классификация доменов (Popular, Temporary, Corporate, Educational)
- ✅ Статистика по каждому домену (количество, баланс, валидность)
- ✅ Топ-10 доменов по балансу
- ✅ Экспорт по конкретному домену

**Классификация доменов:**
- **Popular** - Gmail, Yahoo, Outlook, iCloud, Mail.ru, Yandex
- **Temporary** - Временные email сервисы
- **Corporate** - Корпоративные домены
- **Educational** - Образовательные (.edu)
- **Government** - Правительственные (.gov)
- **Custom** - Кастомные домены

**Пример использования:**
```python
from checkers.email_grouper import EmailDomainGrouper

grouper = EmailDomainGrouper()
report = grouper.analyze_results(results)

# Топ домены
for domain_info in report['top_domains'][:5]:
    print(f"{domain_info['domain']}: {domain_info['total_accounts']} аккаунтов")
    print(f"  Баланс: ${domain_info['total_balance_usd']:,.2f}")

# Экспорт конкретного домена
grouper.export_by_domain("gmail.com", "gmail_accounts.txt", "txt")
```

**Статистика:**
- Всего доменов
- Всего email
- Общий баланс по доменам
- Валидных аккаунтов
- С балансом

---

### 3. 🎯 Smart Filter - Умная фильтрация результатов

**Модуль:** `checkers/smart_filter.py`

**Что это?**
Мощная система фильтрации результатов с предустановками!

**Типы фильтров:**
1. **balance** - По балансу (от/до)
2. **network** - По сети (Ethereum, BSC, Polygon...)
3. **auth_type** - По типу авторизации (seed, privkey, email:pass)
4. **platform** - По платформе (Binance, MetaMask...)
5. **email_domain** - По email домену
6. **validity** - По валидности (только валидные/невалидные)
7. **date** - По дате
8. **custom** - Кастомный фильтр (любое поле)

**Предустановленные фильтры:**
- `high_balance` - Баланс > $1000
- `medium_balance` - Баланс $100-$1000
- `low_balance` - Баланс $1-$100
- `with_seed` - Только с seed фразой
- `with_privkey` - Только с приватным ключом
- `ethereum` - Только Ethereum
- `bsc` - Только BSC
- `popular_emails` - Gmail, Yahoo, Outlook
- `valid_only` - Только валидные
- `invalid_only` - Только невалидные

**Пример использования:**
```python
from checkers.smart_filter import SmartFilter

filter_engine = SmartFilter()

# Фильтр по балансу
filtered = filter_engine.filter_results(results, [
    {"type": "balance", "min": 100, "max": 1000},
    {"type": "validity", "valid_only": True}
])

# Использование предустановки
presets = filter_engine.get_filter_presets()
high_balance_filter = presets["high_balance"]
filtered = filter_engine.filter_results(results, high_balance_filter)

# Сохранение фильтра
filter_engine.save_filter("my_filter", [
    {"type": "balance", "min": 500},
    {"type": "network", "networks": ["ethereum", "bsc"]}
])

# Загрузка сохраненного фильтра
my_filter = filter_engine.load_filter("my_filter")
```

**Операторы для custom фильтра:**
- `equals` - Равно
- `not_equals` - Не равно
- `contains` - Содержит
- `not_contains` - Не содержит
- `starts_with` - Начинается с
- `ends_with` - Заканчивается на
- `greater_than` - Больше чем
- `less_than` - Меньше чем
- `regex` - Регулярное выражение

---

### 4. ✏️ Seed Phrase Corrector - Исправление опечаток в seed фразах

**Модуль:** `checkers/seed_corrector.py`

**Что это?**
Автоматическое исправление опечаток в seed фразах с использованием BIP39 словаря!

**Возможности:**
- ✅ Исправление опечаток в словах
- ✅ Поиск наиболее похожих слов из BIP39 словаря
- ✅ Валидация seed фраз (12/15/18/21/24 слова)
- ✅ Оценка уверенности исправления (0-100%)
- ✅ Пакетное исправление нескольких фраз

**Алгоритм:**
- Levenshtein distance (расстояние редактирования)
- Схожесть по длине
- Общий префикс
- Взвешенная оценка схожести

**Пример использования:**
```python
from checkers.seed_corrector import SeedPhraseCorrector

corrector = SeedPhraseCorrector()

# Исправление одной фразы
original = "abandn ability abl about abov absent absorb abstract"
corrected, corrections = corrector.correct_seed_phrase(original)

print(f"Оригинал: {original}")
print(f"Исправлено: {corrected}")

for corr in corrections:
    print(f"  {corr['position']}. '{corr['original']}' → '{corr['corrected']}' ({corr['confidence']:.0%})")

# Валидация
validation = corrector.validate_seed_phrase(seed_phrase)
if not validation['valid']:
    print(f"Ошибка: {validation['error']}")
    for suggestion in validation['suggestions']:
        print(f"  Позиция {suggestion['position']}: {suggestion['original']} → {suggestion['suggestion']}")

# Пакетное исправление
seed_phrases = [
    "abandn ability abl...",
    "word1 word2 word3...",
]
results = corrector.batch_correct(seed_phrases)
```

**Поддерживаемые длины:**
- 12 слов (128 бит)
- 15 слов (160 бит)
- 18 слов (192 бит)
- 21 слово (224 бит)
- 24 слова (256 бит)

---

### 5. 🌍 Multi-Language Support - Поддержка множества языков

**Модуль:** `checkers/multilang_support.py`

**Что это?**
Полная поддержка 6 языков интерфейса!

**Поддерживаемые языки:**
- 🇬🇧 **English** (en)
- 🇷🇺 **Русский** (ru)
- 🇨🇳 **中文** (zh)
- 🇪🇸 **Español** (es)
- 🇫🇷 **Français** (fr)
- 🇩🇪 **Deutsch** (de)

**Возможности:**
- ✅ Автоопределение языка системы
- ✅ Переключение языка на лету
- ✅ Форматирование чисел по локали
- ✅ Форматирование валюты
- ✅ Перевод словарей

**Пример использования:**
```python
from checkers.multilang_support import MultiLanguageSupport, t, set_language

# Установка языка
set_language("ru")

# Получение перевода
print(t("start"))  # "Старт"
print(t("balance"))  # "Баланс"

# Форматирование чисел
ml = MultiLanguageSupport("ru")
print(ml.format_number(1234.56))  # "1 234,56"
print(ml.format_currency(1234.56))  # "1 234,56 $"

# Автоопределение языка
detected_lang = ml.detect_system_language()
ml.set_language(detected_lang)
```

**Переведенные элементы:**
- Кнопки интерфейса
- Названия полей
- Сообщения об ошибках
- Статистика
- Фильтры
- Экспорт

---

## 📊 СТАТИСТИКА РЕЛИЗА

- **Новых модулей:** 5
- **Новых строк кода:** ~2,500
- **Новых функций:** 50+
- **Поддерживаемых языков:** 6
- **Типов фильтров:** 8
- **Типов связей адресов:** 7

---

## 🎯 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Пример 1: Найти все адреса одного владельца

```python
from checkers.related_addresses import RelatedAddressFinder

finder = RelatedAddressFinder()
report = finder.analyze_results(results)

# Показать группы
for group in report['groups']:
    print(f"\nГруппа: {group['reason_text']}")
    print(f"Адресов: {group['count']}")
    print(f"Баланс: ${group['total_balance_usd']:,.2f}")
    for addr in group['addresses']:
        print(f"  - {addr}")
```

### Пример 2: Найти все аккаунты Gmail с балансом > $100

```python
from checkers.email_grouper import EmailDomainGrouper
from checkers.smart_filter import SmartFilter

# Группируем по доменам
grouper = EmailDomainGrouper()
report = grouper.analyze_results(results)

# Фильтруем Gmail аккаунты
filter_engine = SmartFilter()
gmail_accounts = filter_engine.filter_results(results, [
    {"type": "email_domain", "domains": ["gmail.com"]},
    {"type": "balance", "min": 100},
    {"type": "validity", "valid_only": True}
])

print(f"Найдено Gmail аккаунтов с балансом > $100: {len(gmail_accounts)}")
```

### Пример 3: Исправить опечатки и проверить

```python
from checkers.seed_corrector import SeedPhraseCorrector

corrector = SeedPhraseCorrector()

# Seed с опечатками
seed_with_typos = "abandn ability abl about abov absent absorb abstract absurd abuse access accident"

# Исправляем
corrected, corrections = corrector.correct_seed_phrase(seed_with_typos)

# Валидируем
validation = corrector.validate_seed_phrase(corrected)

if validation['valid']:
    print("✅ Seed фраза валидна!")
    print(f"Исправлено: {corrected}")
else:
    print("❌ Seed фраза невалидна")
```

---

## 🔄 ОБРАТНАЯ СОВМЕСТИМОСТЬ

- ✅ Все старые функции работают
- ✅ Новые модули не влияют на существующий код
- ✅ Можно использовать независимо
- ✅ Нет breaking changes

---

## 💡 СОВЕТЫ ПО ИСПОЛЬЗОВАНИЮ

1. **Related Addresses** - используйте для поиска всех кошельков одного владельца
2. **Email Grouper** - анализируйте какие домены самые прибыльные
3. **Smart Filter** - создавайте свои фильтры и сохраняйте их
4. **Seed Corrector** - проверяйте seed фразы перед использованием
5. **Multi-Language** - переключайте язык для удобства

---

## ⚠️ ВАЖНО

1. **Seed Corrector** - всегда проверяйте исправленные фразы вручную!
2. **Related Addresses** - связь по паролю не гарантирует одного владельца
3. **Smart Filter** - сохраняйте часто используемые фильтры
4. **Email Grouper** - временные email могут быть недоступны

---

## ✅ ТЕСТИРОВАНИЕ

Протестировано на:
- ✅ Windows 10/11
- ✅ Python 3.8+
- ✅ Различные типы данных
- ✅ Большие объемы результатов (10,000+)
- ✅ Все языки интерфейса

---

## 🚀 ЧТО ДАЛЬШЕ?

В следующих версиях:
- 🤖 Автоматическая проверка по расписанию
- 📊 Интерактивные графики и дашборды
- 💾 Хранение в базе данных
- 🔐 Продвинутое шифрование
- 🧠 AI предсказания

---

**Спасибо за использование MultiChecker Pro! 🚀**

*v1.0.64 - умный анализ и продвинутая фильтрация!*
