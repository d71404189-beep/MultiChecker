# -*- coding: utf-8 -*-
"""
NFT Valuation v1.0.58
Проверка и оценка NFT портфеля
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional


# Известные коллекции с floor price (примерные данные)
KNOWN_COLLECTIONS = {
    # Ethereum
    "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d": {
        "name": "Bored Ape Yacht Club",
        "symbol": "BAYC",
        "floor_price_eth": 30.0,
        "chain": "ethereum"
    },
    "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb": {
        "name": "CryptoPunks",
        "symbol": "PUNK",
        "floor_price_eth": 45.0,
        "chain": "ethereum"
    },
    "0xed5af388653567af2f388e6224dc7c4b3241c544": {
        "name": "Azuki",
        "symbol": "AZUKI",
        "floor_price_eth": 10.0,
        "chain": "ethereum"
    },
    "0x60e4d786628fea6478f785a6d7e704777c86a7c6": {
        "name": "Mutant Ape Yacht Club",
        "symbol": "MAYC",
        "floor_price_eth": 5.0,
        "chain": "ethereum"
    },
    "0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b": {
        "name": "CloneX",
        "symbol": "CLONEX",
        "floor_price_eth": 2.0,
        "chain": "ethereum"
    },
    "0x8a90cab2b38dba80c64b7734e58ee1db38b8992e": {
        "name": "Doodles",
        "symbol": "DOODLE",
        "floor_price_eth": 3.0,
        "chain": "ethereum"
    },
    "0x23581767a106ae21c074b2276d25e5c3e136a68b": {
        "name": "Moonbirds",
        "symbol": "MOONBIRD",
        "floor_price_eth": 2.5,
        "chain": "ethereum"
    },
}


class NFTValuation:
    """Оценка NFT портфеля"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 600  # 10 минут
        self.eth_price = 2500  # Примерная цена ETH
    
    async def check_nft_portfolio(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить NFT портфель
        
        Returns:
            {
                "total_nfts": int,
                "collections": [...],
                "estimated_value_eth": float,
                "estimated_value_usd": float,
                "top_nfts": [...],
                "by_marketplace": {...},
            }
        """
        
        portfolio = {
            "total_nfts": 0,
            "collections": [],
            "estimated_value_eth": 0.0,
            "estimated_value_usd": 0.0,
            "top_nfts": [],
            "by_marketplace": {},
        }
        
        try:
            if chain in ["ethereum", "polygon", "arbitrum", "optimism", "base"]:
                portfolio = await self._check_evm_nfts(address, chain, session, timeout)
            elif chain == "solana":
                portfolio = await self._check_solana_nfts(address, session, timeout)
        
        except Exception as e:
            portfolio["error"] = str(e)
        
        return portfolio
    
    async def _check_evm_nfts(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка NFT на EVM-совместимых сетях"""
        
        portfolio = {
            "total_nfts": 0,
            "collections": [],
            "estimated_value_eth": 0.0,
            "estimated_value_usd": 0.0,
            "top_nfts": [],
        }
        
        # API endpoints
        api_urls = {
            "ethereum": "https://api.etherscan.io/api",
            "polygon": "https://api.polygonscan.com/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api",
            "base": "https://api.basescan.org/api",
        }
        
        api_url = api_urls.get(chain, api_urls["ethereum"])
        
        try:
            # Получаем ERC-721 токены
            url = f"{api_url}?module=account&action=tokennfttx&address={address}&page=1&offset=100&sort=desc"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("status") == "1" and data.get("result"):
                        nft_txs = data["result"]
                        
                        # Группируем по коллекциям
                        collections_map = {}
                        
                        for tx in nft_txs:
                            # Только входящие NFT
                            if tx.get("to", "").lower() != address.lower():
                                continue
                            
                            contract_address = tx.get("contractAddress", "").lower()
                            token_id = tx.get("tokenID", "")
                            token_name = tx.get("tokenName", "Unknown")
                            token_symbol = tx.get("tokenSymbol", "")
                            
                            if contract_address not in collections_map:
                                collections_map[contract_address] = {
                                    "contract": contract_address,
                                    "name": token_name,
                                    "symbol": token_symbol,
                                    "count": 0,
                                    "token_ids": [],
                                    "floor_price_eth": 0.0,
                                    "estimated_value_eth": 0.0,
                                }
                            
                            collections_map[contract_address]["count"] += 1
                            collections_map[contract_address]["token_ids"].append(token_id)
                        
                        # Оцениваем коллекции
                        for contract, collection_data in collections_map.items():
                            # Проверяем известные коллекции
                            if contract in KNOWN_COLLECTIONS:
                                known = KNOWN_COLLECTIONS[contract]
                                collection_data["name"] = known["name"]
                                collection_data["symbol"] = known["symbol"]
                                collection_data["floor_price_eth"] = known["floor_price_eth"]
                                collection_data["estimated_value_eth"] = known["floor_price_eth"] * collection_data["count"]
                                collection_data["is_known"] = True
                            else:
                                # Неизвестная коллекция - пытаемся получить floor price
                                floor_price = await self._get_floor_price(contract, chain, session, timeout)
                                collection_data["floor_price_eth"] = floor_price
                                collection_data["estimated_value_eth"] = floor_price * collection_data["count"]
                                collection_data["is_known"] = False
                            
                            portfolio["collections"].append(collection_data)
                            portfolio["total_nfts"] += collection_data["count"]
                            portfolio["estimated_value_eth"] += collection_data["estimated_value_eth"]
                        
                        # Сортируем коллекции по ценности
                        portfolio["collections"].sort(key=lambda x: x["estimated_value_eth"], reverse=True)
                        
                        # Топ-5 NFT
                        portfolio["top_nfts"] = portfolio["collections"][:5]
                        
                        # Конвертируем в USD
                        portfolio["estimated_value_usd"] = portfolio["estimated_value_eth"] * self.eth_price
        
        except Exception as e:
            portfolio["error"] = str(e)
        
        return portfolio
    
    async def _check_solana_nfts(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка NFT на Solana"""
        
        portfolio = {
            "total_nfts": 0,
            "collections": [],
            "estimated_value_sol": 0.0,
            "estimated_value_usd": 0.0,
            "top_nfts": [],
        }
        
        try:
            # Solana RPC для получения токенов
            rpc_url = "https://api.mainnet-beta.solana.com"
            
            # Получаем токены аккаунта
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
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
                        token_accounts = data["result"].get("value", [])
                        
                        # Фильтруем NFT (amount = 1, decimals = 0)
                        nft_count = 0
                        
                        for account in token_accounts:
                            token_amount = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {}).get("tokenAmount", {})
                            
                            amount = int(token_amount.get("amount", 0))
                            decimals = int(token_amount.get("decimals", 0))
                            
                            # NFT обычно имеют amount=1 и decimals=0
                            if amount == 1 and decimals == 0:
                                nft_count += 1
                        
                        portfolio["total_nfts"] = nft_count
                        
                        # Примерная оценка (без детальной информации о коллекциях)
                        # Средняя цена Solana NFT ~0.5 SOL
                        avg_price_sol = 0.5
                        portfolio["estimated_value_sol"] = nft_count * avg_price_sol
                        
                        sol_price = 100
                        portfolio["estimated_value_usd"] = portfolio["estimated_value_sol"] * sol_price
        
        except Exception as e:
            portfolio["error"] = str(e)
        
        return portfolio
    
    async def _get_floor_price(
        self,
        contract_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """
        Получить floor price коллекции
        
        Использует OpenSea API (или другие маркетплейсы)
        """
        
        # Проверяем кэш
        cache_key = f"{chain}:{contract_address}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        floor_price = 0.0
        
        try:
            # OpenSea API v2
            opensea_url = f"https://api.opensea.io/api/v2/collections/{contract_address}/stats"
            
            headers = {
                "Accept": "application/json",
                "X-API-KEY": ""  # Нужен API ключ для production
            }
            
            async with session.get(
                opensea_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Получаем floor price
                    stats = data.get("stats", {})
                    floor_price = float(stats.get("floor_price", 0.0))
        
        except Exception:
            # Если не удалось получить - возвращаем 0
            pass
        
        # Кэшируем
        self.cache[cache_key] = (floor_price, time.time())
        
        return floor_price
    
    def format_nft_report(self, portfolio: Dict[str, Any]) -> str:
        """Форматировать отчет о NFT портфеле"""
        
        if "error" in portfolio:
            return f"❌ NFT check error: {portfolio['error']}"
        
        if portfolio["total_nfts"] == 0:
            return "📦 No NFTs found"
        
        report_lines = []
        
        report_lines.append("🖼️ NFT PORTFOLIO")
        report_lines.append("=" * 50)
        
        # Общая информация
        report_lines.append(f"📊 Total NFTs: {portfolio['total_nfts']}")
        report_lines.append(f"💎 Collections: {len(portfolio.get('collections', []))}")
        
        # Оценка
        if "estimated_value_eth" in portfolio:
            eth_value = portfolio["estimated_value_eth"]
            usd_value = portfolio["estimated_value_usd"]
            report_lines.append(f"💰 Estimated Value: {eth_value:.2f} ETH (~${usd_value:,.2f})")
        elif "estimated_value_sol" in portfolio:
            sol_value = portfolio["estimated_value_sol"]
            usd_value = portfolio["estimated_value_usd"]
            report_lines.append(f"💰 Estimated Value: {sol_value:.2f} SOL (~${usd_value:,.2f})")
        
        # Топ коллекции
        top_nfts = portfolio.get("top_nfts", [])
        if top_nfts:
            report_lines.append("\n🏆 TOP COLLECTIONS:")
            for i, collection in enumerate(top_nfts, 1):
                name = collection.get("name", "Unknown")
                count = collection.get("count", 0)
                floor = collection.get("floor_price_eth", 0)
                value = collection.get("estimated_value_eth", 0)
                is_known = collection.get("is_known", False)
                
                known_badge = "⭐" if is_known else ""
                report_lines.append(f"  {i}. {known_badge} {name}")
                report_lines.append(f"     Count: {count} | Floor: {floor:.2f} ETH | Value: ~{value:.2f} ETH")
        
        return "\n".join(report_lines)
    
    async def check_nft_rarity(
        self,
        contract_address: str,
        token_id: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить редкость конкретного NFT
        
        Returns:
            {
                "token_id": str,
                "rarity_rank": int,
                "rarity_score": float,
                "traits": [...],
                "estimated_value_eth": float,
            }
        """
        
        rarity_data = {
            "token_id": token_id,
            "rarity_rank": 0,
            "rarity_score": 0.0,
            "traits": [],
            "estimated_value_eth": 0.0,
        }
        
        try:
            # Можно использовать Rarity Sniper API или другие сервисы
            # Здесь заглушка
            pass
        
        except Exception as e:
            rarity_data["error"] = str(e)
        
        return rarity_data
