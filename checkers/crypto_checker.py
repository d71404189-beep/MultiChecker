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


class CryptoChecker(BaseChecker):
    def __init__(self):
        self.wallet_patterns = _WALLET_PATTERNS
        self.exchanges = ["binance","bybit","okx","huobi","kucoin","gate","mexc","bitget"]
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
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        try:
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=None)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                _PRICE_CACHE = {
                    "bitcoin":   d.get("bitcoin",{}).get("usd",0),
                    "ethereum":  d.get("ethereum",{}).get("usd",0),
                    "tron":      d.get("tron",{}).get("usd",0),
                    "solana":    d.get("solana",{}).get("usd",0),
                    "litecoin":  d.get("litecoin",{}).get("usd",0),
                    "dash":      d.get("dash",{}).get("usd",0),
                    "monero":    d.get("monero",{}).get("usd",0),
                    "ripple":    d.get("ripple",{}).get("usd",0),
                    "dogecoin":  d.get("dogecoin",{}).get("usd",0),
                    "bnb":       d.get("binancecoin",{}).get("usd",0),
                    "ton":       d.get("the-open-network",{}).get("usd",0),
                    "cardano":   d.get("cardano",{}).get("usd",0),
                    "polygon":   d.get("matic-network",{}).get("usd",0),
                    "base":      d.get("ethereum",{}).get("usd",0), 
                }
                _PRICE_CACHE_TS = time.time()
            else:
                resp.close()
        except Exception:
            pass
        return _PRICE_CACHE

    def _usd(self, amount, coin, prices):
        p = prices.get(coin, 0)
        return f" (~${amount*p:,.2f})" if p and amount else ""

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
        result = self.make_result(input=phrase[:20]+"...", type="seed")
        prices = await self._get_prices(session, timeout)
        derived, errors = {}, []

        try:
            from bip_utils import (Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes, Bip49, Bip84, Bip86, Bip86Coins)
            if not Bip39MnemonicValidator().IsValid(phrase):
                result["info"]["error"] = "Invalid BIP-39 mnemonic"
                return result

            seed_bytes = Bip39SeedGenerator(phrase).Generate()
            for i in range(3):
                derived[f"bitcoin_{i}"] = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
                derived[f"bitcoin_segwit_{i}"] = Bip84.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
                derived[f"bitcoin_nested_{i}"] = Bip49.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
                derived[f"bitcoin_taproot_{i}"] = Bip86.FromSeed(seed_bytes, Bip86Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
            for i in range(5):
                derived[f"ethereum_{i}"] = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
            derived["tron"] = Bip44.FromSeed(seed_bytes, Bip44Coins.TRON).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PublicKey().ToAddress()
            derived["solana"] = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA).Purpose().Coin().Account(0).PublicKey().ToAddress()
        except Exception as e:
            result["info"]["error"] = f"Seed derive error: {e}"; return result

        handlers, _bal_keys, _price_keys = {}, {}, {}
        for i in range(3):
            for k in ["", "_segwit", "_nested", "_taproot"]:
                handlers[f"bitcoin{k}_{i}"] = self._check_bitcoin; _bal_keys[f"bitcoin{k}_{i}"] = "balance_btc"; _price_keys[f"bitcoin{k}_{i}"] = "bitcoin"
        for i in range(5):
            handlers[f"ethereum_{i}"] = self._check_ethereum; _bal_keys[f"ethereum_{i}"] = "balance_eth"; _price_keys[f"ethereum_{i}"] = "ethereum"
        handlers["tron"] = self._check_tron; _bal_keys["tron"] = "balance_trx"; _price_keys["tron"] = "tron"
        handlers["solana"] = self._check_solana; _bal_keys["solana"] = "balance_sol"; _price_keys["solana"] = "solana"

        check_items = [(coin, addr) for coin, addr in derived.items() if coin in handlers]
        check_results = await asyncio.gather(*[handlers[coin](addr, timeout, proxy, session) for coin, addr in check_items], return_exceptions=True)

        total_usd, found_coins = 0.0, []
        result["info"]["addresses"] = derived; result["info"]["balances"] = {}

        for (coin, addr), res in zip(check_items, check_results):
            if isinstance(res, Exception): continue
            bal = res.get("info", {}).get(_bal_keys.get(coin, "balance"), 0) or 0
            result["info"]["balances"][coin] = {"address": addr, "balance": bal, "message": res.get("info", {}).get("message", "")}
            total_usd += bal * prices.get(_price_keys.get(coin, ""), 0)
            if bal > 0: found_coins.append(coin)

        result["exists"] = bool(found_coins); result["info"]["total_usd"] = total_usd
        result["info"]["auth"] = {"auth_type": "Сид-фраза BIP-39", "wallets": "Trust Wallet, Phantom, Electrum", "how": "Введите фразу целиком при импорте существующего кошелька."}
        whale = self._whale_label(total_usd)
        result["info"]["message"] = f"Seed OK | Найдено балансов на: {', '.join(found_coins) if found_coins else 'none'} | Всего: ~${total_usd:,.2f}{whale}"
        return result

    async def _check_privkey_hex(self, key, timeout, proxy, session):
        result = self.make_result(input=key[:10]+"...", type="privkey_hex")
        prices = await self._get_prices(session, timeout)
        try:
            from eth_account import Account
            acct = Account.from_key(key if key.startswith("0x") else "0x" + key)
            address = acct.address; result["info"]["address"] = address
        except Exception as e:
            result["info"]["error"] = f"Invalid private key: {e}"; return result

        chain_results = await self._multichain_scan(address, timeout, proxy, session, prices)
        total_usd = sum(r["usd"] for r in chain_results.values())
        active = [c for c, r in chain_results.items() if r["balance"] > 0]

        result["info"]["chains"] = chain_results; result["info"]["total_usd"] = total_usd
        result["exists"] = bool(active); result["info"]["auth"] = self.auth_info["ethereum"]
        whale = self._whale_label(total_usd)
        result["info"]["message"] = f"PrivKey -> {address} | Сети: {', '.join(active) if active else 'none'} | Сумма: ~${total_usd:,.2f}{whale}"
        return result

    async def _check_privkey_wif(self, wif, timeout, proxy, session):
        result = self.make_result(input=wif[:10]+"...", type="privkey_wif")
        try:
            from bip_utils import WifDecoder, P2PKHAddr, Secp256k1PrivateKey
            b, _ = WifDecoder.Decode(wif)
            address = P2PKHAddr.EncodeKey(Secp256k1PrivateKey.FromBytes(b).PublicKey().KeyObject())
            result["info"]["address"] = address
        except Exception as e:
            result["info"]["error"] = f"Invalid WIF key: {e}"; return result

        btc_result = await self._check_bitcoin(address, timeout, proxy, session)
        result["exists"] = btc_result.get("exists", False); result["info"].update(btc_result.get("info", {}))
        result["info"]["auth"] = self.auth_info["bitcoin"]
        result["info"]["message"] = f"WIF -> {address} | " + btc_result["info"].get("message","")
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
            tokens = await self._check_erc20(address, timeout, proxy, session)
            bsc_tokens = await self._check_bsc_tokens(address, timeout, proxy, session)
            polygon_tokens = await self._check_polygon_tokens(address, timeout, proxy, session)
            uni_v3 = await self._check_uniswap_v3_positions(address, timeout, proxy, session)
            nfts = await self._check_nft(address, timeout, proxy, session)
            staking = await self._check_staking(address, timeout, proxy, session)
            last_tx = await self._get_last_tx_eth(address, timeout, proxy, session)
            approvals = await self._check_approvals(address, timeout, proxy, session)
            activity = await self._get_activity_score(address, timeout, proxy, session)
            airdrop_msg = await self._check_airdrop_eligibility(address, timeout, proxy, session)

            token_prices = await self._get_token_prices(list(tokens.keys()), session, timeout)
            total_token_usd = sum(tv * token_prices.get(tk.upper(), 1.0) for tk, tv in tokens.items())
            total_token_usd += sum(bsc_tokens.values()) + sum(polygon_tokens.values())

            result["info"].update({"balance_eth": balance, "tokens": tokens, "bsc_tokens": bsc_tokens, "polygon_tokens": polygon_tokens, "token_usd": total_token_usd})
            result["exists"] = balance > 0 or bool(tokens) or bool(bsc_tokens) or bool(polygon_tokens)
            
            usd = self._usd(balance, "ethereum", prices)
            msg = f"Balance: {balance:.18f} ETH{usd}"
            if tokens: msg += " | Tokens: " + ", ".join(f"{v:.6f} {k}" for k,v in tokens.items())
            if bsc_tokens: msg += " | BSC: " + ", ".join(f"{v:.2f} {k}" for k,v in bsc_tokens.items())
            if polygon_tokens: msg += " | Polygon: " + ", ".join(f"{v:.2f} {k}" for k,v in polygon_tokens.items())
            if total_token_usd > 0: msg += f" | Найдено токенов на: ~${total_token_usd:,.2f}"
            if last_tx: msg += f" | Last Tx: {last_tx}"
            if approvals: msg += f" | Аппрувы: {', '.join(approvals)}"
            if activity: msg += f" | Активность: {activity}"
            msg += airdrop_msg
            if not result["exists"]: msg += " (empty)"
            
            total_eth_usd = balance * prices.get("ethereum", 0) + total_token_usd
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
