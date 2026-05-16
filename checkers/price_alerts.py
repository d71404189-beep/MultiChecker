# -*- coding: utf-8 -*-
"""
Price Alerts & Predictions v1.0.61
Ценовые алерты и прогнозы
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import statistics


class PriceAlertManager:
    """Менеджер ценовых алертов"""
    
    def __init__(self):
        self.alerts = {}
        self.alert_history = []
    
    def create_alert(
        self,
        alert_id: str,
        asset: str,
        condition_type: str,
        target_price: float,
        notification_channels: Optional[List[str]] = None
    ):
        """
        Создать ценовой алерт
        
        Args:
            alert_id: ID алерта
            asset: Актив (BTC, ETH, etc.)
            condition_type: Тип условия (above, below, change_pct)
            target_price: Целевая цена или процент изменения
            notification_channels: Каналы уведомлений (telegram, discord, email)
        """
        
        self.alerts[alert_id] = {
            "asset": asset,
            "condition_type": condition_type,
            "target_price": target_price,
            "notification_channels": notification_channels or ["telegram"],
            "created_at": datetime.now().isoformat(),
            "triggered": False,
            "triggered_at": None,
        }
    
    async def check_alerts(
        self,
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Проверить алерты
        
        Args:
            current_prices: Текущие цены (asset: price)
        
        Returns:
            Список сработавших алертов
        """
        
        triggered_alerts = []
        
        for alert_id, alert in self.alerts.items():
            if alert["triggered"]:
                continue
            
            asset = alert["asset"]
            condition = alert["condition_type"]
            target = alert["target_price"]
            
            if asset not in current_prices:
                continue
            
            current_price = current_prices[asset]
            triggered = False
            
            if condition == "above" and current_price > target:
                triggered = True
            elif condition == "below" and current_price < target:
                triggered = True
            elif condition == "change_pct":
                # Нужна базовая цена для расчета изменения
                # Для примера используем простую проверку
                triggered = False
            
            if triggered:
                alert["triggered"] = True
                alert["triggered_at"] = datetime.now().isoformat()
                alert["triggered_price"] = current_price
                
                triggered_alerts.append({
                    "alert_id": alert_id,
                    "asset": asset,
                    "condition": condition,
                    "target_price": target,
                    "current_price": current_price,
                    "notification_channels": alert["notification_channels"],
                })
                
                self.alert_history.append({
                    "alert_id": alert_id,
                    "triggered_at": alert["triggered_at"],
                    "asset": asset,
                    "price": current_price,
                })
        
        return triggered_alerts
    
    def delete_alert(self, alert_id: str) -> bool:
        """Удалить алерт"""
        
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return True
        
        return False
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Получить активные алерты"""
        
        return [
            {
                "alert_id": alert_id,
                **alert
            }
            for alert_id, alert in self.alerts.items()
            if not alert["triggered"]
        ]
    
    def get_alert_history(
        self,
        asset: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить историю алертов"""
        
        history = self.alert_history
        
        if asset:
            history = [h for h in history if h["asset"] == asset]
        
        return history[-limit:]


class PricePredictionEngine:
    """Движок прогнозирования цен"""
    
    def __init__(self):
        pass
    
    async def predict_price(
        self,
        asset: str,
        historical_prices: List[float],
        horizon: int = 7
    ) -> Dict[str, Any]:
        """
        Прогнозировать цену
        
        Args:
            asset: Актив
            historical_prices: Исторические цены
            horizon: Горизонт прогноза (дней)
        
        Returns:
            {
                "predictions": [...],
                "confidence": float,
                "method": str,
                "support_levels": [...],
                "resistance_levels": [...]
            }
        """
        
        if len(historical_prices) < 30:
            return {
                "predictions": [],
                "confidence": 0.0,
                "method": "insufficient_data",
                "support_levels": [],
                "resistance_levels": [],
            }
        
        # Используем простую линейную экстраполяцию
        predictions = self._linear_extrapolation(historical_prices, horizon)
        
        # Рассчитываем уровни поддержки и сопротивления
        support_levels = self._calculate_support_levels(historical_prices)
        resistance_levels = self._calculate_resistance_levels(historical_prices)
        
        # Оценка уверенности на основе волатильности
        volatility = self._calculate_volatility(historical_prices)
        confidence = max(0, min(100, 100 - volatility * 10))
        
        return {
            "predictions": predictions,
            "confidence": confidence,
            "method": "linear_extrapolation",
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
        }
    
    def _linear_extrapolation(
        self,
        prices: List[float],
        horizon: int
    ) -> List[Dict[str, Any]]:
        """Линейная экстраполяция"""
        
        # Используем последние 30 дней для тренда
        recent_prices = prices[-30:]
        
        # Простая линейная регрессия
        x = list(range(len(recent_prices)))
        y = recent_prices
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x)))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Прогнозируем
        predictions = []
        last_x = len(recent_prices) - 1
        
        for i in range(1, horizon + 1):
            predicted_price = slope * (last_x + i) + intercept
            
            # Добавляем дату
            prediction_date = datetime.now() + timedelta(days=i)
            
            predictions.append({
                "date": prediction_date.strftime("%Y-%m-%d"),
                "price": max(0, predicted_price),  # Цена не может быть отрицательной
                "day": i,
            })
        
        return predictions
    
    def _calculate_support_levels(
        self,
        prices: List[float],
        num_levels: int = 3
    ) -> List[float]:
        """Рассчитать уровни поддержки"""
        
        # Находим локальные минимумы
        local_mins = []
        
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                local_mins.append(prices[i])
        
        if not local_mins:
            return []
        
        # Кластеризуем близкие уровни
        local_mins.sort()
        
        support_levels = []
        current_cluster = [local_mins[0]]
        
        for price in local_mins[1:]:
            if price - current_cluster[-1] < current_cluster[-1] * 0.02:  # 2% разница
                current_cluster.append(price)
            else:
                support_levels.append(statistics.mean(current_cluster))
                current_cluster = [price]
        
        if current_cluster:
            support_levels.append(statistics.mean(current_cluster))
        
        return support_levels[:num_levels]
    
    def _calculate_resistance_levels(
        self,
        prices: List[float],
        num_levels: int = 3
    ) -> List[float]:
        """Рассчитать уровни сопротивления"""
        
        # Находим локальные максимумы
        local_maxs = []
        
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                local_maxs.append(prices[i])
        
        if not local_maxs:
            return []
        
        # Кластеризуем близкие уровни
        local_maxs.sort()
        
        resistance_levels = []
        current_cluster = [local_maxs[0]]
        
        for price in local_maxs[1:]:
            if price - current_cluster[-1] < current_cluster[-1] * 0.02:  # 2% разница
                current_cluster.append(price)
            else:
                resistance_levels.append(statistics.mean(current_cluster))
                current_cluster = [price]
        
        if current_cluster:
            resistance_levels.append(statistics.mean(current_cluster))
        
        return resistance_levels[:num_levels]
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Рассчитать волатильность"""
        
        if len(prices) < 2:
            return 0.0
        
        # Рассчитываем доходности
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Стандартное отклонение доходностей
        return statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    async def predict_trend(
        self,
        asset: str,
        historical_prices: List[float]
    ) -> Dict[str, Any]:
        """
        Прогнозировать тренд
        
        Returns:
            {
                "trend": str (bullish, bearish, neutral),
                "strength": float (0-100),
                "probability": float (0-100),
                "indicators": {...}
            }
        """
        
        if len(historical_prices) < 20:
            return {
                "trend": "unknown",
                "strength": 0.0,
                "probability": 0.0,
                "indicators": {},
            }
        
        # Анализируем тренд
        recent = historical_prices[-20:]
        
        # Простая линейная регрессия
        x = list(range(len(recent)))
        y = recent
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x)))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Определяем тренд
        if slope > 0.01:
            trend = "bullish"
        elif slope < -0.01:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Сила тренда (R²)
        y_pred = [slope * (i - x_mean) + y_mean for i in x]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(len(y)))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(len(y)))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        strength = max(0, min(100, r_squared * 100))
        
        # Вероятность продолжения тренда
        probability = strength * 0.8  # Консервативная оценка
        
        return {
            "trend": trend,
            "strength": strength,
            "probability": probability,
            "indicators": {
                "slope": slope,
                "r_squared": r_squared,
            },
        }


class SmartAlertEngine:
    """Умный движок алертов"""
    
    def __init__(self):
        self.alert_manager = PriceAlertManager()
        self.prediction_engine = PricePredictionEngine()
    
    async def create_smart_alert(
        self,
        alert_id: str,
        asset: str,
        strategy: str,
        parameters: Dict[str, Any]
    ):
        """
        Создать умный алерт
        
        Args:
            alert_id: ID алерта
            asset: Актив
            strategy: Стратегия (breakout, support_bounce, resistance_break, etc.)
            parameters: Параметры стратегии
        """
        
        if strategy == "breakout":
            # Алерт на пробой уровня
            level = parameters.get("level")
            direction = parameters.get("direction", "up")
            
            condition = "above" if direction == "up" else "below"
            self.alert_manager.create_alert(
                alert_id,
                asset,
                condition,
                level,
                parameters.get("notification_channels")
            )
        
        elif strategy == "trend_reversal":
            # Алерт на разворот тренда
            # Требует более сложной логики
            pass
        
        elif strategy == "volatility_spike":
            # Алерт на всплеск волатильности
            pass
    
    async def analyze_and_suggest_alerts(
        self,
        asset: str,
        historical_prices: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Анализировать и предлагать алерты
        
        Returns:
            Список предложенных алертов
        """
        
        suggestions = []
        
        # Прогнозируем цену
        prediction = await self.prediction_engine.predict_price(
            asset,
            historical_prices,
            horizon=7
        )
        
        # Предлагаем алерты на уровнях поддержки
        for support in prediction.get("support_levels", []):
            suggestions.append({
                "type": "support_level",
                "asset": asset,
                "price": support,
                "reason": f"Уровень поддержки на ${support:.2f}",
                "priority": "medium",
            })
        
        # Предлагаем алерты на уровнях сопротивления
        for resistance in prediction.get("resistance_levels", []):
            suggestions.append({
                "type": "resistance_level",
                "asset": asset,
                "price": resistance,
                "reason": f"Уровень сопротивления на ${resistance:.2f}",
                "priority": "medium",
            })
        
        # Предлагаем алерт на прогнозируемую цену
        if prediction.get("predictions"):
            last_prediction = prediction["predictions"][-1]
            suggestions.append({
                "type": "price_target",
                "asset": asset,
                "price": last_prediction["price"],
                "reason": f"Прогнозируемая цена через 7 дней: ${last_prediction['price']:.2f}",
                "priority": "low",
            })
        
        return suggestions
    
    def format_alert_report(
        self,
        triggered_alerts: List[Dict[str, Any]]
    ) -> str:
        """Форматировать отчет об алертах"""
        
        if not triggered_alerts:
            return "✅ No alerts triggered"
        
        lines = []
        
        lines.append("🔔 PRICE ALERTS TRIGGERED")
        lines.append("=" * 50)
        
        for alert in triggered_alerts:
            asset = alert["asset"]
            condition = alert["condition"]
            target = alert["target_price"]
            current = alert["current_price"]
            
            lines.append(f"\n🚨 {asset}")
            lines.append(f"  Condition: {condition.upper()}")
            lines.append(f"  Target: ${target:,.2f}")
            lines.append(f"  Current: ${current:,.2f}")
            
            if condition == "above":
                change = ((current - target) / target) * 100
                lines.append(f"  Change: +{change:.2f}%")
            elif condition == "below":
                change = ((target - current) / target) * 100
                lines.append(f"  Change: -{change:.2f}%")
        
        return "\n".join(lines)
    
    def format_prediction_report(
        self,
        asset: str,
        prediction: Dict[str, Any]
    ) -> str:
        """Форматировать отчет прогноза"""
        
        lines = []
        
        lines.append(f"🔮 PRICE PREDICTION: {asset}")
        lines.append("=" * 50)
        
        # Метод и уверенность
        method = prediction.get("method", "unknown")
        confidence = prediction.get("confidence", 0)
        lines.append(f"\nMethod: {method}")
        lines.append(f"Confidence: {confidence:.0f}%")
        
        # Прогнозы
        predictions = prediction.get("predictions", [])
        if predictions:
            lines.append("\n📈 PREDICTIONS:")
            for pred in predictions[:7]:
                date = pred["date"]
                price = pred["price"]
                day = pred["day"]
                lines.append(f"  Day {day} ({date}): ${price:,.2f}")
        
        # Уровни поддержки
        support = prediction.get("support_levels", [])
        if support:
            lines.append("\n📉 SUPPORT LEVELS:")
            for level in support:
                lines.append(f"  • ${level:,.2f}")
        
        # Уровни сопротивления
        resistance = prediction.get("resistance_levels", [])
        if resistance:
            lines.append("\n📈 RESISTANCE LEVELS:")
            for level in resistance:
                lines.append(f"  • ${level:,.2f}")
        
        return "\n".join(lines)


class MarketSignalDetector:
    """Детектор рыночных сигналов"""
    
    def __init__(self):
        pass
    
    def detect_signals(
        self,
        asset: str,
        historical_prices: List[float],
        volume: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Обнаружить рыночные сигналы
        
        Returns:
            Список обнаруженных сигналов
        """
        
        signals = []
        
        if len(historical_prices) < 20:
            return signals
        
        # 1. Золотой крест / Мертвый крест
        ma_short = statistics.mean(historical_prices[-7:])
        ma_long = statistics.mean(historical_prices[-30:])
        
        if ma_short > ma_long * 1.02:
            signals.append({
                "type": "golden_cross",
                "signal": "bullish",
                "strength": "strong",
                "description": "Краткосрочная MA пересекла долгосрочную снизу вверх",
            })
        elif ma_short < ma_long * 0.98:
            signals.append({
                "type": "death_cross",
                "signal": "bearish",
                "strength": "strong",
                "description": "Краткосрочная MA пересекла долгосрочную сверху вниз",
            })
        
        # 2. Перекупленность / Перепроданность (RSI)
        rsi = self._calculate_rsi(historical_prices)
        
        if rsi > 70:
            signals.append({
                "type": "overbought",
                "signal": "bearish",
                "strength": "medium",
                "description": f"RSI = {rsi:.0f} (перекупленность)",
            })
        elif rsi < 30:
            signals.append({
                "type": "oversold",
                "signal": "bullish",
                "strength": "medium",
                "description": f"RSI = {rsi:.0f} (перепроданность)",
            })
        
        # 3. Пробой уровня
        current_price = historical_prices[-1]
        recent_high = max(historical_prices[-30:])
        recent_low = min(historical_prices[-30:])
        
        if current_price > recent_high * 0.99:
            signals.append({
                "type": "breakout_high",
                "signal": "bullish",
                "strength": "strong",
                "description": f"Пробой максимума ${recent_high:.2f}",
            })
        elif current_price < recent_low * 1.01:
            signals.append({
                "type": "breakdown_low",
                "signal": "bearish",
                "strength": "strong",
                "description": f"Пробой минимума ${recent_low:.2f}",
            })
        
        return signals
    
    def _calculate_rsi(
        self,
        prices: List[float],
        period: int = 14
    ) -> float:
        """Рассчитать RSI"""
        
        if len(prices) < period + 1:
            return 50.0
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [max(0, change) for change in changes[-period:]]
        losses = [abs(min(0, change)) for change in changes[-period:]]
        
        avg_gain = statistics.mean(gains) if gains else 0
        avg_loss = statistics.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
