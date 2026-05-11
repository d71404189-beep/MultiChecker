import asyncio
import aiohttp
import re

from checkers.base_checker import BaseChecker

# Pre-compiled wallet patterns for fast matching
_WALLET_PATTERNS = [
    ("bitcoin", re.compile(r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$')),
    ("ethereum", re.compile(r'^0x[a-fA-F0-9]{40}$')),
    ("tron", re.compile(r'^T[a-zA-HJ-NP-Z0-9]{33}$')),
    ("solana", re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')),
    ("litecoin", re.compile(r'^(L|M|ltc1)[a-km-zA-HJ-NP-Z1-9]{26,62}$')),
    ("dash", re.compile(r'^X[1-9A-HJ-NP-Za-km-z]{24,33}$')),
    ("monero", re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$')),
    ("ripple", re.compile(r'^r[1-9A-HJ-NP-Za-km-z]{24,34}$')),
    ("dogecoin", re.compile(r'^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$')),
    ("bnb", re.compile(r'^bnb1[a-z0-9]{38}$')),
]

# Quick first-char lookup for fast rejection
_WALLET_FIRST_CHARS = frozenset('bB013456789LMlTXrDd')


class CryptoChecker(BaseChecker):
    def __init__(self):
        self.wallet_patterns = _WALLET_PATTERNS
        self.exchanges = ["binance", "bybit", "okx", "huobi", "kucoin", "gate", "mexc", "bitget"]

        self.auth_info = {
            "bitcoin": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Electrum, Exodus, Trust Wallet, Ledger",
                "how": "Импортируй приватный ключ или seed-фразу в кошелёк (Electrum / Exodus / Trust Wallet)",
            },
            "ethereum": {
                "auth_type": "Приватный ключ / Seed-фраза / Keystore",
                "wallets": "MetaMask, Trust Wallet, Rabby, Ledger",
                "how": "Импортируй приватный ключ в MetaMask (Настройки → Импорт аккаунта)",
            },
            "solana": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Phantom, Solflare, Backpack",
                "how": "Установи Phantom (phantom.app), выбери 'Импортировать приватный ключ' и вставь ключ",
            },
            "tron": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "TronLink, Trust Wallet, Ledger",
                "how": "Установи TronLink, выбери 'Импорт кошелька' и вставь приватный ключ",
            },
            "litecoin": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Electrum-LTC, Exodus, Trust Wallet",
                "how": "Импортируй приватный ключ в Electrum-LTC или Exodus",
            },
            "dash": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Dash Core, Exodus, Trust Wallet",
                "how": "Импортируй приватный ключ в Dash Core (Консоль: importprivkey <ключ>)",
            },
            "monero": {
                "auth_type": "Seed-фраза (25 слов) / Приватные ключи (spend + view)",
                "wallets": "Monero GUI, Cake Wallet, Feather Wallet",
                "how": "В Monero GUI выбери 'Восстановить кошелёк из seed' и введи 25 слов",
            },
            "ripple": {
                "auth_type": "Приватный ключ / Seed-фраза / Family Seed",
                "wallets": "XUMM (Xaman), Trust Wallet, Ledger",
                "how": "Установи XUMM, выбери 'Импорт' и введи Family Seed или мнемоническую фразу",
            },
            "dogecoin": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Dogecoin Core, Exodus, Trust Wallet",
                "how": "Импортируй приватный ключ в Exodus или Dogecoin Core",
            },
            "bnb": {
                "auth_type": "Приватный ключ / Seed-фраза",
                "wallets": "Trust Wallet, MetaMask (BSC), Binance Chain Wallet",
                "how": "Импортируй seed-фразу в Trust Wallet или добавь BSC сеть в MetaMask",
            },
        }

    async def check(self, data: str, timeout: int = 10, proxy: str = None, session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, type="unknown")

        wallet_type = self._detect_wallet(data)
        if wallet_type:
            result["type"] = "wallet"
            result["wallet_type"] = wallet_type

            own_session = session is None
            if own_session:
                session = aiohttp.ClientSession()

            try:
                handler = {
                    "bitcoin": self._check_bitcoin,
                    "ethereum": self._check_ethereum,
                    "solana": self._check_solana,
                    "tron": self._check_tron,
                    "litecoin": self._check_litecoin,
                    "dash": self._check_dash,
                    "monero": self._check_monero,
                    "ripple": self._check_ripple,
                    "dogecoin": self._check_dogecoin,
                    "bnb": self._check_bnb,
                }.get(wallet_type)

                if handler:
                    result = await handler(data, timeout, proxy, session)
                    if result.get("exists") and wallet_type in self.auth_info:
                        result["info"]["auth"] = self.auth_info[wallet_type]
                else:
                    result["info"]["error"] = f"No checker for {wallet_type}"
            finally:
                if own_session:
                    await session.close()
        else:
            exchange = self._detect_exchange(data)
            if exchange:
                result["type"] = "exchange"
                result["exchange"] = exchange
                result["info"]["message"] = f"Detected exchange: {exchange}"
            else:
                result["info"]["error"] = "Unknown crypto format"

        return result

    def _detect_wallet(self, data: str) -> str:
        data = data.strip()
        if not data or data[0] not in _WALLET_FIRST_CHARS:
            return None
        for wallet_type, pattern in self.wallet_patterns:
            if pattern.match(data):
                return wallet_type
        return None

    def _detect_exchange(self, data: str) -> str:
        data = data.lower()
        for exchange in self.exchanges:
            if exchange in data:
                return exchange
        return None

    async def _check_bitcoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bitcoin", valid=True)
        try:
            url = f"https://blockchain.info/q/addressbalance/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                balance = await resp.text()
                resp.close()
                satoshi = int(balance)
                result["info"]["balance_btc"] = satoshi / 100_000_000
                result["exists"] = True
                result["info"]["message"] = f"Balance: {result['info']['balance_btc']:.8f} BTC"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_ethereum(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ethereum", valid=True)
        try:
            url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                if data.get("status") == "1":
                    balance_wei = int(data["result"])
                    result["info"]["balance_eth"] = balance_wei / 10**18
                    result["exists"] = True
                    result["info"]["message"] = f"Balance: {result['info']['balance_eth']:.6f} ETH"
                else:
                    result["info"]["message"] = data.get("message", "Unknown error")
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_solana(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="solana", valid=True)
        try:
            url = "https://api.mainnet-beta.solana.com"
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json=payload, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                if "result" in data:
                    lamports = data["result"]["value"]
                    result["info"]["balance_sol"] = lamports / 10**9
                    result["exists"] = True
                    result["info"]["message"] = f"Balance: {result['info']['balance_sol']:.4f} SOL"
                elif "error" in data:
                    result["info"]["message"] = data["error"].get("message", "RPC error")
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_tron(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="tron", valid=True)
        try:
            url = f"https://apilist.tronscanapi.com/api/accountv2?address={address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                if data.get("totalTransactionCount", 0) > 0 or data.get("balance", 0) > 0:
                    balance = data.get("balance", 0) / 10**6
                    result["info"]["balance_trx"] = balance
                    result["exists"] = True
                    result["info"]["message"] = f"Balance: {balance:.2f} TRX"
                    result["info"]["tx_count"] = data.get("totalTransactionCount", 0)
                else:
                    result["info"]["message"] = "Wallet empty or not found"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_litecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="litecoin", valid=True)
        try:
            url = f"https://api.blockchair.com/litecoin/dashboards/address/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                addr_data = data.get("data", {}).get(address, {}).get("address", {})
                balance = addr_data.get("balance", 0) / 10**8
                result["info"]["balance_ltc"] = balance
                result["exists"] = True
                result["info"]["message"] = f"Balance: {balance:.8f} LTC"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_dash(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dash", valid=True)
        try:
            url = f"https://api.blockchair.com/dash/dashboards/address/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                addr_data = data.get("data", {}).get(address, {}).get("address", {})
                balance = addr_data.get("balance", 0) / 10**8
                result["info"]["balance_dash"] = balance
                result["exists"] = True
                result["info"]["message"] = f"Balance: {balance:.8f} DASH"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_monero(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="monero", valid=True)
        try:
            url = f"https://xmrchain.net/api/outputs?address={address}&viewkey=&page=0&limit=1"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status
            resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Monero address format valid, chain query succeeded"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_ripple(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ripple", valid=True)
        try:
            url = "https://s1.ripple.com:51234/"
            payload = {"method": "account_info", "params": [{"account": address, "strict": True}]}
            resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                    json=payload, headers={"Content-Type": "application/json"})
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                r = data.get("result", {})
                if r.get("status") == "success":
                    balance_drops = int(r.get("account_data", {}).get("Balance", 0))
                    result["info"]["balance_xrp"] = balance_drops / 10**6
                    result["exists"] = True
                    result["info"]["message"] = f"Balance: {result['info']['balance_xrp']:.2f} XRP"
                else:
                    result["info"]["message"] = r.get("error_message", "Account not found")
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_dogecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dogecoin", valid=True)
        try:
            url = f"https://api.blockchair.com/dogecoin/dashboards/address/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                addr_data = data.get("data", {}).get(address, {}).get("address", {})
                balance = addr_data.get("balance", 0) / 10**8
                result["info"]["balance_doge"] = balance
                result["exists"] = True
                result["info"]["message"] = f"Balance: {balance:.4f} DOGE"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_bnb(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bnb", valid=True)
        try:
            url = f"https://dex.binance.org/api/v1/account/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                balances = data.get("balances", [])
                bnb_bal = next((b for b in balances if b.get("symbol") == "BNB"), None)
                if bnb_bal:
                    result["info"]["balance_bnb"] = float(bnb_bal.get("free", 0))
                result["exists"] = True
                result["info"]["message"] = "BNB account found"
            elif resp.status == 404:
                resp.close()
                result["info"]["message"] = "Account not found"
            else:
                resp.close()
                result["info"]["message"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
