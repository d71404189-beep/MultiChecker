# -*- coding: utf-8 -*-
"""
Monitoring v1.0.56
Мониторинг кошельков и алерты: Telegram, Discord, Email
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════
#  TELEGRAM ALERTS
# ═══════════════════════════════════════════════════════════════════════════

class TelegramAlerter:
    """Отправка алертов в Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_alert(
        self,
        message: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Отправить алерт в Telegram
        
        Args:
            message: Текст сообщения (поддерживает HTML/Markdown)
            parse_mode: "HTML" | "Markdown" | "MarkdownV2"
            disable_notification: Тихое уведомление
        
        Returns:
            bool: Успешно отправлено
        """
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        print(f"Telegram error: {resp.status}")
                        return False
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    async def send_balance_alert(
        self,
        address: str,
        chain: str,
        old_balance: float,
        new_balance: float,
        balance_usd: float
    ) -> bool:
        """Отправить алерт об изменении баланса"""
        
        change = new_balance - old_balance
        change_emoji = "📈" if change > 0 else "📉"
        
        message = f"""
{change_emoji} <b>Balance Change Detected!</b>

<b>Address:</b> <code>{address[:10]}...{address[-8:]}</code>
<b>Chain:</b> {chain.upper()}

<b>Old Balance:</b> {old_balance:.6f}
<b>New Balance:</b> {new_balance:.6f}
<b>Change:</b> {change:+.6f}

<b>USD Value:</b> ${balance_usd:,.2f}

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return await self.send_alert(message)
    
    async def send_transaction_alert(
        self,
        address: str,
        tx_hash: str,
        tx_type: str,
        value: float,
        value_usd: float,
        from_addr: str,
        to_addr: str
    ) -> bool:
        """Отправить алерт о новой транзакции"""
        
        type_emoji = "📤" if tx_type == "send" else "📥"
        
        message = f"""
{type_emoji} <b>New Transaction!</b>

<b>Type:</b> {tx_type.upper()}
<b>Value:</b> {value:.6f} (${value_usd:,.2f})

<b>From:</b> <code>{from_addr[:10]}...{from_addr[-8:]}</code>
<b>To:</b> <code>{to_addr[:10]}...{to_addr[-8:]}</code>

<b>TX Hash:</b> <code>{tx_hash[:16]}...</code>

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return await self.send_alert(message)
    
    async def send_whale_alert(
        self,
        address: str,
        balance_usd: float,
        wallet_type: str,
        labels: List[str]
    ) -> bool:
        """Отправить алерт о whale кошельке"""
        
        message = f"""
🐋 <b>WHALE ALERT!</b>

<b>Address:</b> <code>{address[:10]}...{address[-8:]}</code>
<b>Balance:</b> ${balance_usd:,.2f}

<b>Type:</b> {wallet_type.upper()}
<b>Labels:</b> {", ".join(labels)}

<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return await self.send_alert(message)


# ═══════════════════════════════════════════════════════════════════════════
#  DISCORD ALERTS
# ═══════════════════════════════════════════════════════════════════════════

class DiscordAlerter:
    """Отправка алертов в Discord через Webhook"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_alert(
        self,
        title: str,
        description: str,
        color: int = 0x00ff00,
        fields: Optional[List[Dict]] = None
    ) -> bool:
        """
        Отправить алерт в Discord
        
        Args:
            title: Заголовок embed
            description: Описание
            color: Цвет (hex)
            fields: Дополнительные поля
        
        Returns:
            bool: Успешно отправлено
        """
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "MultiChecker Pro"
            }
        }
        
        if fields:
            embed["fields"] = fields
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in [200, 204]:
                        return True
                    else:
                        print(f"Discord error: {resp.status}")
                        return False
        except Exception as e:
            print(f"Discord send error: {e}")
            return False
    
    async def send_balance_alert(
        self,
        address: str,
        chain: str,
        old_balance: float,
        new_balance: float,
        balance_usd: float
    ) -> bool:
        """Отправить алерт об изменении баланса"""
        
        change = new_balance - old_balance
        color = 0x00ff00 if change > 0 else 0xff0000
        
        fields = [
            {"name": "Address", "value": f"`{address[:16]}...`", "inline": False},
            {"name": "Chain", "value": chain.upper(), "inline": True},
            {"name": "Old Balance", "value": f"{old_balance:.6f}", "inline": True},
            {"name": "New Balance", "value": f"{new_balance:.6f}", "inline": True},
            {"name": "Change", "value": f"{change:+.6f}", "inline": True},
            {"name": "USD Value", "value": f"${balance_usd:,.2f}", "inline": True}
        ]
        
        return await self.send_alert(
            title="📊 Balance Change Detected",
            description=f"Balance changed by {change:+.6f}",
            color=color,
            fields=fields
        )
    
    async def send_whale_alert(
        self,
        address: str,
        balance_usd: float,
        wallet_type: str,
        labels: List[str]
    ) -> bool:
        """Отправить алерт о whale кошельке"""
        
        fields = [
            {"name": "Address", "value": f"`{address[:16]}...`", "inline": False},
            {"name": "Balance", "value": f"${balance_usd:,.2f}", "inline": True},
            {"name": "Type", "value": wallet_type.upper(), "inline": True},
            {"name": "Labels", "value": ", ".join(labels), "inline": False}
        ]
        
        return await self.send_alert(
            title="🐋 WHALE ALERT",
            description=f"High-value wallet detected: ${balance_usd:,.2f}",
            color=0xffd700,  # Gold
            fields=fields
        )


# ═══════════════════════════════════════════════════════════════════════════
#  EMAIL ALERTS
# ═══════════════════════════════════════════════════════════════════════════

class EmailAlerter:
    """Отправка алертов по Email"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
    
    async def send_alert(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Отправить алерт по Email
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            body: Текст письма
            html: HTML формат
        
        Returns:
            bool: Успешно отправлено
        """
        
        # Для асинхронной отправки email нужна библиотека aiosmtplib
        # Здесь упрощенная версия
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html' if html else 'plain'))
            
            # Отправляем
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            print(f"Email send error: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════
#  WALLET MONITOR
# ═══════════════════════════════════════════════════════════════════════════

class WalletMonitor:
    """Мониторинг кошельков"""
    
    def __init__(self):
        self.monitored_wallets = {}  # {address: {chain, last_balance, ...}}
        self.alerters = []
        self.running = False
        self.check_interval = 60  # секунд
    
    def add_wallet(
        self,
        address: str,
        chain: str,
        min_balance_change: float = 0.001,
        alert_on_tx: bool = True
    ) -> None:
        """
        Добавить кошелек для мониторинга
        
        Args:
            address: Адрес кошелька
            chain: Сеть
            min_balance_change: Минимальное изменение для алерта
            alert_on_tx: Алерт при каждой транзакции
        """
        
        self.monitored_wallets[address] = {
            "chain": chain,
            "last_balance": None,
            "last_check": None,
            "min_balance_change": min_balance_change,
            "alert_on_tx": alert_on_tx,
            "tx_history": []
        }
    
    def remove_wallet(self, address: str) -> None:
        """Удалить кошелек из мониторинга"""
        if address in self.monitored_wallets:
            del self.monitored_wallets[address]
    
    def add_alerter(self, alerter: Any) -> None:
        """Добавить alerter (Telegram, Discord, Email)"""
        self.alerters.append(alerter)
    
    async def start_monitoring(self, session: aiohttp.ClientSession) -> None:
        """Запустить мониторинг"""
        
        self.running = True
        
        while self.running:
            try:
                # Проверяем все кошельки
                tasks = []
                for address, config in self.monitored_wallets.items():
                    task = self._check_wallet(address, config, session)
                    tasks.append(task)
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Ждем до следующей проверки
                await asyncio.sleep(self.check_interval)
            
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self) -> None:
        """Остановить мониторинг"""
        self.running = False
    
    async def _check_wallet(
        self,
        address: str,
        config: Dict,
        session: aiohttp.ClientSession
    ) -> None:
        """Проверить один кошелек"""
        
        try:
            # Получаем текущий баланс
            balance = await self._get_balance(address, config["chain"], session)
            
            if balance is None:
                return
            
            # Первая проверка
            if config["last_balance"] is None:
                config["last_balance"] = balance
                config["last_check"] = time.time()
                return
            
            # Проверяем изменение баланса
            balance_change = abs(balance - config["last_balance"])
            
            if balance_change >= config["min_balance_change"]:
                # Отправляем алерты
                await self._send_balance_alerts(
                    address,
                    config["chain"],
                    config["last_balance"],
                    balance,
                    balance * 3000  # TODO: получить реальную цену
                )
                
                config["last_balance"] = balance
            
            config["last_check"] = time.time()
        
        except Exception as e:
            print(f"Check wallet error for {address}: {e}")
    
    async def _get_balance(
        self,
        address: str,
        chain: str,
        session: aiohttp.ClientSession
    ) -> Optional[float]:
        """Получить баланс кошелька"""
        
        # Здесь должна быть реальная проверка через RPC
        # Для примера возвращаем None
        return None
    
    async def _send_balance_alerts(
        self,
        address: str,
        chain: str,
        old_balance: float,
        new_balance: float,
        balance_usd: float
    ) -> None:
        """Отправить алерты об изменении баланса"""
        
        tasks = []
        
        for alerter in self.alerters:
            if isinstance(alerter, TelegramAlerter):
                task = alerter.send_balance_alert(
                    address, chain, old_balance, new_balance, balance_usd
                )
                tasks.append(task)
            
            elif isinstance(alerter, DiscordAlerter):
                task = alerter.send_balance_alert(
                    address, chain, old_balance, new_balance, balance_usd
                )
                tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Получить статистику мониторинга"""
        
        total_wallets = len(self.monitored_wallets)
        active_wallets = sum(
            1 for config in self.monitored_wallets.values()
            if config["last_check"] and (time.time() - config["last_check"]) < 300
        )
        
        return {
            "total_wallets": total_wallets,
            "active_wallets": active_wallets,
            "alerters_count": len(self.alerters),
            "running": self.running,
            "check_interval": self.check_interval
        }


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO WITHDRAW ON DEPOSIT
# ═══════════════════════════════════════════════════════════════════════════

class AutoWithdrawMonitor:
    """Автоматический вывод при поступлении"""
    
    def __init__(self):
        self.monitored_addresses = {}
        self.withdraw_callback = None
    
    def add_address(
        self,
        address: str,
        chain: str,
        destination: str,
        min_amount: float = 0.001,
        leave_gas: float = 0.001
    ) -> None:
        """
        Добавить адрес для автовывода
        
        Args:
            address: Адрес для мониторинга
            chain: Сеть
            destination: Адрес назначения
            min_amount: Минимальная сумма для вывода
            leave_gas: Оставить на газ
        """
        
        self.monitored_addresses[address] = {
            "chain": chain,
            "destination": destination,
            "min_amount": min_amount,
            "leave_gas": leave_gas,
            "last_balance": 0,
            "total_withdrawn": 0,
            "withdraw_count": 0
        }
    
    def set_withdraw_callback(self, callback: Callable) -> None:
        """Установить callback для вывода"""
        self.withdraw_callback = callback
    
    async def check_and_withdraw(
        self,
        address: str,
        current_balance: float
    ) -> Optional[Dict]:
        """
        Проверить и выполнить вывод если нужно
        
        Returns:
            Dict: Информация о выводе или None
        """
        
        if address not in self.monitored_addresses:
            return None
        
        config = self.monitored_addresses[address]
        
        # Проверяем поступление
        if current_balance > config["last_balance"]:
            deposit = current_balance - config["last_balance"]
            
            # Проверяем минимум
            if deposit >= config["min_amount"]:
                # Рассчитываем сумму вывода
                withdraw_amount = current_balance - config["leave_gas"]
                
                if withdraw_amount > 0 and self.withdraw_callback:
                    # Выполняем вывод
                    result = await self.withdraw_callback(
                        from_address=address,
                        to_address=config["destination"],
                        amount=withdraw_amount,
                        chain=config["chain"]
                    )
                    
                    if result.get("success"):
                        config["total_withdrawn"] += withdraw_amount
                        config["withdraw_count"] += 1
                        
                        return {
                            "address": address,
                            "amount": withdraw_amount,
                            "destination": config["destination"],
                            "tx_hash": result.get("tx_hash"),
                            "timestamp": time.time()
                        }
        
        config["last_balance"] = current_balance
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  MONITORING DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

class MonitoringDashboard:
    """Dashboard для мониторинга"""
    
    def __init__(self, monitor: WalletMonitor):
        self.monitor = monitor
        self.events = []  # История событий
        self.max_events = 100
    
    def add_event(
        self,
        event_type: str,
        address: str,
        data: Dict
    ) -> None:
        """Добавить событие"""
        
        event = {
            "type": event_type,
            "address": address,
            "data": data,
            "timestamp": time.time()
        }
        
        self.events.append(event)
        
        # Ограничиваем размер
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Получить данные для dashboard"""
        
        stats = self.monitor.get_monitoring_stats()
        
        # Последние события
        recent_events = self.events[-10:]
        
        # Статистика по типам событий
        event_counts = defaultdict(int)
        for event in self.events:
            event_counts[event["type"]] += 1
        
        return {
            "monitoring_stats": stats,
            "recent_events": recent_events,
            "event_counts": dict(event_counts),
            "total_events": len(self.events),
            "uptime": time.time() - self.events[0]["timestamp"] if self.events else 0
        }
    
    def generate_dashboard_html(self) -> str:
        """Генерировать HTML dashboard"""
        
        data = self.get_dashboard_data()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MultiChecker Monitoring Dashboard</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .stat {{ display: inline-block; margin-right: 30px; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #58a6ff; }}
        .stat-label {{ font-size: 14px; color: #8b949e; }}
        .event {{ padding: 10px; border-bottom: 1px solid #30363d; }}
        .event:last-child {{ border-bottom: none; }}
        .status-running {{ color: #3fb950; }}
        .status-stopped {{ color: #f85149; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 MultiChecker Monitoring Dashboard</h1>
        
        <div class="card">
            <h2>Monitoring Status</h2>
            <div class="stat">
                <div class="stat-value">{data['monitoring_stats']['total_wallets']}</div>
                <div class="stat-label">Total Wallets</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data['monitoring_stats']['active_wallets']}</div>
                <div class="stat-label">Active Wallets</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data['monitoring_stats']['alerters_count']}</div>
                <div class="stat-label">Alerters</div>
            </div>
            <div class="stat">
                <div class="stat-value class="{'status-running' if data['monitoring_stats']['running'] else 'status-stopped'}">
                    {'RUNNING' if data['monitoring_stats']['running'] else 'STOPPED'}
                </div>
                <div class="stat-label">Status</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Events</h2>
            {''.join(f'<div class="event">{event["type"]} - {event["address"][:16]}... - {datetime.fromtimestamp(event["timestamp"]).strftime("%H:%M:%S")}</div>' for event in data['recent_events'])}
        </div>
        
        <div class="card">
            <h2>Event Statistics</h2>
            {''.join(f'<div class="stat"><div class="stat-value">{count}</div><div class="stat-label">{event_type}</div></div>' for event_type, count in data['event_counts'].items())}
        </div>
    </div>
</body>
</html>
"""
        
        return html
