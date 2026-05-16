# -*- coding: utf-8 -*-
"""
Dashboard Statistics v1.0.60
Дашборд со статистикой и аналитикой
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict


class DashboardStats:
    """Статистика для дашборда"""
    
    def __init__(self):
        self.stats_cache = {}
        self.cache_ttl = 300  # 5 минут
    
    async def get_portfolio_overview(
        self,
        addresses: List[str],
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Получить обзор портфеля
        
        Returns:
            {
                "total_wallets": int,
                "total_balance_usd": float,
                "total_tokens": int,
                "total_nfts": int,
                "chains": {...},
                "top_assets": [...],
                "distribution": {...}
            }
        """
        
        overview = {
            "total_wallets": len(addresses),
            "total_balance_usd": 0.0,
            "total_tokens": 0,
            "total_nfts": 0,
            "chains": {},
            "top_assets": [],
            "distribution": {},
        }
        
        # Собираем данные по всем кошелькам
        tasks = []
        for address in addresses:
            task = self._get_wallet_overview(address, session, timeout)
            tasks.append(task)
        
        wallet_overviews = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Агрегируем данные
        all_assets = defaultdict(float)
        
        for wallet_data in wallet_overviews:
            if isinstance(wallet_data, Exception):
                continue
            
            overview["total_balance_usd"] += wallet_data.get("balance_usd", 0)
            overview["total_tokens"] += wallet_data.get("tokens_count", 0)
            overview["total_nfts"] += wallet_data.get("nfts_count", 0)
            
            # По сетям
            for chain, balance in wallet_data.get("chains", {}).items():
                if chain not in overview["chains"]:
                    overview["chains"][chain] = 0.0
                overview["chains"][chain] += balance
            
            # Собираем активы
            for asset, amount in wallet_data.get("assets", {}).items():
                all_assets[asset] += amount
        
        # Топ активы
        sorted_assets = sorted(
            all_assets.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        overview["top_assets"] = [
            {"asset": asset, "amount": amount}
            for asset, amount in sorted_assets[:10]
        ]
        
        # Распределение по сетям
        total = overview["total_balance_usd"]
        if total > 0:
            overview["distribution"] = {
                chain: (balance / total) * 100
                for chain, balance in overview["chains"].items()
            }
        
        return overview
    
    async def _get_wallet_overview(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Получить обзор кошелька"""
        
        overview = {
            "address": address,
            "balance_usd": 0.0,
            "tokens_count": 0,
            "nfts_count": 0,
            "chains": {},
            "assets": {},
        }
        
        # Проверяем кэш
        cache_key = f"wallet_{address}"
        if cache_key in self.stats_cache:
            cached = self.stats_cache[cache_key]
            if datetime.now().timestamp() - cached["timestamp"] < self.cache_ttl:
                return cached["data"]
        
        # Получаем данные
        chains = ["ethereum", "bsc", "polygon", "arbitrum", "optimism"]
        
        for chain in chains:
            balance = await self._get_chain_balance(address, chain, session, timeout)
            if balance > 0:
                overview["chains"][chain] = balance
                overview["balance_usd"] += balance
        
        # Кэшируем
        self.stats_cache[cache_key] = {
            "timestamp": datetime.now().timestamp(),
            "data": overview,
        }
        
        return overview
    
    async def _get_chain_balance(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """Получить баланс на сети"""
        
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "bsc": "https://bsc-dataseed.binance.org",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return 0.0
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    balance_wei = int(result.get("result", "0x0"), 16)
                    balance = balance_wei / 1e18
                    
                    # Примерная цена (в реальности нужно получать через API)
                    prices = {
                        "ethereum": 2500,
                        "bsc": 300,
                        "polygon": 0.8,
                        "arbitrum": 2500,
                        "optimism": 2500,
                    }
                    
                    price = prices.get(chain, 0)
                    return balance * price
        
        except Exception:
            pass
        
        return 0.0
    
    async def get_performance_stats(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Получить статистику производительности
        
        Returns:
            {
                "period_days": int,
                "total_profit_loss": float,
                "total_profit_loss_pct": float,
                "best_performer": {...},
                "worst_performer": {...},
                "daily_changes": [...]
            }
        """
        
        stats = {
            "period_days": period_days,
            "total_profit_loss": 0.0,
            "total_profit_loss_pct": 0.0,
            "best_performer": None,
            "worst_performer": None,
            "daily_changes": [],
        }
        
        # Здесь должна быть реальная логика получения исторических данных
        # Для примера используем mock данные
        
        return stats
    
    async def get_activity_stats(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Получить статистику активности
        
        Returns:
            {
                "period_days": int,
                "total_transactions": int,
                "total_volume_usd": float,
                "unique_contracts": int,
                "unique_tokens": int,
                "gas_spent_usd": float,
                "by_chain": {...},
                "by_day": [...]
            }
        """
        
        stats = {
            "period_days": period_days,
            "total_transactions": 0,
            "total_volume_usd": 0.0,
            "unique_contracts": 0,
            "unique_tokens": 0,
            "gas_spent_usd": 0.0,
            "by_chain": {},
            "by_day": [],
        }
        
        # Здесь должна быть реальная логика
        
        return stats
    
    def format_dashboard_report(
        self,
        overview: Dict[str, Any],
        performance: Optional[Dict[str, Any]] = None,
        activity: Optional[Dict[str, Any]] = None
    ) -> str:
        """Форматировать отчет дашборда"""
        
        lines = []
        
        lines.append("📊 PORTFOLIO DASHBOARD")
        lines.append("=" * 50)
        
        # Обзор портфеля
        lines.append("\n💼 PORTFOLIO OVERVIEW:")
        lines.append(f"  👛 Total Wallets: {overview['total_wallets']}")
        lines.append(f"  💰 Total Balance: ${overview['total_balance_usd']:,.2f}")
        lines.append(f"  🪙 Total Tokens: {overview['total_tokens']}")
        lines.append(f"  🖼️ Total NFTs: {overview['total_nfts']}")
        
        # По сетям
        chains = overview.get("chains", {})
        if chains:
            lines.append("\n🔗 BY CHAIN:")
            for chain, balance in sorted(chains.items(), key=lambda x: x[1], reverse=True):
                pct = overview["distribution"].get(chain, 0)
                lines.append(f"  • {chain}: ${balance:,.2f} ({pct:.1f}%)")
        
        # Топ активы
        top_assets = overview.get("top_assets", [])
        if top_assets:
            lines.append("\n🏆 TOP ASSETS:")
            for i, asset_data in enumerate(top_assets[:5], 1):
                asset = asset_data["asset"]
                amount = asset_data["amount"]
                lines.append(f"  {i}. {asset}: {amount:,.6f}")
        
        # Производительность
        if performance:
            lines.append("\n📈 PERFORMANCE:")
            lines.append(f"  Period: {performance['period_days']} days")
            
            profit_loss = performance.get("total_profit_loss", 0)
            profit_loss_pct = performance.get("total_profit_loss_pct", 0)
            
            if profit_loss >= 0:
                lines.append(f"  💹 Profit: +${profit_loss:,.2f} (+{profit_loss_pct:.2f}%)")
            else:
                lines.append(f"  📉 Loss: ${profit_loss:,.2f} ({profit_loss_pct:.2f}%)")
        
        # Активность
        if activity:
            lines.append("\n⚡ ACTIVITY:")
            lines.append(f"  Period: {activity['period_days']} days")
            lines.append(f"  📊 Transactions: {activity['total_transactions']}")
            lines.append(f"  💵 Volume: ${activity['total_volume_usd']:,.2f}")
            lines.append(f"  ⛽ Gas Spent: ${activity['gas_spent_usd']:,.2f}")
            lines.append(f"  📝 Unique Contracts: {activity['unique_contracts']}")
            lines.append(f"  🪙 Unique Tokens: {activity['unique_tokens']}")
        
        return "\n".join(lines)


class ChartGenerator:
    """Генератор графиков (ASCII)"""
    
    @staticmethod
    def generate_bar_chart(
        data: Dict[str, float],
        title: str = "",
        width: int = 40
    ) -> str:
        """Генерировать столбчатую диаграмму"""
        
        if not data:
            return "No data"
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * len(title))
        
        # Находим максимум
        max_value = max(data.values())
        
        # Генерируем столбцы
        for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            bar_length = int((value / max_value) * width) if max_value > 0 else 0
            bar = "█" * bar_length
            lines.append(f"{label:15} {bar} {value:,.2f}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_line_chart(
        data: List[float],
        labels: Optional[List[str]] = None,
        title: str = "",
        height: int = 10,
        width: int = 50
    ) -> str:
        """Генерировать линейный график"""
        
        if not data:
            return "No data"
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * len(title))
        
        # Нормализуем данные
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Создаем сетку
        grid = [[" " for _ in range(width)] for _ in range(height)]
        
        # Рисуем линию
        for i, value in enumerate(data):
            if i >= width:
                break
            
            normalized = (value - min_val) / range_val
            y = int(normalized * (height - 1))
            y = height - 1 - y  # Инвертируем Y
            
            grid[y][i] = "●"
        
        # Выводим сетку
        for row in grid:
            lines.append("".join(row))
        
        # Добавляем ось X
        if labels:
            lines.append("-" * width)
            lines.append(" ".join(labels[:width]))
        
        # Добавляем значения
        lines.append(f"Min: {min_val:.2f}  Max: {max_val:.2f}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_pie_chart(
        data: Dict[str, float],
        title: str = ""
    ) -> str:
        """Генерировать круговую диаграмму (текстовую)"""
        
        if not data:
            return "No data"
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * len(title))
        
        total = sum(data.values())
        
        for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total) * 100 if total > 0 else 0
            bar_length = int(pct / 2)  # 50 символов = 100%
            bar = "█" * bar_length
            lines.append(f"{label:15} {bar} {pct:5.1f}%")
        
        return "\n".join(lines)


class MetricsCalculator:
    """Калькулятор метрик"""
    
    @staticmethod
    def calculate_roi(
        initial_value: float,
        current_value: float
    ) -> float:
        """Рассчитать ROI (Return on Investment)"""
        
        if initial_value == 0:
            return 0.0
        
        return ((current_value - initial_value) / initial_value) * 100
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """Рассчитать коэффициент Шарпа"""
        
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        
        # Стандартное отклонение
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        return (avg_return - risk_free_rate) / std_dev
    
    @staticmethod
    def calculate_max_drawdown(
        values: List[float]
    ) -> float:
        """Рассчитать максимальную просадку"""
        
        if not values:
            return 0.0
        
        max_value = values[0]
        max_drawdown = 0.0
        
        for value in values:
            if value > max_value:
                max_value = value
            
            drawdown = (max_value - value) / max_value if max_value > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100
    
    @staticmethod
    def calculate_volatility(
        values: List[float]
    ) -> float:
        """Рассчитать волатильность"""
        
        if len(values) < 2:
            return 0.0
        
        # Рассчитываем доходности
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                ret = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Стандартное отклонение доходностей
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        
        return (variance ** 0.5) * 100
