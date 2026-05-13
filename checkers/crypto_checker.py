import asyncio
import aiohttp
import re

from checkers.base_checker import BaseChecker

# ── Wallet patterns ────────────────────────────────────────────────────────────
_WALLET_PATTERNS = [
    ("bitcoin",  re.compile(r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$')),
    ("ethereum", re.compile(r'^0x[a-fA-F0-9]{40}$')),
    ("tron",     re.compile(r'^T[a-zA-HJ-NP-Z0-9]{33}$')),
    ("solana",   re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')),
    ("ton",      re.compile(r'^(EQ|UQ)[a-zA-Z0-9_-]{46}$')),
    ("cardano",  re.compile(r'^addr1[a-z0-9]{50,100}$')),
    ("litecoin", re.compile(r'^(L|M|ltc1)[a-km-zA-HJ-NP-Z1-9]{26,62}$')),
    ("dash",     re.compile(r'^X[1-9A-HJ-NP-Za-km-z]{24,33}$')),
    ("monero",   re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$')),
    ("ripple",   re.compile(r'^r[1-9A-HJ-NP-Za-km-z]{24,34}$')),
    ("dogecoin", re.compile(r'^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$')),
    ("bnb",      re.compile(r'^bnb1[a-z0-9]{38}$')),
    ("polygon",  re.compile(r'^0x[a-fA-F0-9]{40}$')),   # same as ETH, detected by context
    ("avalanche",re.compile(r'^0x[a-fA-F0-9]{40}$')),   # same as ETH
]

_WALLET_FIRST_CHARS = frozenset('bB013456789LMlTXrDdEUa')

# ── Coin prices cache (filled once per session) ────────────────────────────────
_PRICE_CACHE: dict = {}
_PRICE_CACHE_TS: float = 0.0
_PRICE_TTL = 300  # seconds

# ── ERC-20 token contracts (USDT / USDC on Ethereum) ──────────────────────────
_ERC20_TOKENS = {
    "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
}

# ── TRC-20 token contracts ─────────────────────────────────────────────────────
_TRC20_TOKENS = {
    "USDT": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
}


class CryptoChecker(BaseChecker):
    def __init__(self):
        self.wallet_patterns = _WALLET_PATTERNS
        self.exchanges = ["binance","bybit","okx","huobi","kucoin","gate","mexc","bitget"]
        self.auth_info = {
            "bitcoin":   {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Electrum, Exodus, Trust Wallet, Ledger",              "how": "Import private key or seed phrase into Electrum / Exodus / Trust Wallet"},
            "ethereum":  {"auth_type": "Private Key / Seed Phrase / Keystore",             "wallets": "MetaMask, Trust Wallet, Rabby, Ledger",               "how": "Import private key into MetaMask (Settings -> Import account)"},
            "polygon":   {"auth_type": "Private Key / Seed Phrase",                        "wallets": "MetaMask (Polygon network), Trust Wallet",            "how": "Add Polygon network in MetaMask and import private key"},
            "avalanche": {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Core Wallet, MetaMask (Avalanche C-Chain), Trust Wallet", "how": "Import private key into Core Wallet or MetaMask with Avalanche C-Chain"},
            "solana":    {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Phantom, Solflare, Backpack",                         "how": "Install Phantom (phantom.app), choose Import private key"},
            "ton":       {"auth_type": "Seed Phrase (24 words) / Private Key",             "wallets": "Tonkeeper, MyTonWallet, TonHub",                      "how": "Install Tonkeeper, choose Import wallet and enter 24-word seed phrase"},
            "cardano":   {"auth_type": "Seed Phrase (15/24 words)",                        "wallets": "Daedalus, Yoroi, Eternl",                             "how": "Install Yoroi or Eternl, choose Restore wallet and enter seed phrase"},
            "tron":      {"auth_type": "Private Key / Seed Phrase",                        "wallets": "TronLink, Trust Wallet, Ledger",                      "how": "Install TronLink, choose Import wallet and paste the private key"},
            "litecoin":  {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Electrum-LTC, Exodus, Trust Wallet",                  "how": "Import private key into Electrum-LTC or Exodus"},
            "dash":      {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Dash Core, Exodus, Trust Wallet",                     "how": "Import private key into Dash Core (Console: importprivkey <key>)"},
            "monero":    {"auth_type": "Seed Phrase (25 words) / Private Keys (spend+view)","wallets": "Monero GUI, Cake Wallet, Feather Wallet",            "how": "In Monero GUI choose Restore wallet from seed and enter 25 words"},
            "ripple":    {"auth_type": "Private Key / Seed Phrase / Family Seed",          "wallets": "XUMM (Xaman), Trust Wallet, Ledger",                  "how": "Install XUMM, choose Import and enter Family Seed or mnemonic phrase"},
            "dogecoin":  {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Dogecoin Core, Exodus, Trust Wallet",                 "how": "Import private key into Exodus or Dogecoin Core"},
            "bnb":       {"auth_type": "Private Key / Seed Phrase",                        "wallets": "Trust Wallet, MetaMask (BSC), Binance Chain Wallet",  "how": "Import seed phrase into Trust Wallet or add BSC network in MetaMask"},
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  PRICE CACHE
    # ═══════════════════════════════════════════════════════════════════════════

    async def _get_prices(self, session, timeout):
        """Fetch USD prices from CoinGecko, cached for 5 minutes."""
        import time
        global _PRICE_CACHE, _PRICE_CACHE_TS
        if _PRICE_CACHE and (time.time() - _PRICE_CACHE_TS) < _PRICE_TTL:
            return _PRICE_CACHE
        ids = "bitcoin,ethereum,tron,solana,litecoin,dash,monero,ripple,dogecoin,binancecoin,the-open-network,cardano,matic-network,avalanche-2"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        try:
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=None)
            if resp.status == 200:
                data = await resp.json()
                resp.close()
                _PRICE_CACHE = {
                    "bitcoin":   data.get("bitcoin",    {}).get("usd", 0),
                    "ethereum":  data.get("ethereum",   {}).get("usd", 0),
                    "tron":      data.get("tron",       {}).get("usd", 0),
                    "solana":    data.get("solana",     {}).get("usd", 0),
                    "litecoin":  data.get("litecoin",   {}).get("usd", 0),
                    "dash":      data.get("dash",       {}).get("usd", 0),
                    "monero":    data.get("monero",     {}).get("usd", 0),
                    "ripple":    data.get("ripple",     {}).get("usd", 0),
                    "dogecoin":  data.get("dogecoin",   {}).get("usd", 0),
                    "bnb":       data.get("binancecoin",{}).get("usd", 0),
                    "ton":       data.get("the-open-network",{}).get("usd", 0),
                    "cardano":   data.get("cardano",    {}).get("usd", 0),
                    "polygon":   data.get("matic-network",{}).get("usd", 0),
                    "avalanche": data.get("avalanche-2",{}).get("usd", 0),
                }
                _PRICE_CACHE_TS = time.time()
            else:
                resp.close()
        except Exception:
            pass
        return _PRICE_CACHE

    def _usd(self, amount, coin, prices):
        """Format amount with USD equivalent."""
        price = prices.get(coin, 0)
        if price and amount:
            usd = amount * price
            return f" (~${usd:,.2f})"
        return ""

    # ═══════════════════════════════════════════════════════════════════════════
    #  MAIN CHECK
    # ═══════════════════════════════════════════════════════════════════════════

    async def check(self, data: str, timeout: int = 10, proxy: str = None,
                    session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, type="unknown")

        wallet_type = self._detect_wallet(data)
        if wallet_type:
            result["type"]        = "wallet"
            result["wallet_type"] = wallet_type

            own_session = session is None
            if own_session:
                session = aiohttp.ClientSession()
            try:
                handler = {
                    "bitcoin":   self._check_bitcoin,
                    "ethereum":  self._check_ethereum,
                    "polygon":   self._check_polygon,
                    "avalanche": self._check_avalanche,
                    "solana":    self._check_solana,
                    "ton":       self._check_ton,
                    "cardano":   self._check_cardano,
                    "tron":      self._check_tron,
                    "litecoin":  self._check_litecoin,
                    "dash":      self._check_dash,
                    "monero":    self._check_monero,
                    "ripple":    self._check_ripple,
                    "dogecoin":  self._check_dogecoin,
                    "bnb":       self._check_bnb,
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
                result["type"]     = "exchange"
                result["exchange"] = exchange
                result["platform"] = exchange
                login, password    = self._parse_credentials(data)
                result["exists"]   = True
                result["info"]["exchange"] = exchange
                result["info"]["login"]    = login
                result["info"]["password"] = password
                parts = [f"Exchange: {exchange}"]
                if login:    parts.append(f"Login: {login}")
                if password: parts.append(f"Pass: {password}")
                result["info"]["message"] = "  |  ".join(parts)
            else:
                result["info"]["error"] = "Unknown crypto format"

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  DETECT HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_wallet(self, data: str) -> str:
        s = data.strip()
        if not s or s[0] not in _WALLET_FIRST_CHARS:
            return None
        # ETH-like: check polygon/avalanche by length only — treat as ethereum
        for wallet_type, pattern in _WALLET_PATTERNS:
            if wallet_type in ("polygon", "avalanche"):
                continue
            if pattern.match(s):
                return wallet_type
        return None

    def _detect_exchange(self, data: str) -> str:
        dl = data.lower()
        for ex in self.exchanges:
            if ex in dl:
                return ex
        return None

    def _parse_credentials(self, data: str):
        s = data.strip().replace("|", ":")
        url_m = re.match(r"https?://[^\s:]+", s)
        if url_m:
            rest   = s[url_m.end():]
            tokens = [t for t in rest.split(":") if t.strip()]
        else:
            tokens = [t for t in s.split(":") if t.strip()]
            if tokens and "." in tokens[0]:
                tokens = tokens[1:]
        login    = tokens[0] if len(tokens) > 0 else ""
        password = tokens[1] if len(tokens) > 1 else ""
        return login, password

    # ═══════════════════════════════════════════════════════════════════════════
    #  WALLET CHECKERS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_bitcoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bitcoin", valid=True)
        prices = await self._get_prices(session, timeout)
        # Fallback chain: blockchain.info -> blockstream.info -> mempool.space
        apis = [
            ("blockchain.info", f"https://blockchain.info/q/addressbalance/{address}", "text"),
            ("blockstream",     f"https://blockstream.info/api/address/{address}",     "json"),
            ("mempool.space",   f"https://mempool.space/api/address/{address}",        "json"),
        ]
        for api_name, url, fmt in apis:
            try:
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                if resp.status == 200:
                    if fmt == "text":
                        raw = await resp.text(); resp.close()
                        satoshi = int(raw.strip())
                    else:
                        data = await resp.json(); resp.close()
                        satoshi = data.get("chain_stats", {}).get("funded_txo_sum", 0) - \
                                  data.get("chain_stats", {}).get("spent_txo_sum", 0)
                        tx_count = data.get("chain_stats", {}).get("tx_count", 0)
                        result["info"]["tx_count"] = tx_count
                    balance = satoshi / 100_000_000
                    result["info"]["balance_btc"] = balance
                    result["info"]["api_source"]  = api_name
                    result["exists"] = balance > 0
                    usd = self._usd(balance, "bitcoin", prices)
                    result["info"]["message"] = f"Balance: {balance:.8f} BTC{usd}"
                    if not result["exists"]:
                        result["info"]["message"] += "  (empty)"
                    resp.close() if hasattr(resp, "closed") and not resp.closed else None
                    return result
                resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All APIs failed"
        return result

    async def _check_ethereum(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ethereum", valid=True)
        prices = await self._get_prices(session, timeout)
        # Fallback: etherscan -> infura public -> cloudflare-eth
        apis = [
            ("etherscan", f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest", "etherscan"),
            ("cloudflare", "https://cloudflare-eth.com", "rpc"),
        ]
        balance = None
        for api_name, url, fmt in apis:
            try:
                if fmt == "etherscan":
                    resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                    if resp.status == 200:
                        data = await resp.json(); resp.close()
                        if data.get("status") == "1":
                            balance = int(data["result"]) / 10**18
                            result["info"]["api_source"] = api_name
                            break
                        resp.close()
                elif fmt == "rpc":
                    payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
                    resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                            json=payload, headers={"Content-Type":"application/json"})
                    if resp.status == 200:
                        data = await resp.json(); resp.close()
                        if "result" in data:
                            balance = int(data["result"], 16) / 10**18
                            result["info"]["api_source"] = api_name
                            break
                        resp.close()
            except Exception:
                continue

        if balance is not None:
            # Also check ERC-20 tokens (USDT, USDC)
            tokens = await self._check_erc20_tokens(address, timeout, proxy, session)
            result["info"]["balance_eth"] = balance
            result["info"]["tokens"]      = tokens
            result["exists"] = balance > 0 or bool(tokens)
            usd = self._usd(balance, "ethereum", prices)
            msg = f"Balance: {balance:.6f} ETH{usd}"
            if tokens:
                msg += "  |  Tokens: " + ", ".join(f"{v:.2f} {k}" for k, v in tokens.items() if v > 0)
            if not result["exists"]:
                msg += "  (empty)"
            result["info"]["message"] = msg
            # tx count via etherscan
            try:
                tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1&sort=desc"
                r2 = await self.fetch(session, "GET", tx_url, timeout=timeout, proxy=proxy)
                if r2.status == 200:
                    d2 = await r2.json(); r2.close()
                    result["info"]["tx_count"] = len(d2.get("result", []))
            except Exception:
                pass
        else:
            result["info"]["error"] = "All ETH APIs failed"
        return result

    async def _check_erc20_tokens(self, address, timeout, proxy, session):
        """Check USDT and USDC balances on Ethereum."""
        balances = {}
        for symbol, contract in _ERC20_TOKENS.items():
            try:
                # eth_call balanceOf(address)
                data_hex = "0x70a08231" + "000000000000000000000000" + address[2:]
                payload  = {"jsonrpc":"2.0","id":1,"method":"eth_call",
                            "params":[{"to": contract, "data": data_hex}, "latest"]}
                resp = await self.fetch(session, "POST", "https://cloudflare-eth.com",
                                        timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    raw = d.get("result", "0x0")
                    val = int(raw, 16) / 10**6  # USDT/USDC use 6 decimals
                    if val > 0:
                        balances[symbol] = val
                else:
                    resp.close()
            except Exception:
                continue
        return balances

    async def _check_polygon(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="polygon", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
            resp = await self.fetch(session, "POST", "https://polygon-rpc.com",
                                    timeout=timeout, proxy=proxy,
                                    json=payload, headers={"Content-Type":"application/json"})
            if resp.status == 200:
                data = await resp.json(); resp.close()
                balance = int(data["result"], 16) / 10**18
                result["info"]["balance_matic"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance, "polygon", prices)
                result["info"]["message"] = f"Balance: {balance:.4f} MATIC{usd}"
                if not result["exists"]: result["info"]["message"] += "  (empty)"
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_avalanche(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="avalanche", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
            resp = await self.fetch(session, "POST", "https://api.avax.network/ext/bc/C/rpc",
                                    timeout=timeout, proxy=proxy,
                                    json=payload, headers={"Content-Type":"application/json"})
            if resp.status == 200:
                data = await resp.json(); resp.close()
                balance = int(data["result"], 16) / 10**18
                result["info"]["balance_avax"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance, "avalanche", prices)
                result["info"]["message"] = f"Balance: {balance:.4f} AVAX{usd}"
                if not result["exists"]: result["info"]["message"] += "  (empty)"
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_solana(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="solana", valid=True)
        prices = await self._get_prices(session, timeout)
        apis = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
        ]
        for url in apis:
            try:
                payload = {"jsonrpc":"2.0","id":1,"method":"getBalance","params":[address]}
                resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    data = await resp.json(); resp.close()
                    if "result" in data:
                        balance = data["result"]["value"] / 10**9
                        result["info"]["balance_sol"] = balance
                        result["exists"] = balance > 0
                        usd = self._usd(balance, "solana", prices)
                        result["info"]["message"] = f"Balance: {balance:.4f} SOL{usd}"
                        if not result["exists"]: result["info"]["message"] += "  (empty)"
                        return result
                    resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All Solana APIs failed"
        return result

    async def _check_ton(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ton", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            url  = f"https://toncenter.com/api/v2/getAddressInformation?address={address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json(); resp.close()
                if data.get("ok"):
                    balance = int(data["result"].get("balance", 0)) / 10**9
                    result["info"]["balance_ton"] = balance
                    result["exists"] = balance > 0
                    usd = self._usd(balance, "ton", prices)
                    result["info"]["message"] = f"Balance: {balance:.4f} TON{usd}"
                    if not result["exists"]: result["info"]["message"] += "  (empty)"
                else:
                    result["info"]["error"] = data.get("error", "TON API error")
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_cardano(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="cardano", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            url  = f"https://cardano-mainnet.blockfrost.io/api/v0/addresses/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    headers={"project_id": "mainnetplaceholder"})
            if resp.status == 200:
                data = await resp.json(); resp.close()
                lovelace = int(next((a["quantity"] for a in data.get("amount",[])
                                     if a["unit"]=="lovelace"), 0))
                balance = lovelace / 10**6
                result["info"]["balance_ada"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance, "cardano", prices)
                result["info"]["message"] = f"Balance: {balance:.2f} ADA{usd}"
                if not result["exists"]: result["info"]["message"] += "  (empty)"
            elif resp.status == 403:
                resp.close()
                result["info"]["message"] = "Cardano: API key required (Blockfrost)"
                result["exists"] = False
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_tron(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="tron", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            url  = f"https://apilist.tronscanapi.com/api/accountv2?address={address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json(); resp.close()
                balance  = data.get("balance", 0) / 10**6
                tx_count = data.get("totalTransactionCount", 0)
                # TRC-20 USDT balance
                trc20 = {}
                for token in data.get("trc20token_balances", []):
                    sym = token.get("tokenAbbr","").upper()
                    if sym in ("USDT","USDC"):
                        trc20[sym] = int(token.get("balance",0)) / 10**6
                result["info"]["balance_trx"] = balance
                result["info"]["tx_count"]    = tx_count
                result["info"]["tokens"]      = trc20
                result["exists"] = balance > 0 or tx_count > 0 or bool(trc20)
                usd = self._usd(balance, "tron", prices)
                msg = f"Balance: {balance:.2f} TRX{usd}  |  Tx: {tx_count}"
                if trc20:
                    msg += "  |  Tokens: " + ", ".join(f"{v:.2f} {k}" for k,v in trc20.items())
                if not result["exists"]: msg += "  (empty)"
                result["info"]["message"] = msg
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_litecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="litecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        apis = [
            f"https://api.blockchair.com/litecoin/dashboards/address/{address}",
            f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance",
        ]
        for url in apis:
            try:
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                if resp.status == 200:
                    data = await resp.json(); resp.close()
                    if "blockchair" in url:
                        ad = data.get("data",{}).get(address,{}).get("address",{})
                        balance  = ad.get("balance",0) / 10**8
                        tx_count = ad.get("transaction_count",0)
                    else:
                        balance  = data.get("balance",0) / 10**8
                        tx_count = data.get("n_tx",0)
                    result["info"]["balance_ltc"] = balance
                    result["info"]["tx_count"]    = tx_count
                    result["exists"] = balance > 0
                    usd = self._usd(balance, "litecoin", prices)
                    result["info"]["message"] = f"Balance: {balance:.8f} LTC{usd}  |  Tx: {tx_count}"
                    if not result["exists"]: result["info"]["message"] += "  (empty)"
                    return result
                resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All LTC APIs failed"
        return result

    async def _check_dash(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dash", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            url  = f"https://api.blockchair.com/dash/dashboards/address/{address}"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                data = await resp.json(); resp.close()
                ad = data.get("data",{}).get(address,{}).get("address",{})
                balance  = ad.get("balance",0) / 10**8
                tx_count = ad.get("transaction_count",0)
                result["info"]["balance_dash"] = balance
                result["info"]["tx_count"]     = tx_count
                result["exists"] = balance > 0
                usd = self._usd(balance, "dash", prices)
                result["info"]["message"] = f"Balance: {balance:.8f} DASH{usd}  |  Tx: {tx_count}"
                if not result["exists"]: result["info"]["message"] += "  (empty)"
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_monero(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="monero", valid=True)
        try:
            url  = f"https://xmrchain.net/api/outputs?address={address}&viewkey=&page=0&limit=1"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            status = resp.status; resp.close()
            if status == 200:
                result["exists"] = True
                result["info"]["message"] = "Monero address valid (balance requires view key)"
            else:
                result["info"]["message"] = f"HTTP {status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_ripple(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ripple", valid=True)
        prices = await self._get_prices(session, timeout)
        apis = [
            ("ripple_s1",  "https://s1.ripple.com:51234/"),
            ("ripple_s2",  "https://s2.ripple.com:51234/"),
            ("xrplcluster","https://xrplcluster.com/"),
        ]
        for api_name, url in apis:
            try:
                payload = {"method":"account_info","params":[{"account":address,"strict":True}]}
                resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    data = await resp.json(); resp.close()
                    r = data.get("result",{})
                    if r.get("status") == "success":
                        drops   = int(r.get("account_data",{}).get("Balance",0))
                        balance = drops / 10**6
                        tx_seq  = r.get("account_data",{}).get("Sequence",0)
                        result["info"]["balance_xrp"] = balance
                        result["info"]["tx_sequence"]  = tx_seq
                        result["info"]["api_source"]   = api_name
                        result["exists"] = balance > 0
                        usd = self._usd(balance, "ripple", prices)
                        result["info"]["message"] = f"Balance: {balance:.2f} XRP{usd}  |  Seq: {tx_seq}"
                        if not result["exists"]: result["info"]["message"] += "  (empty)"
                        return result
                    resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All XRP APIs failed"
        return result

    async def _check_dogecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dogecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        apis = [
            f"https://api.blockchair.com/dogecoin/dashboards/address/{address}",
            f"https://api.blockcypher.com/v1/doge/main/addrs/{address}/balance",
        ]
        for url in apis:
            try:
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                if resp.status == 200:
                    data = await resp.json(); resp.close()
                    if "blockchair" in url:
                        ad = data.get("data",{}).get(address,{}).get("address",{})
                        balance  = ad.get("balance",0) / 10**8
                        tx_count = ad.get("transaction_count",0)
                    else:
                        balance  = data.get("balance",0) / 10**8
                        tx_count = data.get("n_tx",0)
                    result["info"]["balance_doge"] = balance
                    result["info"]["tx_count"]     = tx_count
                    result["exists"] = balance > 0
                    usd = self._usd(balance, "dogecoin", prices)
                    result["info"]["message"] = f"Balance: {balance:.4f} DOGE{usd}  |  Tx: {tx_count}"
                    if not result["exists"]: result["info"]["message"] += "  (empty)"
                    return result
                resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All DOGE APIs failed"
        return result

    async def _check_bnb(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bnb", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            # BSC via public RPC
            payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
            resp = await self.fetch(session, "POST", "https://bsc-dataseed.binance.org/",
                                    timeout=timeout, proxy=proxy,
                                    json=payload, headers={"Content-Type":"application/json"})
            if resp.status == 200:
                data = await resp.json(); resp.close()
                balance = int(data["result"], 16) / 10**18
                result["info"]["balance_bnb"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance, "bnb", prices)
                result["info"]["message"] = f"Balance: {balance:.4f} BNB{usd}"
                if not result["exists"]: result["info"]["message"] += "  (empty)"
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
