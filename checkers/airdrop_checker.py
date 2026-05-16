# -*- coding: utf-8 -*-
"""
Airdrop Eligibility Checker v1.0.60
Проверка права на получение airdrop'ов
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime


# Известные airdrop критерии
AIRDROP_CRITERIA = {
    "arbitrum": {
        "name": "Arbitrum",
        "token": "ARB",
        "criteria": {
            "min_transactions": 4,
            "min_volume_usd": 10000,
            "min_unique_contracts": 4,
            "min_unique_months": 2,
        },
        "snapshot_date": "2023-02-06",
        "claimed": True,
    },
    
    "optimism": {
        "name": "Optimism",
        "token": "OP",
        "criteria": {
            "min_transactions": 1,
            "min_volume_usd": 0,
            "bridge_used": True,
        },
        "snapshot_date": "2022-03-25",
        "claimed": True,
    },
    
    "aptos": {
        "name": "Aptos",
        "token": "APT",
        "criteria": {
            "testnet_participation": True,
            "min_testnet_tx": 10,
        },
        "snapshot_date": "2022-09-12",
        "claimed": True,
    },
    
    "sui": {
        "name": "Sui",
        "token": "SUI",
        "criteria": {
            "testnet_participation": True,
            "min_testnet_tx": 10,
        },
        "snapshot_date": "2023-04-01",
        "claimed": True,
    },
    
    "zksync": {
        "name": "zkSync",
        "token": "ZK",
        "criteria": {
            "min_transactions": 10,
            "min_volume_usd": 1000,
            "min_unique_contracts": 5,
            "min_unique_months": 3,
            "bridge_used": True,
        },
        "snapshot_date": "2024-03-24",
        "claimed": False,
    },
    
    "starknet": {
        "name": "Starknet",
        "token": "STRK",
        "criteria": {
            "min_transactions": 5,
            "min_volume_usd": 100,
            "min_unique_contracts": 3,
        },
        "snapshot_date": "2024-02-01",
        "claimed": False,
    },
    
    "layerzero": {
        "name": "LayerZero",
        "token": "ZRO",
        "criteria": {
            "min_transactions": 10,
            "min_unique_chains": 3,
            "min_volume_usd": 1000,
            "min_unique_months": 6,
        },
        "snapshot_date": None,  # Еще не объявлен
        "claimed": False,
    },
    
    "scroll": {
        "name": "Scroll",
        "token": "SCR",
        "criteria": {
            "min_transactions": 5,
            "min_volume_usd": 500,
            "bridge_used": True,
        },
        "snapshot_date": None,
        "claimed": False,
    },
    
    "linea": {
        "name": "Linea",
        "token": "LINEA",
        "criteria": {
            "min_transactions": 10,
            "min_volume_usd": 1000,
            "min_unique_contracts": 5,
            "bridge_used": True,
        },
        "snapshot_date": None,
        "claimed": False,
    },
    
    "base": {
        "name": "Base",
        "token": "BASE",
        "criteria": {
            "min_transactions": 5,
            "min_volume_usd": 500,
            "min_unique_contracts": 3,
        },
        "snapshot_date": None,
        "claimed": False,
    },
}


class AirdropChecker:
    """Проверка права на airdrop'ы"""
    
    def __init__(self):
        self.criteria = AIRDROP_CRITERIA
    
    async def check_all_airdrops(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить все airdrop'ы
        
        Returns:
            {
                "total_airdrops": int,
                "eligible_count": int,
                "claimed_count": int,
                "potential_count": int,
                "airdrops": {...},
                "summary": {...}
            }
        """
        
        result = {
            "total_airdrops": len(self.criteria),
            "eligible_count": 0,
            "claimed_count": 0,
            "potential_count": 0,
            "airdrops": {},
            "summary": {},
        }
        
        # Проверяем каждый airdrop
        tasks = []
        for airdrop_id, airdrop_data in self.criteria.items():
            task = self._check_airdrop(address, airdrop_id, airdrop_data, session, timeout)
            tasks.append(task)
        
        airdrop_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (airdrop_id, airdrop_data) in enumerate(self.criteria.items()):
            if isinstance(airdrop_results[i], Exception):
                continue
            
            airdrop_result = airdrop_results[i]
            
            result["airdrops"][airdrop_id] = airdrop_result
            
            if airdrop_result.get("eligible"):
                result["eligible_count"] += 1
                
                if airdrop_result.get("claimed"):
                    result["claimed_count"] += 1
                else:
                    result["potential_count"] += 1
        
        # Сводка
        result["summary"] = self._generate_summary(result["airdrops"])
        
        return result
    
    async def _check_airdrop(
        self,
        address: str,
        airdrop_id: str,
        airdrop_data: Dict[str, Any],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверить конкретный airdrop"""
        
        result = {
            "name": airdrop_data["name"],
            "token": airdrop_data["token"],
            "eligible": False,
            "claimed": airdrop_data.get("claimed", False),
            "snapshot_date": airdrop_data.get("snapshot_date"),
            "criteria_met": {},
            "score": 0.0,
            "estimated_amount": 0.0,
        }
        
        criteria = airdrop_data.get("criteria", {})
        
        # Получаем статистику кошелька
        stats = await self._get_wallet_stats(address, airdrop_id, session, timeout)
        
        # Проверяем критерии
        total_criteria = len(criteria)
        met_criteria = 0
        
        for criterion, required_value in criteria.items():
            actual_value = stats.get(criterion, 0)
            
            if criterion.startswith("min_"):
                # Минимальное значение
                met = actual_value >= required_value
            elif criterion.endswith("_used"):
                # Булево значение
                met = actual_value == required_value
            else:
                met = actual_value >= required_value
            
            result["criteria_met"][criterion] = {
                "required": required_value,
                "actual": actual_value,
                "met": met,
            }
            
            if met:
                met_criteria += 1
        
        # Считаем score
        if total_criteria > 0:
            result["score"] = (met_criteria / total_criteria) * 100
        
        # Eligible если все критерии выполнены
        result["eligible"] = met_criteria == total_criteria
        
        # Оценка количества токенов
        if result["eligible"]:
            result["estimated_amount"] = self._estimate_airdrop_amount(
                airdrop_id,
                stats
            )
        
        return result
    
    async def _get_wallet_stats(
        self,
        address: str,
        airdrop_id: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Получить статистику кошелька"""
        
        stats = {
            "transactions": 0,
            "min_transactions": 0,
            "volume_usd": 0.0,
            "min_volume_usd": 0.0,
            "unique_contracts": 0,
            "min_unique_contracts": 0,
            "unique_months": 0,
            "min_unique_months": 0,
            "unique_chains": 0,
            "min_unique_chains": 0,
            "bridge_used": False,
            "testnet_participation": False,
            "min_testnet_tx": 0,
        }
        
        # Здесь должна быть реальная проверка через API
        # Для примера используем mock данные
        
        # RPC endpoints
        rpc_urls = {
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
            "zksync": "https://mainnet.era.zksync.io",
            "starknet": "https://starknet-mainnet.public.blastapi.io",
            "scroll": "https://rpc.scroll.io",
            "linea": "https://rpc.linea.build",
            "base": "https://mainnet.base.org",
        }
        
        rpc_url = rpc_urls.get(airdrop_id)
        if not rpc_url:
            return stats
        
        try:
            # Получаем количество транзакций
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getTransactionCount",
                "params": [address, "latest"]
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
                        tx_count = int(result["result"], 16)
                        
                        stats["transactions"] = tx_count
                        stats["min_transactions"] = tx_count
                        
                        # Примерные значения для других метрик
                        stats["volume_usd"] = tx_count * 100  # ~$100 per TX
                        stats["min_volume_usd"] = stats["volume_usd"]
                        stats["unique_contracts"] = min(tx_count // 2, 20)
                        stats["min_unique_contracts"] = stats["unique_contracts"]
                        stats["unique_months"] = min(tx_count // 5, 12)
                        stats["min_unique_months"] = stats["unique_months"]
                        stats["bridge_used"] = tx_count > 0
        
        except Exception:
            pass
        
        return stats
    
    def _estimate_airdrop_amount(
        self,
        airdrop_id: str,
        stats: Dict[str, Any]
    ) -> float:
        """Оценить количество токенов в airdrop"""
        
        # Примерные формулы для разных проектов
        estimates = {
            "arbitrum": lambda s: min(s.get("transactions", 0) * 100, 10000),
            "optimism": lambda s: min(s.get("transactions", 0) * 50, 5000),
            "zksync": lambda s: min(s.get("volume_usd", 0) * 0.1, 5000),
            "starknet": lambda s: min(s.get("transactions", 0) * 80, 8000),
            "layerzero": lambda s: min(s.get("unique_chains", 0) * 500, 5000),
            "scroll": lambda s: min(s.get("transactions", 0) * 60, 3000),
            "linea": lambda s: min(s.get("volume_usd", 0) * 0.05, 2000),
            "base": lambda s: min(s.get("transactions", 0) * 40, 2000),
        }
        
        estimator = estimates.get(airdrop_id)
        if estimator:
            return estimator(stats)
        
        return 0.0
    
    def _generate_summary(self, airdrops: Dict[str, Any]) -> Dict[str, Any]:
        """Генерировать сводку"""
        
        summary = {
            "by_status": {
                "eligible": [],
                "not_eligible": [],
                "claimed": [],
                "potential": [],
            },
            "total_estimated_value": 0.0,
            "best_opportunities": [],
        }
        
        # Группируем по статусу
        for airdrop_id, data in airdrops.items():
            if data.get("eligible"):
                if data.get("claimed"):
                    summary["by_status"]["claimed"].append(data["name"])
                else:
                    summary["by_status"]["potential"].append(data["name"])
                    summary["by_status"]["eligible"].append(data["name"])
            else:
                summary["by_status"]["not_eligible"].append(data["name"])
        
        # Лучшие возможности (по score)
        sorted_airdrops = sorted(
            airdrops.items(),
            key=lambda x: x[1].get("score", 0),
            reverse=True
        )
        
        summary["best_opportunities"] = [
            {
                "name": data["name"],
                "token": data["token"],
                "score": data.get("score", 0),
                "eligible": data.get("eligible", False),
                "estimated_amount": data.get("estimated_amount", 0),
            }
            for airdrop_id, data in sorted_airdrops[:5]
        ]
        
        return summary
    
    def format_airdrop_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет об airdrop'ах"""
        
        lines = []
        
        lines.append("🎁 AIRDROP ELIGIBILITY REPORT")
        lines.append("=" * 50)
        
        # Общая информация
        lines.append(f"📊 Total Airdrops: {result['total_airdrops']}")
        lines.append(f"✅ Eligible: {result['eligible_count']}")
        lines.append(f"🎯 Potential (unclaimed): {result['potential_count']}")
        lines.append(f"✔️ Already Claimed: {result['claimed_count']}")
        
        # Лучшие возможности
        summary = result.get("summary", {})
        best = summary.get("best_opportunities", [])
        
        if best:
            lines.append("\n🏆 BEST OPPORTUNITIES:")
            for i, opp in enumerate(best, 1):
                name = opp["name"]
                token = opp["token"]
                score = opp["score"]
                eligible = "✅" if opp["eligible"] else "❌"
                amount = opp["estimated_amount"]
                
                lines.append(f"  {i}. {name} ({token}): {score:.1f}% {eligible}")
                if amount > 0:
                    lines.append(f"     Estimated: ~{amount:,.0f} {token}")
        
        # Детали по airdrop'ам
        airdrops = result.get("airdrops", {})
        
        # Eligible airdrops
        eligible_airdrops = {k: v for k, v in airdrops.items() if v.get("eligible")}
        if eligible_airdrops:
            lines.append("\n✅ ELIGIBLE AIRDROPS:")
            for airdrop_id, data in eligible_airdrops.items():
                name = data["name"]
                token = data["token"]
                claimed = "✔️ CLAIMED" if data.get("claimed") else "🎯 POTENTIAL"
                amount = data.get("estimated_amount", 0)
                
                lines.append(f"\n🎁 {name} ({token}) - {claimed}")
                if amount > 0:
                    lines.append(f"  Estimated: ~{amount:,.0f} {token}")
                
                # Критерии
                criteria_met = data.get("criteria_met", {})
                if criteria_met:
                    lines.append("  Criteria:")
                    for criterion, info in criteria_met.items():
                        status = "✅" if info["met"] else "❌"
                        lines.append(f"    {status} {criterion}: {info['actual']} (required: {info['required']})")
        
        # Not eligible airdrops
        not_eligible = {k: v for k, v in airdrops.items() if not v.get("eligible")}
        if not_eligible:
            lines.append("\n❌ NOT ELIGIBLE:")
            for airdrop_id, data in not_eligible.items():
                name = data["name"]
                token = data["token"]
                score = data.get("score", 0)
                
                lines.append(f"\n🎁 {name} ({token}) - Score: {score:.1f}%")
                
                # Критерии
                criteria_met = data.get("criteria_met", {})
                if criteria_met:
                    lines.append("  Missing criteria:")
                    for criterion, info in criteria_met.items():
                        if not info["met"]:
                            lines.append(f"    ❌ {criterion}: {info['actual']} (need: {info['required']})")
        
        return "\n".join(lines)


class AirdropMonitor:
    """Мониторинг новых airdrop'ов"""
    
    def __init__(self):
        self.known_airdrops = set(AIRDROP_CRITERIA.keys())
    
    async def check_new_airdrops(
        self,
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """Проверить новые airdrop'ы"""
        
        # Здесь можно добавить проверку через API
        # Например, через DefiLlama, CoinGecko и т.д.
        
        new_airdrops = []
        
        return new_airdrops
    
    def add_custom_airdrop(
        self,
        airdrop_id: str,
        name: str,
        token: str,
        criteria: Dict[str, Any],
        snapshot_date: Optional[str] = None
    ):
        """Добавить кастомный airdrop"""
        
        AIRDROP_CRITERIA[airdrop_id] = {
            "name": name,
            "token": token,
            "criteria": criteria,
            "snapshot_date": snapshot_date,
            "claimed": False,
        }
