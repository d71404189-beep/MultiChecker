# -*- coding: utf-8 -*-
"""
New Chains Support v1.0.58
Поддержка новых блокчейнов: Arbitrum, Optimism, zkSync, Sui, Aptos
"""

import asyncio
import aiohttp
import re
from typing import Dict, Any, Optional


# Паттерны для определения адресов
CHAIN_PATTERNS = {
    "arbitrum": re.compile(r'^0x[a-fA-F0-9]{40}$'),  # EVM-совместимый
    "optimism": re.compile(r'^0x[a-fA-F0-9]{40}$'),  # EVM-совместимый
    "zksync": re.compile(r'^0x[a-fA-F0-9]{40}$'),    # EVM-совместимый
    "sui": re.compile(r'^0x[a-fA-F0-9]{64}$'),       # 64 hex символа
    "aptos": re.compile(r'^0x[a-fA-F0-9]{64}$'),     # 64 hex символа
}

# RPC endpoints
RPC_ENDPOINTS = {
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
    "zksync": "https://mainnet.era.zksync.io",
    "sui": "https://fullnode.mainnet.sui.io:443",
    "aptos": "https://fullnode.mainnet.aptoslabs.com/v1",
}

# Block explorers
EXPLORERS = {
    "arbitrum": "https://api.arbiscan.io/api",
    "optimism": "https://api-optimistic.etherscan.io/api",
    "zksync": "https://block-explorer-api.mainnet.zksync.io/api",
}


async def _get_live_price(symbol: str, fallback: float) -> float:
    """v1.0.92: реальная цена через PriceService вместо хардкода (fallback при недоступности API)."""
    try:
        from checkers.price_service import global_price_service
        price = await global_price_service.get_price(symbol)
        if price and price > 0:
            return float(price)
    except Exception:
        pass
    return fallback


class NewChainsChecker:
    """Проверка кошельков в новых блокчейнах"""
    
    def __init__(self):
        self.supported_chains = ["arbitrum", "optimism", "zksync", "sui", "aptos"]
    
    def detect_chain(self, address: str) -> Optional[str]:
        """
        Определить блокчейн по адресу
        
        Returns:
            Название блокчейна или None
        """
        # EVM-совместимые (Arbitrum, Optimism, zkSync) - одинаковый формат
        if CHAIN_PATTERNS["arbitrum"].match(address):
            # Невозможно точно определить без контекста
            # Возвращаем список возможных
            return "evm_compatible"  # Нужна дополнительная проверка
        
        # Sui и Aptos - 64 символа
        if CHAIN_PATTERNS["sui"].match(address):
            return "sui_or_aptos"  # Нужна дополнительная проверка
        
        return None
    
    async def check_arbitrum(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """Проверка Arbitrum кошелька"""
        
        result = {
            "chain": "arbitrum",
            "address": address,
            "exists": False,
            "balance": 0.0,
            "balance_usd": 0.0,
            "tokens": {},
            "nfts": [],
            "message": "",
        }
        
        try:
            # Проверяем баланс через RPC
            rpc_url = RPC_ENDPOINTS["arbitrum"]
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        balance_wei = int(data["result"], 16)
                        balance_eth = balance_wei / 1e18
                        
                        result["balance"] = balance_eth
                        result["exists"] = balance_eth > 0
                        
                        eth_price = await _get_live_price("ETH", 2500)
                        result["balance_usd"] = balance_eth * eth_price
                        
                        result["message"] = f"Balance: {balance_eth:.6f} ETH (~${result['balance_usd']:.2f})"
                        
                        if not result["exists"]:
                            result["message"] += " (empty)"
            
            # Проверяем токены через Arbiscan API (если есть)
            tokens = await self._check_evm_tokens(address, "arbitrum", session, timeout)
            if tokens:
                result["tokens"] = tokens
                result["exists"] = True
                result["message"] += f" | Tokens: {len(tokens)}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_optimism(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """Проверка Optimism кошелька"""
        
        result = {
            "chain": "optimism",
            "address": address,
            "exists": False,
            "balance": 0.0,
            "balance_usd": 0.0,
            "tokens": {},
            "message": "",
        }
        
        try:
            # Проверяем баланс через RPC
            rpc_url = RPC_ENDPOINTS["optimism"]
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        balance_wei = int(data["result"], 16)
                        balance_eth = balance_wei / 1e18
                        
                        result["balance"] = balance_eth
                        result["exists"] = balance_eth > 0
                        
                        eth_price = await _get_live_price("ETH", 2500)
                        result["balance_usd"] = balance_eth * eth_price
                        
                        result["message"] = f"Balance: {balance_eth:.6f} ETH (~${result['balance_usd']:.2f})"
                        
                        if not result["exists"]:
                            result["message"] += " (empty)"
            
            # Проверяем токены
            tokens = await self._check_evm_tokens(address, "optimism", session, timeout)
            if tokens:
                result["tokens"] = tokens
                result["exists"] = True
                result["message"] += f" | Tokens: {len(tokens)}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_zksync(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """Проверка zkSync Era кошелька"""
        
        result = {
            "chain": "zksync",
            "address": address,
            "exists": False,
            "balance": 0.0,
            "balance_usd": 0.0,
            "tokens": {},
            "message": "",
        }
        
        try:
            # Проверяем баланс через RPC
            rpc_url = RPC_ENDPOINTS["zksync"]
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        balance_wei = int(data["result"], 16)
                        balance_eth = balance_wei / 1e18
                        
                        result["balance"] = balance_eth
                        result["exists"] = balance_eth > 0
                        
                        eth_price = await _get_live_price("ETH", 2500)
                        result["balance_usd"] = balance_eth * eth_price
                        
                        result["message"] = f"Balance: {balance_eth:.6f} ETH (~${result['balance_usd']:.2f})"
                        
                        if not result["exists"]:
                            result["message"] += " (empty)"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_sui(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """Проверка Sui кошелька"""
        
        result = {
            "chain": "sui",
            "address": address,
            "exists": False,
            "balance": 0.0,
            "balance_usd": 0.0,
            "objects": [],
            "message": "",
        }
        
        try:
            # Sui RPC API
            rpc_url = RPC_ENDPOINTS["sui"]
            
            # Получаем баланс SUI
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "suix_getBalance",
                "params": [address]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        balance_mist = int(data["result"].get("totalBalance", 0))
                        balance_sui = balance_mist / 1e9  # SUI имеет 9 decimals
                        
                        result["balance"] = balance_sui
                        result["exists"] = balance_sui > 0
                        
                        sui_price = await _get_live_price("SUI", 1.5)
                        result["balance_usd"] = balance_sui * sui_price
                        
                        result["message"] = f"Balance: {balance_sui:.6f} SUI (~${result['balance_usd']:.2f})"
                        
                        if not result["exists"]:
                            result["message"] += " (empty)"
            
            # Получаем объекты (NFT, токены)
            payload_objects = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "suix_getOwnedObjects",
                "params": [
                    address,
                    {
                        "filter": None,
                        "options": {
                            "showType": True,
                            "showContent": False
                        }
                    }
                ]
            }
            
            async with session.post(
                rpc_url,
                json=payload_objects,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        objects = data["result"].get("data", [])
                        result["objects"] = objects
                        
                        if objects:
                            result["exists"] = True
                            result["message"] += f" | Objects: {len(objects)}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_aptos(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """Проверка Aptos кошелька"""
        
        result = {
            "chain": "aptos",
            "address": address,
            "exists": False,
            "balance": 0.0,
            "balance_usd": 0.0,
            "resources": [],
            "message": "",
        }
        
        try:
            # Aptos REST API
            api_url = RPC_ENDPOINTS["aptos"]
            
            # Получаем информацию об аккаунте
            account_url = f"{api_url}/accounts/{address}"
            
            async with session.get(
                account_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    account_data = await resp.json()
                    
                    # Аккаунт существует
                    result["exists"] = True
                    
                    # Получаем ресурсы (включая баланс APT)
                    resources_url = f"{api_url}/accounts/{address}/resources"
                    
                    async with session.get(
                        resources_url,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        headers={"Content-Type": "application/json"}
                    ) as resp_res:
                        if resp_res.status == 200:
                            resources = await resp_res.json()
                            
                            # Ищем баланс APT
                            for resource in resources:
                                if resource.get("type") == "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>":
                                    coin_data = resource.get("data", {}).get("coin", {})
                                    balance_octas = int(coin_data.get("value", 0))
                                    balance_apt = balance_octas / 1e8  # APT имеет 8 decimals
                                    
                                    result["balance"] = balance_apt
                                    
                                    apt_price = await _get_live_price("APT", 8.0)
                                    result["balance_usd"] = balance_apt * apt_price
                                    
                                    result["message"] = f"Balance: {balance_apt:.6f} APT (~${result['balance_usd']:.2f})"
                                    
                                    if balance_apt == 0:
                                        result["message"] += " (empty)"
                                    
                                    break
                            
                            result["resources"] = len(resources)
                            if len(resources) > 1:
                                result["message"] += f" | Resources: {len(resources)}"
                
                elif resp.status == 404:
                    result["message"] = "Account not found (never used)"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_evm_tokens(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, float]:
        """Проверка ERC-20 токенов для EVM-совместимых сетей"""
        
        tokens = {}
        
        try:
            explorer_url = EXPLORERS.get(chain)
            if not explorer_url:
                return tokens
            
            # Получаем список токенов
            url = f"{explorer_url}?module=account&action=tokentx&address={address}&page=1&offset=100&sort=desc"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("status") == "1" and data.get("result"):
                        # Собираем уникальные токены
                        seen_tokens = set()
                        
                        for tx in data["result"]:
                            token_symbol = tx.get("tokenSymbol", "")
                            token_address = tx.get("contractAddress", "")
                            
                            if token_symbol and token_address not in seen_tokens:
                                seen_tokens.add(token_address)
                                # Здесь можно добавить запрос баланса конкретного токена
                                tokens[token_symbol] = 0.0  # Placeholder
        
        except Exception:
            pass
        
        return tokens
    
    async def check_all_new_chains(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить адрес во всех новых сетях
        
        Returns:
            {
                "arbitrum": {...},
                "optimism": {...},
                "zksync": {...},
                "sui": {...},
                "aptos": {...},
            }
        """
        
        results = {}
        
        # Определяем какие сети проверять
        chains_to_check = []
        
        # EVM-совместимые (0x + 40 hex)
        if CHAIN_PATTERNS["arbitrum"].match(address):
            chains_to_check.extend(["arbitrum", "optimism", "zksync"])
        
        # Sui/Aptos (0x + 64 hex)
        if CHAIN_PATTERNS["sui"].match(address):
            chains_to_check.extend(["sui", "aptos"])
        
        # Проверяем параллельно
        tasks = []
        for chain in chains_to_check:
            if chain == "arbitrum":
                tasks.append(self.check_arbitrum(address, session, timeout))
            elif chain == "optimism":
                tasks.append(self.check_optimism(address, session, timeout))
            elif chain == "zksync":
                tasks.append(self.check_zksync(address, session, timeout))
            elif chain == "sui":
                tasks.append(self.check_sui(address, session, timeout))
            elif chain == "aptos":
                tasks.append(self.check_aptos(address, session, timeout))
        
        if tasks:
            chain_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, chain in enumerate(chains_to_check):
                if isinstance(chain_results[i], Exception):
                    results[chain] = {"error": str(chain_results[i])}
                else:
                    results[chain] = chain_results[i]
        
        return results
