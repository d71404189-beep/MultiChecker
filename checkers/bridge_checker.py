# -*- coding: utf-8 -*-
"""
Bridge Checker v1.0.59
Проверка средств в процессе перевода через мосты
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List


# Известные мосты и их контракты
BRIDGES = {
    "stargate": {
        "name": "Stargate Finance",
        "protocol": "LayerZero",
        "contracts": {
            "ethereum": "0x8731d54E9D02c286767d56ac03e8037C07e01e98",
            "bsc": "0x4a364f8c717cAAD9A442737Eb7b8A55cc6cf18D8",
            "polygon": "0x45A01E4e04F14f7A4a6702c74187c5F6222033cd",
            "arbitrum": "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614",
            "optimism": "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b",
            "avalanche": "0x45A01E4e04F14f7A4a6702c74187c5F6222033cd",
        },
        "api": "https://api.stargate.finance"
    },
    
    "layerzero": {
        "name": "LayerZero",
        "protocol": "LayerZero",
        "contracts": {
            "ethereum": "0x66A71Dcef29A0fFBDBE3c6a460a3B5BC225Cd675",
            "bsc": "0x3c2269811836af69497E5F486A85D7316753cf62",
            "polygon": "0x3c2269811836af69497E5F486A85D7316753cf62",
            "arbitrum": "0x3c2269811836af69497E5F486A85D7316753cf62",
            "optimism": "0x3c2269811836af69497E5F486A85D7316753cf62",
        },
        "api": "https://api.layerzero.network"
    },
    
    "wormhole": {
        "name": "Wormhole",
        "protocol": "Wormhole",
        "contracts": {
            "ethereum": "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B",
            "bsc": "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B",
            "polygon": "0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7",
            "avalanche": "0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c",
            "solana": "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth",
        },
        "api": "https://api.wormholescan.io"
    },
    
    "across": {
        "name": "Across Protocol",
        "protocol": "Across",
        "contracts": {
            "ethereum": "0x4D9079Bb4165aeb4084c526a32695dCfd2F77381",
            "polygon": "0x69B5c72837769eF1e7C164Abc6515DcFf217F920",
            "arbitrum": "0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A",
            "optimism": "0x6f26Bf09B1C792e3228e5467807a900A503c0281",
        },
        "api": "https://across.to/api"
    },
    
    "hop": {
        "name": "Hop Protocol",
        "protocol": "Hop",
        "contracts": {
            "ethereum": "0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a",
            "polygon": "0x58c61AeE5eD3D748a1467085ED2650B697A66234",
            "arbitrum": "0x3E4a3a4796d16c0Cd582C382691998f7c06420B6",
            "optimism": "0x83f6244Bd87662118d96D9a6D44f09dffF14b30E",
        },
        "api": "https://api.hop.exchange"
    },
}


class BridgeChecker:
    """Проверка средств в мостах"""
    
    def __init__(self):
        self.bridges = BRIDGES
    
    async def check_all_bridges(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить все мосты
        
        Returns:
            {
                "total_bridges": int,
                "bridges_with_funds": int,
                "total_value_usd": float,
                "bridges": {...},
                "pending_transfers": [...],
            }
        """
        
        result = {
            "total_bridges": len(self.bridges),
            "bridges_with_funds": 0,
            "total_value_usd": 0.0,
            "bridges": {},
            "pending_transfers": [],
        }
        
        # Проверяем каждый мост
        tasks = []
        for bridge_id, bridge_data in self.bridges.items():
            task = self._check_bridge(address, bridge_id, bridge_data, session, timeout)
            tasks.append(task)
        
        bridge_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (bridge_id, bridge_data) in enumerate(self.bridges.items()):
            if isinstance(bridge_results[i], Exception):
                continue
            
            bridge_result = bridge_results[i]
            
            if bridge_result.get("has_funds"):
                result["bridges"][bridge_id] = bridge_result
                result["bridges_with_funds"] += 1
                result["total_value_usd"] += bridge_result.get("total_value_usd", 0)
                
                # Добавляем pending переводы
                pending = bridge_result.get("pending_transfers", [])
                result["pending_transfers"].extend(pending)
        
        return result
    
    async def _check_bridge(
        self,
        address: str,
        bridge_id: str,
        bridge_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверить конкретный мост"""
        
        result = {
            "name": bridge_data["name"],
            "protocol": bridge_data["protocol"],
            "has_funds": False,
            "balances": {},
            "total_value_usd": 0.0,
            "pending_transfers": [],
        }
        
        contracts = bridge_data.get("contracts", {})
        
        # Проверяем балансы на каждой сети
        for chain, contract_address in contracts.items():
            if chain == "solana":
                # Solana использует другой формат
                continue
            
            balance = await self._check_bridge_balance(
                address,
                contract_address,
                chain,
                session,
                timeout
            )
            
            if balance > 0:
                result["balances"][chain] = balance
                result["has_funds"] = True
                
                # Примерная оценка (предполагаем что это ETH/стейблкоины)
                result["total_value_usd"] += balance * 2500  # ETH price
        
        # Проверяем pending переводы через API (если доступно)
        api_url = bridge_data.get("api")
        if api_url:
            pending = await self._check_pending_transfers(
                address,
                bridge_id,
                api_url,
                session,
                timeout
            )
            
            if pending:
                result["pending_transfers"] = pending
                result["has_funds"] = True
        
        return result
    
    async def _check_bridge_balance(
        self,
        address: str,
        contract_address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """Проверить баланс в мосте"""
        
        # RPC endpoints
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "bsc": "https://bsc-dataseed.binance.org/",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
            "avalanche": "https://api.avax.network/ext/bc/C/rpc",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return 0.0
        
        try:
            # Проверяем баланс через eth_call
            # Обычно мосты имеют функцию balanceOf или userBalance
            
            # balanceOf(address)
            data = "0x70a08231" + "0" * 24 + address[2:]
            
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
                    result = await resp.json()
                    
                    if "result" in result:
                        balance_hex = result["result"]
                        balance_wei = int(balance_hex, 16)
                        balance = balance_wei / 1e18
                        
                        return balance
        
        except Exception:
            pass
        
        return 0.0
    
    async def _check_pending_transfers(
        self,
        address: str,
        bridge_id: str,
        api_url: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> List[Dict[str, Any]]:
        """Проверить pending переводы через API"""
        
        pending = []
        
        try:
            # Разные мосты имеют разные API
            if bridge_id == "stargate":
                url = f"{api_url}/v1/transfers/{address}"
            elif bridge_id == "layerzero":
                url = f"{api_url}/v1/messages/{address}"
            elif bridge_id == "wormhole":
                url = f"{api_url}/api/v1/vaas/{address}"
            else:
                return pending
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Парсим ответ (формат зависит от моста)
                    # Здесь упрощенная версия
                    
                    if isinstance(data, list):
                        for transfer in data:
                            if transfer.get("status") == "pending":
                                pending.append({
                                    "from_chain": transfer.get("source_chain"),
                                    "to_chain": transfer.get("destination_chain"),
                                    "amount": transfer.get("amount"),
                                    "token": transfer.get("token"),
                                    "timestamp": transfer.get("timestamp"),
                                    "tx_hash": transfer.get("tx_hash"),
                                })
        
        except Exception:
            pass
        
        return pending
    
    def format_bridge_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о мостах"""
        
        if result["bridges_with_funds"] == 0:
            return "🌉 No funds in bridges"
        
        lines = []
        
        lines.append("🌉 BRIDGE CHECKER")
        lines.append("=" * 50)
        
        # Общая информация
        lines.append(f"🔗 Bridges with funds: {result['bridges_with_funds']}/{result['total_bridges']}")
        lines.append(f"💰 Total Value: ~${result['total_value_usd']:,.2f}")
        
        # По мостам
        lines.append("\n📊 BY BRIDGE:")
        
        for bridge_id, bridge_data in result["bridges"].items():
            name = bridge_data["name"]
            value = bridge_data["total_value_usd"]
            
            lines.append(f"\n🌉 {name} (~${value:,.2f})")
            
            # Балансы по сетям
            balances = bridge_data.get("balances", {})
            if balances:
                lines.append("  💎 Balances:")
                for chain, balance in balances.items():
                    lines.append(f"    • {chain}: {balance:.6f}")
            
            # Pending переводы
            pending = bridge_data.get("pending_transfers", [])
            if pending:
                lines.append(f"  ⏳ Pending Transfers: {len(pending)}")
                for transfer in pending[:3]:  # Первые 3
                    from_chain = transfer.get("from_chain", "?")
                    to_chain = transfer.get("to_chain", "?")
                    amount = transfer.get("amount", 0)
                    token = transfer.get("token", "?")
                    lines.append(f"    • {from_chain} → {to_chain}: {amount} {token}")
        
        # Все pending переводы
        all_pending = result.get("pending_transfers", [])
        if all_pending:
            lines.append(f"\n⏳ TOTAL PENDING TRANSFERS: {len(all_pending)}")
        
        return "\n".join(lines)
    
    async def check_specific_bridge(
        self,
        address: str,
        bridge: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить конкретный мост
        
        Args:
            bridge: stargate, layerzero, wormhole, across, hop
        """
        
        if bridge not in self.bridges:
            return {"error": f"Unknown bridge: {bridge}"}
        
        bridge_data = self.bridges[bridge]
        
        result = await self._check_bridge(
            address,
            bridge,
            bridge_data,
            session,
            timeout
        )
        
        return result
    
    async def estimate_bridge_time(
        self,
        from_chain: str,
        to_chain: str,
        bridge: str
    ) -> Dict[str, Any]:
        """
        Оценить время перевода через мост
        
        Returns:
            {
                "bridge": str,
                "from_chain": str,
                "to_chain": str,
                "estimated_time_minutes": int,
                "fee_estimate_usd": float,
            }
        """
        
        # Примерные времена (в минутах)
        bridge_times = {
            "stargate": 5,
            "layerzero": 5,
            "wormhole": 15,
            "across": 3,
            "hop": 10,
        }
        
        # Примерные комиссии (в USD)
        bridge_fees = {
            "stargate": 5.0,
            "layerzero": 3.0,
            "wormhole": 10.0,
            "across": 2.0,
            "hop": 4.0,
        }
        
        return {
            "bridge": bridge,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "estimated_time_minutes": bridge_times.get(bridge, 10),
            "fee_estimate_usd": bridge_fees.get(bridge, 5.0),
        }
