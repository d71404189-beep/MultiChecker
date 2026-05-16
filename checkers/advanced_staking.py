# -*- coding: utf-8 -*-
"""
Advanced Staking & Farming v1.0.60
Расширенная проверка стейкинга и yield farming
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List


# Известные DeFi протоколы
DEFI_PROTOCOLS = {
    "aave_v3": {
        "name": "Aave V3",
        "contracts": {
            "ethereum": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
            "polygon": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
            "arbitrum": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
            "optimism": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        },
        "type": "lending"
    },
    
    "compound_v3": {
        "name": "Compound V3",
        "contracts": {
            "ethereum": "0xc3d688B66703497DAA19211EEdff47f25384cdc3",
            "polygon": "0xF25212E676D1F7F89Cd72fFEe66158f541246445",
            "arbitrum": "0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA",
        },
        "type": "lending"
    },
    
    "curve": {
        "name": "Curve Finance",
        "contracts": {
            "ethereum": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # 3pool
            "polygon": "0x445FE580eF8d70FF569aB36e80c647af338db351",
            "arbitrum": "0x7f90122BF0700F9E7e1F688fe926940E8839F353",
        },
        "type": "dex"
    },
    
    "yearn": {
        "name": "Yearn Finance",
        "contracts": {
            "ethereum": "0xdA816459F1AB5631232FE5e97a05BBBb94970c95",  # yvDAI
        },
        "type": "vault"
    },
    
    "convex": {
        "name": "Convex Finance",
        "contracts": {
            "ethereum": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31",  # Booster
        },
        "type": "yield_aggregator"
    },
    
    "lido": {
        "name": "Lido",
        "contracts": {
            "ethereum": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # stETH
        },
        "type": "liquid_staking"
    },
    
    "rocket_pool": {
        "name": "Rocket Pool",
        "contracts": {
            "ethereum": "0xae78736Cd615f374D3085123A210448E74Fc6393",  # rETH
        },
        "type": "liquid_staking"
    },
}


class AdvancedStaking:
    """Расширенная проверка стейкинга и фарминга"""
    
    def __init__(self):
        self.protocols = DEFI_PROTOCOLS
    
    async def check_all_staking(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить все стейкинг позиции
        
        Returns:
            {
                "total_protocols": int,
                "protocols_with_positions": int,
                "total_staked_usd": float,
                "total_rewards_usd": float,
                "protocols": {...},
                "summary": {...}
            }
        """
        
        result = {
            "total_protocols": len(self.protocols),
            "protocols_with_positions": 0,
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "protocols": {},
            "summary": {},
        }
        
        # Проверяем каждый протокол
        tasks = []
        for protocol_id, protocol_data in self.protocols.items():
            task = self._check_protocol(address, protocol_id, protocol_data, session, timeout)
            tasks.append(task)
        
        protocol_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (protocol_id, protocol_data) in enumerate(self.protocols.items()):
            if isinstance(protocol_results[i], Exception):
                continue
            
            protocol_result = protocol_results[i]
            
            if protocol_result.get("has_positions"):
                result["protocols"][protocol_id] = protocol_result
                result["protocols_with_positions"] += 1
                result["total_staked_usd"] += protocol_result.get("total_staked_usd", 0)
                result["total_rewards_usd"] += protocol_result.get("total_rewards_usd", 0)
        
        # Сводка по типам
        result["summary"] = self._generate_summary(result["protocols"])
        
        return result
    
    async def _check_protocol(
        self,
        address: str,
        protocol_id: str,
        protocol_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверить позиции в протоколе"""
        
        result = {
            "name": protocol_data["name"],
            "type": protocol_data["type"],
            "has_positions": False,
            "positions": {},
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "apy": 0.0,
        }
        
        protocol_type = protocol_data["type"]
        
        # Разные методы для разных типов протоколов
        if protocol_type == "lending":
            result = await self._check_lending_protocol(address, protocol_id, protocol_data, session, timeout)
        elif protocol_type == "dex":
            result = await self._check_dex_protocol(address, protocol_id, protocol_data, session, timeout)
        elif protocol_type == "vault":
            result = await self._check_vault_protocol(address, protocol_id, protocol_data, session, timeout)
        elif protocol_type == "liquid_staking":
            result = await self._check_liquid_staking(address, protocol_id, protocol_data, session, timeout)
        
        return result
    
    async def _check_lending_protocol(
        self,
        address: str,
        protocol_id: str,
        protocol_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка lending протокола (Aave, Compound)"""
        
        result = {
            "name": protocol_data["name"],
            "type": "lending",
            "has_positions": False,
            "positions": {},
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "supplied": {},
            "borrowed": {},
            "health_factor": 0.0,
        }
        
        contracts = protocol_data.get("contracts", {})
        
        # Проверяем на каждой сети
        for chain, contract_address in contracts.items():
            position = await self._get_lending_position(
                address,
                contract_address,
                chain,
                session,
                timeout
            )
            
            if position.get("has_position"):
                result["has_positions"] = True
                result["positions"][chain] = position
                result["total_staked_usd"] += position.get("supplied_usd", 0)
                result["total_rewards_usd"] += position.get("rewards_usd", 0)
        
        return result
    
    async def _get_lending_position(
        self,
        address: str,
        contract_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Получить lending позицию"""
        
        position = {
            "has_position": False,
            "supplied": {},
            "borrowed": {},
            "supplied_usd": 0.0,
            "borrowed_usd": 0.0,
            "rewards_usd": 0.0,
            "health_factor": 0.0,
        }
        
        # RPC endpoints
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return position
        
        try:
            # Вызываем getUserAccountData для Aave
            # function getUserAccountData(address user) returns (
            #     uint256 totalCollateralBase,
            #     uint256 totalDebtBase,
            #     uint256 availableBorrowsBase,
            #     uint256 currentLiquidationThreshold,
            #     uint256 ltv,
            #     uint256 healthFactor
            # )
            
            # Selector: 0xbf92857c
            data = "0xbf92857c" + "0" * 24 + address[2:]
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [
                    {
                        "to": contract_address,
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
                    result_data = await resp.json()
                    
                    if "result" in result_data and result_data["result"] != "0x":
                        result_hex = result_data["result"]
                        
                        # Парсим результат (6 uint256)
                        # Каждый uint256 = 64 hex символа
                        if len(result_hex) >= 2 + 64 * 6:
                            total_collateral = int(result_hex[2:66], 16) / 1e8  # Base 8 decimals
                            total_debt = int(result_hex[66:130], 16) / 1e8
                            health_factor = int(result_hex[322:386], 16) / 1e18
                            
                            if total_collateral > 0 or total_debt > 0:
                                position["has_position"] = True
                                position["supplied_usd"] = total_collateral
                                position["borrowed_usd"] = total_debt
                                position["health_factor"] = health_factor
        
        except Exception:
            pass
        
        return position
    
    async def _check_dex_protocol(
        self,
        address: str,
        protocol_id: str,
        protocol_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка DEX протокола (Curve, Uniswap)"""
        
        result = {
            "name": protocol_data["name"],
            "type": "dex",
            "has_positions": False,
            "positions": {},
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "lp_tokens": {},
        }
        
        # Здесь можно добавить проверку LP токенов
        # Для Curve это сложнее, нужны специфичные вызовы
        
        return result
    
    async def _check_vault_protocol(
        self,
        address: str,
        protocol_id: str,
        protocol_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка vault протокола (Yearn)"""
        
        result = {
            "name": protocol_data["name"],
            "type": "vault",
            "has_positions": False,
            "positions": {},
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "vaults": {},
        }
        
        # Проверка vault токенов (yvTokens)
        
        return result
    
    async def _check_liquid_staking(
        self,
        address: str,
        protocol_id: str,
        protocol_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка liquid staking (Lido, Rocket Pool)"""
        
        result = {
            "name": protocol_data["name"],
            "type": "liquid_staking",
            "has_positions": False,
            "positions": {},
            "total_staked_usd": 0.0,
            "total_rewards_usd": 0.0,
            "staked_eth": 0.0,
        }
        
        contracts = protocol_data.get("contracts", {})
        
        for chain, contract_address in contracts.items():
            balance = await self._get_token_balance(
                address,
                contract_address,
                chain,
                session,
                timeout
            )
            
            if balance > 0:
                result["has_positions"] = True
                result["staked_eth"] = balance
                
                # Примерная цена ETH
                eth_price = 2500
                result["total_staked_usd"] = balance * eth_price
                
                # Примерные rewards (4% APY)
                result["total_rewards_usd"] = balance * eth_price * 0.04
        
        return result
    
    async def _get_token_balance(
        self,
        address: str,
        token_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """Получить баланс токена"""
        
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return 0.0
        
        try:
            # balanceOf(address)
            data = "0x70a08231" + "0" * 24 + address[2:]
            
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
                        balance = balance_wei / 1e18
                        
                        return balance
        
        except Exception:
            pass
        
        return 0.0
    
    def _generate_summary(self, protocols: Dict[str, Any]) -> Dict[str, Any]:
        """Генерировать сводку"""
        
        summary = {
            "by_type": {},
            "top_protocols": [],
            "total_apy_weighted": 0.0,
        }
        
        # Группируем по типам
        for protocol_id, protocol_data in protocols.items():
            protocol_type = protocol_data.get("type", "unknown")
            
            if protocol_type not in summary["by_type"]:
                summary["by_type"][protocol_type] = {
                    "count": 0,
                    "total_staked_usd": 0.0,
                    "total_rewards_usd": 0.0,
                }
            
            summary["by_type"][protocol_type]["count"] += 1
            summary["by_type"][protocol_type]["total_staked_usd"] += protocol_data.get("total_staked_usd", 0)
            summary["by_type"][protocol_type]["total_rewards_usd"] += protocol_data.get("total_rewards_usd", 0)
        
        # Топ протоколы
        sorted_protocols = sorted(
            protocols.items(),
            key=lambda x: x[1].get("total_staked_usd", 0),
            reverse=True
        )
        
        summary["top_protocols"] = [
            {
                "name": data["name"],
                "staked_usd": data.get("total_staked_usd", 0),
                "rewards_usd": data.get("total_rewards_usd", 0),
            }
            for protocol_id, data in sorted_protocols[:5]
        ]
        
        return summary
    
    def format_staking_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о стейкинге"""
        
        if result["protocols_with_positions"] == 0:
            return "💰 No staking positions found"
        
        lines = []
        
        lines.append("💰 STAKING & FARMING REPORT")
        lines.append("=" * 50)
        
        # Общая информация
        lines.append(f"📊 Protocols: {result['protocols_with_positions']}/{result['total_protocols']}")
        lines.append(f"💎 Total Staked: ~${result['total_staked_usd']:,.2f}")
        lines.append(f"🎁 Total Rewards: ~${result['total_rewards_usd']:,.2f}")
        
        # По типам
        summary = result.get("summary", {})
        by_type = summary.get("by_type", {})
        
        if by_type:
            lines.append("\n📋 BY TYPE:")
            for protocol_type, data in by_type.items():
                lines.append(f"  • {protocol_type}: {data['count']} protocols, ${data['total_staked_usd']:,.2f}")
        
        # Топ протоколы
        top_protocols = summary.get("top_protocols", [])
        if top_protocols:
            lines.append("\n🏆 TOP PROTOCOLS:")
            for i, protocol in enumerate(top_protocols, 1):
                name = protocol["name"]
                staked = protocol["staked_usd"]
                rewards = protocol["rewards_usd"]
                lines.append(f"  {i}. {name}: ${staked:,.2f} (rewards: ${rewards:,.2f})")
        
        # Детали по протоколам
        protocols = result.get("protocols", {})
        if protocols:
            lines.append("\n📊 DETAILS:")
            for protocol_id, protocol_data in protocols.items():
                name = protocol_data["name"]
                protocol_type = protocol_data["type"]
                staked = protocol_data.get("total_staked_usd", 0)
                
                lines.append(f"\n💎 {name} ({protocol_type})")
                lines.append(f"  Staked: ${staked:,.2f}")
                
                # Специфичные детали
                if protocol_type == "lending":
                    health_factor = protocol_data.get("health_factor", 0)
                    if health_factor > 0:
                        lines.append(f"  Health Factor: {health_factor:.2f}")
                
                elif protocol_type == "liquid_staking":
                    staked_eth = protocol_data.get("staked_eth", 0)
                    if staked_eth > 0:
                        lines.append(f"  Staked ETH: {staked_eth:.4f}")
        
        return "\n".join(lines)
