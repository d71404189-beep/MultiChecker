# -*- coding: utf-8 -*-
"""
Advanced Analytics v1.0.61
Продвинутая аналитика портфеля
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class AdvancedAnalytics:
    """Продвинутая аналитика"""
    
    def __init__(self):
        self.cache = {}
    
    async def perform_full_analysis(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Полный анализ портфеля
        
        Returns:
            {
                "correlation_analysis": {...},
                "risk_metrics": {...},
                "performance_attribution": {...},
                "market_exposure": {...},
                "liquidity_analysis": {...}
            }
        """
        
        analysis = {}
        
        # 1. Корреляционный анализ
        analysis["correlation_analysis"] = await self._correlation_analysis(
            addresses, period_days, session
        )
        
        # 2. Метрики риска
        analysis["risk_metrics"] = await self._calculate_risk_metrics(
            addresses, period_days, session
        )
        
        # 3. Атрибуция производительности
        analysis["performance_attribution"] = await self._performance_attribution(
            addresses, period_days, session
        )
        
        # 4. Рыночная экспозиция
        analysis["market_exposure"] = await self._market_exposure_analysis(
            addresses, session
        )
        
        # 5. Анализ ликвидности
        analysis["liquidity_analysis"] = await self._liquidity_analysis(
            addresses, session
        )
        
        return analysis
    
    async def _correlation_analysis(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Корреляционный анализ активов"""
        
        correlation = {
            "matrix": {},
            "highly_correlated": [],
            "diversification_benefit": 0.0,
        }
        
        # Здесь должна быть реальная логика расчета корреляции
        # Для примера используем mock данные
        
        assets = ["BTC", "ETH", "BNB", "MATIC"]
        
        # Матрица корреляции (mock)
        correlation["matrix"] = {
            "BTC": {"BTC": 1.0, "ETH": 0.85, "BNB": 0.75, "MATIC": 0.70},
            "ETH": {"BTC": 0.85, "ETH": 1.0, "BNB": 0.80, "MATIC": 0.75},
            "BNB": {"BTC": 0.75, "ETH": 0.80, "BNB": 1.0, "MATIC": 0.65},
            "MATIC": {"BTC": 0.70, "ETH": 0.75, "BNB": 0.65, "MATIC": 1.0},
        }
        
        # Высоко коррелированные пары
        for asset1 in assets:
            for asset2 in assets:
                if asset1 < asset2:  # Избегаем дубликатов
                    corr = correlation["matrix"][asset1][asset2]
                    if corr > 0.8:
                        correlation["highly_correlated"].append({
                            "pair": f"{asset1}-{asset2}",
                            "correlation": corr,
                        })
        
        # Польза от диверсификации
        avg_correlation = statistics.mean([
            correlation["matrix"][a1][a2]
            for a1 in assets
            for a2 in assets
            if a1 != a2
        ])
        
        correlation["diversification_benefit"] = (1 - avg_correlation) * 100
        
        return correlation
    
    async def _calculate_risk_metrics(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Расчет метрик риска"""
        
        metrics = {
            "var_95": 0.0,  # Value at Risk (95%)
            "cvar_95": 0.0,  # Conditional VaR (95%)
            "beta": 0.0,  # Beta к рынку
            "alpha": 0.0,  # Alpha
            "information_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
        }
        
        # Mock данные для демонстрации
        # В реальности нужно получать исторические данные
        
        # Value at Risk (95% confidence)
        # VaR показывает максимальную потерю с вероятностью 95%
        metrics["var_95"] = 5.2  # 5.2% потенциальная потеря
        
        # Conditional VaR (ожидаемая потеря при превышении VaR)
        metrics["cvar_95"] = 7.8  # 7.8% ожидаемая потеря
        
        # Beta (чувствительность к рынку)
        # Beta = 1: движется с рынком
        # Beta > 1: более волатилен чем рынок
        # Beta < 1: менее волатилен чем рынок
        metrics["beta"] = 1.15
        
        # Alpha (избыточная доходность)
        # Alpha > 0: превосходит рынок
        # Alpha < 0: отстает от рынка
        metrics["alpha"] = 2.3  # 2.3% годовых
        
        # Information Ratio (качество активного управления)
        metrics["information_ratio"] = 0.85
        
        # Sortino Ratio (доходность к downside риску)
        metrics["sortino_ratio"] = 1.45
        
        # Calmar Ratio (доходность к максимальной просадке)
        metrics["calmar_ratio"] = 1.20
        
        return metrics
    
    async def _performance_attribution(
        self,
        addresses: List[str],
        period_days: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Атрибуция производительности"""
        
        attribution = {
            "total_return": 0.0,
            "by_asset": {},
            "by_sector": {},
            "by_chain": {},
            "top_contributors": [],
            "top_detractors": [],
        }
        
        # Mock данные
        attribution["total_return"] = 15.5  # 15.5% за период
        
        # По активам
        attribution["by_asset"] = {
            "ETH": 8.2,  # ETH принес 8.2% из 15.5%
            "BTC": 4.5,
            "BNB": 2.3,
            "MATIC": 0.5,
        }
        
        # По секторам
        attribution["by_sector"] = {
            "Layer 1": 10.5,
            "DeFi": 3.2,
            "Stablecoins": 1.8,
        }
        
        # По сетям
        attribution["by_chain"] = {
            "Ethereum": 9.5,
            "BSC": 3.8,
            "Polygon": 2.2,
        }
        
        # Топ контрибьюторы
        attribution["top_contributors"] = [
            {"asset": "ETH", "contribution": 8.2},
            {"asset": "BTC", "contribution": 4.5},
            {"asset": "BNB", "contribution": 2.3},
        ]
        
        # Топ детракторы (отрицательный вклад)
        attribution["top_detractors"] = [
            {"asset": "SHIB", "contribution": -0.5},
        ]
        
        return attribution
    
    async def _market_exposure_analysis(
        self,
        addresses: List[str],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Анализ рыночной экспозиции"""
        
        exposure = {
            "by_market_cap": {},
            "by_sector": {},
            "by_geography": {},
            "concentration_risk": 0.0,
        }
        
        # По капитализации
        exposure["by_market_cap"] = {
            "large_cap": 65.0,  # > $10B
            "mid_cap": 25.0,    # $1B - $10B
            "small_cap": 10.0,  # < $1B
        }
        
        # По секторам
        exposure["by_sector"] = {
            "Layer 1": 45.0,
            "DeFi": 25.0,
            "NFT": 10.0,
            "Gaming": 8.0,
            "Stablecoins": 12.0,
        }
        
        # По географии (где базируются проекты)
        exposure["by_geography"] = {
            "USA": 35.0,
            "Europe": 25.0,
            "Asia": 30.0,
            "Other": 10.0,
        }
        
        # Риск концентрации (Herfindahl Index)
        exposure["concentration_risk"] = 0.28  # 0-1, чем ниже тем лучше
        
        return exposure
    
    async def _liquidity_analysis(
        self,
        addresses: List[str],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Анализ ликвидности"""
        
        liquidity = {
            "overall_score": 0.0,
            "by_asset": {},
            "illiquid_assets": [],
            "time_to_liquidate": {},
        }
        
        # Общий скор ликвидности (0-100)
        liquidity["overall_score"] = 85.0
        
        # По активам
        liquidity["by_asset"] = {
            "ETH": 95.0,  # Очень ликвидный
            "BTC": 98.0,
            "BNB": 90.0,
            "MATIC": 85.0,
            "SHIB": 70.0,
        }
        
        # Неликвидные активы
        liquidity["illiquid_assets"] = [
            {"asset": "SHIB", "liquidity_score": 70.0, "reason": "Низкий объем торгов"},
        ]
        
        # Время до полной ликвидации (без значительного влияния на цену)
        liquidity["time_to_liquidate"] = {
            "50%": "< 1 hour",
            "75%": "< 4 hours",
            "100%": "< 24 hours",
        }
        
        return liquidity
    
    def format_analytics_report(self, analysis: Dict[str, Any]) -> str:
        """Форматировать отчет аналитики"""
        
        lines = []
        
        lines.append("📊 ADVANCED ANALYTICS REPORT")
        lines.append("=" * 50)
        
        # Корреляционный анализ
        correlation = analysis.get("correlation_analysis", {})
        if correlation:
            lines.append("\n🔗 CORRELATION ANALYSIS:")
            
            div_benefit = correlation.get("diversification_benefit", 0)
            lines.append(f"  Diversification Benefit: {div_benefit:.1f}%")
            
            highly_corr = correlation.get("highly_correlated", [])
            if highly_corr:
                lines.append("\n  Highly Correlated Pairs:")
                for pair in highly_corr[:5]:
                    lines.append(f"    • {pair['pair']}: {pair['correlation']:.2f}")
        
        # Метрики риска
        risk = analysis.get("risk_metrics", {})
        if risk:
            lines.append("\n⚠️ RISK METRICS:")
            lines.append(f"  VaR (95%): {risk.get('var_95', 0):.2f}%")
            lines.append(f"  CVaR (95%): {risk.get('cvar_95', 0):.2f}%")
            lines.append(f"  Beta: {risk.get('beta', 0):.2f}")
            lines.append(f"  Alpha: {risk.get('alpha', 0):.2f}%")
            lines.append(f"  Sharpe Ratio: {risk.get('information_ratio', 0):.2f}")
            lines.append(f"  Sortino Ratio: {risk.get('sortino_ratio', 0):.2f}")
        
        # Атрибуция производительности
        perf = analysis.get("performance_attribution", {})
        if perf:
            lines.append("\n📈 PERFORMANCE ATTRIBUTION:")
            lines.append(f"  Total Return: {perf.get('total_return', 0):.2f}%")
            
            top_contrib = perf.get("top_contributors", [])
            if top_contrib:
                lines.append("\n  Top Contributors:")
                for contrib in top_contrib[:3]:
                    lines.append(f"    • {contrib['asset']}: +{contrib['contribution']:.2f}%")
        
        # Рыночная экспозиция
        exposure = analysis.get("market_exposure", {})
        if exposure:
            lines.append("\n🌐 MARKET EXPOSURE:")
            
            by_cap = exposure.get("by_market_cap", {})
            if by_cap:
                lines.append("  By Market Cap:")
                for cap_type, pct in by_cap.items():
                    lines.append(f"    • {cap_type}: {pct:.1f}%")
            
            by_sector = exposure.get("by_sector", {})
            if by_sector:
                lines.append("\n  By Sector:")
                for sector, pct in sorted(by_sector.items(), key=lambda x: x[1], reverse=True)[:5]:
                    lines.append(f"    • {sector}: {pct:.1f}%")
        
        # Ликвидность
        liquidity = analysis.get("liquidity_analysis", {})
        if liquidity:
            lines.append("\n💧 LIQUIDITY ANALYSIS:")
            lines.append(f"  Overall Score: {liquidity.get('overall_score', 0):.0f}/100")
            
            time_to_liq = liquidity.get("time_to_liquidate", {})
            if time_to_liq:
                lines.append("\n  Time to Liquidate:")
                for pct, time in time_to_liq.items():
                    lines.append(f"    • {pct}: {time}")
        
        return "\n".join(lines)


class TechnicalAnalysis:
    """Технический анализ"""
    
    def __init__(self):
        pass
    
    def calculate_moving_averages(
        self,
        prices: List[float],
        periods: List[int] = [7, 30, 90]
    ) -> Dict[int, float]:
        """Рассчитать скользящие средние"""
        
        mas = {}
        
        for period in periods:
            if len(prices) >= period:
                ma = statistics.mean(prices[-period:])
                mas[period] = ma
        
        return mas
    
    def calculate_rsi(
        self,
        prices: List[float],
        period: int = 14
    ) -> float:
        """
        Рассчитать RSI (Relative Strength Index)
        
        Returns:
            RSI значение (0-100)
        """
        if len(prices) < period + 1:
            return 50.0
        
        # Рассчитываем изменения цен
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Разделяем на прибыли и убытки
        gains = [max(0, change) for change in changes[-period:]]
        losses = [abs(min(0, change)) for change in changes[-period:]]
        
        # Средние прибыли и убытки
        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def detect_trend(
        self,
        prices: List[float],
        window: int = 20
    ) -> Dict[str, Any]:
        """
        Определить тренд
        
        Returns:
            {
                "direction": str (up, down, sideways),
                "strength": float (0-100),
                "support": float,
                "resistance": float
            }
        """
        if len(prices) < window:
            return {
                "direction": "unknown",
                "strength": 0.0,
                "support": 0.0,
                "resistance": 0.0,
            }
        
        recent_prices = prices[-window:]
        
        # Линейная регрессия для определения тренда
        x = list(range(len(recent_prices)))
        y = recent_prices
        
        # Простой расчет наклона
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x)))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Определение направления
        if slope > 0.01:
            direction = "up"
        elif slope < -0.01:
            direction = "down"
        else:
            direction = "sideways"
        
        # Сила тренда (на основе R²)
        y_pred = [slope * (i - x_mean) + y_mean for i in x]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(len(y)))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(len(y)))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        strength = max(0, min(100, r_squared * 100))
        
        # Поддержка и сопротивление
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        return {
            "direction": direction,
            "strength": strength,
            "support": support,
            "resistance": resistance,
        }
    
    def detect_patterns(
        self,
        prices: List[float]
    ) -> List[Dict[str, Any]]:
        """Обнаружить паттерны"""
        
        patterns = []
        
        if len(prices) < 10:
            return patterns
        
        # Двойное дно
        if self._is_double_bottom(prices):
            patterns.append({
                "type": "double_bottom",
                "signal": "bullish",
                "confidence": 0.75,
            })
        
        # Двойная вершина
        if self._is_double_top(prices):
            patterns.append({
                "type": "double_top",
                "signal": "bearish",
                "confidence": 0.75,
            })
        
        # Голова и плечи
        if self._is_head_and_shoulders(prices):
            patterns.append({
                "type": "head_and_shoulders",
                "signal": "bearish",
                "confidence": 0.80,
            })
        
        return patterns
    
    def _is_double_bottom(self, prices: List[float]) -> bool:
        """Проверка на двойное дно"""
        # Упрощенная проверка
        if len(prices) < 10:
            return False
        
        recent = prices[-10:]
        min_price = min(recent)
        min_indices = [i for i, p in enumerate(recent) if abs(p - min_price) < min_price * 0.02]
        
        return len(min_indices) >= 2 and (min_indices[-1] - min_indices[0]) >= 3
    
    def _is_double_top(self, prices: List[float]) -> bool:
        """Проверка на двойную вершину"""
        if len(prices) < 10:
            return False
        
        recent = prices[-10:]
        max_price = max(recent)
        max_indices = [i for i, p in enumerate(recent) if abs(p - max_price) < max_price * 0.02]
        
        return len(max_indices) >= 2 and (max_indices[-1] - max_indices[0]) >= 3
    
    def _is_head_and_shoulders(self, prices: List[float]) -> bool:
        """Проверка на голову и плечи"""
        if len(prices) < 15:
            return False
        
        # Упрощенная проверка: ищем 3 пика, где средний выше остальных
        recent = prices[-15:]
        
        # Находим локальные максимумы
        peaks = []
        for i in range(1, len(recent) - 1):
            if recent[i] > recent[i-1] and recent[i] > recent[i+1]:
                peaks.append((i, recent[i]))
        
        if len(peaks) >= 3:
            # Проверяем, что средний пик выше остальных
            sorted_peaks = sorted(peaks, key=lambda x: x[1], reverse=True)
            highest = sorted_peaks[0]
            
            # Средний пик должен быть в середине
            if 4 < highest[0] < len(recent) - 4:
                return True
        
        return False


class SentimentAnalysis:
    """Анализ настроений рынка"""
    
    def __init__(self):
        pass
    
    def analyze_market_sentiment(
        self,
        asset: str
    ) -> Dict[str, Any]:
        """
        Анализ настроений рынка
        
        Returns:
            {
                "sentiment": str (bullish, bearish, neutral),
                "score": float (-100 to 100),
                "indicators": {...}
            }
        """
        # Mock данные для демонстрации
        sentiment = {
            "sentiment": "bullish",
            "score": 65.0,  # Положительный настрой
            "indicators": {
                "social_media": 70.0,
                "news": 60.0,
                "trading_volume": 65.0,
                "whale_activity": 55.0,
            },
        }
        
        return sentiment
    
    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Индекс страха и жадности
        
        Returns:
            {
                "value": int (0-100),
                "classification": str,
                "description": str
            }
        """
        # Mock данные
        value = 65
        
        if value >= 75:
            classification = "Extreme Greed"
        elif value >= 55:
            classification = "Greed"
        elif value >= 45:
            classification = "Neutral"
        elif value >= 25:
            classification = "Fear"
        else:
            classification = "Extreme Fear"
        
        return {
            "value": value,
            "classification": classification,
            "description": f"Market is in {classification} zone",
        }
