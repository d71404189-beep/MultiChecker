# -*- coding: utf-8 -*-
"""
Advanced Withdraw v1.0.54
Улучшенный автовывод: Batch, EIP-1559, Flashbots, Scheduled
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════════════
#  BATCH TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════

class BatchWithdrawManager:
    """
    Менеджер batch транзакций для экономии газа
    """
    
    def __init__(self):
        self.pending_withdrawals = []
        self.batch_size = 10  # Максимум транзакций в batch
        self.batch_timeout = 60  # Секунд до автоматической отправки
        self.last_batch_time = time.time()
    
    def add_withdrawal(self, withdrawal: Dict) -> None:
        """
        Добавить вывод в очередь
        
        Args:
            withdrawal: {
                "from": "0x...",
                "to": "0x...",
                "amount": 1.5,
                "token": "ETH" | "USDT" | ...,
                "chain": "ethereum",
                "priority": "low" | "medium" | "high"
            }
        """
        withdrawal["timestamp"] = time.time()
        self.pending_withdrawals.append(withdrawal)
    
    def should_execute_batch(self) -> bool:
        """
        Проверить, нужно ли выполнить batch
        """
        # Если достигнут размер batch
        if len(self.pending_withdrawals) >= self.batch_size:
            return True
        
        # Если прошло достаточно времени
        if time.time() - self.last_batch_time >= self.batch_timeout:
            return len(self.pending_withdrawals) > 0
        
        # Если есть высокоприоритетные транзакции
        high_priority = [w for w in self.pending_withdrawals if w.get("priority") == "high"]
        if len(high_priority) >= 3:
            return True
        
        return False
    
    def get_batch(self) -> List[Dict]:
        """
        Получить batch для выполнения
        """
        if not self.pending_withdrawals:
            return []
        
        # Сортируем по приоритету
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_withdrawals = sorted(
            self.pending_withdrawals,
            key=lambda w: (priority_order.get(w.get("priority", "medium"), 1), w["timestamp"])
        )
        
        # Берем до batch_size транзакций
        batch = sorted_withdrawals[:self.batch_size]
        
        # Удаляем из очереди
        self.pending_withdrawals = sorted_withdrawals[self.batch_size:]
        self.last_batch_time = time.time()
        
        return batch
    
    def estimate_batch_savings(self, batch: List[Dict]) -> Dict[str, float]:
        """
        Оценить экономию от batch транзакций
        
        Returns:
            Dict: {
                "individual_gas": 0.021,  # ETH
                "batch_gas": 0.008,
                "savings": 0.013,
                "savings_percent": 61.9
            }
        """
        if not batch:
            return {"individual_gas": 0, "batch_gas": 0, "savings": 0, "savings_percent": 0}
        
        # Примерные значения газа
        gas_per_tx = 21000  # Простой перевод
        gas_per_token_tx = 65000  # ERC-20 перевод
        
        # Рассчитываем индивидуальный газ
        individual_gas = 0
        for w in batch:
            if w.get("token") == "ETH":
                individual_gas += gas_per_tx
            else:
                individual_gas += gas_per_token_tx
        
        # Batch экономит ~30% газа
        batch_gas = int(individual_gas * 0.7)
        
        # Конвертируем в ETH (предполагаем 30 gwei)
        gas_price_gwei = 30
        individual_gas_eth = (individual_gas * gas_price_gwei * 1e9) / 1e18
        batch_gas_eth = (batch_gas * gas_price_gwei * 1e9) / 1e18
        
        savings = individual_gas_eth - batch_gas_eth
        savings_percent = (savings / individual_gas_eth * 100) if individual_gas_eth > 0 else 0
        
        return {
            "individual_gas": individual_gas_eth,
            "batch_gas": batch_gas_eth,
            "savings": savings,
            "savings_percent": savings_percent
        }


# ═══════════════════════════════════════════════════════════════════════════
#  FLASHBOTS INTEGRATION (MEV Protection)
# ═══════════════════════════════════════════════════════════════════════════

class FlashbotsManager:
    """
    Менеджер Flashbots для защиты от MEV
    """
    
    FLASHBOTS_RPC = "https://relay.flashbots.net"
    
    def __init__(self):
        self.enabled = False
        self.signing_key = None  # Приватный ключ для подписи bundle
    
    async def send_bundle(
        self,
        transactions: List[Dict],
        session: aiohttp.ClientSession,
        target_block: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Отправить bundle через Flashbots
        
        Args:
            transactions: Список подписанных транзакций
            session: aiohttp сессия
            target_block: Целевой блок (None = следующий)
        
        Returns:
            Dict: {
                "success": True,
                "bundle_hash": "0x...",
                "target_block": 12345678,
                "simulation": {...}
            }
        """
        
        if not self.enabled:
            return {"success": False, "error": "Flashbots not enabled"}
        
        try:
            # Получаем текущий блок
            if target_block is None:
                target_block = await self._get_current_block(session) + 1
            
            # Формируем bundle
            bundle = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_sendBundle",
                "params": [
                    {
                        "txs": [tx["raw"] for tx in transactions],
                        "blockNumber": hex(target_block),
                        "minTimestamp": 0,
                        "maxTimestamp": int(time.time()) + 120  # +2 минуты
                    }
                ]
            }
            
            # Отправляем bundle
            async with session.post(
                self.FLASHBOTS_RPC,
                json=bundle,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "bundle_hash": data.get("result", {}).get("bundleHash"),
                        "target_block": target_block
                    }
                else:
                    return {"success": False, "error": f"HTTP {resp.status}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def simulate_bundle(
        self,
        transactions: List[Dict],
        session: aiohttp.ClientSession,
        block_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Симулировать bundle перед отправкой
        
        Returns:
            Dict: {
                "success": True,
                "gas_used": 150000,
                "eth_sent_to_coinbase": 0.01,
                "profit": 0.05,
                "reverts": []
            }
        """
        
        try:
            if block_number is None:
                block_number = await self._get_current_block(session)
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_callBundle",
                "params": [
                    {
                        "txs": [tx["raw"] for tx in transactions],
                        "blockNumber": hex(block_number),
                        "stateBlockNumber": "latest"
                    }
                ]
            }
            
            async with session.post(
                self.FLASHBOTS_RPC,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("result", {})
                    
                    return {
                        "success": True,
                        "gas_used": int(result.get("totalGasUsed", 0)),
                        "eth_sent_to_coinbase": int(result.get("coinbaseDiff", 0)) / 1e18,
                        "reverts": result.get("results", [])
                    }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_current_block(self, session: aiohttp.ClientSession) -> int:
        """
        Получить текущий номер блока
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            async with session.post(
                "https://cloudflare-eth.com",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return int(data.get("result", "0x0"), 16)
        except:
            pass
        
        return 0
    
    def calculate_mev_protection_value(self, transaction: Dict) -> float:
        """
        Оценить ценность MEV защиты для транзакции
        
        Returns:
            float: Потенциальная экономия в USD
        """
        amount_usd = transaction.get("amount_usd", 0)
        
        # MEV атаки обычно крадут 0.1-2% от суммы
        if amount_usd > 10000:
            return amount_usd * 0.02  # 2% для больших сумм
        elif amount_usd > 1000:
            return amount_usd * 0.01  # 1% для средних
        else:
            return amount_usd * 0.005  # 0.5% для малых
    
    def should_use_flashbots(self, transaction: Dict) -> bool:
        """
        Определить, нужно ли использовать Flashbots
        """
        amount_usd = transaction.get("amount_usd", 0)
        
        # Используем Flashbots для сумм > $1000
        if amount_usd > 1000:
            return True
        
        # Или для DEX транзакций (swap)
        if transaction.get("type") == "swap":
            return True
        
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  SCHEDULED WITHDRAWALS
# ═══════════════════════════════════════════════════════════════════════════

class ScheduledWithdrawManager:
    """
    Менеджер отложенных выводов
    """
    
    def __init__(self):
        self.scheduled_withdrawals = []
    
    def schedule_withdrawal(
        self,
        withdrawal: Dict,
        schedule_time: Optional[datetime] = None,
        condition: Optional[Dict] = None
    ) -> str:
        """
        Запланировать вывод
        
        Args:
            withdrawal: Данные вывода
            schedule_time: Время выполнения (None = сейчас)
            condition: Условие выполнения {
                "type": "balance" | "gas_price" | "time",
                "operator": ">" | "<" | "==" | ">=" | "<=",
                "value": 100
            }
        
        Returns:
            str: ID запланированного вывода
        """
        
        withdrawal_id = f"scheduled_{int(time.time() * 1000)}"
        
        scheduled = {
            "id": withdrawal_id,
            "withdrawal": withdrawal,
            "schedule_time": schedule_time or datetime.now(),
            "condition": condition,
            "status": "pending",
            "created_at": datetime.now()
        }
        
        self.scheduled_withdrawals.append(scheduled)
        return withdrawal_id
    
    def check_scheduled_withdrawals(self, current_state: Dict) -> List[Dict]:
        """
        Проверить, какие выводы готовы к выполнению
        
        Args:
            current_state: {
                "balance": 1.5,
                "gas_price": 25,
                "time": datetime.now()
            }
        
        Returns:
            List[Dict]: Список готовых к выполнению выводов
        """
        
        ready_withdrawals = []
        
        for scheduled in self.scheduled_withdrawals:
            if scheduled["status"] != "pending":
                continue
            
            # Проверяем время
            if scheduled["schedule_time"] > datetime.now():
                continue
            
            # Проверяем условие
            if scheduled["condition"]:
                if not self._check_condition(scheduled["condition"], current_state):
                    continue
            
            # Готов к выполнению
            scheduled["status"] = "ready"
            ready_withdrawals.append(scheduled["withdrawal"])
        
        return ready_withdrawals
    
    def _check_condition(self, condition: Dict, state: Dict) -> bool:
        """
        Проверить условие
        """
        cond_type = condition.get("type")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if cond_type == "balance":
            current_value = state.get("balance", 0)
        elif cond_type == "gas_price":
            current_value = state.get("gas_price", 999)
        elif cond_type == "time":
            current_value = state.get("time", datetime.now()).timestamp()
            value = value.timestamp() if isinstance(value, datetime) else value
        else:
            return False
        
        # Применяем оператор
        if operator == ">":
            return current_value > value
        elif operator == "<":
            return current_value < value
        elif operator == ">=":
            return current_value >= value
        elif operator == "<=":
            return current_value <= value
        elif operator == "==":
            return current_value == value
        
        return False
    
    def cancel_scheduled_withdrawal(self, withdrawal_id: str) -> bool:
        """
        Отменить запланированный вывод
        """
        for scheduled in self.scheduled_withdrawals:
            if scheduled["id"] == withdrawal_id:
                scheduled["status"] = "cancelled"
                return True
        return False
    
    def get_scheduled_withdrawals(self, status: Optional[str] = None) -> List[Dict]:
        """
        Получить список запланированных выводов
        """
        if status:
            return [s for s in self.scheduled_withdrawals if s["status"] == status]
        return self.scheduled_withdrawals.copy()


# ═══════════════════════════════════════════════════════════════════════════
#  CONDITIONAL WITHDRAWALS
# ═══════════════════════════════════════════════════════════════════════════

class ConditionalWithdrawManager:
    """
    Менеджер условных выводов (если баланс > X)
    """
    
    def __init__(self):
        self.conditions = []
    
    def add_condition(
        self,
        address: str,
        min_balance: float,
        token: str,
        destination: str,
        leave_amount: float = 0
    ) -> str:
        """
        Добавить условие автовывода
        
        Args:
            address: Адрес для мониторинга
            min_balance: Минимальный баланс для вывода
            token: Токен (ETH, USDT, ...)
            destination: Адрес назначения
            leave_amount: Сколько оставить (для газа)
        
        Returns:
            str: ID условия
        """
        
        condition_id = f"condition_{int(time.time() * 1000)}"
        
        condition = {
            "id": condition_id,
            "address": address,
            "min_balance": min_balance,
            "token": token,
            "destination": destination,
            "leave_amount": leave_amount,
            "enabled": True,
            "last_check": None,
            "total_withdrawn": 0,
            "withdraw_count": 0
        }
        
        self.conditions.append(condition)
        return condition_id
    
    async def check_conditions(
        self,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> List[Dict]:
        """
        Проверить все условия и вернуть готовые выводы
        
        Returns:
            List[Dict]: Список выводов для выполнения
        """
        
        withdrawals = []
        
        for condition in self.conditions:
            if not condition["enabled"]:
                continue
            
            # Проверяем баланс
            balance = await self._check_balance(
                condition["address"],
                condition["token"],
                session,
                timeout
            )
            
            condition["last_check"] = datetime.now()
            
            # Если баланс >= минимума
            if balance >= condition["min_balance"]:
                withdraw_amount = balance - condition["leave_amount"]
                
                if withdraw_amount > 0:
                    withdrawals.append({
                        "from": condition["address"],
                        "to": condition["destination"],
                        "amount": withdraw_amount,
                        "token": condition["token"],
                        "condition_id": condition["id"]
                    })
                    
                    # Обновляем статистику
                    condition["total_withdrawn"] += withdraw_amount
                    condition["withdraw_count"] += 1
        
        return withdrawals
    
    async def _check_balance(
        self,
        address: str,
        token: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """
        Проверить баланс адреса
        """
        # Здесь должна быть реальная проверка через RPC
        # Для примера возвращаем 0
        return 0.0
    
    def remove_condition(self, condition_id: str) -> bool:
        """
        Удалить условие
        """
        self.conditions = [c for c in self.conditions if c["id"] != condition_id]
        return True
    
    def get_conditions(self) -> List[Dict]:
        """
        Получить все условия
        """
        return self.conditions.copy()


# ═══════════════════════════════════════════════════════════════════════════
#  BRIDGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

class BridgeManager:
    """
    Менеджер мостов между сетями (LayerZero, Stargate)
    """
    
    SUPPORTED_BRIDGES = {
        "stargate": {
            "name": "Stargate Finance",
            "chains": ["ethereum", "bsc", "polygon", "avalanche", "arbitrum", "optimism"],
            "tokens": ["USDC", "USDT"],
            "fee_percent": 0.06  # 0.06%
        },
        "layerzero": {
            "name": "LayerZero",
            "chains": ["ethereum", "bsc", "polygon", "avalanche", "arbitrum", "optimism", "fantom"],
            "tokens": ["ETH", "USDC", "USDT"],
            "fee_percent": 0.1  # 0.1%
        },
        "across": {
            "name": "Across Protocol",
            "chains": ["ethereum", "polygon", "arbitrum", "optimism"],
            "tokens": ["ETH", "USDC", "USDT", "DAI"],
            "fee_percent": 0.05  # 0.05%
        }
    }
    
    def find_best_bridge(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Найти лучший мост для перевода
        
        Returns:
            Dict: {
                "bridge": "stargate",
                "fee": 0.06,
                "fee_usd": 1.2,
                "estimated_time": "2-5 min",
                "route": ["ethereum", "arbitrum"]
            }
        """
        
        best_bridge = None
        best_fee = float('inf')
        
        for bridge_id, bridge_info in self.SUPPORTED_BRIDGES.items():
            # Проверяем поддержку сетей
            if from_chain not in bridge_info["chains"] or to_chain not in bridge_info["chains"]:
                continue
            
            # Проверяем поддержку токена
            if token not in bridge_info["tokens"]:
                continue
            
            # Рассчитываем комиссию
            fee_percent = bridge_info["fee_percent"]
            fee_amount = amount * (fee_percent / 100)
            
            if fee_amount < best_fee:
                best_fee = fee_amount
                best_bridge = {
                    "bridge": bridge_id,
                    "name": bridge_info["name"],
                    "fee_percent": fee_percent,
                    "fee_amount": fee_amount,
                    "estimated_time": "2-5 min",
                    "route": [from_chain, to_chain]
                }
        
        return best_bridge or {"error": "No bridge found"}
    
    def estimate_bridge_cost(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float,
        amount_usd: float
    ) -> Dict[str, float]:
        """
        Оценить полную стоимость bridge
        
        Returns:
            Dict: {
                "bridge_fee": 1.2,  # USD
                "gas_cost": 5.0,
                "total_cost": 6.2,
                "net_amount": 993.8
            }
        """
        
        bridge = self.find_best_bridge(from_chain, to_chain, token, amount)
        
        if "error" in bridge:
            return {"error": bridge["error"]}
        
        bridge_fee_usd = (amount_usd * bridge["fee_percent"]) / 100
        
        # Примерная стоимость газа
        gas_costs = {
            "ethereum": 10.0,
            "bsc": 0.5,
            "polygon": 0.1,
            "avalanche": 1.0,
            "arbitrum": 1.0,
            "optimism": 1.0,
            "fantom": 0.2
        }
        
        gas_cost = gas_costs.get(from_chain, 5.0)
        total_cost = bridge_fee_usd + gas_cost
        net_amount = amount_usd - total_cost
        
        return {
            "bridge_fee": bridge_fee_usd,
            "gas_cost": gas_cost,
            "total_cost": total_cost,
            "net_amount": net_amount,
            "cost_percent": (total_cost / amount_usd * 100) if amount_usd > 0 else 0
        }
