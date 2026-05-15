# -*- coding: utf-8 -*-
"""
Wallet Analyzer v1.0.56
Умный анализ кошельков: whale/trader/holder, история транзакций, PnL анализ
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════
#  WALLET TYPE DETECTION
# ═══════════════════════════════════════════════════════════════════════════

class WalletTypeDetector:
    """Определение типа кошелька: Whale, Trader, Holder, Bot"""
    
    # Пороги для классификации
    WHALE_THRESHOLD_USD = 100000  # $100k+
    TRADER_TX_COUNT = 100  # 100+ транзакций
    TRADER_FREQUENCY_DAYS = 7  # Активность в последние 7 дней
    HOLDER_MIN_AGE_DAYS = 180  # 6+ месяцев без активности
    BOT_TX_PATTERN_THRESHOLD = 0.8  # 80% похожих транзакций
    
    @staticmethod
    async def detect_wallet_type(
        address: str,
        balance_usd: float,
        transactions: List[Dict],
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Определить тип кошелька
        
        Returns:
            Dict: {
                "type": "whale" | "trader" | "holder" | "bot" | "new",
                "confidence": 0.95,
                "characteristics": {
                    "balance_usd": 150000,
                    "tx_count": 250,
                    "age_days": 365,
                    "activity_score": 8.5,
                    "trading_frequency": "high",
                    "avg_tx_value": 5000
                },
                "labels": ["whale", "active_trader", "defi_user"]
            }
        """
        
        result = {
            "type": "unknown",
            "confidence": 0.0,
            "characteristics": {},
            "labels": []
        }
        
        if not transactions:
            result["type"] = "new"
            result["confidence"] = 0.9
            return result
        
        # Анализируем характеристики
        chars = WalletTypeDetector._analyze_characteristics(
            address, balance_usd, transactions
        )
        result["characteristics"] = chars
        
        # Определяем тип
        scores = {
            "whale": 0.0,
            "trader": 0.0,
            "holder": 0.0,
            "bot": 0.0
        }
        
        # Whale detection
        if chars["balance_usd"] >= WalletTypeDetector.WHALE_THRESHOLD_USD:
            scores["whale"] += 0.5
        if chars["max_tx_value"] >= 50000:
            scores["whale"] += 0.3
        if chars["avg_tx_value"] >= 10000:
            scores["whale"] += 0.2
        
        # Trader detection
        if chars["tx_count"] >= WalletTypeDetector.TRADER_TX_COUNT:
            scores["trader"] += 0.4
        if chars["days_since_last_tx"] <= WalletTypeDetector.TRADER_FREQUENCY_DAYS:
            scores["trader"] += 0.3
        if chars["trading_frequency"] == "high":
            scores["trader"] += 0.3
        
        # Holder detection
        if chars["age_days"] >= WalletTypeDetector.HOLDER_MIN_AGE_DAYS:
            scores["holder"] += 0.4
        if chars["days_since_last_tx"] >= 30:
            scores["holder"] += 0.3
        if chars["tx_count"] < 20:
            scores["holder"] += 0.3
        
        # Bot detection
        if chars["pattern_similarity"] >= WalletTypeDetector.BOT_TX_PATTERN_THRESHOLD:
            scores["bot"] += 0.5
        if chars["tx_count"] >= 500:
            scores["bot"] += 0.3
        if chars["avg_tx_interval_minutes"] < 5:
            scores["bot"] += 0.2
        
        # Выбираем тип с максимальным score
        wallet_type = max(scores, key=scores.get)
        confidence = scores[wallet_type]
        
        result["type"] = wallet_type
        result["confidence"] = min(confidence, 1.0)
        
        # Добавляем labels
        result["labels"] = WalletTypeDetector._generate_labels(chars, scores)
        
        return result
    
    @staticmethod
    def _analyze_characteristics(
        address: str,
        balance_usd: float,
        transactions: List[Dict]
    ) -> Dict[str, Any]:
        """Анализировать характеристики кошелька"""
        
        if not transactions:
            return {
                "balance_usd": balance_usd,
                "tx_count": 0,
                "age_days": 0,
                "days_since_last_tx": 0,
                "activity_score": 0,
                "trading_frequency": "none",
                "avg_tx_value": 0,
                "max_tx_value": 0,
                "pattern_similarity": 0,
                "avg_tx_interval_minutes": 0
            }
        
        # Сортируем по времени
        sorted_txs = sorted(transactions, key=lambda x: x.get("timestamp", 0))
        
        # Возраст кошелька
        first_tx_time = sorted_txs[0].get("timestamp", time.time())
        age_days = (time.time() - first_tx_time) / 86400
        
        # Последняя активность
        last_tx_time = sorted_txs[-1].get("timestamp", time.time())
        days_since_last_tx = (time.time() - last_tx_time) / 86400
        
        # Средняя стоимость транзакций
        tx_values = [tx.get("value_usd", 0) for tx in transactions]
        avg_tx_value = sum(tx_values) / len(tx_values) if tx_values else 0
        max_tx_value = max(tx_values) if tx_values else 0
        
        # Частота транзакций
        tx_count = len(transactions)
        if age_days > 0:
            tx_per_day = tx_count / age_days
            if tx_per_day >= 5:
                trading_frequency = "high"
            elif tx_per_day >= 1:
                trading_frequency = "medium"
            else:
                trading_frequency = "low"
        else:
            trading_frequency = "unknown"
        
        # Activity score (0-10)
        activity_score = min(10, (tx_count / 100) * 5 + (1 / max(days_since_last_tx, 1)) * 5)
        
        # Паттерн похожести (для bot detection)
        pattern_similarity = WalletTypeDetector._calculate_pattern_similarity(transactions)
        
        # Средний интервал между транзакциями
        if len(sorted_txs) > 1:
            intervals = []
            for i in range(1, len(sorted_txs)):
                interval = sorted_txs[i]["timestamp"] - sorted_txs[i-1]["timestamp"]
                intervals.append(interval / 60)  # в минутах
            avg_tx_interval_minutes = sum(intervals) / len(intervals)
        else:
            avg_tx_interval_minutes = 0
        
        return {
            "balance_usd": balance_usd,
            "tx_count": tx_count,
            "age_days": age_days,
            "days_since_last_tx": days_since_last_tx,
            "activity_score": activity_score,
            "trading_frequency": trading_frequency,
            "avg_tx_value": avg_tx_value,
            "max_tx_value": max_tx_value,
            "pattern_similarity": pattern_similarity,
            "avg_tx_interval_minutes": avg_tx_interval_minutes
        }
    
    @staticmethod
    def _calculate_pattern_similarity(transactions: List[Dict]) -> float:
        """Рассчитать похожесть паттернов транзакций (для bot detection)"""
        
        if len(transactions) < 10:
            return 0.0
        
        # Анализируем значения транзакций
        values = [tx.get("value_usd", 0) for tx in transactions]
        
        # Считаем уникальные значения
        unique_values = len(set(round(v, 2) for v in values))
        total_values = len(values)
        
        # Если много одинаковых значений - похоже на бота
        similarity = 1.0 - (unique_values / total_values)
        
        return similarity
    
    @staticmethod
    def _generate_labels(chars: Dict, scores: Dict) -> List[str]:
        """Генерировать labels для кошелька"""
        
        labels = []
        
        # Balance labels
        if chars["balance_usd"] >= 1000000:
            labels.append("mega_whale")
        elif chars["balance_usd"] >= 100000:
            labels.append("whale")
        elif chars["balance_usd"] >= 10000:
            labels.append("dolphin")
        
        # Activity labels
        if chars["days_since_last_tx"] <= 1:
            labels.append("active_today")
        elif chars["days_since_last_tx"] <= 7:
            labels.append("active_week")
        elif chars["days_since_last_tx"] >= 180:
            labels.append("dormant")
        
        # Trading labels
        if chars["trading_frequency"] == "high":
            labels.append("active_trader")
        elif chars["tx_count"] >= 1000:
            labels.append("power_user")
        
        # Type labels
        if scores["bot"] >= 0.5:
            labels.append("possible_bot")
        if scores["holder"] >= 0.5:
            labels.append("long_term_holder")
        
        # DeFi labels (упрощенно)
        if chars["tx_count"] >= 50 and chars["avg_tx_value"] >= 1000:
            labels.append("defi_user")
        
        return labels


# ═══════════════════════════════════════════════════════════════════════════
#  TRANSACTION HISTORY
# ═══════════════════════════════════════════════════════════════════════════

class TransactionHistoryAnalyzer:
    """Анализ истории транзакций"""
    
    @staticmethod
    async def get_transaction_history(
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        limit: int = 50,
        timeout: int = 10
    ) -> List[Dict]:
        """
        Получить историю транзакций
        
        Returns:
            List[Dict]: [
                {
                    "hash": "0x...",
                    "from": "0x...",
                    "to": "0x...",
                    "value": 1.5,
                    "value_usd": 3000,
                    "timestamp": 1234567890,
                    "block": 12345678,
                    "gas_used": 21000,
                    "gas_price": 30,
                    "status": "success" | "failed",
                    "type": "send" | "receive" | "contract"
                },
                ...
            ]
        """
        
        transactions = []
        
        try:
            if chain == "ethereum":
                transactions = await TransactionHistoryAnalyzer._get_eth_transactions(
                    address, session, limit, timeout
                )
            elif chain == "bsc":
                transactions = await TransactionHistoryAnalyzer._get_bsc_transactions(
                    address, session, limit, timeout
                )
            # Добавить другие сети...
        
        except Exception as e:
            print(f"Ошибка получения транзакций: {e}")
        
        return transactions
    
    @staticmethod
    async def _get_eth_transactions(
        address: str,
        session: aiohttp.ClientSession,
        limit: int,
        timeout: int
    ) -> List[Dict]:
        """Получить Ethereum транзакции через Etherscan API"""
        
        import os
        api_key = os.environ.get("ETHERSCAN_API_KEY", "")
        
        url = f"https://api.etherscan.io/api"
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": limit,
            "sort": "desc",
            "apikey": api_key
        }
        
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("status") == "1":
                        transactions = []
                        
                        for tx in data.get("result", []):
                            transactions.append({
                                "hash": tx["hash"],
                                "from": tx["from"],
                                "to": tx["to"],
                                "value": int(tx["value"]) / 1e18,
                                "value_usd": 0,  # TODO: получить цену ETH
                                "timestamp": int(tx["timeStamp"]),
                                "block": int(tx["blockNumber"]),
                                "gas_used": int(tx["gasUsed"]),
                                "gas_price": int(tx["gasPrice"]) / 1e9,  # gwei
                                "status": "success" if tx.get("txreceipt_status") == "1" else "failed",
                                "type": "receive" if tx["to"].lower() == address.lower() else "send"
                            })
                        
                        return transactions
        except:
            pass
        
        return []
    
    @staticmethod
    async def _get_bsc_transactions(
        address: str,
        session: aiohttp.ClientSession,
        limit: int,
        timeout: int
    ) -> List[Dict]:
        """Получить BSC транзакции через BscScan API"""
        
        # Аналогично Etherscan
        return []
    
    @staticmethod
    def analyze_transaction_patterns(transactions: List[Dict]) -> Dict[str, Any]:
        """
        Анализировать паттерны транзакций
        
        Returns:
            Dict: {
                "total_sent": 10.5,
                "total_received": 15.2,
                "net_flow": 4.7,
                "send_count": 25,
                "receive_count": 30,
                "avg_send": 0.42,
                "avg_receive": 0.51,
                "most_active_hours": [14, 15, 16],
                "most_active_days": ["Monday", "Tuesday"],
                "top_counterparties": [
                    {"address": "0x...", "tx_count": 10, "total_value": 5.0}
                ]
            }
        """
        
        if not transactions:
            return {}
        
        sends = [tx for tx in transactions if tx["type"] == "send"]
        receives = [tx for tx in transactions if tx["type"] == "receive"]
        
        total_sent = sum(tx["value"] for tx in sends)
        total_received = sum(tx["value"] for tx in receives)
        
        # Анализ времени активности
        hours = [datetime.fromtimestamp(tx["timestamp"]).hour for tx in transactions]
        hour_counts = defaultdict(int)
        for hour in hours:
            hour_counts[hour] += 1
        most_active_hours = sorted(hour_counts, key=hour_counts.get, reverse=True)[:3]
        
        # Анализ дней недели
        days = [datetime.fromtimestamp(tx["timestamp"]).strftime("%A") for tx in transactions]
        day_counts = defaultdict(int)
        for day in days:
            day_counts[day] += 1
        most_active_days = sorted(day_counts, key=day_counts.get, reverse=True)[:3]
        
        # Топ контрагенты
        counterparties = defaultdict(lambda: {"tx_count": 0, "total_value": 0})
        for tx in transactions:
            counterparty = tx["to"] if tx["type"] == "send" else tx["from"]
            counterparties[counterparty]["tx_count"] += 1
            counterparties[counterparty]["total_value"] += tx["value"]
        
        top_counterparties = sorted(
            [{"address": addr, **data} for addr, data in counterparties.items()],
            key=lambda x: x["tx_count"],
            reverse=True
        )[:5]
        
        return {
            "total_sent": total_sent,
            "total_received": total_received,
            "net_flow": total_received - total_sent,
            "send_count": len(sends),
            "receive_count": len(receives),
            "avg_send": total_sent / len(sends) if sends else 0,
            "avg_receive": total_received / len(receives) if receives else 0,
            "most_active_hours": most_active_hours,
            "most_active_days": most_active_days,
            "top_counterparties": top_counterparties
        }


# ═══════════════════════════════════════════════════════════════════════════
#  PROFIT/LOSS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

class PnLAnalyzer:
    """Анализ прибыли/убытков"""
    
    @staticmethod
    async def calculate_pnl(
        address: str,
        transactions: List[Dict],
        current_balance: float,
        current_price: float,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Рассчитать PnL (Profit and Loss)
        
        Returns:
            Dict: {
                "total_invested": 10000,  # USD
                "current_value": 15000,
                "realized_pnl": 2000,
                "unrealized_pnl": 3000,
                "total_pnl": 5000,
                "roi_percent": 50.0,
                "win_rate": 0.65,
                "best_trade": {"hash": "0x...", "pnl": 1000},
                "worst_trade": {"hash": "0x...", "pnl": -500}
            }
        """
        
        if not transactions:
            return {
                "total_invested": 0,
                "current_value": current_balance * current_price,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_pnl": 0,
                "roi_percent": 0,
                "win_rate": 0,
                "best_trade": None,
                "worst_trade": None
            }
        
        # Разделяем на покупки и продажи
        buys = [tx for tx in transactions if tx["type"] == "receive"]
        sells = [tx for tx in transactions if tx["type"] == "send"]
        
        # Рассчитываем инвестиции
        total_invested = sum(tx["value_usd"] for tx in buys)
        total_withdrawn = sum(tx["value_usd"] for tx in sells)
        
        # Текущая стоимость
        current_value = current_balance * current_price
        
        # Realized PnL (уже зафиксированная прибыль/убыток)
        realized_pnl = total_withdrawn - total_invested
        
        # Unrealized PnL (незафиксированная прибыль/убыток)
        unrealized_pnl = current_value - (total_invested - total_withdrawn)
        
        # Total PnL
        total_pnl = realized_pnl + unrealized_pnl
        
        # ROI
        roi_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Win rate (упрощенно)
        profitable_trades = sum(1 for tx in sells if tx["value_usd"] > 0)
        win_rate = profitable_trades / len(sells) if sells else 0
        
        # Лучшая/худшая сделка (упрощенно)
        if sells:
            best_trade = max(sells, key=lambda x: x["value_usd"])
            worst_trade = min(sells, key=lambda x: x["value_usd"])
        else:
            best_trade = None
            worst_trade = None
        
        return {
            "total_invested": total_invested,
            "current_value": current_value,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "roi_percent": roi_percent,
            "win_rate": win_rate,
            "best_trade": best_trade,
            "worst_trade": worst_trade
        }
    
    @staticmethod
    def generate_pnl_report(pnl_data: Dict) -> str:
        """
        Генерировать текстовый отчет PnL
        
        Returns:
            str: Форматированный отчет
        """
        
        report = []
        report.append("=" * 50)
        report.append("PROFIT/LOSS ANALYSIS")
        report.append("=" * 50)
        
        report.append(f"\n💰 Total Invested: ${pnl_data['total_invested']:,.2f}")
        report.append(f"📊 Current Value: ${pnl_data['current_value']:,.2f}")
        
        total_pnl = pnl_data['total_pnl']
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        report.append(f"\n{pnl_emoji} Total PnL: ${total_pnl:,.2f}")
        report.append(f"   ├─ Realized: ${pnl_data['realized_pnl']:,.2f}")
        report.append(f"   └─ Unrealized: ${pnl_data['unrealized_pnl']:,.2f}")
        
        roi = pnl_data['roi_percent']
        roi_emoji = "🟢" if roi >= 0 else "🔴"
        report.append(f"\n{roi_emoji} ROI: {roi:+.2f}%")
        report.append(f"🎯 Win Rate: {pnl_data['win_rate']*100:.1f}%")
        
        if pnl_data['best_trade']:
            report.append(f"\n🏆 Best Trade: ${pnl_data['best_trade']['value_usd']:,.2f}")
        if pnl_data['worst_trade']:
            report.append(f"💔 Worst Trade: ${pnl_data['worst_trade']['value_usd']:,.2f}")
        
        report.append("\n" + "=" * 50)
        
        return "\n".join(report)


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED WALLET ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class WalletAnalyzer:
    """Универсальный анализатор кошельков"""
    
    @staticmethod
    async def analyze_wallet(
        address: str,
        chain: str,
        balance: float,
        balance_usd: float,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Полный анализ кошелька
        
        Returns:
            Dict: {
                "address": "0x...",
                "chain": "ethereum",
                "balance": 1.5,
                "balance_usd": 3000,
                "wallet_type": {...},
                "transaction_history": [...],
                "transaction_patterns": {...},
                "pnl_analysis": {...},
                "risk_score": 0.3,
                "recommendations": [...]
            }
        """
        
        # Получаем историю транзакций
        transactions = await TransactionHistoryAnalyzer.get_transaction_history(
            address, chain, session, limit=50, timeout=timeout
        )
        
        # Определяем тип кошелька
        wallet_type = await WalletTypeDetector.detect_wallet_type(
            address, balance_usd, transactions, session, timeout
        )
        
        # Анализируем паттерны
        patterns = TransactionHistoryAnalyzer.analyze_transaction_patterns(transactions)
        
        # Рассчитываем PnL
        current_price = balance_usd / balance if balance > 0 else 0
        pnl = await PnLAnalyzer.calculate_pnl(
            address, transactions, balance, current_price, session
        )
        
        # Рассчитываем risk score
        risk_score = WalletAnalyzer._calculate_risk_score(
            wallet_type, transactions, patterns
        )
        
        # Генерируем рекомендации
        recommendations = WalletAnalyzer._generate_recommendations(
            wallet_type, patterns, pnl, risk_score
        )
        
        return {
            "address": address,
            "chain": chain,
            "balance": balance,
            "balance_usd": balance_usd,
            "wallet_type": wallet_type,
            "transaction_history": transactions[:10],  # Первые 10
            "transaction_patterns": patterns,
            "pnl_analysis": pnl,
            "risk_score": risk_score,
            "recommendations": recommendations
        }
    
    @staticmethod
    def _calculate_risk_score(
        wallet_type: Dict,
        transactions: List[Dict],
        patterns: Dict
    ) -> float:
        """
        Рассчитать risk score (0-1)
        
        0.0-0.3: Low risk
        0.3-0.7: Medium risk
        0.7-1.0: High risk
        """
        
        risk = 0.0
        
        # Новый кошелек - высокий риск
        if wallet_type["type"] == "new":
            risk += 0.5
        
        # Бот - средний риск
        if wallet_type["type"] == "bot":
            risk += 0.3
        
        # Мало транзакций - высокий риск
        if len(transactions) < 5:
            risk += 0.3
        
        # Негативный net flow - средний риск
        if patterns.get("net_flow", 0) < 0:
            risk += 0.2
        
        # Dormant кошелек - низкий риск
        if "dormant" in wallet_type.get("labels", []):
            risk -= 0.2
        
        # Whale - низкий риск
        if "whale" in wallet_type.get("labels", []):
            risk -= 0.3
        
        return max(0.0, min(1.0, risk))
    
    @staticmethod
    def _generate_recommendations(
        wallet_type: Dict,
        patterns: Dict,
        pnl: Dict,
        risk_score: float
    ) -> List[str]:
        """Генерировать рекомендации"""
        
        recommendations = []
        
        # По типу кошелька
        if wallet_type["type"] == "whale":
            recommendations.append("🐋 Whale кошелек - высокая ценность, приоритет для мониторинга")
        elif wallet_type["type"] == "trader":
            recommendations.append("📊 Активный трейдер - мониторить транзакции в реальном времени")
        elif wallet_type["type"] == "holder":
            recommendations.append("💎 Long-term holder - низкий риск движения средств")
        elif wallet_type["type"] == "bot":
            recommendations.append("🤖 Возможно бот - проверить паттерны активности")
        
        # По PnL
        if pnl["roi_percent"] > 100:
            recommendations.append("🚀 Высокая прибыльность - изучить стратегию")
        elif pnl["roi_percent"] < -50:
            recommendations.append("⚠️ Большие убытки - возможна паника-продажа")
        
        # По risk score
        if risk_score >= 0.7:
            recommendations.append("🔴 Высокий риск - быстрый вывод рекомендуется")
        elif risk_score <= 0.3:
            recommendations.append("🟢 Низкий риск - безопасно для хранения")
        
        # По активности
        if patterns.get("net_flow", 0) > 0:
            recommendations.append("💰 Положительный net flow - кошелек накапливает")
        
        return recommendations
