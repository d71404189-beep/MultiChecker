# -*- coding: utf-8 -*-
"""
NFT Checker - Проверка NFT коллекций и их стоимости
Поддержка: Ethereum, Polygon, Solana
API: OpenSea, Blur, Magic Eden
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional


class NFTChecker:
    """Проверка NFT на кошельках"""
    
    def __init__(self):
        self.opensea_api = "https://api.opensea.io/api/v2"
        self.blur_api = "https://api.blur.io/v1"
        self.magiceden_api = "https://api-mainnet.magiceden.dev/v2"
        
        # Популярные коллекции для быстрой проверки
        self.popular_collections = {
            "ethereum": [
                "boredapeyachtclub",
                "mutant-ape-yacht-club", 
                "azuki",
                "clonex",
                "doodles-official",
                "pudgypenguins",
                "proof-moonbirds",
                "otherdeed",
                "cryptopunks",
                "meebits"
            ],
            "polygon": [
                "y00ts",
                "degods"
            ],
            "solana": [
                "okay_bears",
                "degods",
                "y00ts",
                "mad_lads"
            ]
        }
    
    async def check_nfts(self, address: str, chain: str = "ethereum", 
                        session: aiohttp.ClientSession = None) -> Dict:
        """
        Проверить NFT на адресе
        
        Args:
            address: адрес кошелька
            chain: блокчейн (ethereum, polygon, solana)
            session: aiohttp сессия
            
        Returns:
            dict с информацией о NFT
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            if chain in ["ethereum", "polygon"]:
                result = await self._check_evm_nfts(address, chain, session)
            elif chain == "solana":
                result = await self._check_solana_nfts(address, session)
            else:
                result = {"error": f"Unsupported chain: {chain}"}
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            if own_session:
                await session.close()
    
    async def _check_evm_nfts(self, address: str, chain: str, 
                              session: aiohttp.ClientSession) -> Dict:
        """Проверка NFT на EVM сетях (Ethereum, Polygon)"""
        
        result = {
            "address": address,
            "chain": chain,
            "total_nfts": 0,
            "total_value_eth": 0.0,
            "total_value_usd": 0.0,
            "collections": [],
            "valuable_nfts": []  # NFT дороже $100
        }
        
        try:
            # OpenSea API v2
            url = f"{self.opensea_api}/chain/{chain}/account/{address}/nfts"
            headers = {
                "Accept": "application/json",
                "X-API-KEY": ""  # Можно добавить API ключ для больших лимитов
            }
            
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    nfts = data.get("nfts", [])
                    
                    result["total_nfts"] = len(nfts)
                    
                    # Группируем по коллекциям
                    collections_map = {}
                    
                    for nft in nfts:
                        collection_slug = nft.get("collection", "unknown")
                        
                        if collection_slug not in collections_map:
                            collections_map[collection_slug] = {
                                "name": nft.get("name", "Unknown"),
                                "count": 0,
                                "floor_price_eth": 0.0,
                                "total_value_eth": 0.0
                            }
                        
                        collections_map[collection_slug]["count"] += 1
                        
                        # Получаем floor price коллекции
                        floor_price = await self._get_collection_floor(
                            collection_slug, chain, session
                        )
                        
                        if floor_price > 0:
                            collections_map[collection_slug]["floor_price_eth"] = floor_price
                            collections_map[collection_slug]["total_value_eth"] += floor_price
                            result["total_value_eth"] += floor_price
                            
                            # Добавляем в ценные NFT если > $100
                            if floor_price * 2500 > 100:  # Примерная цена ETH
                                result["valuable_nfts"].append({
                                    "name": nft.get("name", "Unknown"),
                                    "collection": collection_slug,
                                    "floor_price_eth": floor_price,
                                    "estimated_usd": floor_price * 2500
                                })
                    
                    # Конвертируем в список
                    result["collections"] = [
                        {
                            "slug": slug,
                            **data
                        }
                        for slug, data in collections_map.items()
                    ]
                    
                    # Сортируем по стоимости
                    result["collections"].sort(
                        key=lambda x: x["total_value_eth"], 
                        reverse=True
                    )
                    result["valuable_nfts"].sort(
                        key=lambda x: x["floor_price_eth"],
                        reverse=True
                    )
                    
                    # Конвертируем в USD (примерная цена ETH)
                    eth_price = await self._get_eth_price(session)
                    result["total_value_usd"] = result["total_value_eth"] * eth_price
                    
                elif resp.status == 429:
                    result["error"] = "Rate limit exceeded. Try again later."
                else:
                    result["error"] = f"API error: {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _check_solana_nfts(self, address: str, 
                                 session: aiohttp.ClientSession) -> Dict:
        """Проверка NFT на Solana через Magic Eden"""
        
        result = {
            "address": address,
            "chain": "solana",
            "total_nfts": 0,
            "total_value_sol": 0.0,
            "total_value_usd": 0.0,
            "collections": [],
            "valuable_nfts": []
        }
        
        try:
            # Magic Eden API
            url = f"{self.magiceden_api}/wallets/{address}/tokens"
            
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    nfts = await resp.json()
                    result["total_nfts"] = len(nfts)
                    
                    # Группируем по коллекциям
                    collections_map = {}
                    
                    for nft in nfts:
                        collection = nft.get("collection", "unknown")
                        
                        if collection not in collections_map:
                            collections_map[collection] = {
                                "name": nft.get("collectionName", "Unknown"),
                                "count": 0,
                                "floor_price_sol": 0.0,
                                "total_value_sol": 0.0
                            }
                        
                        collections_map[collection]["count"] += 1
                    
                    # Получаем floor price для каждой коллекции
                    for collection_slug, data in collections_map.items():
                        floor_price = await self._get_solana_collection_floor(
                            collection_slug, session
                        )
                        
                        if floor_price > 0:
                            data["floor_price_sol"] = floor_price
                            data["total_value_sol"] = floor_price * data["count"]
                            result["total_value_sol"] += data["total_value_sol"]
                    
                    result["collections"] = [
                        {"slug": slug, **data}
                        for slug, data in collections_map.items()
                    ]
                    
                    # Конвертируем в USD
                    sol_price = await self._get_sol_price(session)
                    result["total_value_usd"] = result["total_value_sol"] * sol_price
                    
                elif resp.status == 429:
                    result["error"] = "Rate limit exceeded"
                else:
                    result["error"] = f"API error: {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _get_collection_floor(self, collection_slug: str, chain: str,
                                    session: aiohttp.ClientSession) -> float:
        """Получить floor price коллекции на OpenSea"""
        try:
            url = f"{self.opensea_api}/collections/{collection_slug}/stats"
            
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    floor_price = data.get("total", {}).get("floor_price", 0)
                    return float(floor_price) if floor_price else 0.0
        except Exception:
            pass
        
        return 0.0
    
    async def _get_solana_collection_floor(self, collection_slug: str,
                                          session: aiohttp.ClientSession) -> float:
        """Получить floor price коллекции на Magic Eden"""
        try:
            url = f"{self.magiceden_api}/collections/{collection_slug}/stats"
            
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    floor_price = data.get("floorPrice", 0)
                    return float(floor_price) / 1e9 if floor_price else 0.0  # Lamports to SOL
        except Exception:
            pass
        
        return 0.0
    
    async def _get_eth_price(self, session: aiohttp.ClientSession) -> float:
        """Получить текущую цену ETH"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("ethereum", {}).get("usd", 2500)
        except Exception:
            pass
        
        return 2500  # Fallback цена
    
    async def _get_sol_price(self, session: aiohttp.ClientSession) -> float:
        """Получить текущую цену SOL"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("solana", {}).get("usd", 100)
        except Exception:
            pass
        
        return 100  # Fallback цена
    
    def format_nft_result(self, result: Dict) -> str:
        """Форматировать результат проверки NFT для вывода"""
        
        if "error" in result:
            return f"❌ Ошибка: {result['error']}"
        
        if result["total_nfts"] == 0:
            return "📭 NFT не найдено"
        
        output = []
        output.append(f"🖼️ NFT НАЙДЕНО: {result['total_nfts']} шт")
        output.append(f"💰 Общая стоимость: ~${result['total_value_usd']:,.2f}")
        
        if result["valuable_nfts"]:
            output.append(f"\n💎 ЦЕННЫЕ NFT (>{len(result['valuable_nfts'])} шт):")
            for nft in result["valuable_nfts"][:5]:  # Топ-5
                output.append(
                    f"  • {nft['name']} - ${nft['estimated_usd']:,.2f}"
                )
        
        if result["collections"]:
            output.append(f"\n📚 КОЛЛЕКЦИИ:")
            for col in result["collections"][:5]:  # Топ-5
                output.append(
                    f"  • {col['name']}: {col['count']} NFT "
                    f"(~${col['total_value_eth'] * 2500:,.2f})"
                )
        
        return "\n".join(output)
