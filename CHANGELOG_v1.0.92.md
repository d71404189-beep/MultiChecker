# 📋 CHANGELOG v1.0.92 — Новые сети, Telegram 2.0, багфиксы

## 🎯 Основные изменения

### 🌐 8 новых блокчейнов в мультичейн-проверке

Теперь EVM мультичейн проверяет **18 сетей** (было 10):

| Сеть | Токен | RPC |
|------|-------|-----|
| Cronos | CRO | evm.cronos.org |
| Scroll | ETH | rpc.scroll.io |
| Blast | ETH | rpc.blast.io |
| Mantle | MNT | rpc.mantle.xyz |
| Gnosis | xDAI | rpc.gnosischain.com |
| Celo | CELO | forno.celo.org |
| Moonbeam | GLMR | rpc.api.moonbeam.network |
| opBNB | BNB | opbnb-mainnet-rpc.bnbchain.org |

- Все новые сети включены в автоматическую мультичейн-проверку ETH адресов
  (`crypto_checker.py` → `check_evm_all_chains`)
- Цены новых токенов (CRO, MNT, xDAI, CELO, GLMR) добавлены в CoinGecko
  маппинги `price_service.py` и `_get_prices()`

### 📱 Telegram уведомления 2.0

**1. Неблокирующая отправка**
- Раньше: `urllib.urlopen` вызывался прямо в event loop → при медленном
  Telegram API вся проверка подвисала на каждом уведомлении
- Теперь: отправка в фоновом daemon-потоке, скан не тормозит

**2. Ретраи с учётом rate limit**
- До 3 попыток отправки
- При 429 читается `retry_after` из ответа Telegram (cap 30 сек)
- При сетевых ошибках — возрастающая задержка 1.5s → 3s

**3. Итоговое уведомление после скана**
```
✅ Проверка завершена — Crypto
Проверено: 1500 | Найдено: 12
💰 Сумма: ~$4,210.55
⏱ Время: 03:42
```
- Новый i18n ключ `tg_summary` (RU/EN)

**4. HTML-экранирование**
- Спецсимволы (`<`, `>`, `&`) в проверяемых данных больше не ломают
  `parse_mode=HTML` — раньше такие уведомления молча не доставлялись

## 🐛 Багфиксы

### 1. Fantom: USD всегда был $0
`_get_prices()` не запрашивал цену FTM у CoinGecko, хотя Fantom есть в
`EVM_NETWORKS` → баланс находился, но оценивался в $0 и не попадал в
Telegram-уведомления. Добавлены fantom + все новые сети в запрос цен.

### 2. Fantom: мёртвый RPC
`rpc.ftm.tools` отдаёт `401 API key disabled` → проверка Fantom вообще не
работала. Заменён на `rpcapi.fantom.network` во всех модулях
(`evm_multichain`, `crypto_checker`, `crosschain_checker`, `multichain_checker`).

### 3. new_chains.py: захардкоженные цены
- Было: `ETH = $2500`, `SUI = $1.5`, `APT = $8.0` (захардкожено)
- Стало: живые цены через `PriceService` (CoinGecko, кэш 5 мин) с fallback
  на старые значения при недоступности API

## ⚡ Производительность

- Telegram-уведомления больше не блокируют event loop (см. выше) — на сканах
  с десятками находок это экономит до нескольких секунд на каждое уведомление
- Тайминг скана: время выполнения записывается и показывается в итоговом
  уведомлении

## 📁 Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `main.py` | TG: фоновая отправка + ретраи + summary + HTML-escape; тайминг; v1.0.92 |
| `i18n.py` | Ключ `tg_summary` (RU/EN) |
| `checkers/evm_multichain.py` | +8 сетей, фикс Fantom RPC |
| `checkers/crypto_checker.py` | Цены новых сетей (фикс FTM=$0), новые сети в мультичейн, фикс Fantom RPC |
| `checkers/price_service.py` | MNT/GLMR/XDAI/CELO маппинги, chain_to_symbol для новых сетей |
| `checkers/new_chains.py` | Живые цены вместо хардкода |
| `checkers/crosschain_checker.py` | Фикс Fantom RPC |
| `checkers/multichain_checker.py` | Фикс Fantom RPC |

## ✅ Тестирование

- Компиляция всех модулей: OK
- Конфиг 18 сетей (уникальность ID, полнота полей, маппинги цен): OK
- Живой запрос балансов по всем 18 RPC: 18/18 отвечают
- CoinGecko цены для всех новых токенов: OK
- Парсинг ненулевого баланса (Gnosis): OK
- Формат `tg_summary` RU/EN: OK
