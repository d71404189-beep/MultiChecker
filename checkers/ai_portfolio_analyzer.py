# -*- coding: utf-8 -*-
"""
AI-Powered Portfolio Analyzer v1.0.61
AI анализ портфеля с рекомендациями
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import hashlib


class AIPortfolioAnalyzer:
    """AI анализатор портфеля"""
    
    def __init__(self):
        self.analysis_cache = {}
        self.models = {
            "risk_assessment": "gpt-4",
            "diversification": "gpt-4",
            "recommendations": "gpt-4",
        }
    
    async def analyze_portfolio(
        self,
        portfolio_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Полный AI анализ портфеля
        
        Args:
            portfolio_data: Данные портфеля
            user_profile: Профиль пользователя (риск-толерантность, цели)
        
        Returns:
            {
                "risk_score": float,
                "diversification_score": float,
                "health_score": float,
                "recommendations": [...],
                "warnings": [...],
                "opportunities": [...],
                "ai_insights": str
            }
        """
        
        analysis = {
            "risk_score": 0.0,
            "diversification_score": 0.0,
            "health_score": 0.0,
            "recommendations": [],
            "warnings": [],
            "opportunities": [],
            "ai_insights": "",
        }
        
        # 1. Оценка риска
        risk_analysis = await self._analyze_risk(portfolio_data, user_profile)
        analysis["risk_score"] = risk_analysis["score"]
        analysis["warnings"].extend(risk_analysis.get("warnings", []))
        
        # 2. Анализ диверсификации
        diversification = await self._analyze_diversification(portfolio_data)
        analysis["diversification_score"] = diversification["score"]
        analysis["recommendations"].extend(diversification.get("recommendations", []))
        
        # 3. Общее здоровье портфеля
        health = await self._analyze_health(portfolio_data)
        analysis["health_score"] = health["score"]
        
        # 4. Поиск возможностей
        opportunities = await self._find_opportunities(portfolio_data)
        analysis["opportunities"] = opportunities
        
        # 5. AI инсайты
        ai_insights = await self._generate_ai_insights(
            portfolio_data,
            risk_analysis,
            diversification,
            health,
            user_profile
        )
        analysis["ai_insights"] = ai_insights
        
        return analysis
    
    async def _analyze_risk(
        self,
        portfolio_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Анализ рисков портфеля"""
        
        risk_analysis = {
            "score": 0.0,
            "level": "unknown",
            "factors": {},
            "warnings": [],
        }
        
        total_value = portfolio_data.get("total_balance_usd", 0)
        assets = portfolio_data.get("assets", {})
        chains = portfolio_data.get("chains", {})
        
        # Факторы риска
        risk_factors = []
        
        # 1. Концентрация в одном активе
        if assets:
            max_asset_value = max(assets.values()) if assets else 0
            concentration = (max_asset_value / total_value * 100) if total_value > 0 else 0
            
            if concentration > 50:
                risk_factors.append({
                    "type": "high_concentration",
                    "severity": "high",
                    "value": concentration,
                    "description": f"Высокая концентрация в одном активе: {concentration:.1f}%"
                })
                risk_analysis["warnings"].append(
                    f"⚠️ Высокая концентрация: {concentration:.1f}% в одном активе"
                )
        
        # 2. Концентрация в одной сети
        if chains:
            max_chain_value = max(chains.values()) if chains else 0
            chain_concentration = (max_chain_value / total_value * 100) if total_value > 0 else 0
            
            if chain_concentration > 70:
                risk_factors.append({
                    "type": "chain_concentration",
                    "severity": "medium",
                    "value": chain_concentration,
                    "description": f"Концентрация в одной сети: {chain_concentration:.1f}%"
                })
        
        # 3. Волатильные активы
        volatile_assets = ["DOGE", "SHIB", "PEPE", "FLOKI"]
        volatile_value = sum(
            value for asset, value in assets.items()
            if any(vol in asset.upper() for vol in volatile_assets)
        )
        volatile_pct = (volatile_value / total_value * 100) if total_value > 0 else 0
        
        if volatile_pct > 20:
            risk_factors.append({
                "type": "high_volatility",
                "severity": "medium",
                "value": volatile_pct,
                "description": f"Высокая доля волатильных активов: {volatile_pct:.1f}%"
            })
        
        # 4. Малая капитализация
        small_cap_threshold = 1000  # < $1000
        if total_value < small_cap_threshold:
            risk_factors.append({
                "type": "small_portfolio",
                "severity": "low",
                "value": total_value,
                "description": f"Малый размер портфеля: ${total_value:.2f}"
            })
        
        # Расчет общего риск-скора
        risk_score = 0.0
        for factor in risk_factors:
            if factor["severity"] == "high":
                risk_score += 30
            elif factor["severity"] == "medium":
                risk_score += 20
            elif factor["severity"] == "low":
                risk_score += 10
        
        risk_score = min(risk_score, 100)
        risk_analysis["score"] = risk_score
        risk_analysis["factors"] = risk_factors
        
        # Определение уровня риска
        if risk_score < 30:
            risk_analysis["level"] = "low"
        elif risk_score < 60:
            risk_analysis["level"] = "medium"
        else:
            risk_analysis["level"] = "high"
        
        return risk_analysis
    
    async def _analyze_diversification(
        self,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Анализ диверсификации"""
        
        diversification = {
            "score": 0.0,
            "level": "unknown",
            "metrics": {},
            "recommendations": [],
        }
        
        assets = portfolio_data.get("assets", {})
        chains = portfolio_data.get("chains", {})
        total_value = portfolio_data.get("total_balance_usd", 0)
        
        # Метрики диверсификации
        
        # 1. Количество активов
        num_assets = len(assets)
        diversification["metrics"]["num_assets"] = num_assets
        
        if num_assets < 3:
            diversification["recommendations"].append(
                "💡 Рекомендуется увеличить количество активов до 5-10"
            )
        
        # 2. Количество сетей
        num_chains = len(chains)
        diversification["metrics"]["num_chains"] = num_chains
        
        if num_chains < 2:
            diversification["recommendations"].append(
                "💡 Рекомендуется диверсифицировать по нескольким сетям"
            )
        
        # 3. Индекс Херфиндаля (концентрация)
        if assets and total_value > 0:
            herfindahl_index = sum(
                (value / total_value) ** 2
                for value in assets.values()
            )
            diversification["metrics"]["herfindahl_index"] = herfindahl_index
            
            # Чем ниже индекс, тем лучше диверсификация
            # 1.0 = полная концентрация, 0.1 = хорошая диверсификация
            if herfindahl_index > 0.5:
                diversification["recommendations"].append(
                    "💡 Портфель слишком концентрирован, рекомендуется ребалансировка"
                )
        
        # 4. Баланс между типами активов
        # Определяем типы активов
        stablecoins = ["USDT", "USDC", "DAI", "BUSD"]
        blue_chips = ["BTC", "ETH", "BNB"]
        
        stable_value = sum(
            value for asset, value in assets.items()
            if any(stable in asset.upper() for stable in stablecoins)
        )
        blue_chip_value = sum(
            value for asset, value in assets.items()
            if any(blue in asset.upper() for blue in blue_chips)
        )
        
        stable_pct = (stable_value / total_value * 100) if total_value > 0 else 0
        blue_chip_pct = (blue_chip_value / total_value * 100) if total_value > 0 else 0
        
        diversification["metrics"]["stable_pct"] = stable_pct
        diversification["metrics"]["blue_chip_pct"] = blue_chip_pct
        
        if stable_pct < 10:
            diversification["recommendations"].append(
                "💡 Рекомендуется добавить стейблкоины для снижения волатильности"
            )
        
        if blue_chip_pct < 30:
            diversification["recommendations"].append(
                "💡 Рекомендуется увеличить долю blue-chip активов (BTC, ETH)"
            )
        
        # Расчет общего скора диверсификации
        score = 0.0
        
        # Количество активов (макс 30 баллов)
        score += min(num_assets * 5, 30)
        
        # Количество сетей (макс 20 баллов)
        score += min(num_chains * 10, 20)
        
        # Индекс Херфиндаля (макс 30 баллов)
        if "herfindahl_index" in diversification["metrics"]:
            herfindahl = diversification["metrics"]["herfindahl_index"]
            score += max(0, 30 - herfindahl * 30)
        
        # Баланс типов активов (макс 20 баллов)
        if stable_pct > 10:
            score += 10
        if blue_chip_pct > 30:
            score += 10
        
        diversification["score"] = min(score, 100)
        
        # Определение уровня
        if score >= 70:
            diversification["level"] = "excellent"
        elif score >= 50:
            diversification["level"] = "good"
        elif score >= 30:
            diversification["level"] = "fair"
        else:
            diversification["level"] = "poor"
        
        return diversification
    
    async def _analyze_health(
        self,
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Анализ общего здоровья портфеля"""
        
        health = {
            "score": 0.0,
            "status": "unknown",
            "indicators": {},
        }
        
        total_value = portfolio_data.get("total_balance_usd", 0)
        
        # Индикаторы здоровья
        
        # 1. Размер портфеля
        if total_value > 100000:
            health["indicators"]["size"] = "large"
            size_score = 30
        elif total_value > 10000:
            health["indicators"]["size"] = "medium"
            size_score = 20
        elif total_value > 1000:
            health["indicators"]["size"] = "small"
            size_score = 10
        else:
            health["indicators"]["size"] = "micro"
            size_score = 5
        
        # 2. Активность (если есть данные)
        activity_score = 20  # По умолчанию средняя активность
        
        # 3. Производительность (если есть данные)
        performance_score = 25  # По умолчанию нейтральная
        
        # 4. Ликвидность
        # Предполагаем, что большинство активов ликвидны
        liquidity_score = 25
        
        # Общий скор
        health["score"] = size_score + activity_score + performance_score + liquidity_score
        
        # Статус
        if health["score"] >= 80:
            health["status"] = "excellent"
        elif health["score"] >= 60:
            health["status"] = "good"
        elif health["score"] >= 40:
            health["status"] = "fair"
        else:
            health["status"] = "poor"
        
        return health
    
    async def _find_opportunities(
        self,
        portfolio_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Поиск возможностей для улучшения"""
        
        opportunities = []
        
        assets = portfolio_data.get("assets", {})
        chains = portfolio_data.get("chains", {})
        total_value = portfolio_data.get("total_balance_usd", 0)
        
        # 1. Стейкинг возможности
        stakeable_assets = ["ETH", "BNB", "MATIC", "ATOM", "DOT", "ADA"]
        for asset in stakeable_assets:
            if any(asset in a.upper() for a in assets.keys()):
                opportunities.append({
                    "type": "staking",
                    "asset": asset,
                    "potential_apy": "4-8%",
                    "description": f"Можно застейкать {asset} и получать пассивный доход",
                    "priority": "high",
                })
        
        # 2. Yield farming
        if total_value > 1000:
            opportunities.append({
                "type": "yield_farming",
                "protocol": "Aave",
                "potential_apy": "3-6%",
                "description": "Можно использовать Aave для lending и получения процентов",
                "priority": "medium",
            })
        
        # 3. Ребалансировка
        if assets:
            max_asset_value = max(assets.values())
            concentration = (max_asset_value / total_value * 100) if total_value > 0 else 0
            
            if concentration > 60:
                opportunities.append({
                    "type": "rebalancing",
                    "description": "Рекомендуется ребалансировка для снижения концентрации",
                    "priority": "high",
                })
        
        # 4. Новые сети
        if len(chains) < 3:
            new_chains = ["Arbitrum", "Optimism", "Base"]
            opportunities.append({
                "type": "expansion",
                "chains": new_chains,
                "description": f"Рассмотрите диверсификацию на {', '.join(new_chains)}",
                "priority": "medium",
            })
        
        # 5. DeFi протоколы
        opportunities.append({
            "type": "defi",
            "protocols": ["Uniswap", "Curve", "Convex"],
            "description": "Можно использовать DeFi протоколы для дополнительного дохода",
            "priority": "low",
        })
        
        return opportunities
    
    async def _generate_ai_insights(
        self,
        portfolio_data: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        diversification: Dict[str, Any],
        health: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """Генерация AI инсайтов"""
        
        insights = []
        
        # Общая оценка
        insights.append("📊 ОБЩАЯ ОЦЕНКА ПОРТФЕЛЯ:")
        insights.append("")
        
        # Здоровье
        health_status = health["status"]
        health_score = health["score"]
        insights.append(f"Здоровье портфеля: {health_status.upper()} ({health_score:.0f}/100)")
        
        # Риск
        risk_level = risk_analysis["level"]
        risk_score = risk_analysis["score"]
        insights.append(f"Уровень риска: {risk_level.upper()} ({risk_score:.0f}/100)")
        
        # Диверсификация
        div_level = diversification["level"]
        div_score = diversification["score"]
        insights.append(f"Диверсификация: {div_level.upper()} ({div_score:.0f}/100)")
        
        insights.append("")
        insights.append("💡 КЛЮЧЕВЫЕ РЕКОМЕНДАЦИИ:")
        insights.append("")
        
        # Рекомендации на основе анализа
        if risk_score > 60:
            insights.append("1. ⚠️ ВЫСОКИЙ РИСК: Рекомендуется снизить концентрацию и добавить стейблкоины")
        elif risk_score > 30:
            insights.append("1. ⚡ СРЕДНИЙ РИСК: Портфель сбалансирован, но есть возможности для улучшения")
        else:
            insights.append("1. ✅ НИЗКИЙ РИСК: Портфель хорошо защищен от волатильности")
        
        if div_score < 50:
            insights.append("2. 📊 Улучшите диверсификацию: добавьте больше активов и сетей")
        else:
            insights.append("2. ✅ Диверсификация на хорошем уровне")
        
        if health_score < 60:
            insights.append("3. 💊 Рекомендуется увеличить размер портфеля и активность")
        
        insights.append("")
        insights.append("🎯 СТРАТЕГИЯ:")
        insights.append("")
        
        # Стратегия на основе профиля
        if user_profile:
            risk_tolerance = user_profile.get("risk_tolerance", "medium")
            
            if risk_tolerance == "low":
                insights.append("• Консервативная стратегия: 60% стейблкоины, 30% blue-chips, 10% альткоины")
            elif risk_tolerance == "high":
                insights.append("• Агрессивная стратегия: 20% стейблкоины, 40% blue-chips, 40% альткоины")
            else:
                insights.append("• Сбалансированная стратегия: 30% стейблкоины, 50% blue-chips, 20% альткоины")
        else:
            insights.append("• Рекомендуется сбалансированная стратегия для оптимального соотношения риск/доходность")
        
        return "\n".join(insights)
    
    def format_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """Форматировать отчет анализа"""
        
        lines = []
        
        lines.append("🤖 AI PORTFOLIO ANALYSIS")
        lines.append("=" * 50)
        
        # Скоры
        lines.append("\n📊 SCORES:")
        lines.append(f"  Health: {analysis['health_score']:.0f}/100")
        lines.append(f"  Risk: {analysis['risk_score']:.0f}/100")
        lines.append(f"  Diversification: {analysis['diversification_score']:.0f}/100")
        
        # Предупреждения
        warnings = analysis.get("warnings", [])
        if warnings:
            lines.append("\n⚠️ WARNINGS:")
            for warning in warnings:
                lines.append(f"  {warning}")
        
        # Рекомендации
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            lines.append("\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                lines.append(f"  {rec}")
        
        # Возможности
        opportunities = analysis.get("opportunities", [])
        if opportunities:
            lines.append("\n🎯 OPPORTUNITIES:")
            for opp in opportunities[:5]:
                opp_type = opp.get("type", "unknown")
                desc = opp.get("description", "")
                priority = opp.get("priority", "medium")
                
                priority_icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                lines.append(f"  {priority_icon} {opp_type.upper()}: {desc}")
        
        # AI инсайты
        ai_insights = analysis.get("ai_insights", "")
        if ai_insights:
            lines.append("\n" + ai_insights)
        
        return "\n".join(lines)


class SmartRecommendationEngine:
    """Умный движок рекомендаций"""
    
    def __init__(self):
        pass
    
    def generate_personalized_recommendations(
        self,
        portfolio_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Генерация персонализированных рекомендаций"""
        
        recommendations = []
        
        risk_tolerance = user_profile.get("risk_tolerance", "medium")
        investment_goal = user_profile.get("goal", "growth")
        time_horizon = user_profile.get("time_horizon", "medium")  # short, medium, long
        
        # Рекомендации на основе профиля
        
        if investment_goal == "income":
            # Фокус на доход
            recommendations.append({
                "type": "strategy",
                "title": "Стратегия пассивного дохода",
                "actions": [
                    "Застейкать ETH в Lido (4-5% APY)",
                    "Использовать Aave для lending (3-6% APY)",
                    "Добавить yield farming на Curve",
                ],
                "expected_return": "4-8% годовых",
            })
        
        elif investment_goal == "growth":
            # Фокус на рост
            recommendations.append({
                "type": "strategy",
                "title": "Стратегия роста капитала",
                "actions": [
                    "Увеличить долю blue-chip активов (BTC, ETH)",
                    "Диверсифицировать в перспективные L2 (Arbitrum, Optimism)",
                    "Рассмотреть DeFi протоколы с высоким потенциалом",
                ],
                "expected_return": "15-30% годовых (высокий риск)",
            })
        
        elif investment_goal == "preservation":
            # Фокус на сохранение
            recommendations.append({
                "type": "strategy",
                "title": "Консервативная стратегия",
                "actions": [
                    "Увеличить долю стейблкоинов до 60-70%",
                    "Использовать только проверенные протоколы (Aave, Compound)",
                    "Минимизировать exposure к волатильным активам",
                ],
                "expected_return": "2-5% годовых (низкий риск)",
            })
        
        return recommendations
    
    def suggest_rebalancing(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Предложить ребалансировку"""
        
        actions = []
        
        for asset, target_pct in target_allocation.items():
            current_pct = current_allocation.get(asset, 0)
            diff = target_pct - current_pct
            
            if abs(diff) > 5:  # Разница больше 5%
                if diff > 0:
                    actions.append({
                        "action": "buy",
                        "asset": asset,
                        "amount_pct": diff,
                        "reason": f"Увеличить долю {asset} до {target_pct:.1f}%",
                    })
                else:
                    actions.append({
                        "action": "sell",
                        "asset": asset,
                        "amount_pct": abs(diff),
                        "reason": f"Уменьшить долю {asset} до {target_pct:.1f}%",
                    })
        
        return actions
