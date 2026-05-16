# -*- coding: utf-8 -*-
"""
Wallet Analytics v1.0.58
Расширенная аналитика криптокошельков
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple


class WalletAnalytics:
    """Расширенная аналитика кошелька"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 минут
    
    async def analyze_wallet(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Полный анализ кошелька
        
        Returns:
            {
                "transaction_history": [...],
                "activity_score": "active|moderate|dormant",
                "risk_score": 0-100,
                "wallet_age_days": int,
                "first_tx_date": str,
                "last_tx_date": str,
                "total_transactions": int,
                "incoming_count": int,
                "outgoing_count": int,
                "related_addresses": [...],
                "labels": [...],
            }
        """
        
        analysis = {
            "transaction_history": [],
            "activity_score": "unknown",
            "risk_score": 0,
            "wallet_age_days": 0,
            "first_tx_date": None,
            "last_tx_date": None,
            "total_transactions": 0,
            "incoming_count": 0,
            "outgoing_count": 0,
            "related_addresses": [],
            "labels": [],
        }
        
        try:
            if chain in ["ethereum", "bsc", "polygon", "arbitrum", "optimism", "base"]:
                analysis = await self._analyze_evm_wallet(address, chain, session, timeout)
            elif chain == "bitcoin":
                analysis = await self._analyze_btc_wallet(address, session, timeout)
            elif chain == "solana":
                analysis = await self._analyze_sol_wallet(address, session, timeout)
            elif chain == "tron":
                analysis = await self._analyze_trx_wallet(address, session, timeout)
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_evm_wallet(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ EVM кошелька (Ethereum, BSC, Polygon, etc.)"""
        
        analysis = {
            "transaction_history": [],
            "activity_score": "unknown",
            "risk_score": 0,
            "wallet_age_days": 0,
            "first_tx_date": None,
            "last_tx_date": None,
            "total_transactions": 0,
            "incoming_count": 0,
            "outgoing_count": 0,
            "related_addresses": [],
            "labels": [],
        }
        
        # API endpoints для разных сетей
        api_urls = {
            "ethereum": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "polygon": "https://api.polygonscan.com/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api",
            "base": "https://api.basescan.org/api",
        }
        
        api_url = api_urls.get(chain, api_urls["ethereum"])
        
        # Получаем историю транзакций
        url = f"{api_url}?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=100&sort=desc"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("status") == "1" and data.get("result"):
                        txs = data["result"]
                        analysis["total_transactions"] = len(txs)
                        
                        # Обрабатываем транзакции
                        for tx in txs[:20]:  # Первые 20
                            tx_info = {
                                "hash": tx.get("hash", ""),
                                "from": tx.get("from", ""),
                                "to": tx.get("to", ""),
                                "value": int(tx.get("value", 0)) / 1e18,
                                "timestamp": int(tx.get("timeStamp", 0)),
                                "date": datetime.fromtimestamp(int(tx.get("timeStamp", 0))).strftime("%Y-%m-%d %H:%M"),
                                "is_incoming": tx.get("to", "").lower() == address.lower(),
                            }
                            
                            analysis["transaction_history"].append(tx_info)
                            
                            # Считаем входящие/исходящие
                            if tx_info["is_incoming"]:
                                analysis["incoming_count"] += 1
                            else:
                                analysis["outgoing_count"] += 1
                            
                            # Собираем связанные адреса
                            related = tx.get("from") if tx_info["is_incoming"] else tx.get("to")
                            if related and related.lower() != address.lower():
                                if related not in analysis["related_addresses"]:
                                    analysis["related_addresses"].append(related)
                        
                        # Определяем возраст кошелька
                        if txs:
                            first_tx_ts = int(txs[-1].get("timeStamp", 0))
                            last_tx_ts = int(txs[0].get("timeStamp", 0))
                            
                            analysis["first_tx_date"] = datetime.fromtimestamp(first_tx_ts).strftime("%Y-%m-%d")
                            analysis["last_tx_date"] = datetime.fromtimestamp(last_tx_ts).strftime("%Y-%m-%d")
                            
                            wallet_age = (time.time() - first_tx_ts) / 86400
                            analysis["wallet_age_days"] = int(wallet_age)
                            
                            # Определяем активность
                            days_since_last = (time.time() - last_tx_ts) / 86400
                            
                            if days_since_last < 7:
                                analysis["activity_score"] = "active"
                            elif days_since_last < 90:
                                analysis["activity_score"] = "moderate"
                            else:
                                analysis["activity_score"] = "dormant"
                            
                            # Рассчитываем риск-скор
                            analysis["risk_score"] = self._calculate_risk_score(
                                wallet_age_days=analysis["wallet_age_days"],
                                total_tx=analysis["total_transactions"],
                                days_since_last=days_since_last,
                                incoming_count=analysis["incoming_count"],
                                outgoing_count=analysis["outgoing_count"]
                            )
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_btc_wallet(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ Bitcoin кошелька"""
        
        analysis = {
            "transaction_history": [],
            "activity_score": "unknown",
            "risk_score": 0,
            "wallet_age_days": 0,
            "first_tx_date": None,
            "last_tx_date": None,
            "total_transactions": 0,
            "incoming_count": 0,
            "outgoing_count": 0,
            "related_addresses": [],
            "labels": [],
        }
        
        try:
            url = f"https://mempool.space/api/address/{address}/txs"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    txs = await resp.json()
                    
                    analysis["total_transactions"] = len(txs)
                    
                    for tx in txs[:20]:
                        # Определяем входящая или исходящая
                        is_incoming = any(
                            vout.get("scriptpubkey_address") == address
                            for vout in tx.get("vout", [])
                        )
                        
                        tx_info = {
                            "hash": tx.get("txid", ""),
                            "timestamp": tx.get("status", {}).get("block_time", 0),
                            "date": datetime.fromtimestamp(tx.get("status", {}).get("block_time", 0)).strftime("%Y-%m-%d %H:%M") if tx.get("status", {}).get("block_time") else "pending",
                            "is_incoming": is_incoming,
                            "confirmations": tx.get("status", {}).get("confirmed", False),
                        }
                        
                        analysis["transaction_history"].append(tx_info)
                        
                        if is_incoming:
                            analysis["incoming_count"] += 1
                        else:
                            analysis["outgoing_count"] += 1
                    
                    # Возраст кошелька
                    if txs:
                        first_tx_ts = txs[-1].get("status", {}).get("block_time", 0)
                        last_tx_ts = txs[0].get("status", {}).get("block_time", 0)
                        
                        if first_tx_ts:
                            analysis["first_tx_date"] = datetime.fromtimestamp(first_tx_ts).strftime("%Y-%m-%d")
                            wallet_age = (time.time() - first_tx_ts) / 86400
                            analysis["wallet_age_days"] = int(wallet_age)
                        
                        if last_tx_ts:
                            analysis["last_tx_date"] = datetime.fromtimestamp(last_tx_ts).strftime("%Y-%m-%d")
                            days_since_last = (time.time() - last_tx_ts) / 86400
                            
                            if days_since_last < 7:
                                analysis["activity_score"] = "active"
                            elif days_since_last < 90:
                                analysis["activity_score"] = "moderate"
                            else:
                                analysis["activity_score"] = "dormant"
                            
                            analysis["risk_score"] = self._calculate_risk_score(
                                wallet_age_days=analysis["wallet_age_days"],
                                total_tx=analysis["total_transactions"],
                                days_since_last=days_since_last,
                                incoming_count=analysis["incoming_count"],
                                outgoing_count=analysis["outgoing_count"]
                            )
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_sol_wallet(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ Solana кошелька"""
        
        analysis = {
            "transaction_history": [],
            "activity_score": "unknown",
            "risk_score": 0,
            "wallet_age_days": 0,
            "total_transactions": 0,
            "incoming_count": 0,
            "outgoing_count": 0,
            "labels": [],
        }
        
        # Solana RPC для получения транзакций
        try:
            url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": 20}]
            }
            
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if "result" in data:
                        sigs = data["result"]
                        analysis["total_transactions"] = len(sigs)
                        
                        for sig_info in sigs:
                            tx_info = {
                                "signature": sig_info.get("signature", ""),
                                "timestamp": sig_info.get("blockTime", 0),
                                "date": datetime.fromtimestamp(sig_info.get("blockTime", 0)).strftime("%Y-%m-%d %H:%M") if sig_info.get("blockTime") else "unknown",
                                "slot": sig_info.get("slot", 0),
                                "err": sig_info.get("err"),
                            }
                            
                            analysis["transaction_history"].append(tx_info)
                        
                        # Возраст кошелька
                        if sigs:
                            last_tx_ts = sigs[0].get("blockTime", 0)
                            first_tx_ts = sigs[-1].get("blockTime", 0)
                            
                            if first_tx_ts:
                                wallet_age = (time.time() - first_tx_ts) / 86400
                                analysis["wallet_age_days"] = int(wallet_age)
                            
                            if last_tx_ts:
                                days_since_last = (time.time() - last_tx_ts) / 86400
                                
                                if days_since_last < 7:
                                    analysis["activity_score"] = "active"
                                elif days_since_last < 90:
                                    analysis["activity_score"] = "moderate"
                                else:
                                    analysis["activity_score"] = "dormant"
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    async def _analyze_trx_wallet(
        self,
        address: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Анализ Tron кошелька"""
        
        analysis = {
            "transaction_history": [],
            "activity_score": "unknown",
            "risk_score": 0,
            "wallet_age_days": 0,
            "total_transactions": 0,
            "labels": [],
        }
        
        try:
            url = f"https://apilist.tronscanapi.com/api/transaction?sort=-timestamp&count=true&limit=20&start=0&address={address}"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    txs = data.get("data", [])
                    analysis["total_transactions"] = data.get("total", 0)
                    
                    for tx in txs:
                        tx_info = {
                            "hash": tx.get("hash", ""),
                            "timestamp": tx.get("timestamp", 0) // 1000,
                            "date": datetime.fromtimestamp(tx.get("timestamp", 0) // 1000).strftime("%Y-%m-%d %H:%M"),
                            "from": tx.get("ownerAddress", ""),
                            "to": tx.get("toAddress", ""),
                            "amount": tx.get("amount", 0) / 1e6,
                        }
                        
                        analysis["transaction_history"].append(tx_info)
                    
                    # Возраст кошелька
                    if txs:
                        last_tx_ts = txs[0].get("timestamp", 0) // 1000
                        
                        if last_tx_ts:
                            days_since_last = (time.time() - last_tx_ts) / 86400
                            
                            if days_since_last < 7:
                                analysis["activity_score"] = "active"
                            elif days_since_last < 90:
                                analysis["activity_score"] = "moderate"
                            else:
                                analysis["activity_score"] = "dormant"
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    def _calculate_risk_score(
        self,
        wallet_age_days: int,
        total_tx: int,
        days_since_last: float,
        incoming_count: int,
        outgoing_count: int
    ) -> int:
        """
        Рассчитать риск-скор кошелька (0-100)
        
        Низкий риск (0-30): Старый кошелек, много транзакций, активный
        Средний риск (31-60): Средний возраст, умеренная активность
        Высокий риск (61-100): Новый кошелек, мало транзакций, неактивный
        """
        
        risk = 0
        
        # Возраст кошелька (чем новее - тем рискованнее)
        if wallet_age_days < 30:
            risk += 30
        elif wallet_age_days < 180:
            risk += 20
        elif wallet_age_days < 365:
            risk += 10
        else:
            risk += 0  # Старый кошелек - низкий риск
        
        # Количество транзакций (чем меньше - тем рискованнее)
        if total_tx < 5:
            risk += 30
        elif total_tx < 20:
            risk += 20
        elif total_tx < 100:
            risk += 10
        else:
            risk += 0  # Много транзакций - низкий риск
        
        # Активность (чем давнее последняя TX - тем рискованнее)
        if days_since_last > 365:
            risk += 20
        elif days_since_last > 180:
            risk += 15
        elif days_since_last > 90:
            risk += 10
        elif days_since_last > 30:
            risk += 5
        else:
            risk += 0  # Активный - низкий риск
        
        # Баланс входящих/исходящих (только исходящие - подозрительно)
        if outgoing_count > 0 and incoming_count == 0:
            risk += 20  # Только отправка - возможно дроп
        
        return min(risk, 100)
    
    def format_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """Форматировать отчет анализа для отображения"""
        
        if "error" in analysis:
            return f"❌ Analysis error: {analysis['error']}"
        
        report_lines = []
        
        # Основная информация
        report_lines.append("📊 WALLET ANALYSIS")
        report_lines.append("=" * 50)
        
        # Возраст и активность
        if analysis.get("wallet_age_days"):
            report_lines.append(f"🕐 Age: {analysis['wallet_age_days']} days")
        
        if analysis.get("first_tx_date"):
            report_lines.append(f"📅 First TX: {analysis['first_tx_date']}")
        
        if analysis.get("last_tx_date"):
            report_lines.append(f"📅 Last TX: {analysis['last_tx_date']}")
        
        # Активность
        activity = analysis.get("activity_score", "unknown")
        activity_emoji = {"active": "🟢", "moderate": "🟡", "dormant": "🔴"}.get(activity, "⚪")
        report_lines.append(f"{activity_emoji} Activity: {activity.upper()}")
        
        # Риск-скор
        risk = analysis.get("risk_score", 0)
        if risk <= 30:
            risk_label = "🟢 LOW RISK"
        elif risk <= 60:
            risk_label = "🟡 MEDIUM RISK"
        else:
            risk_label = "🔴 HIGH RISK"
        report_lines.append(f"⚠️ Risk Score: {risk}/100 ({risk_label})")
        
        # Транзакции
        report_lines.append(f"📈 Total TX: {analysis.get('total_transactions', 0)}")
        report_lines.append(f"📥 Incoming: {analysis.get('incoming_count', 0)}")
        report_lines.append(f"📤 Outgoing: {analysis.get('outgoing_count', 0)}")
        
        # Последние транзакции
        tx_history = analysis.get("transaction_history", [])
        if tx_history:
            report_lines.append("\n🔄 RECENT TRANSACTIONS (last 5):")
            for tx in tx_history[:5]:
                direction = "📥 IN" if tx.get("is_incoming") else "📤 OUT"
                date = tx.get("date", "unknown")
                value = tx.get("value", 0)
                report_lines.append(f"  {direction} | {date} | {value:.6f}")
        
        # Связанные адреса
        related = analysis.get("related_addresses", [])
        if related:
            report_lines.append(f"\n🔗 Related addresses: {len(related)}")
            for addr in related[:3]:
                report_lines.append(f"  • {addr[:10]}...{addr[-8:]}")
        
        return "\n".join(report_lines)
