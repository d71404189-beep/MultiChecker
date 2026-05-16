# -*- coding: utf-8 -*-
"""
GameFi Checker v1.0.59
Проверка GameFi и метавселенных активов
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List


# Известные GameFi проекты и их контракты
GAMEFI_PROJECTS = {
    # Axie Infinity
    "axie": {
        "name": "Axie Infinity",
        "tokens": {
            "AXS": "0xbb0e17ef65f82ab018d8edd776e8dd940327b28b",  # Ethereum
            "SLP": "0xcc8fa225d80b9c7d42f96e9570156c65d6caaa25",  # Ronin
        },
        "nfts": {
            "axie": "0xf5b0a3efb8e8e4c201e2a935f110eaaf3ffecb8d",  # Axie NFT
            "land": "0x8c811e3c958e190f5ec15fb376533a3398620500",  # Land NFT
        },
        "chain": "ronin"
    },
    
    # The Sandbox
    "sandbox": {
        "name": "The Sandbox",
        "tokens": {
            "SAND": "0x3845badade8e6dff049820680d1f14bd3903a5d0",  # Ethereum
        },
        "nfts": {
            "land": "0x50f5474724e0ee42d9a4e711ccfb275809fd6d4a",  # LAND
            "assets": "0xa342f5d851e866e18ff98f351f2c6637f4478db5",  # Assets
        },
        "chain": "ethereum"
    },
    
    # Decentraland
    "decentraland": {
        "name": "Decentraland",
        "tokens": {
            "MANA": "0x0f5d2fb29fb7d3cfee444a200298f468908cc942",  # Ethereum
        },
        "nfts": {
            "land": "0xf87e31492faf9a91b02ee0deaad50d51d56d5d4d",  # LAND
            "estate": "0x959e104e1a4db6317fa58f8295f586e1a978c297",  # Estate
            "wearables": "0xc04528c14c8ffd84c7c1fb6719b4a89853035cdd",  # Wearables
        },
        "chain": "ethereum"
    },
    
    # Illuvium
    "illuvium": {
        "name": "Illuvium",
        "tokens": {
            "ILV": "0x767fe9edc9e0df98e07454847909b5e959d7ca0e",  # Ethereum
        },
        "nfts": {
            "illuvials": "0x8cc8538d60901d19692f5ba22684732bc28f54a3",  # Illuvials
            "land": "0x9e0d99b864e1ac12565125c5a82b59adea5a09cd",  # Land
        },
        "chain": "ethereum"
    },
    
    # Gods Unchained
    "gods": {
        "name": "Gods Unchained",
        "tokens": {
            "GODS": "0xccc8cb5229b0ac8069c51fd58367fd1e622afd97",  # Ethereum
        },
        "nfts": {
            "cards": "0x0e3a2a1f2146d86a604adc220b4967a898d7fe07",  # Cards
        },
        "chain": "immutablex"
    },
    
    # Gala Games
    "gala": {
        "name": "Gala Games",
        "tokens": {
            "GALA": "0x15d4c048f83bd7e37d49ea4c83a07267ec4203da",  # Ethereum
        },
        "chain": "ethereum"
    },
}


class GameFiChecker:
    """Проверка GameFi активов"""
    
    def __init__(self):
        self.projects = GAMEFI_PROJECTS
    
    async def check_gamefi_portfolio(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить GameFi портфель
        
        Returns:
            {
                "total_projects": int,
                "projects": {...},
                "total_value_usd": float,
                "tokens": {...},
                "nfts": {...},
            }
        """
        
        portfolio = {
            "total_projects": 0,
            "projects": {},
            "total_value_usd": 0.0,
            "tokens": {},
            "nfts": {},
        }
        
        # Проверяем каждый проект
        for project_id, project_data in self.projects.items():
            project_result = await self._check_project(
                address,
                project_id,
                project_data,
                session,
                timeout
            )
            
            if project_result.get("has_assets"):
                portfolio["projects"][project_id] = project_result
                portfolio["total_projects"] += 1
                portfolio["total_value_usd"] += project_result.get("total_value_usd", 0)
        
        return portfolio
    
    async def _check_project(
        self,
        address: str,
        project_id: str,
        project_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверить активы в конкретном проекте"""
        
        result = {
            "name": project_data["name"],
            "has_assets": False,
            "tokens": {},
            "nfts": {},
            "total_value_usd": 0.0,
        }
        
        chain = project_data.get("chain", "ethereum")
        
        # Проверяем токены
        tokens = project_data.get("tokens", {})
        for token_symbol, token_address in tokens.items():
            balance = await self._check_token_balance(
                address,
                token_address,
                chain,
                session,
                timeout
            )
            
            if balance > 0:
                result["tokens"][token_symbol] = balance
                result["has_assets"] = True
                
                # Примерная оценка (нужны реальные цены)
                token_prices = {
                    "AXS": 7.0,
                    "SLP": 0.003,
                    "SAND": 0.5,
                    "MANA": 0.4,
                    "ILV": 50.0,
                    "GODS": 0.2,
                    "GALA": 0.02,
                }
                
                price = token_prices.get(token_symbol, 0)
                result["total_value_usd"] += balance * price
        
        # Проверяем NFT
        nfts = project_data.get("nfts", {})
        for nft_type, nft_address in nfts.items():
            nft_count = await self._check_nft_balance(
                address,
                nft_address,
                chain,
                session,
                timeout
            )
            
            if nft_count > 0:
                result["nfts"][nft_type] = nft_count
                result["has_assets"] = True
        
        return result
    
    async def _check_token_balance(
        self,
        address: str,
        token_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """Проверить баланс токена"""
        
        if chain == "ronin":
            # Ronin использует свой RPC
            rpc_url = "https://api.roninchain.com/rpc"
        elif chain == "immutablex":
            # ImmutableX использует свой API
            return 0.0  # Заглушка
        else:
            # Ethereum и совместимые
            rpc_url = "https://cloudflare-eth.com"
        
        try:
            # ERC-20 balanceOf
            # function balanceOf(address) returns (uint256)
            # selector: 0x70a08231
            
            data = "0x70a08231" + "0" * 24 + address[2:]  # Убираем 0x
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": token_address,
                        "data": data
                    },
                    "latest"
                ]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if "result" in result:
                        balance_hex = result["result"]
                        balance_wei = int(balance_hex, 16)
                        balance = balance_wei / 1e18  # Предполагаем 18 decimals
                        
                        return balance
        
        except Exception:
            pass
        
        return 0.0
    
    async def _check_nft_balance(
        self,
        address: str,
        nft_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> int:
        """Проверить количество NFT"""
        
        if chain == "ronin":
            rpc_url = "https://api.roninchain.com/rpc"
        elif chain == "immutablex":
            return 0  # Заглушка
        else:
            rpc_url = "https://cloudflare-eth.com"
        
        try:
            # ERC-721 balanceOf
            data = "0x70a08231" + "0" * 24 + address[2:]
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": nft_address,
                        "data": data
                    },
                    "latest"
                ]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if "result" in result:
                        balance_hex = result["result"]
                        balance = int(balance_hex, 16)
                        
                        return balance
        
        except Exception:
            pass
        
        return 0
    
    def format_gamefi_report(self, portfolio: Dict[str, Any]) -> str:
        """Форматировать отчет GameFi портфеля"""
        
        if portfolio["total_projects"] == 0:
            return "🎮 No GameFi assets found"
        
        lines = []
        
        lines.append("🎮 GAMEFI PORTFOLIO")
        lines.append("=" * 50)
        
        # Общая информация
        lines.append(f"🎯 Projects: {portfolio['total_projects']}")
        lines.append(f"💰 Total Value: ~${portfolio['total_value_usd']:,.2f}")
        
        # По проектам
        lines.append("\n📊 BY PROJECT:")
        
        for project_id, project_data in portfolio["projects"].items():
            name = project_data["name"]
            value = project_data["total_value_usd"]
            
            lines.append(f"\n🎮 {name} (~${value:,.2f})")
            
            # Токены
            tokens = project_data.get("tokens", {})
            if tokens:
                lines.append("  💎 Tokens:")
                for symbol, balance in tokens.items():
                    lines.append(f"    • {symbol}: {balance:.4f}")
            
            # NFT
            nfts = project_data.get("nfts", {})
            if nfts:
                lines.append("  🖼️ NFTs:")
                for nft_type, count in nfts.items():
                    lines.append(f"    • {nft_type}: {count}")
        
        return "\n".join(lines)
    
    async def check_specific_game(
        self,
        address: str,
        game: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить активы в конкретной игре
        
        Args:
            game: axie, sandbox, decentraland, illuvium, gods, gala
        """
        
        if game not in self.projects:
            return {"error": f"Unknown game: {game}"}
        
        project_data = self.projects[game]
        
        result = await self._check_project(
            address,
            game,
            project_data,
            session,
            timeout
        )
        
        return result


class MetaverseChecker:
    """Проверка активов в метавселенных"""
    
    def __init__(self):
        self.metaverses = {
            "sandbox": GAMEFI_PROJECTS["sandbox"],
            "decentraland": GAMEFI_PROJECTS["decentraland"],
        }
    
    async def check_metaverse_land(
        self,
        address: str,
        metaverse: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить владение землей в метавселенной
        
        Returns:
            {
                "metaverse": str,
                "has_land": bool,
                "land_count": int,
                "land_value_usd": float,
                "coordinates": [...],
            }
        """
        
        result = {
            "metaverse": metaverse,
            "has_land": False,
            "land_count": 0,
            "land_value_usd": 0.0,
            "coordinates": [],
        }
        
        if metaverse not in self.metaverses:
            result["error"] = f"Unknown metaverse: {metaverse}"
            return result
        
        metaverse_data = self.metaverses[metaverse]
        land_contract = metaverse_data["nfts"].get("land")
        
        if not land_contract:
            return result
        
        # Проверяем количество земли
        gamefi_checker = GameFiChecker()
        land_count = await gamefi_checker._check_nft_balance(
            address,
            land_contract,
            metaverse_data["chain"],
            session,
            timeout
        )
        
        if land_count > 0:
            result["has_land"] = True
            result["land_count"] = land_count
            
            # Примерная оценка
            land_prices = {
                "sandbox": 1500.0,  # ~$1500 за LAND
                "decentraland": 2000.0,  # ~$2000 за LAND
            }
            
            price = land_prices.get(metaverse, 0)
            result["land_value_usd"] = land_count * price
        
        return result
    
    def format_metaverse_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о метавселенной"""
        
        if "error" in result:
            return f"❌ {result['error']}"
        
        if not result["has_land"]:
            return f"🌍 {result['metaverse'].upper()}: No land owned"
        
        lines = []
        
        lines.append(f"🌍 {result['metaverse'].upper()} LAND")
        lines.append("=" * 50)
        
        lines.append(f"🏞️ Land Parcels: {result['land_count']}")
        lines.append(f"💰 Estimated Value: ~${result['land_value_usd']:,.2f}")
        
        return "\n".join(lines)
