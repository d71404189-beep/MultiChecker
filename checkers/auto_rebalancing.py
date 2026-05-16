# -*- coding: utf-8 -*-
"""
Auto-Rebalancing v1.0.61
Автоматическая ребалансировка портфеля
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json


class AutoRebalancer:
    """Автоматическая ребалансировка портфеля"""
    
    def __init__(self):
        self.strategies = {}
        self.rebalance_history = []
    
    def create_strategy(
        self,
        strategy_id: str,
        target_allocation: Dict[str, float],
        rebalance_threshold: float = 5.0,
        rebalance_frequency: str = "monthly"
    ):
        """
        Создать стратегию ребалансировки
        
        Args:
            strategy_id: ID стратегии
            target_allocation: Целевое распределение (asset: percentage)
            rebalance_threshold: Порог отклонения для ребалансировки (%)
            rebalance_frequency: Частота (daily, weekly, monthly, quarterly)
        """
        
        # Проверяем, что сумма = 100%
        total = sum(target_allocation.values())
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Target allocation must sum to 100%, got {total}%")
        
        self.strategies[strategy_id] = {
            "target_allocation": target_allocation,
            "rebalance_threshold": rebalance_threshold,
            "rebalance_frequency": rebalance_frequency,
            "created_at": datetime.now().isoformat(),
            "last_rebalance": None,
        }
    
    async def check_rebalance_needed(
        self,
        strategy_id: str,
        current_allocation: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Проверить, нужна ли ребалансировка
        
        Args:
            strategy_id: ID стратегии
            current_allocation: Текущее распределение (asset: percentage)
        
        Returns:
            {
                "needed": bool,
                "deviations": {...},
                "max_deviation": float,
                "actions": [...]
            }
        """
        
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        target = strategy["target_allocation"]
        threshold = strategy["rebalance_threshold"]
        
        result = {
            "needed": False,
            "deviations": {},
            "max_deviation": 0.0,
            "actions": [],
        }
        
        # Рассчитываем отклонения
        for asset, target_pct in target.items():
            current_pct = current_allocation.get(asset, 0.0)
            deviation = current_pct - target_pct
            
            result["deviations"][asset] = {
                "current": current_pct,
                "target": target_pct,
                "deviation": deviation,
                "deviation_pct": abs(deviation),
            }
            
            result["max_deviation"] = max(result["max_deviation"], abs(deviation))
        
        # Проверяем, превышен ли порог
        if result["max_deviation"] > threshold:
            result["needed"] = True
            result["actions"] = self._generate_rebalance_actions(
                current_allocation,
                target
            )
        
        return result
    
    def _generate_rebalance_actions(
        self,
        current: Dict[str, float],
        target: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Генерировать действия для ребалансировки"""
        
        actions = []
        
        for asset, target_pct in target.items():
            current_pct = current.get(asset, 0.0)
            diff = target_pct - current_pct
            
            if abs(diff) > 0.5:  # Игнорируем малые отклонения
                if diff > 0:
                    actions.append({
                        "action": "buy",
                        "asset": asset,
                        "current_pct": current_pct,
                        "target_pct": target_pct,
                        "change_pct": diff,
                        "priority": abs(diff),
                    })
                else:
                    actions.append({
                        "action": "sell",
                        "asset": asset,
                        "current_pct": current_pct,
                        "target_pct": target_pct,
                        "change_pct": abs(diff),
                        "priority": abs(diff),
                    })
        
        # Сортируем по приоритету
        actions.sort(key=lambda x: x["priority"], reverse=True)
        
        return actions
    
    async def execute_rebalance(
        self,
        strategy_id: str,
        actions: List[Dict[str, Any]],
        portfolio_value: float,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Выполнить ребалансировку
        
        Args:
            strategy_id: ID стратегии
            actions: Действия для выполнения
            portfolio_value: Общая стоимость портфеля
            dry_run: Если True, только симуляция
        
        Returns:
            {
                "success": bool,
                "executed_actions": [...],
                "failed_actions": [...],
                "summary": {...}
            }
        """
        
        result = {
            "success": True,
            "executed_actions": [],
            "failed_actions": [],
            "summary": {
                "total_actions": len(actions),
                "successful": 0,
                "failed": 0,
                "total_volume": 0.0,
            },
        }
        
        for action in actions:
            # Рассчитываем объем
            change_pct = action["change_pct"]
            volume = portfolio_value * (change_pct / 100)
            
            action_result = {
                "action": action["action"],
                "asset": action["asset"],
                "volume": volume,
                "status": "pending",
            }
            
            if not dry_run:
                # Здесь должна быть реальная логика выполнения
                # Для примера просто помечаем как успешное
                action_result["status"] = "success"
                result["executed_actions"].append(action_result)
                result["summary"]["successful"] += 1
                result["summary"]["total_volume"] += volume
            else:
                action_result["status"] = "simulated"
                result["executed_actions"].append(action_result)
                result["summary"]["successful"] += 1
                result["summary"]["total_volume"] += volume
        
        # Записываем в историю
        if not dry_run:
            self.rebalance_history.append({
                "strategy_id": strategy_id,
                "timestamp": datetime.now().isoformat(),
                "actions": actions,
                "result": result,
            })
            
            # Обновляем время последней ребалансировки
            self.strategies[strategy_id]["last_rebalance"] = datetime.now().isoformat()
        
        return result
    
    def get_optimal_allocation(
        self,
        assets: List[str],
        risk_tolerance: str = "medium",
        investment_goal: str = "growth"
    ) -> Dict[str, float]:
        """
        Получить оптимальное распределение
        
        Args:
            assets: Список активов
            risk_tolerance: Толерантность к риску (low, medium, high)
            investment_goal: Цель инвестирования (preservation, income, growth)
        
        Returns:
            Оптимальное распределение (asset: percentage)
        """
        
        allocation = {}
        
        # Предопределенные стратегии
        if risk_tolerance == "low":
            # Консервативная стратегия
            if "USDT" in assets or "USDC" in assets:
                allocation["USDT"] = 60.0
            if "BTC" in assets:
                allocation["BTC"] = 25.0
            if "ETH" in assets:
                allocation["ETH"] = 15.0
        
        elif risk_tolerance == "high":
            # Агрессивная стратегия
            if "BTC" in assets:
                allocation["BTC"] = 30.0
            if "ETH" in assets:
                allocation["ETH"] = 30.0
            if "BNB" in assets:
                allocation["BNB"] = 20.0
            # Остальное в альткоины
            remaining = 20.0
            other_assets = [a for a in assets if a not in ["BTC", "ETH", "BNB"]]
            if other_assets:
                per_asset = remaining / len(other_assets)
                for asset in other_assets:
                    allocation[asset] = per_asset
        
        else:
            # Сбалансированная стратегия
            if "USDT" in assets or "USDC" in assets:
                allocation["USDT"] = 30.0
            if "BTC" in assets:
                allocation["BTC"] = 35.0
            if "ETH" in assets:
                allocation["ETH"] = 25.0
            if "BNB" in assets:
                allocation["BNB"] = 10.0
        
        # Нормализуем до 100%
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: (v / total) * 100 for k, v in allocation.items()}
        
        return allocation
    
    def format_rebalance_report(
        self,
        check_result: Dict[str, Any],
        execute_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """Форматировать отчет о ребалансировке"""
        
        lines = []
        
        lines.append("🔄 REBALANCE REPORT")
        lines.append("=" * 50)
        
        # Проверка необходимости
        lines.append(f"\n📊 Rebalance Needed: {'YES' if check_result['needed'] else 'NO'}")
        lines.append(f"Max Deviation: {check_result['max_deviation']:.2f}%")
        
        # Отклонения
        deviations = check_result.get("deviations", {})
        if deviations:
            lines.append("\n📈 DEVIATIONS:")
            for asset, dev in sorted(deviations.items(), key=lambda x: abs(x[1]["deviation"]), reverse=True):
                current = dev["current"]
                target = dev["target"]
                deviation = dev["deviation"]
                
                symbol = "▲" if deviation > 0 else "▼" if deviation < 0 else "="
                lines.append(f"  {symbol} {asset}: {current:.1f}% (target: {target:.1f}%, {deviation:+.1f}%)")
        
        # Действия
        actions = check_result.get("actions", [])
        if actions:
            lines.append("\n🎯 RECOMMENDED ACTIONS:")
            for i, action in enumerate(actions, 1):
                action_type = action["action"].upper()
                asset = action["asset"]
                change = action["change_pct"]
                
                lines.append(f"  {i}. {action_type} {asset}: {change:.2f}%")
        
        # Результат выполнения
        if execute_result:
            lines.append("\n✅ EXECUTION RESULT:")
            summary = execute_result.get("summary", {})
            lines.append(f"  Total Actions: {summary.get('total_actions', 0)}")
            lines.append(f"  Successful: {summary.get('successful', 0)}")
            lines.append(f"  Failed: {summary.get('failed', 0)}")
            lines.append(f"  Total Volume: ${summary.get('total_volume', 0):,.2f}")
        
        return "\n".join(lines)


class DynamicRebalancer:
    """Динамическая ребалансировка с учетом рыночных условий"""
    
    def __init__(self):
        pass
    
    async def calculate_dynamic_allocation(
        self,
        current_allocation: Dict[str, float],
        market_conditions: Dict[str, Any],
        risk_profile: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Рассчитать динамическое распределение
        
        Args:
            current_allocation: Текущее распределение
            market_conditions: Рыночные условия (volatility, trend, etc.)
            risk_profile: Профиль риска пользователя
        
        Returns:
            Новое оптимальное распределение
        """
        
        new_allocation = current_allocation.copy()
        
        # Анализируем рыночные условия
        volatility = market_conditions.get("volatility", "medium")
        trend = market_conditions.get("trend", "neutral")
        
        # Корректируем распределение
        if volatility == "high":
            # Увеличиваем долю стейблкоинов
            if "USDT" in new_allocation:
                new_allocation["USDT"] = min(new_allocation.get("USDT", 0) + 10, 70)
        
        if trend == "bullish":
            # Увеличиваем долю рисковых активов
            if "BTC" in new_allocation:
                new_allocation["BTC"] = min(new_allocation.get("BTC", 0) + 5, 50)
        
        elif trend == "bearish":
            # Уменьшаем долю рисковых активов
            if "BTC" in new_allocation:
                new_allocation["BTC"] = max(new_allocation.get("BTC", 0) - 5, 10)
        
        # Нормализуем
        total = sum(new_allocation.values())
        if total > 0:
            new_allocation = {k: (v / total) * 100 for k, v in new_allocation.items()}
        
        return new_allocation
    
    def calculate_rebalance_cost(
        self,
        actions: List[Dict[str, Any]],
        portfolio_value: float,
        fee_rate: float = 0.001
    ) -> Dict[str, Any]:
        """
        Рассчитать стоимость ребалансировки
        
        Args:
            actions: Действия для ребалансировки
            portfolio_value: Стоимость портфеля
            fee_rate: Ставка комиссии (0.1% = 0.001)
        
        Returns:
            {
                "total_cost": float,
                "trading_fees": float,
                "slippage": float,
                "gas_fees": float
            }
        """
        
        cost = {
            "total_cost": 0.0,
            "trading_fees": 0.0,
            "slippage": 0.0,
            "gas_fees": 0.0,
        }
        
        for action in actions:
            change_pct = action["change_pct"]
            volume = portfolio_value * (change_pct / 100)
            
            # Торговые комиссии
            trading_fee = volume * fee_rate
            cost["trading_fees"] += trading_fee
            
            # Проскальзывание (примерно 0.1%)
            slippage = volume * 0.001
            cost["slippage"] += slippage
            
            # Gas fees (примерно $5 за транзакцию)
            cost["gas_fees"] += 5.0
        
        cost["total_cost"] = cost["trading_fees"] + cost["slippage"] + cost["gas_fees"]
        
        return cost


class TaxOptimizedRebalancer:
    """Ребалансировка с учетом налогов"""
    
    def __init__(self):
        pass
    
    def calculate_tax_impact(
        self,
        actions: List[Dict[str, Any]],
        cost_basis: Dict[str, float],
        current_prices: Dict[str, float],
        tax_rate: float = 0.20
    ) -> Dict[str, Any]:
        """
        Рассчитать налоговое влияние
        
        Args:
            actions: Действия для ребалансировки
            cost_basis: Базовая стоимость активов
            current_prices: Текущие цены
            tax_rate: Ставка налога на прирост капитала
        
        Returns:
            {
                "total_tax": float,
                "by_asset": {...},
                "tax_loss_harvesting": [...]
            }
        """
        
        result = {
            "total_tax": 0.0,
            "by_asset": {},
            "tax_loss_harvesting": [],
        }
        
        for action in actions:
            if action["action"] == "sell":
                asset = action["asset"]
                
                if asset in cost_basis and asset in current_prices:
                    basis = cost_basis[asset]
                    current = current_prices[asset]
                    
                    # Прирост/убыток капитала
                    capital_gain = current - basis
                    
                    if capital_gain > 0:
                        # Прибыль - платим налог
                        tax = capital_gain * tax_rate
                        result["total_tax"] += tax
                        result["by_asset"][asset] = {
                            "capital_gain": capital_gain,
                            "tax": tax,
                        }
                    else:
                        # Убыток - можно использовать для tax loss harvesting
                        result["tax_loss_harvesting"].append({
                            "asset": asset,
                            "capital_loss": abs(capital_gain),
                            "tax_benefit": abs(capital_gain) * tax_rate,
                        })
        
        return result
    
    def optimize_for_taxes(
        self,
        actions: List[Dict[str, Any]],
        cost_basis: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Оптимизировать действия с учетом налогов
        
        Returns:
            Оптимизированный список действий
        """
        
        optimized = []
        
        for action in actions:
            if action["action"] == "sell":
                asset = action["asset"]
                
                if asset in cost_basis and asset in current_prices:
                    basis = cost_basis[asset]
                    current = current_prices[asset]
                    capital_gain = current - basis
                    
                    # Если большая прибыль, возможно стоит отложить продажу
                    if capital_gain > basis * 0.5:  # > 50% прибыль
                        action["tax_warning"] = "High capital gain - consider holding"
                        action["priority"] = action.get("priority", 0) * 0.5
            
            optimized.append(action)
        
        # Пересортируем по приоритету
        optimized.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return optimized
