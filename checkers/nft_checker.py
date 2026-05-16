# -*- coding: utf-8 -*-
"""
NFT Checker & Valuation v1.0.65
Проверка NFT и оценка стоимости
"""

import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class NFTChecker:
    """Проверка NFT и оценка стоимости"""
    
    # Популярные коллекции
    POPULAR_COLLECTIONS = {
        "ethereum": [
            {"name": "Bored Ape Yacht Club", "contract": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d"},
            {"name": "CryptoPunks", "contract": "0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb"},
            {"name": "Mutant Ape Yacht Club", "contract": "0x60e4d786628fea6478f785a6d7e704777c86a7c6"},
            {"name": "Azuki", "contract": "0xed5af388653567af2f388e6224dc7c4b3241c544"},
            {"name": "Pudgy Penguins", "contract": "0xbd3531da5cf5857e7cfaa92426877b022e612cf8"},
            {"name": "Doodles", "contract": "0x8a90cab2b38dba80c64b7734e58ee1db38b8992e"},
            {"name": "CloneX", "contract": "0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b"},
            {"name": "Moonbirds", "contract": "0x23581767a106ae21c074b2276d25e5c3e136a68b"},
        ],
        "polygon": [
            {"name": "Polygon Apes", "contract": "0x..."},
        ],
        "solana": [
            {"name": "DeGods", "mint": "..."},
            {"name": "y00ts", "mint": "..."},
        ]
    }
    
    def __init__(self):
        self.opensea_api_key = None  # Опционально
        self.cache = {}
        self.cache_ttl = 300  # 5 минут
    
    async def check_nfts(
        self,
        address: str,
        chain: str = "ethereum",
        session: Optional[aiohttp.ClientSession] = None
    ) -> Dict[str, Any]:
        """
        Проверить NFT на адресе
        
        Args:
            address: Адрес кошелька
            chain: Сеть (ethereum, polygon, solana, base)
            session: aiohttp сессия
        
        Returns:
            Словарь с NFT и их оценкой
        """
        
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            if chain == "solana":
                result = await self._check_solana_nfts(address, session)
            else:
                result = await self._check_evm_nfts(address, chain, session)
            
            return result
        
        finally:
            if own_session:
                await session.close()
    
    async def _check_evm_nfts(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Проверить NFT на EVM сетях"""
        
        result = {
            "address": address,
            "chain": chain,
            "nfts": [],
            "total_nfts": 0,
            "total_value_usd": 0.0,
            "collections": {},
        }
        
        # Используем Alchemy API (бесплатный tier)
        alchemy_keys = {
            "ethereum": "demo",  # Замените на свой ключ
            "polygon": "demo",
            "base": "demo",
        }
        
        alchemy_key = alchemy_keys.get(chain, "demo")
        
        # Alchemy NFT API
        url = f"https://{chain}-mainnet.g.alchemy.com/nft/v2/{alchemy_key}/getNFTs"
        params = {"owner": address, "withMetadata": "true"}
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    owned_nfts = data.get("ownedNfts", [])
                    result["total_nfts"] = len(owned_nfts)
                    
                    # Обрабатываем каждый NFT
                    for nft in owned_nfts:
                        contract = nft.get("contract", {}).get("address", "").lower()
                        token_id = nft.get("id", {}).get("tokenId", "")
                        
                        # Получаем метаданные
                        metadata = nft.get("metadata", {})
                        name = metadata.get("name", "Unknown")
                        image = metadata.get("image", "")
                        
                        # Получаем floor price
                        floor_price = await self._get_floor_price(contract, chain, session)
                        
                        nft_info = {
                            "name": name,
                            "token_id": token_id,
                            "contract": contract,
                            "image": image,
                            "floor_price_eth": floor_price,
                            "floor_price_usd": floor_price * 2500 if floor_price else 0,  # ETH price
                            "collection": self._identify_collection(contract, chain),
                        }
                        
                        result["nfts"].append(nft_info)
                        result["total_value_usd"] += nft_info["floor_price_usd"]
                        
                        # Группируем по коллекциям
                        collection_name = nft_info["collection"]
                        if collection_name not in result["collections"]:
                            result["collections"][collection_name] = {
                                "count": 0,
                                "total_value": 0.0,
                                "nfts": []
                            }
                        
                        result["collections"][collection_name]["count"] += 1
                        result["collections"][collection_name]["total_value"] += nft_info["floor_price_usd"]
                        result["collections"][collection_name]["nfts"].append(nft_info)
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_solana_nfts(
        self,
        address: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Проверить NFT на Solana"""
        
        result = {
            "address": address,
            "chain": "solana",
            "nfts": [],
            "total_nfts": 0,
            "total_value_usd": 0.0,
            "collections": {},
        }
        
        # Используем Helius API (бесплатный tier)
        url = f"https://api.helius.xyz/v0/addresses/{address}/nfts"
        params = {"api-key": "demo"}  # Замените на свой ключ
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    result["total_nfts"] = len(data)
                    
                    for nft in data:
                        name = nft.get("name", "Unknown")
                        mint = nft.get("mint", "")
                        image = nft.get("image", "")
                        collection = nft.get("collection", {}).get("name", "Unknown")
                        
                        # Получаем floor price (примерно)
                        floor_price_sol = 0.0  # Нужен Magic Eden API
                        
                        nft_info = {
                            "name": name,
                            "mint": mint,
                            "image": image,
                            "floor_price_sol": floor_price_sol,
                            "floor_price_usd": floor_price_sol * 100,  # SOL price
                            "collection": collection,
                        }
                        
                        result["nfts"].append(nft_info)
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _get_floor_price(
        self,
        contract: str,
        chain: str,
        session: aiohttp.ClientSession
    ) -> float:
        """Получить floor price коллекции"""
        
        # Кэш
        cache_key = f"{chain}:{contract}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.now().timestamp() - timestamp) < self.cache_ttl:
                return cached_data
        
        # OpenSea API
        try:
            url = f"https://api.opensea.io/api/v1/collection/{contract}/stats"
            headers = {}
            if self.opensea_api_key:
                headers["X-API-KEY"] = self.opensea_api_key
            
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    floor_price = data.get("stats", {}).get("floor_price", 0.0)
                    
                    # Кэшируем
                    self.cache[cache_key] = (floor_price, datetime.now().timestamp())
                    
                    return floor_price
        
        except Exception:
            pass
        
        return 0.0
    
    def _identify_collection(self, contract: str, chain: str) -> str:
        """Определить название коллекции"""
        
        collections = self.POPULAR_COLLECTIONS.get(chain, [])
        
        for collection in collections:
            if collection["contract"].lower() == contract.lower():
                return collection["name"]
        
        return "Unknown Collection"
    
    def format_nft_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о NFT"""
        
        lines = []
        
        lines.append("=" * 60)
        lines.append("NFT REPORT")
        lines.append("=" * 60)
        
        lines.append(f"\nAddress: {result['address']}")
        lines.append(f"Chain: {result['chain'].upper()}")
        lines.append(f"Total NFTs: {result['total_nfts']}")
        lines.append(f"Total Value: ${result['total_value_usd']:,.2f}")
        
        # По коллекциям
        if result['collections']:
            lines.append(f"\n{'=' * 60}")
            lines.append("BY COLLECTIONS:")
            lines.append("=" * 60)
            
            for collection_name, data in sorted(
                result['collections'].items(),
                key=lambda x: x[1]['total_value'],
                reverse=True
            ):
                lines.append(f"\n{collection_name}:")
                lines.append(f"  Count: {data['count']}")
                lines.append(f"  Total Value: ${data['total_value']:,.2f}")
        
        # Топ NFT
        if result['nfts']:
            lines.append(f"\n{'=' * 60}")
            lines.append("TOP NFTs:")
            lines.append("=" * 60)
            
            sorted_nfts = sorted(
                result['nfts'],
                key=lambda x: x.get('floor_price_usd', 0),
                reverse=True
            )
            
            for i, nft in enumerate(sorted_nfts[:10], 1):
                lines.append(f"\n{i}. {nft['name']}")
                lines.append(f"   Collection: {nft['collection']}")
                lines.append(f"   Floor Price: ${nft['floor_price_usd']:,.2f}")
                if 'token_id' in nft:
                    lines.append(f"   Token ID: {nft['token_id']}")
        
        return "\n".join(lines)
    
    def export_nfts_to_json(self, result: Dict[str, Any], output_file: str) -> bool:
        """Экспортировать NFT в JSON"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting NFTs: {e}")
            return False
