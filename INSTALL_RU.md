# 🚀 УСТАНОВКА И ЗАПУСК MultiChecker v1.0.47

## ✅ ПРОВЕРКА УСТАНОВКИ

Перед запуском убедитесь что все зависимости установлены:

```bash
python test_app.py
```

Если все тесты пройдены - можно запускать!

---

## 📦 УСТАНОВКА ЗАВИСИМОСТЕЙ

### Автоматическая установка:

```bash
pip install -r requirements.txt
```

### Ручная установка (если автоматическая не сработала):

```bash
pip install customtkinter==5.2.1
pip install aiohttp==3.9.1
pip install Pillow==10.1.0
pip install dnspython==2.4.2
pip install bip_utils==2.12.1
pip install eth_account==0.13.7
pip install mnemonic==0.21
pip install base58==2.1.1
pip install qrcode==7.4.2
pip install web3
```

---

## 🎯 ЗАПУСК ПРИЛОЖЕНИЯ

### GUI (графический интерфейс):

```bash
python main.py
```

### Тестирование:

```bash
python test_app.py
```

---

## 🔧 УСТРАНЕНИЕ ПРОБЛЕМ

### Проблема: "No module named 'web3'"

**Решение:**
```bash
pip install web3
```

### Проблема: "No module named 'pkg_resources'"

**Решение:**
```bash
pip install setuptools
```

### Проблема: "No module named 'customtkinter'"

**Решение:**
```bash
pip install customtkinter
```

### Проблема: "No module named 'bip_utils'"

**Решение:**
```bash
pip install bip_utils
```

---

## 📋 СИСТЕМНЫЕ ТРЕБОВАНИЯ

- **Python**: 3.8 или выше
- **ОС**: Windows 10/11, Linux, macOS
- **RAM**: минимум 2 GB
- **Интернет**: требуется для проверки балансов

---

## 🎨 ОСОБЕННОСТИ v1.0.47

### ✅ Реализовано:

1. **Проверка криптокошельков**
   - Bitcoin (все форматы: Legacy, SegWit, Native SegWit, Taproot)
   - Ethereum + все EVM сети (BSC, Polygon, Avalanche, Base, Arbitrum, Optimism)
   - Solana, Tron, TON, Cardano, Litecoin, Dash, Monero, Ripple, Dogecoin, BNB

2. **Проверка сид-фраз (12-24 слова)**
   - Валидация BIP-39 (английский и русский)
   - Расширенная деривация (первые 10 адресов для каждого пути)
   - Поддержка 8 монет: BTC, ETH, LTC, DOGE, DASH, BNB, SOL, TRX
   - Все форматы BTC адресов

3. **Проверка приватных ключей**
   - HEX формат (с/без 0x)
   - WIF формат (compressed/uncompressed)
   - Автоопределение формата
   - Конвертация между форматами
   - Проверка безопасности ключа

4. **Автовывод средств** 🔥
   - Автоматический вывод найденных средств
   - Поддержка всех EVM сетей
   - Настраиваемые минимальные суммы
   - Логирование всех транзакций
   - Экспорт лога в JSON

5. **Расширенная аналитика**
   - ERC-20/BEP-20/TRC-20 токены
   - NFT (OpenSea, Ordinals)
   - Staking (Lido, Rocket Pool)
   - DeFi позиции (Uniswap V3)
   - DEX аппрувы
   - Airdrop eligibility
   - Цены в USD с изменением за 24ч
   - Gas price tracker
   - Wallet age (возраст кошелька)
   - Activity score

6. **Проверка бирж**
   - Binance, Bybit, OKX, Huobi, KuCoin, Gate, MEXC, Bitget
   - Формат: url:login:pass или url|login|pass
   - API ключи

7. **Проверка Email/Social/Games/AI**
   - Email аккаунты
   - Социальные сети
   - Игровые аккаунты
   - AI сервисы

---

## 🔐 АВТОВЫВОД - ИНСТРУКЦИЯ

### Включение автовывода:

```python
from checkers.crypto_checker import CryptoChecker

checker = CryptoChecker()

# Настройка адресов для вывода
checker.enable_auto_withdraw(
    addresses={
        "ethereum": "0xВАШ_ETH_АДРЕС",
        "bsc": "0xВАШ_BSC_АДРЕС",
        "bitcoin": "bc1ВАШ_BTC_АДРЕС",
        "tron": "TВАШ_TRX_АДРЕС",
        "solana": "ВАШ_SOL_АДРЕС",
    },
    min_amounts={
        "ethereum": 0.01,  # Минимум 0.01 ETH для вывода
        "bsc": 0.01,       # Минимум 0.01 BNB
        "bitcoin": 0.001,  # Минимум 0.001 BTC
        "tron": 10,        # Минимум 10 TRX
        "solana": 0.1,     # Минимум 0.1 SOL
    }
)
```

**Подробная документация:** см. `AUTO_WITHDRAW_README.md`

---

## 📊 РЕКОМЕНДАЦИИ ПО ПОТОКАМ

- **Email/Social**: 50-100 потоков
- **Crypto адреса**: 30-50 потоков
- **Crypto сид-фразы**: **5-10 потоков** ⚠️ (каждая фраза проверяет 100+ адресов!)
- **Games**: 20-30 потоков
- **AI**: 10-20 потоков

---

## 📝 CHANGELOG v1.0.47

### Добавлено:
- ✅ Автовывод средств на EVM сетях
- ✅ Логирование всех транзакций
- ✅ Экспорт лога выводов
- ✅ Документация по автовыводу
- ✅ Настраиваемые минимальные суммы
- ✅ Автоматический расчет газа
- ✅ Безопасное подписание транзакций

### Исправлено:
- ✅ Проблемы с зависимостями
- ✅ Совместимость с web3 v7.x
- ✅ Кодировка в логах

---

## 👨‍💻 АВТОР

**Bes Bits**

---

## 📞 ПОДДЕРЖКА

Если возникли проблемы:

1. Запустите `python test_app.py` для диагностики
2. Проверьте версию Python: `python --version` (должна быть 3.8+)
3. Переустановите зависимости: `pip install -r requirements.txt --force-reinstall`
4. Проверьте логи в консоли

---

## ⚠️ ВАЖНО!

- **Автовывод** - мощная функция, используйте осторожно!
- Всегда проверяйте адреса **ДВАЖДЫ** перед включением
- Храните приватные ключи в **БЕЗОПАСНОСТИ**
- Рекомендуется тестировать на малых суммах

---

## 🎉 ГОТОВО!

Теперь вы можете запустить MultiChecker:

```bash
python main.py
```

**Удачи! 🚀**
