# 📋 Changelog v1.0.55

## 🆕 Новые функции

### 💱 Проверка API ключей CEX (криптобирж)
Проверка балансов на биржах через API ключи:

**Поддерживаемые биржи:**
1. **Binance** - крупнейшая биржа
2. **Bybit** - популярная для фьючерсов
3. **OKX** - топ-3 биржа
4. **KuCoin** - широкий выбор альткоинов
5. **Huobi** (в разработке)
6. **Gate.io** (в разработке)
7. **MEXC** (в разработке)
8. **Bitget** (в разработке)

**Что проверяется:**
- ✅ **Spot балансы** - основной счет
- ✅ **Futures балансы** - фьючерсы
- ✅ **Margin балансы** - маржинальная торговля
- ✅ **Total USD** - общая стоимость
- ✅ **Permissions** - права API ключа
- ✅ **Account type** - тип аккаунта

**Пример вывода:**
```
Binance: ✅ $15,000 | Spot: BTC 0.5, USDT 1000 | Futures: USDT 500 | Permissions: SPOT, FUTURES
Bybit: ✅ $5,000 | Spot: ETH 2.5, USDT 2000
OKX: ✅ $3,000 | Spot: BTC 0.1, USDT 1500
```

**Безопасность:**
- Только READ права (не нужны TRADE/WITHDRAW)
- API ключи не сохраняются
- Все запросы через HTTPS
- Подпись HMAC-SHA256

**Как использовать:**
```python
from checkers.cex_checker import CEXChecker

# Проверить один API ключ
result = await CEXChecker.check_api_key(
    exchange="binance",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Проверить несколько бирж параллельно
results = await CEXChecker.check_multiple_exchanges([
    {"exchange": "binance", "api_key": "...", "api_secret": "..."},
    {"exchange": "bybit", "api_key": "...", "api_secret": "..."},
    {"exchange": "okx", "api_key": "...", "api_secret": "...", "passphrase": "..."}
])
```

### 📱 Мобильные кошельки
Проверка backup файлов мобильных кошельков:

**Поддерживаемые кошельки:**
1. **Trust Wallet** - самый популярный мобильный кошелек
2. **MetaMask Mobile** - мобильная версия MetaMask
3. **Coinbase Wallet** - кошелек от Coinbase

**Trust Wallet:**
- Формат: JSON backup
- Расположение Android: `/sdcard/TrustWallet/backup.json`
- Расположение iOS: `iCloud Drive/Trust/backup.json`
- Шифрование: AES-256-CBC с PBKDF2
- Поддержка: ✅ Расшифровка с паролем

**MetaMask Mobile:**
- Формат: JSON с зашифрованным vault
- Расположение Android: `/data/data/io.metamask/files/persist-root`
- Расположение iOS: `Library/Application Support/`
- Шифрование: eth-sig-util encryption
- Поддержка: ✅ Расшифровка с паролем

**Coinbase Wallet:**
- Формат: Device-encrypted JSON
- Расположение: iCloud / Google Drive
- Шифрование: Device-specific key
- Поддержка: ⚠️ Только на оригинальном устройстве

**Что извлекается:**
- 🔑 **Mnemonic** (сид-фраза)
- 📍 **Addresses** (адреса всех аккаунтов)
- 🔢 **Account count** (количество аккаунтов)
- 🪙 **Supported coins** (поддерживаемые монеты)

**Пример вывода:**
```
Trust Wallet: ✅ 12 words | 5 accounts | ETH: 0x1234..., BTC: bc1...
MetaMask Mobile: ✅ 12 words | 3 accounts | ETH: 0xabcd...
Coinbase Wallet: ❌ Device-encrypted (can only decrypt on original device)
```

**Как использовать:**
```python
from checkers.mobile_wallet_checker import MobileWalletChecker

# Автоопределение типа кошелька
result = MobileWalletChecker.check_backup(
    backup_data="path/to/backup.json",
    password="your_password"
)

# Или указать тип явно
result = MobileWalletChecker.check_backup(
    backup_data="path/to/backup.json",
    wallet_type="trust",
    password="your_password"
)
```

### 🔐 Экспорт ключей в разные форматы
Экспорт приватных ключей в различные форматы:

**Поддерживаемые форматы:**

#### 1. HEX формат
Простой HEX формат (0x...):
```
0x1234567890abcdef...
```

#### 2. WIF (Wallet Import Format)
Bitcoin формат для импорта в кошельки:
```
5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ  (Uncompressed)
KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn  (Compressed)
```

**Типы:**
- Compressed WIF (начинается с K/L)
- Uncompressed WIF (начинается с 5)
- Testnet WIF (начинается с 9/c)

#### 3. Keystore JSON (Ethereum)
Зашифрованный JSON для Ethereum кошельков:
```json
{
  "version": 3,
  "id": "...",
  "address": "...",
  "crypto": {
    "ciphertext": "...",
    "cipher": "aes-128-ctr",
    "kdf": "scrypt",
    "kdfparams": {...},
    "mac": "..."
  }
}
```

**KDF алгоритмы:**
- `scrypt` - более безопасный (по умолчанию)
- `pbkdf2` - быстрее

**Совместимость:**
- MetaMask
- MyEtherWallet (MEW)
- MyCrypto
- Geth
- Parity

#### 4. Encrypted (AES-256)
Зашифрованный формат для безопасного хранения:
```json
{
  "version": "1.0",
  "encryption": "AES-256-GCM",
  "kdf": "PBKDF2",
  "kdf_params": {
    "iterations": 100000,
    "salt": "..."
  },
  "cipher_params": {
    "nonce": "...",
    "tag": "..."
  },
  "ciphertext": "...",
  "created_at": "2024-01-01T00:00:00"
}
```

**Особенности:**
- AES-256-GCM шифрование
- PBKDF2 с 100,000 итераций
- Authenticated encryption (защита от подделки)
- Метаданные (адрес, баланс, дата)

**Как использовать:**
```python
from checkers.key_export import KeyExporter

# Экспорт в HEX
hex_key = KeyExporter.export_key(
    private_key="0x1234...",
    format="hex"
)

# Экспорт в WIF (Bitcoin)
wif_key = KeyExporter.export_key(
    private_key="0x1234...",
    format="wif",
    compressed=True,
    testnet=False
)

# Экспорт в Keystore (Ethereum)
keystore = KeyExporter.export_key(
    private_key="0x1234...",
    format="keystore",
    password="strong_password",
    kdf="scrypt"
)

# Экспорт в зашифрованный формат
encrypted = KeyExporter.export_key(
    private_key="0x1234...",
    format="encrypted",
    password="strong_password",
    address="0xabcd...",
    chain="ethereum",
    balance=1.5,
    balance_usd=3000
)

# Экспорт нескольких ключей
keys = [
    {"value": "0x1234...", "address": "0xabcd...", "balance": 1.5},
    {"value": "0x5678...", "address": "0xefgh...", "balance": 0.5}
]

KeyExporter.export_multiple_keys(
    keys=keys,
    format="encrypted",
    password="strong_password",
    output_file="keys_backup.json"
)
```

### 🔄 Импорт ключей
Импорт из различных форматов обратно в HEX:

```python
# Импорт из WIF
private_key = KeyExporter.import_key(
    data="5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ",
    format="wif"
)

# Импорт из Keystore
private_key = KeyExporter.import_key(
    data=keystore_json,
    format="keystore",
    password="password"
)

# Импорт из зашифрованного
private_key = KeyExporter.import_key(
    data=encrypted_json,
    format="encrypted",
    password="password"
)
```

## 🔧 Технические улучшения

### Новые модули

#### 1. cex_checker.py (650+ строк)
Модуль для проверки API ключей бирж:

**Классы:**
- `BinanceChecker` - Binance API
- `BybitChecker` - Bybit API
- `OKXChecker` - OKX API (требует passphrase)
- `KuCoinChecker` - KuCoin API (требует passphrase)
- `CEXChecker` - Универсальный чекер

**Функции:**
- `check_api_key()` - проверка одного ключа
- `check_multiple_exchanges()` - параллельная проверка
- `format_result()` - форматирование вывода
- `_check_futures_balance()` - проверка фьючерсов
- `_calculate_total_usd()` - расчет USD

**API интеграция:**
- Binance REST API v3
- Bybit API v5
- OKX API v5
- KuCoin API v1

#### 2. mobile_wallet_checker.py (450+ строк)
Модуль для проверки мобильных кошельков:

**Классы:**
- `TrustWalletChecker` - Trust Wallet backup
- `MetaMaskMobileChecker` - MetaMask Mobile backup
- `CoinbaseWalletChecker` - Coinbase Wallet backup
- `MobileWalletChecker` - Универсальный чекер
- `BackupFormats` - Информация о форматах

**Функции:**
- `check_backup()` - проверка backup файла
- `detect_wallet_type()` - автоопределение типа
- `format_result()` - форматирование вывода
- `_decrypt_wallet()` - расшифровка Trust Wallet
- `_decrypt_vault()` - расшифровка MetaMask

**Шифрование:**
- AES-256-CBC (Trust Wallet)
- AES-GCM (MetaMask)
- PBKDF2 key derivation
- Device-specific encryption (Coinbase)

#### 3. key_export.py (550+ строк)
Модуль для экспорта/импорта ключей:

**Классы:**
- `WIFExporter` - WIF формат (Bitcoin)
- `KeystoreExporter` - Keystore JSON (Ethereum)
- `EncryptedExporter` - Зашифрованный формат
- `KeyExporter` - Универсальный экспортер

**Функции:**
- `export_key()` - экспорт одного ключа
- `export_multiple_keys()` - экспорт нескольких
- `import_key()` - импорт ключа
- `private_key_to_wif()` - конвертация в WIF
- `wif_to_private_key()` - конвертация из WIF
- `create_keystore()` - создание Keystore
- `decrypt_keystore()` - расшифровка Keystore
- `encrypt_keys()` - шифрование ключей
- `decrypt_keys()` - расшифровка ключей

**Криптография:**
- Base58 encoding/decoding
- HMAC-SHA256 подпись
- AES-128-CTR (Keystore)
- AES-256-GCM (Encrypted)
- Scrypt KDF
- PBKDF2 KDF

### Зависимости

Добавлены новые зависимости:
```
pycryptodome>=3.18.0  # Для шифрования
```

## 📊 Производительность

### CEX проверка
- **Одна биржа**: ~1-2 сек
- **Несколько бирж параллельно**: ~2-3 сек (независимо от количества)
- **Ускорение**: N раз (где N - количество бирж)

### Mobile wallet расшифровка
- **Trust Wallet**: ~0.5-1 сек (PBKDF2 10,000 итераций)
- **MetaMask**: ~0.5-1 сек (PBKDF2 10,000 итераций)
- **Зависит от**: Количество итераций KDF

### Key export
- **HEX**: мгновенно
- **WIF**: <0.1 сек (Base58 encoding)
- **Keystore (scrypt)**: ~2-3 сек (262,144 итераций)
- **Keystore (pbkdf2)**: ~1-2 сек (262,144 итераций)
- **Encrypted**: ~0.5-1 сек (100,000 итераций)

## 🎯 Примеры использования

### Пример 1: Проверка Binance API
```python
result = await CEXChecker.check_api_key(
    exchange="binance",
    api_key="your_api_key",
    api_secret="your_api_secret"
)

if result["valid"]:
    print(f"Total: ${result['total_usd']:,.2f}")
    print(f"Spot: {result['spot_balance']}")
    print(f"Futures: {result['futures_balance']}")
else:
    print(f"Error: {result['error']}")
```

### Пример 2: Trust Wallet backup
```python
result = MobileWalletChecker.check_backup(
    backup_data="trust_backup.json",
    password="your_password"
)

if result["valid"]:
    print(f"Mnemonic: {result['mnemonic']}")
    print(f"Accounts: {result['accounts']}")
    print(f"Addresses: {result['addresses']}")
```

### Пример 3: Экспорт в Keystore
```python
keystore = KeyExporter.export_key(
    private_key="0x1234567890abcdef...",
    format="keystore",
    password="strong_password",
    kdf="scrypt"
)

# Сохраняем в файл
with open("keystore.json", "w") as f:
    json.dump(keystore, f, indent=2)

# Импортируем обратно
private_key = KeyExporter.import_key(
    data=keystore,
    format="keystore",
    password="strong_password"
)
```

### Пример 4: Batch экспорт найденных ключей
```python
# Найденные ключи с балансами
found_keys = [
    {
        "value": "0x1234...",
        "address": "0xabcd...",
        "chain": "ethereum",
        "balance": 1.5,
        "balance_usd": 3000
    },
    {
        "value": "0x5678...",
        "address": "0xefgh...",
        "chain": "bsc",
        "balance": 10.0,
        "balance_usd": 2000
    }
]

# Экспортируем все в зашифрованный файл
KeyExporter.export_multiple_keys(
    keys=found_keys,
    format="encrypted",
    password="super_strong_password",
    output_file="found_keys_backup.json"
)

print("✅ Все ключи зашифрованы и сохранены!")
```

## 🐛 Исправления

- Улучшена обработка ошибок для CEX API
- Исправлена работа с OKX passphrase
- Добавлен fallback для недоступных API
- Улучшена валидация WIF формата
- Исправлена работа с Keystore MAC

## 💡 Советы

### Для CEX API ключей

1. **Создавайте READ-ONLY ключи:**
   - Не давайте права TRADE/WITHDRAW
   - Только READ права достаточно
   - Безопаснее для проверки

2. **IP whitelist:**
   - Добавьте свой IP в whitelist
   - Дополнительная защита
   - Предотвращает кражу ключей

3. **Регулярно обновляйте:**
   - Меняйте API ключи раз в месяц
   - Удаляйте неиспользуемые ключи
   - Мониторьте активность

### Для мобильных кошельков

1. **Backup файлы:**
   - Храните в безопасном месте
   - Используйте сильные пароли
   - Не храните в облаке без шифрования

2. **Trust Wallet:**
   - Backup автоматически в iCloud/Google Drive
   - Можно экспортировать вручную
   - Проверяйте регулярно

3. **MetaMask Mobile:**
   - Backup только вручную
   - Храните отдельно от устройства
   - Тестируйте восстановление

### Для экспорта ключей

1. **Используйте сильные пароли:**
   - Минимум 16 символов
   - Буквы, цифры, символы
   - Уникальный для каждого файла

2. **Keystore vs Encrypted:**
   - Keystore - для Ethereum кошельков
   - Encrypted - для универсального хранения
   - Encrypted быстрее (меньше итераций)

3. **Безопасное хранение:**
   - Не храните на том же устройстве
   - Используйте USB флешки
   - Делайте несколько копий
   - Храните в разных местах

## 🔐 Безопасность

### CEX API
- Только READ права
- HTTPS для всех запросов
- HMAC-SHA256 подпись
- Не сохраняем ключи

### Mobile Wallets
- Расшифровка только с паролем
- Не сохраняем пароли
- Безопасное удаление из памяти

### Key Export
- AES-256 шифрование
- Scrypt/PBKDF2 KDF
- Authenticated encryption (GCM)
- Защита от brute-force (100,000+ итераций)

## 📝 Известные ограничения

1. **CEX API:**
   - Huobi, Gate.io, MEXC, Bitget - в разработке
   - Rate limits бирж (обычно 1200 req/min)
   - Некоторые биржи требуют IP whitelist

2. **Mobile Wallets:**
   - Coinbase Wallet - только на оригинальном устройстве
   - MetaMask расшифровка упрощенная (может не работать для всех версий)
   - Требуется правильный пароль

3. **Key Export:**
   - WIF только для Bitcoin-like монет
   - Keystore только для Ethereum
   - Scrypt медленный (2-3 сек)

## 🚀 Что дальше?

### Планы на v1.0.56
- Умный анализ кошельков (whale/trader/holder)
- Мониторинг и алерты (Telegram, Discord, Email)
- История транзакций и PnL анализ
- Автоматический вывод при поступлении
- Dashboard с live обновлениями

---

**Версия**: 1.0.55  
**Дата**: 2024  
**Автор**: Bes Bits

## Благодарности

Спасибо за использование MultiChecker! Теперь с поддержкой CEX API и мобильных кошельков! 🚀

**Новые возможности v1.0.55:**
- ✅ Проверка 4+ бирж (Binance, Bybit, OKX, KuCoin)
- ✅ Мобильные кошельки (Trust Wallet, MetaMask Mobile)
- ✅ 4 формата экспорта (HEX, WIF, Keystore, Encrypted)
- ✅ Безопасное шифрование (AES-256)
- ✅ Импорт/экспорт ключей

**Итого: Полный контроль над вашими крипто-активами!** 💰
