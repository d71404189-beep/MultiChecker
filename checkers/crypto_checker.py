import asyncio
import aiohttp
import re

class CryptoChecker:
    def __init__(self):
        self.wallet_patterns = {
            "bitcoin": r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$',
            "ethereum": r'^0x[a-fA-F0-9]{40}$',
            "solana": r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
            "litecoin": r'^(L|M|[ltc])[a-km-zA-HJ-NP-Z1-9]{26,62}$',
            "tron": r'^T[a-zA-HJ-NP-Z0-9]{33}$',
            "dash": r'^X[1-9A-HJ-NP-Za-km-z]{24,33}$',
            "monero": r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$',
            "ripple": r'^r[1-9A-HJ-NP-Za-km-z]{24,34}$',
        }
        
        self.exchanges = ["binance", "bybit", "okx", "huobi", "kucoin", "gate", "mexc", "bitget"]
    
    async def check(self, data: str, timeout: int = 10) -> dict:
        result = {
            "input": data,
            "type": "unknown",
            "valid": False,
            "exists": False,
            "info": {}
        }
        
        wallet_type = self._detect_wallet(data)
        if wallet_type:
            result["type"] = "wallet"
            result["wallet_type"] = wallet_type
            
            if wallet_type == "bitcoin":
                result = await self._check_bitcoin(data, timeout)
            elif wallet_type == "ethereum":
                result = await self._check_ethereum(data, timeout)
            elif wallet_type == "solana":
                result = await self._check_solana(data, timeout)
            elif wallet_type == "tron":
                result = await self._check_tron(data, timeout)
            elif wallet_type == "litecoin":
                result = await self._check_litecoin(data, timeout)
            elif wallet_type == "dash":
                result = await self._check_dash(data, timeout)
            elif wallet_type == "monero":
                result = await self._check_monero(data, timeout)
            elif wallet_type == "ripple":
                result = await self._check_ripple(data, timeout)
        else:
            exchange = self._detect_exchange(data)
            if exchange:
                result["type"] = "exchange"
                result["exchange"] = exchange
                result = await self._check_exchange(data, exchange, timeout)
            else:
                result["info"]["error"] = "Unknown crypto format"
        
        return result
    
    def _detect_wallet(self, data: str) -> str:
        data = data.strip()
        
        for wallet_type, pattern in self.wallet_patterns.items():
            if re.match(pattern, data):
                return wallet_type
        return None
    
    def _detect_exchange(self, data: str) -> str:
        data = data.lower()
        
        for exchange in self.exchanges:
            if exchange in data:
                return exchange
        return None
    
    async def _check_bitcoin(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "bitcoin", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://blockchain.info/q/addressbalance/{address}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        balance = await resp.text()
                        satoshi = int(balance)
                        result["info"]["balance_btc"] = satoshi / 100000000
                        result["exists"] = satoshi >= 0
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_ethereum(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "ethereum", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "1":
                            balance_wei = int(data["result"])
                            result["info"]["balance_eth"] = balance_wei / 10**18
                            result["exists"] = True
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_solana(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "solana", "valid": True, "exists": False, "info": {}}
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.mainnet-beta.solana.com"
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [address]
                }
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "result" in data:
                            lamports = data["result"]["value"]
                            result["info"]["balance_sol"] = lamports / 10**9
                            result["exists"] = True
        except Exception as e:
            result["info"]["error"] = str(e)
        
        return result
    
    async def _check_tron(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "tron", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_litecoin(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "litecoin", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_dash(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "dash", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_monero(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "monero", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_ripple(self, address: str, timeout: int) -> dict:
        result = {"input": address, "type": "wallet", "wallet_type": "ripple", "valid": True, "exists": False, "info": {}}
        return result
    
    async def _check_exchange(self, data: str, exchange: str, timeout: int) -> dict:
        result = {"input": data, "type": "exchange", "exchange": exchange, "valid": True, "exists": False, "info": {}}
        
        if exchange == "binance":
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.binance.com/api/v3/account?address={data}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                        result["info"]["status"] = resp.status
            except Exception as e:
                result["info"]["error"] = str(e)
        
        return result
