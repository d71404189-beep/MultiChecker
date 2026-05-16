# -*- coding: utf-8 -*-
"""
Historical Analysis v1.0.59
Исторический анализ балансов кошельков
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple


class HistoricalAnalysis:
    """Исторический анализ кошельков"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 600  # 10 минут
    
    async def analyze_wallet_history(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Полный исторический анализ кошелька
        
        Returns:
            {
                "current_balance": float,
                "max_balance": float,
                "max_balance_date": str,
                "min_balance": float,
                "min_balance_date": str,
                "balance_changes": [...],
                "profit_loss": float,
                "profit_loss_pct": float,
                "chart_data": [...],
            }
        """
        
        analysis = {
            "current_balance": 0.0,
            "max_balance": 0.0,
            "max_balance_date": None,
            "min_balance": 0.0,
            "min_balance_date": None,
            "balance_changes": [],
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "chart_data": [],
        }
        
        try:
            if chain in ["ethereum", "bsc", "polygon", "arbitrum", "optimism"]:
                analysis = await self._analyze_evm_history(address, chain, session, timeout)
            elif chain == "bitcoin":
                analysis = await self._analyze_btc_history(address, session, timeout)
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_evm_history(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ истории EVM кошелька"""
        
        analysis = {
            "current_balance": 0.0,
            "max_balance": 0.0,
            "max_balance_date": None,
            "min_balance": float('inf'),
            "min_balance_date": None,
            "balance_changes": [],
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "chart_data": [],
        }
        
        # API endpoints
        api_urls = {
            "ethereum": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "polygon": "https://api.polygonscan.com/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api",
        }
        
        api_url = api_urls.get(chain, api_urls["ethereum"])
        
        try:
            # Получаем все транзакции
            url = f"{api_url}?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=10000&sort=asc"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("status") == "1" and data.get("result"):
                        txs = data["result"]
                        
                        # Симулируем изменение баланса
                        running_balance = 0.0
                        balance_history = []
                        
                        for tx in txs:
                            timestamp = int(tx.get("timeStamp", 0))
                            value = int(tx.get("value", 0)) / 1e18
                            is_incoming = tx.get("to", "").lower() == address.lower()
                            
                            # Обновляем баланс
                            if is_incoming:
                                running_balance += value
                            else:
                                running_balance -= value
                                # Вычитаем gas
                                gas_used = int(tx.get("gasUsed", 0))
                                gas_price = int(tx.get("gasPrice", 0))
                                gas_cost = (gas_used * gas_price) / 1e18
                                running_balance -= gas_cost
                            
                            # Сохраняем точку
                            balance_history.append({
                                "timestamp": timestamp,
                                "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
                                "balance": running_balance,
                                "change": value if is_incoming else -value,
                                "tx_hash": tx.get("hash", ""),
                            })
                            
                            # Обновляем макс/мин
                            if running_balance > analysis["max_balance"]:
                                analysis["max_balance"] = running_balance
                                analysis["max_balance_date"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                            
                            if running_balance < analysis["min_balance"]:
                                analysis["min_balance"] = running_balance
                                analysis["min_balance_date"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                        
                        # Текущий баланс (последняя точка)
                        if balance_history:
                            analysis["current_balance"] = balance_history[-1]["balance"]
                            
                            # Profit/Loss
                            first_balance = balance_history[0]["balance"]
                            if first_balance > 0:
                                analysis["profit_loss"] = analysis["current_balance"] - first_balance
                                analysis["profit_loss_pct"] = (analysis["profit_loss"] / first_balance) * 100
                        
                        # Сохраняем историю
                        analysis["balance_changes"] = balance_history[-100:]  # Последние 100
                        
                        # Данные для графика (агрегируем по дням)
                        analysis["chart_data"] = self._aggregate_chart_data(balance_history)
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_btc_history(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ истории Bitcoin кошелька"""
        
        analysis = {
            "current_balance": 0.0,
            "max_balance": 0.0,
            "max_balance_date": None,
            "min_balance": float('inf'),
            "min_balance_date": None,
            "balance_changes": [],
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "chart_data": [],
        }
        
        try:
            # Получаем транзакции
            url = f"https://mempool.space/api/address/{address}/txs"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    txs = await resp.json()
                    
                    # Симулируем баланс
                    running_balance = 0.0
                    balance_history = []
                    
                    # Сортируем по времени
                    txs_sorted = sorted(
                        txs,
                        key=lambda x: x.get("status", {}).get("block_time", 0)
                    )
                    
                    for tx in txs_sorted:
                        timestamp = tx.get("status", {}).get("block_time", 0)
                        
                        if not timestamp:
                            continue
                        
                        # Считаем изменение баланса
                        change = 0.0
                        
                        # Входящие
                        for vout in tx.get("vout", []):
                            if vout.get("scriptpubkey_address") == address:
                                change += vout.get("value", 0) / 1e8
                        
                        # Исходящие
                        for vin in tx.get("vin", []):
                            if vin.get("prevout", {}).get("scriptpubkey_address") == address:
                                change -= vin.get("prevout", {}).get("value", 0) / 1e8
                        
                        running_balance += change
                        
                        # Сохраняем точку
                        balance_history.append({
                            "timestamp": timestamp,
                            "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
                            "balance": running_balance,
                            "change": change,
                            "tx_hash": tx.get("txid", ""),
                        })
                        
                        # Обновляем макс/мин
                        if running_balance > analysis["max_balance"]:
                            analysis["max_balance"] = running_balance
                            analysis["max_balance_date"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                        
                        if running_balance < analysis["min_balance"]:
                            analysis["min_balance"] = running_balance
                            analysis["min_balance_date"] = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    
                    # Текущий баланс
                    if balance_history:
                        analysis["current_balance"] = balance_history[-1]["balance"]
                        
                        # Profit/Loss
                        first_balance = balance_history[0]["balance"]
                        if first_balance > 0:
                            analysis["profit_loss"] = analysis["current_balance"] - first_balance
                            analysis["profit_loss_pct"] = (analysis["profit_loss"] / first_balance) * 100
                    
                    # Сохраняем историю
                    analysis["balance_changes"] = balance_history[-100:]
                    
                    # График
                    analysis["chart_data"] = self._aggregate_chart_data(balance_history)
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    def _aggregate_chart_data(
        self,
        balance_history: List[Dict[str, Any]],
        max_points: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Агрегировать данные для графика
        
        Группирует по дням и берет последнее значение дня
        """
        
        if not balance_history:
            return []
        
        # Группируем по дням
        by_date = {}
        
        for point in balance_history:
            date = point["date"]
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(point)
        
        # Берем последнее значение каждого дня
        chart_data = []
        for date in sorted(by_date.keys()):
            points = by_date[date]
            last_point = points[-1]
            
            chart_data.append({
                "date": date,
                "balance": last_point["balance"],
            })
        
        # Если точек слишком много - прореживаем
        if len(chart_data) > max_points:
            step = len(chart_data) // max_points
            chart_data = chart_data[::step]
        
        return chart_data
    
    def format_history_report(self, analysis: Dict[str, Any], chain: str) -> str:
        """Форматировать отчет истории"""
        
        if "error" in analysis:
            return f"❌ History analysis error: {analysis['error']}"
        
        lines = []
        
        lines.append("📈 HISTORICAL ANALYSIS")
        lines.append("=" * 50)
        
        # Текущий баланс
        current = analysis["current_balance"]
        lines.append(f"💰 Current Balance: {current:.8f}")
        
        # Максимальный баланс
        max_bal = analysis["max_balance"]
        max_date = analysis["max_balance_date"]
        if max_date:
            lines.append(f"📊 Max Balance: {max_bal:.8f} (on {max_date})")
            
            # Сколько потеряно с пика
            if current < max_bal:
                loss = max_bal - current
                loss_pct = (loss / max_bal) * 100
                lines.append(f"📉 Lost from peak: {loss:.8f} (-{loss_pct:.1f}%)")
        
        # Минимальный баланс
        min_bal = analysis["min_balance"]
        min_date = analysis["min_balance_date"]
        if min_date and min_bal != float('inf'):
            lines.append(f"📊 Min Balance: {min_bal:.8f} (on {min_date})")
            
            # Сколько заработано с минимума
            if current > min_bal:
                gain = current - min_bal
                gain_pct = (gain / min_bal) * 100 if min_bal > 0 else 0
                lines.append(f"📈 Gained from bottom: {gain:.8f} (+{gain_pct:.1f}%)")
        
        # Profit/Loss
        profit_loss = analysis["profit_loss"]
        profit_loss_pct = analysis["profit_loss_pct"]
        
        if profit_loss != 0:
            if profit_loss > 0:
                lines.append(f"💹 Total Profit: +{profit_loss:.8f} (+{profit_loss_pct:.1f}%)")
            else:
                lines.append(f"📉 Total Loss: {profit_loss:.8f} ({profit_loss_pct:.1f}%)")
        
        # Последние изменения
        balance_changes = analysis["balance_changes"]
        if balance_changes:
            lines.append(f"\n🔄 Recent Changes (last 5):")
            for change in balance_changes[-5:]:
                date = change["date"]
                balance = change["balance"]
                delta = change["change"]
                direction = "📥" if delta > 0 else "📤"
                lines.append(f"  {direction} {date}: {balance:.8f} ({delta:+.8f})")
        
        # График (ASCII)
        chart_data = analysis["chart_data"]
        if len(chart_data) > 5:
            lines.append("\n📊 Balance Chart (last 10 days):")
            lines.append(self._generate_ascii_chart(chart_data[-10:]))
        
        return "\n".join(lines)
    
    def _generate_ascii_chart(self, chart_data: List[Dict[str, Any]]) -> str:
        """Генерировать ASCII график"""
        
        if not chart_data:
            return "No data"
        
        # Находим мин/макс для масштабирования
        balances = [point["balance"] for point in chart_data]
        min_bal = min(balances)
        max_bal = max(balances)
        
        if max_bal == min_bal:
            return "Balance unchanged"
        
        # Высота графика
        height = 10
        
        # Масштабируем значения
        scaled = []
        for balance in balances:
            normalized = (balance - min_bal) / (max_bal - min_bal)
            scaled_value = int(normalized * height)
            scaled.append(scaled_value)
        
        # Рисуем график
        lines = []
        
        for row in range(height, -1, -1):
            line = ""
            for value in scaled:
                if value >= row:
                    line += "█"
                else:
                    line += " "
            
            # Добавляем метку значения
            if row == height:
                label = f" {max_bal:.4f}"
            elif row == 0:
                label = f" {min_bal:.4f}"
            else:
                label = ""
            
            lines.append(line + label)
        
        # Добавляем ось X (даты)
        dates_line = ""
        for i, point in enumerate(chart_data):
            if i % 2 == 0:  # Каждая вторая дата
                date = point["date"][-5:]  # MM-DD
                dates_line += date[:2]
            else:
                dates_line += "  "
        
        lines.append("─" * len(scaled))
        lines.append(dates_line)
        
        return "\n".join(lines)
    
    async def compare_wallets(
        self,
        addresses: List[str],
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Сравнить несколько кошельков
        
        Returns:
            {
                "wallets": [...],
                "best_performer": {...},
                "worst_performer": {...},
            }
        """
        
        comparison = {
            "wallets": [],
            "best_performer": None,
            "worst_performer": None,
        }
        
        # Анализируем каждый кошелек
        tasks = []
        for address in addresses:
            task = self.analyze_wallet_history(address, chain, session, timeout)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        best_profit = float('-inf')
        worst_profit = float('inf')
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            
            wallet_data = {
                "address": addresses[i],
                "current_balance": result.get("current_balance", 0),
                "max_balance": result.get("max_balance", 0),
                "profit_loss": result.get("profit_loss", 0),
                "profit_loss_pct": result.get("profit_loss_pct", 0),
            }
            
            comparison["wallets"].append(wallet_data)
            
            # Определяем лучший/худший
            profit = result.get("profit_loss", 0)
            
            if profit > best_profit:
                best_profit = profit
                comparison["best_performer"] = wallet_data
            
            if profit < worst_profit:
                worst_profit = profit
                comparison["worst_performer"] = wallet_data
        
        return comparison
