import asyncio
import aiohttp
import re
import hashlib
import hmac
import struct
import time

from checkers.base_checker import BaseChecker

# ── Wallet address patterns ────────────────────────────────────────────────────
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

# Private key patterns
_PRIVKEY_HEX_RE  = re.compile(r'^(0x)?[a-fA-F0-9]{64}$')          # ETH/BSC hex
_PRIVKEY_WIF_RE  = re.compile(r'^[5KLc][1-9A-HJ-NP-Za-km-z]{50,51}$')  # BTC WIF

# Seed phrase: 12 or 24 space-separated BIP-39 words
_SEED_RE = re.compile(r'^([a-z]+\s){11,23}[a-z]+$', re.IGNORECASE)

_WALLET_FIRST_CHARS = frozenset('bB013456789LMlTXrDdEUa')

# ── Price cache ────────────────────────────────────────────────────────────────
_PRICE_CACHE: dict = {}
_PRICE_CACHE_TS: float = 0.0
_PRICE_TTL = 300

# ── ERC-20 tokens to check ─────────────────────────────────────────────────────
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

# ── TRC-20 tokens ──────────────────────────────────────────────────────────────
_TRC20_TOKENS = {"USDT", "USDC"}

# ── EVM chains for multichain scan ────────────────────────────────────────────
_EVM_CHAINS = [
    ("ethereum",  "https://cloudflare-eth.com",                    "ETH"),
    ("bsc",       "https://bsc-dataseed.binance.org/",             "BNB"),
    ("polygon",   "https://polygon-rpc.com",                       "MATIC"),
    ("avalanche", "https://api.avax.network/ext/bc/C/rpc",         "AVAX"),
    ("arbitrum",  "https://arb1.arbitrum.io/rpc",                  "ETH"),
    ("optimism",  "https://mainnet.optimism.io",                   "ETH"),
]


class CryptoChecker(BaseChecker):
    def __init__(self):
        self.wallet_patterns = _WALLET_PATTERNS
        self.exchanges = ["binance","bybit","okx","huobi","kucoin","gate","mexc","bitget"]
        self.auth_info = {
            "bitcoin":   {"auth_type":"Private Key / Seed Phrase","wallets":"Electrum, Exodus, Trust Wallet, Ledger","how":"Import private key or seed phrase into Electrum / Exodus / Trust Wallet"},
            "ethereum":  {"auth_type":"Private Key / Seed Phrase / Keystore","wallets":"MetaMask, Trust Wallet, Rabby, Ledger","how":"Import private key into MetaMask (Settings -> Import account)"},
            "polygon":   {"auth_type":"Private Key / Seed Phrase","wallets":"MetaMask (Polygon), Trust Wallet","how":"Add Polygon network in MetaMask and import private key"},
            "avalanche": {"auth_type":"Private Key / Seed Phrase","wallets":"Core Wallet, MetaMask (Avalanche C-Chain)","how":"Import private key into Core Wallet or MetaMask with Avalanche C-Chain"},
            "solana":    {"auth_type":"Private Key / Seed Phrase","wallets":"Phantom, Solflare, Backpack","how":"Install Phantom (phantom.app), choose Import private key"},
            "ton":       {"auth_type":"Seed Phrase (24 words) / Private Key","wallets":"Tonkeeper, MyTonWallet, TonHub","how":"Install Tonkeeper, choose Import wallet and enter 24-word seed phrase"},
            "cardano":   {"auth_type":"Seed Phrase (15/24 words)","wallets":"Daedalus, Yoroi, Eternl","how":"Install Yoroi or Eternl, choose Restore wallet and enter seed phrase"},
            "tron":      {"auth_type":"Private Key / Seed Phrase","wallets":"TronLink, Trust Wallet, Ledger","how":"Install TronLink, choose Import wallet and paste the private key"},
            "litecoin":  {"auth_type":"Private Key / Seed Phrase","wallets":"Electrum-LTC, Exodus, Trust Wallet","how":"Import private key into Electrum-LTC or Exodus"},
            "dash":      {"auth_type":"Private Key / Seed Phrase","wallets":"Dash Core, Exodus, Trust Wallet","how":"Import private key into Dash Core (Console: importprivkey <key>)"},
            "monero":    {"auth_type":"Seed Phrase (25 words) / Private Keys (spend+view)","wallets":"Monero GUI, Cake Wallet, Feather Wallet","how":"In Monero GUI choose Restore wallet from seed and enter 25 words"},
            "ripple":    {"auth_type":"Private Key / Seed Phrase / Family Seed","wallets":"XUMM (Xaman), Trust Wallet, Ledger","how":"Install XUMM, choose Import and enter Family Seed or mnemonic phrase"},
            "dogecoin":  {"auth_type":"Private Key / Seed Phrase","wallets":"Dogecoin Core, Exodus, Trust Wallet","how":"Import private key into Exodus or Dogecoin Core"},
            "bnb":       {"auth_type":"Private Key / Seed Phrase","wallets":"Trust Wallet, MetaMask (BSC), Binance Chain Wallet","how":"Import seed phrase into Trust Wallet or add BSC network in MetaMask"},
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  PRICE CACHE  (point 6 — USD equivalent)
    # ═══════════════════════════════════════════════════════════════════════════

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
                    "avalanche": d.get("avalanche-2",{}).get("usd",0),
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

    # ═══════════════════════════════════════════════════════════════════════════
    #  MAIN ENTRY
    # ═══════════════════════════════════════════════════════════════════════════

    async def check(self, data: str, timeout: int = 10, proxy: str = None,
                    session: aiohttp.ClientSession = None) -> dict:
        result = self.make_result(input=data, type="unknown")
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        try:
            result = await self._dispatch(data.strip(), timeout, proxy, session)
        finally:
            if own_session:
                await session.close()
        return result

    async def _dispatch(self, data, timeout, proxy, session):
        # 1. Seed phrase (12 or 24 words)
        words = data.split()
        if len(words) in (12, 15, 18, 21, 24) and _SEED_RE.match(data):
            return await self._check_seed(data, timeout, proxy, session)

        # 2. Private key hex (ETH/BSC/Polygon/Avalanche)
        if _PRIVKEY_HEX_RE.match(data):
            return await self._check_privkey_hex(data, timeout, proxy, session)

        # 8. WIF private key (Bitcoin)
        if _PRIVKEY_WIF_RE.match(data):
            return await self._check_privkey_wif(data, timeout, proxy, session)

        # Regular wallet address
        wallet_type = self._detect_wallet(data)
        if wallet_type:
            result = self.make_result(input=data, type="wallet", wallet_type=wallet_type)
            handler = {
                "bitcoin":  self._check_bitcoin,
                "ethereum": self._check_ethereum,
                "tron":     self._check_tron,
                "solana":   self._check_solana,
                "ton":      self._check_ton,
                "cardano":  self._check_cardano,
                "litecoin": self._check_litecoin,
                "dash":     self._check_dash,
                "monero":   self._check_monero,
                "ripple":   self._check_ripple,
                "dogecoin": self._check_dogecoin,
                "bnb":      self._check_bnb,
            }.get(wallet_type)
            if handler:
                result = await handler(data, timeout, proxy, session)
                if result.get("exists") and wallet_type in self.auth_info:
                    result["info"]["auth"] = self.auth_info[wallet_type]
            else:
                result["info"]["error"] = f"No checker for {wallet_type}"
            return result

        # Exchange credentials
        exchange = self._detect_exchange(data)
        if exchange:
            login, password = self._parse_credentials(data)
            result = self.make_result(input=data, type="exchange")
            result["exchange"] = exchange
            result["platform"] = exchange
            result["exists"]   = True
            result["info"].update({"exchange": exchange, "login": login, "password": password,
                                   "message": "  |  ".join(filter(None, [
                                       f"Exchange: {exchange}",
                                       f"Login: {login}" if login else "",
                                       f"Pass: {password}" if password else ""]))})
            return result

        result = self.make_result(input=data, type="unknown")
        result["info"]["error"] = "Unknown crypto format"
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  POINT 1 — SEED PHRASE
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_seed(self, phrase, timeout, proxy, session):
        """Derive BTC/ETH/SOL/TRX addresses from seed and check all balances."""
        result = self.make_result(input=phrase[:20]+"...", type="seed")
        prices = await self._get_prices(session, timeout)
        derived = {}
        errors  = []

        try:
            from bip_utils import (Bip39MnemonicValidator, Bip39SeedGenerator,
                                   Bip44, Bip44Coins, Bip44Changes,
                                   Bip49, Bip49Coins, Bip84, Bip84Coins)
            from eth_account import Account

            if not Bip39MnemonicValidator().IsValid(phrase):
                result["info"]["error"] = "Invalid BIP-39 mnemonic"
                return result

            seed_bytes = Bip39SeedGenerator(phrase).Generate()

            # BTC (m/44'/0'/0'/0/0)
            try:
                btc_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                derived["bitcoin"] = btc_ctx.PublicKey().ToAddress()
            except Exception as e:
                errors.append(f"BTC derive: {e}")

            # ETH (m/44'/60'/0'/0/0)
            try:
                eth_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                derived["ethereum"] = eth_ctx.PublicKey().ToAddress()
            except Exception as e:
                errors.append(f"ETH derive: {e}")

            # TRX (m/44'/195'/0'/0/0)
            try:
                trx_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.TRON).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                derived["tron"] = trx_ctx.PublicKey().ToAddress()
            except Exception as e:
                errors.append(f"TRX derive: {e}")

            # SOL (m/44'/501'/0'/0')
            try:
                sol_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA).Purpose().Coin().Account(0)
                derived["solana"] = sol_ctx.PublicKey().ToAddress()
            except Exception as e:
                errors.append(f"SOL derive: {e}")

        except Exception as e:
            result["info"]["error"] = f"Seed derive error: {e}"
            return result

        # Check all derived addresses concurrently
        tasks = {}
        handlers = {
            "bitcoin":  self._check_bitcoin,
            "ethereum": self._check_ethereum,
            "tron":     self._check_tron,
            "solana":   self._check_solana,
        }
        check_results = await asyncio.gather(*[
            handlers[coin](addr, timeout, proxy, session)
            for coin, addr in derived.items()
            if coin in handlers
        ], return_exceptions=True)

        total_usd = 0.0
        found_coins = []
        result["info"]["addresses"] = derived
        result["info"]["balances"]  = {}

        for (coin, addr), res in zip(
            [(c, a) for c, a in derived.items() if c in handlers],
            check_results
        ):
            if isinstance(res, Exception):
                continue
            bal_key = f"balance_{coin[:3].lower()}"
            bal = res.get("info", {}).get(bal_key, 0) or 0
            result["info"]["balances"][coin] = {
                "address": addr,
                "balance": bal,
                "message": res.get("info", {}).get("message", ""),
            }
            price = prices.get(coin, 0)
            total_usd += bal * price
            if bal > 0:
                found_coins.append(coin)

        result["exists"] = bool(found_coins)
        result["info"]["total_usd"] = total_usd
        result["info"]["message"] = (
            f"Seed OK | Coins with balance: {', '.join(found_coins) if found_coins else 'none'} "
            f"| Total: ~${total_usd:,.2f}"
        )
        if errors:
            result["info"]["derive_errors"] = errors
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  POINT 2 — PRIVATE KEY HEX  (ETH/BSC/Polygon/Avalanche/Arbitrum/Optimism)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_privkey_hex(self, key, timeout, proxy, session):
        result = self.make_result(input=key[:10]+"...", type="privkey_hex")
        prices = await self._get_prices(session, timeout)
        try:
            from eth_account import Account
            key_hex = key if key.startswith("0x") else "0x" + key
            acct    = Account.from_key(key_hex)
            address = acct.address
            result["info"]["address"] = address
        except Exception as e:
            result["info"]["error"] = f"Invalid private key: {e}"
            return result

        # Point 7 — multichain scan
        chain_results = await self._multichain_scan(address, timeout, proxy, session, prices)
        total_usd   = sum(r["usd"] for r in chain_results.values())
        active      = [c for c, r in chain_results.items() if r["balance"] > 0]

        result["info"]["chains"]    = chain_results
        result["info"]["total_usd"] = total_usd
        result["exists"] = bool(active)
        result["info"]["message"] = (
            f"PrivKey -> {address} | "
            f"Active chains: {', '.join(active) if active else 'none'} | "
            f"Total: ~${total_usd:,.2f}"
        )
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  POINT 8 — WIF PRIVATE KEY (Bitcoin)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_privkey_wif(self, wif, timeout, proxy, session):
        result = self.make_result(input=wif[:10]+"...", type="privkey_wif")
        prices = await self._get_prices(session, timeout)
        try:
            from bip_utils import WifDecoder, Bip44, Bip44Coins, Secp256k1PrivateKey
            priv_bytes, _ = WifDecoder.Decode(wif)
            priv_key = Secp256k1PrivateKey.FromBytes(priv_bytes)
            # Derive P2PKH address
            from bip_utils import P2PKHAddr
            address = P2PKHAddr.EncodeKey(priv_key.PublicKey().KeyObject())
            result["info"]["address"] = address
        except Exception as e:
            result["info"]["error"] = f"Invalid WIF key: {e}"
            return result

        btc_result = await self._check_bitcoin(address, timeout, proxy, session)
        result["exists"] = btc_result.get("exists", False)
        result["info"].update(btc_result.get("info", {}))
        result["info"]["message"] = f"WIF -> {address} | " + result["info"].get("message","")
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    #  POINT 7 — MULTICHAIN SCAN (EVM)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _multichain_scan(self, address, timeout, proxy, session, prices):
        """Check ETH address balance on all EVM chains concurrently."""
        async def _check_chain(chain_name, rpc_url, symbol):
            try:
                payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
                resp = await self.fetch(session, "POST", rpc_url, timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    bal = int(d.get("result","0x0"), 16) / 10**18
                    coin_key = {"ETH":"ethereum","BNB":"bnb","MATIC":"polygon","AVAX":"avalanche"}.get(symbol, "ethereum")
                    usd = bal * prices.get(coin_key, 0)
                    return chain_name, {"balance": bal, "symbol": symbol, "usd": usd,
                                        "message": f"{bal:.6f} {symbol} (~${usd:,.2f})"}
                resp.close()
            except Exception:
                pass
            return chain_name, {"balance": 0, "symbol": symbol, "usd": 0, "message": "error"}

        tasks = [_check_chain(name, url, sym) for name, url, sym in _EVM_CHAINS]
        results = await asyncio.gather(*tasks)
        return dict(results)

    # ═══════════════════════════════════════════════════════════════════════════
    #  DETECT HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_wallet(self, data):
        s = data.strip()
        if not s or s[0] not in _WALLET_FIRST_CHARS:
            return None
        for wallet_type, pattern in _WALLET_PATTERNS:
            if pattern.match(s):
                return wallet_type
        return None

    def _detect_exchange(self, data):
        dl = data.lower()
        for ex in self.exchanges:
            if ex in dl:
                return ex
        return None

    def _parse_credentials(self, data):
        s = data.strip().replace("|", ":")
        url_m = re.match(r"https?://[^\s:]+", s)
        if url_m:
            rest   = s[url_m.end():]
            tokens = [t for t in rest.split(":") if t.strip()]
        else:
            tokens = [t for t in s.split(":") if t.strip()]
            if tokens and "." in tokens[0]:
                tokens = tokens[1:]
        return (tokens[0] if tokens else ""), (tokens[1] if len(tokens) > 1 else "")

    # ═══════════════════════════════════════════════════════════════════════════
    #  WALLET CHECKERS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_bitcoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="bitcoin", valid=True)
        prices = await self._get_prices(session, timeout)
        for api_name, url, fmt in [
            ("blockchain.info", f"https://blockchain.info/q/addressbalance/{address}", "text"),
            ("blockstream",     f"https://blockstream.info/api/address/{address}",     "json"),
            ("mempool.space",   f"https://mempool.space/api/address/{address}",        "json"),
        ]:
            try:
                resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                if resp.status == 200:
                    if fmt == "text":
                        raw = await resp.text(); resp.close()
                        satoshi = int(raw.strip())
                        tx_count = None
                    else:
                        d = await resp.json(); resp.close()
                        cs = d.get("chain_stats", {})
                        satoshi  = cs.get("funded_txo_sum",0) - cs.get("spent_txo_sum",0)
                        tx_count = cs.get("tx_count", 0)
                    balance = satoshi / 1e8
                    result["info"]["balance_btc"] = balance
                    result["info"]["api_source"]  = api_name
                    if tx_count is not None: result["info"]["tx_count"] = tx_count
                    result["exists"] = balance > 0
                    usd = self._usd(balance, "bitcoin", prices)
                    result["info"]["message"] = f"Balance: {balance:.8f} BTC{usd}" + ("  (empty)" if not result["exists"] else "")
                    if tx_count: result["info"]["message"] += f"  |  Tx: {tx_count}"
                    return result
                resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All BTC APIs failed"
        return result

    async def _check_ethereum(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ethereum", valid=True)
        prices = await self._get_prices(session, timeout)
        balance = None
        for api_name, url, fmt in [
            ("etherscan",  f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest", "etherscan"),
            ("cloudflare", "https://cloudflare-eth.com", "rpc"),
        ]:
            try:
                if fmt == "etherscan":
                    resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
                    if resp.status == 200:
                        d = await resp.json(); resp.close()
                        if d.get("status") == "1":
                            balance = int(d["result"]) / 1e18
                            result["info"]["api_source"] = api_name; break
                        resp.close()
                else:
                    payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
                    resp = await self.fetch(session, "POST", url, timeout=timeout, proxy=proxy,
                                            json=payload, headers={"Content-Type":"application/json"})
                    if resp.status == 200:
                        d = await resp.json(); resp.close()
                        if "result" in d:
                            balance = int(d["result"],16) / 1e18
                            result["info"]["api_source"] = api_name; break
                        resp.close()
            except Exception:
                continue

        if balance is not None:
            tokens = await self._check_erc20(address, timeout, proxy, session)
            # Point 3 — NFT check
            nfts   = await self._check_nft(address, timeout, proxy, session)
            # Point 5 — staking
            staking = await self._check_staking(address, timeout, proxy, session)
            # Point 6 — last tx
            last_tx = await self._get_last_tx_eth(address, timeout, proxy, session)

            result["info"]["balance_eth"] = balance
            result["info"]["tokens"]      = tokens
            result["info"]["nfts"]        = nfts
            result["info"]["staking"]     = staking
            result["info"]["last_tx"]     = last_tx
            result["exists"] = balance > 0 or bool(tokens) or bool(nfts) or bool(staking)
            usd = self._usd(balance, "ethereum", prices)
            msg = f"Balance: {balance:.6f} ETH{usd}"
            if tokens:  msg += "  |  Tokens: " + ", ".join(f"{v:.2f} {k}" for k,v in tokens.items() if v>0)
            if nfts:    msg += f"  |  NFTs: {nfts}"
            if staking: msg += "  |  Staking: " + ", ".join(f"{v:.4f} {k}" for k,v in staking.items())
            if last_tx: msg += f"  |  Last tx: {last_tx}"
            if not result["exists"]: msg += "  (empty)"
            result["info"]["message"] = msg
        else:
            result["info"]["error"] = "All ETH APIs failed"
        return result

    # ── Point 4 — ERC-20 tokens ────────────────────────────────────────────────
    async def _check_erc20(self, address, timeout, proxy, session):
        balances = {}
        for symbol, (contract, decimals) in _ERC20_TOKENS.items():
            try:
                data_hex = "0x70a08231" + "000000000000000000000000" + address[2:]
                payload  = {"jsonrpc":"2.0","id":1,"method":"eth_call",
                            "params":[{"to":contract,"data":data_hex},"latest"]}
                resp = await self.fetch(session, "POST", "https://cloudflare-eth.com",
                                        timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    raw = d.get("result","0x0")
                    val = int(raw,16) / 10**decimals
                    if val > 0:
                        balances[symbol] = val
                else:
                    resp.close()
            except Exception:
                continue
        return balances

    # ── Point 3 — NFT check ────────────────────────────────────────────────────
    async def _check_nft(self, address, timeout, proxy, session):
        """Check NFT count via OpenSea public API (no key needed for count)."""
        try:
            url  = f"https://api.opensea.io/api/v2/chain/ethereum/account/{address}/nfts?limit=1"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy,
                                    headers={"accept":"application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                count = len(d.get("nfts", []))
                # OpenSea returns next cursor if more exist
                has_more = bool(d.get("next"))
                return f"{count}+" if has_more else str(count) if count else ""
            resp.close()
        except Exception:
            pass
        return ""

    # ── Point 5 — Staking / DeFi ──────────────────────────────────────────────
    async def _check_staking(self, address, timeout, proxy, session):
        """Check stETH (Lido) and rETH (Rocket Pool) balances."""
        staking = {}
        staking_tokens = {
            "stETH": ("0xae7ab96520de3a18e5e111b5eaab095312d7fe84", 18),
            "rETH":  ("0xae78736cd615f374d3085123a210448e74fc6393", 18),
            "wstETH":("0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", 18),
        }
        for symbol, (contract, decimals) in staking_tokens.items():
            try:
                data_hex = "0x70a08231" + "000000000000000000000000" + address[2:]
                payload  = {"jsonrpc":"2.0","id":1,"method":"eth_call",
                            "params":[{"to":contract,"data":data_hex},"latest"]}
                resp = await self.fetch(session, "POST", "https://cloudflare-eth.com",
                                        timeout=timeout, proxy=proxy,
                                        json=payload, headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    val = int(d.get("result","0x0"),16) / 10**decimals
                    if val > 0:
                        staking[symbol] = val
                else:
                    resp.close()
            except Exception:
                continue
        return staking

    # ── Point 6 — Last transaction ────────────────────────────────────────────
    async def _get_last_tx_eth(self, address, timeout, proxy, session):
        try:
            url  = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&page=1&offset=1&sort=desc"
            resp = await self.fetch(session, "GET", url, timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                txs = d.get("result", [])
                if txs and isinstance(txs, list) and txs[0]:
                    ts  = int(txs[0].get("timeStamp", 0))
                    val = int(txs[0].get("value", 0)) / 1e18
                    from datetime import datetime
                    dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    return f"{dt}  {val:.4f} ETH"
            else:
                resp.close()
        except Exception:
            pass
        return ""

    async def _check_tron(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="tron", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session, "GET",
                f"https://apilist.tronscanapi.com/api/accountv2?address={address}",
                timeout=timeout, proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                balance  = d.get("balance",0) / 1e6
                tx_count = d.get("totalTransactionCount",0)
                trc20 = {t.get("tokenAbbr","").upper(): int(t.get("balance",0))/1e6
                         for t in d.get("trc20token_balances",[])
                         if t.get("tokenAbbr","").upper() in _TRC20_TOKENS and int(t.get("balance",0))>0}
                result["info"].update({"balance_trx":balance,"tx_count":tx_count,"tokens":trc20})
                result["exists"] = balance>0 or tx_count>0 or bool(trc20)
                usd = self._usd(balance,"tron",prices)
                msg = f"Balance: {balance:.2f} TRX{usd}  |  Tx: {tx_count}"
                if trc20: msg += "  |  Tokens: " + ", ".join(f"{v:.2f} {k}" for k,v in trc20.items())
                if not result["exists"]: msg += "  (empty)"
                result["info"]["message"] = msg
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_solana(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="solana", valid=True)
        prices = await self._get_prices(session, timeout)
        for url in ["https://api.mainnet-beta.solana.com","https://solana-api.projectserum.com"]:
            try:
                payload = {"jsonrpc":"2.0","id":1,"method":"getBalance","params":[address]}
                resp = await self.fetch(session,"POST",url,timeout=timeout,proxy=proxy,
                                        json=payload,headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    if "result" in d:
                        balance = d["result"]["value"] / 1e9
                        result["info"]["balance_sol"] = balance
                        result["exists"] = balance > 0
                        usd = self._usd(balance,"solana",prices)
                        result["info"]["message"] = f"Balance: {balance:.4f} SOL{usd}" + ("  (empty)" if not result["exists"] else "")
                        return result
                    resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All SOL APIs failed"
        return result

    async def _check_ton(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ton", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session,"GET",
                f"https://toncenter.com/api/v2/getAddressInformation?address={address}",
                timeout=timeout,proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                if d.get("ok"):
                    balance = int(d["result"].get("balance",0)) / 1e9
                    result["info"]["balance_ton"] = balance
                    result["exists"] = balance > 0
                    usd = self._usd(balance,"ton",prices)
                    result["info"]["message"] = f"Balance: {balance:.4f} TON{usd}" + ("  (empty)" if not result["exists"] else "")
                else:
                    result["info"]["error"] = d.get("error","TON API error")
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_cardano(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="cardano", valid=True)
        prices = await self._get_prices(session, timeout)
        try:
            resp = await self.fetch(session,"GET",
                f"https://cardano-mainnet.blockfrost.io/api/v0/addresses/{address}",
                timeout=timeout,proxy=proxy,headers={"project_id":"mainnetplaceholder"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                lovelace = int(next((a["quantity"] for a in d.get("amount",[]) if a["unit"]=="lovelace"),0))
                balance  = lovelace / 1e6
                result["info"]["balance_ada"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance,"cardano",prices)
                result["info"]["message"] = f"Balance: {balance:.2f} ADA{usd}" + ("  (empty)" if not result["exists"] else "")
            elif resp.status == 403:
                resp.close(); result["info"]["message"] = "Cardano: Blockfrost API key required"
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_litecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="litecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        for url in [f"https://api.blockchair.com/litecoin/dashboards/address/{address}",
                    f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"]:
            try:
                resp = await self.fetch(session,"GET",url,timeout=timeout,proxy=proxy)
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    if "blockchair" in url:
                        ad = d.get("data",{}).get(address,{}).get("address",{})
                        balance,tx_count = ad.get("balance",0)/1e8, ad.get("transaction_count",0)
                    else:
                        balance,tx_count = d.get("balance",0)/1e8, d.get("n_tx",0)
                    result["info"].update({"balance_ltc":balance,"tx_count":tx_count})
                    result["exists"] = balance > 0
                    usd = self._usd(balance,"litecoin",prices)
                    result["info"]["message"] = f"Balance: {balance:.8f} LTC{usd}  |  Tx: {tx_count}" + ("  (empty)" if not result["exists"] else "")
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
            resp = await self.fetch(session,"GET",
                f"https://api.blockchair.com/dash/dashboards/address/{address}",
                timeout=timeout,proxy=proxy)
            if resp.status == 200:
                d = await resp.json(); resp.close()
                ad = d.get("data",{}).get(address,{}).get("address",{})
                balance,tx_count = ad.get("balance",0)/1e8, ad.get("transaction_count",0)
                result["info"].update({"balance_dash":balance,"tx_count":tx_count})
                result["exists"] = balance > 0
                usd = self._usd(balance,"dash",prices)
                result["info"]["message"] = f"Balance: {balance:.8f} DASH{usd}  |  Tx: {tx_count}" + ("  (empty)" if not result["exists"] else "")
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_monero(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="monero", valid=True)
        try:
            resp = await self.fetch(session,"GET",
                f"https://xmrchain.net/api/outputs?address={address}&viewkey=&page=0&limit=1",
                timeout=timeout,proxy=proxy)
            status = resp.status; resp.close()
            result["exists"] = status == 200
            result["info"]["message"] = ("Monero address valid (balance requires view key)"
                                         if status==200 else f"HTTP {status}")
        except Exception as e:
            result["info"]["error"] = str(e)
        return result

    async def _check_ripple(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="ripple", valid=True)
        prices = await self._get_prices(session, timeout)
        for api_name, url in [("s1","https://s1.ripple.com:51234/"),
                               ("s2","https://s2.ripple.com:51234/"),
                               ("xrplcluster","https://xrplcluster.com/")]:
            try:
                payload = {"method":"account_info","params":[{"account":address,"strict":True}]}
                resp = await self.fetch(session,"POST",url,timeout=timeout,proxy=proxy,
                                        json=payload,headers={"Content-Type":"application/json"})
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    r = d.get("result",{})
                    if r.get("status") == "success":
                        balance = int(r.get("account_data",{}).get("Balance",0)) / 1e6
                        seq     = r.get("account_data",{}).get("Sequence",0)
                        result["info"].update({"balance_xrp":balance,"tx_sequence":seq,"api_source":api_name})
                        result["exists"] = balance > 0
                        usd = self._usd(balance,"ripple",prices)
                        result["info"]["message"] = f"Balance: {balance:.2f} XRP{usd}  |  Seq: {seq}" + ("  (empty)" if not result["exists"] else "")
                        return result
                    resp.close()
            except Exception:
                continue
        result["info"]["error"] = "All XRP APIs failed"
        return result

    async def _check_dogecoin(self, address, timeout, proxy, session):
        result = self.make_result(input=address, type="wallet", wallet_type="dogecoin", valid=True)
        prices = await self._get_prices(session, timeout)
        for url in [f"https://api.blockchair.com/dogecoin/dashboards/address/{address}",
                    f"https://api.blockcypher.com/v1/doge/main/addrs/{address}/balance"]:
            try:
                resp = await self.fetch(session,"GET",url,timeout=timeout,proxy=proxy)
                if resp.status == 200:
                    d = await resp.json(); resp.close()
                    if "blockchair" in url:
                        ad = d.get("data",{}).get(address,{}).get("address",{})
                        balance,tx_count = ad.get("balance",0)/1e8, ad.get("transaction_count",0)
                    else:
                        balance,tx_count = d.get("balance",0)/1e8, d.get("n_tx",0)
                    result["info"].update({"balance_doge":balance,"tx_count":tx_count})
                    result["exists"] = balance > 0
                    usd = self._usd(balance,"dogecoin",prices)
                    result["info"]["message"] = f"Balance: {balance:.4f} DOGE{usd}  |  Tx: {tx_count}" + ("  (empty)" if not result["exists"] else "")
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
            payload = {"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":[address,"latest"]}
            resp = await self.fetch(session,"POST","https://bsc-dataseed.binance.org/",
                                    timeout=timeout,proxy=proxy,
                                    json=payload,headers={"Content-Type":"application/json"})
            if resp.status == 200:
                d = await resp.json(); resp.close()
                balance = int(d["result"],16) / 1e18
                result["info"]["balance_bnb"] = balance
                result["exists"] = balance > 0
                usd = self._usd(balance,"bnb",prices)
                result["info"]["message"] = f"Balance: {balance:.4f} BNB{usd}" + ("  (empty)" if not result["exists"] else "")
            else:
                resp.close(); result["info"]["error"] = f"HTTP {resp.status}"
        except Exception as e:
            result["info"]["error"] = str(e)
        return result
