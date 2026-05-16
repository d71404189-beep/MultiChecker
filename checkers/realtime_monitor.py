# -*- coding: utf-8 -*-
"""
Real-time Monitoring v1.0.60
Мониторинг кошельков в реальном времени
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import websockets


class RealtimeMonitor:
    """Мониторинг в реальном времени через WebSocket"""
    
    def __init__(self):
        self.active_monitors = {}
        self.callbacks = {}
        self.ws_connections = {}
    
    async def start_monitoring(
        self,
        address: str,
        chains: List[str],
        callback: Callable,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Начать мониторинг кошелька
        
        Args:
            address: Адрес кошелька
            chains: Список сетей для мониторинга
            callback: Функция обратного вызова при событии
            filters: Фильтры событий
        
        Returns:
            monitor_id: ID монитора
        """
        
        monitor_id = f"{address}_{datetime.now().timestamp()}"
        
        self.active_monitors[monitor_id] = {
            "address": address,
            "chains": chains,
            "filters": filters or {},
            "started_at": datetime.now().isoformat(),
            "events_count": 0,
        }
        
        self.callbacks[monitor_id] = callback
        
        # Запускаем мониторинг для каждой сети
        tasks = []
        for chain in chains:
            task = asyncio.create_task(
                self._monitor_chain(monitor_id, address, chain)
            )
            tasks.append(task)
        
        return monitor_id
    
    async def stop_monitoring(self, monitor_id: str):
        """Остановить мониторинг"""
        
        if monitor_id in self.active_monitors:
            del self.active_monitors[monitor_id]
        
        if monitor_id in self.callbacks:
            del self.callbacks[monitor_id]
        
        # Закрываем WebSocket соединения
        if monitor_id in self.ws_connections:
            for ws in self.ws_connections[monitor_id].values():
                await ws.close()
            del self.ws_connections[monitor_id]
    
    async def _monitor_chain(
        self,
        monitor_id: str,
        address: str,
        chain: str
    ):
        """Мониторить сеть"""
        
        ws_urls = {
            "ethereum": "wss://mainnet.infura.io/ws/v3/YOUR_KEY",
            "bsc": "wss://bsc-ws-node.nariox.org:443",
            "polygon": "wss://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY",
            "arbitrum": "wss://arb-mainnet.g.alchemy.com/v2/YOUR_KEY",
            "optimism": "wss://opt-mainnet.g.alchemy.com/v2/YOUR_KEY",
        }
        
        ws_url = ws_urls.get(chain)
        if not ws_url:
            return
        
        try:
            # Для демонстрации используем polling вместо WebSocket
            # В реальной версии нужно использовать WebSocket
            await self._poll_chain(monitor_id, address, chain)
        
        except Exception as e:
            print(f"Error monitoring {chain}: {e}")
    
    async def _poll_chain(
        self,
        monitor_id: str,
        address: str,
        chain: str
    ):
        """Polling вместо WebSocket (для демонстрации)"""
        
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "bsc": "https://bsc-dataseed.binance.org",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return
        
        last_block = 0
        
        async with aiohttp.ClientSession() as session:
            while monitor_id in self.active_monitors:
                try:
                    # Получаем последний блок
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_blockNumber",
                        "params": []
                    }
                    
                    async with session.post(
                        rpc_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            current_block = int(result.get("result", "0x0"), 16)
                            
                            if current_block > last_block:
                                # Проверяем транзакции в новых блоках
                                for block_num in range(last_block + 1, current_block + 1):
                                    await self._check_block(
                                        monitor_id,
                                        address,
                                        chain,
                                        block_num,
                                        session
                                    )
                                
                                last_block = current_block
                    
                    # Ждем 5 секунд перед следующей проверкой
                    await asyncio.sleep(5)
                
                except Exception:
                    await asyncio.sleep(5)
    
    async def _check_block(
        self,
        monitor_id: str,
        address: str,
        chain: str,
        block_num: int,
        session: aiohttp.ClientSession
    ):
        """Проверить блок на наличие транзакций"""
        
        rpc_urls = {
            "ethereum": "https://cloudflare-eth.com",
            "bsc": "https://bsc-dataseed.binance.org",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc",
            "optimism": "https://mainnet.optimism.io",
        }
        
        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            return
        
        try:
            # Получаем блок с транзакциями
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBlockByNumber",
                "params": [hex(block_num), True]
            }
            
            async with session.post(
                rpc_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    block = result.get("result")
                    
                    if block and "transactions" in block:
                        for tx in block["transactions"]:
                            # Проверяем, связана ли транзакция с нашим адресом
                            if (tx.get("from", "").lower() == address.lower() or
                                tx.get("to", "").lower() == address.lower()):
                                
                                # Создаем событие
                                event = {
                                    "type": "transaction",
                                    "chain": chain,
                                    "address": address,
                                    "tx_hash": tx.get("hash"),
                                    "from": tx.get("from"),
                                    "to": tx.get("to"),
                                    "value": int(tx.get("value", "0x0"), 16) / 1e18,
                                    "block": block_num,
                                    "timestamp": datetime.now().isoformat(),
                                }
                                
                                # Вызываем callback
                                await self._trigger_event(monitor_id, event)
        
        except Exception:
            pass
    
    async def _trigger_event(self, monitor_id: str, event: Dict[str, Any]):
        """Вызвать событие"""
        
        if monitor_id not in self.active_monitors:
            return
        
        # Применяем фильтры
        filters = self.active_monitors[monitor_id].get("filters", {})
        
        if not self._apply_filters(event, filters):
            return
        
        # Увеличиваем счетчик
        self.active_monitors[monitor_id]["events_count"] += 1
        
        # Вызываем callback
        callback = self.callbacks.get(monitor_id)
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    def _apply_filters(self, event: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Применить фильтры"""
        
        # Фильтр по минимальной сумме
        min_value = filters.get("min_value", 0)
        if event.get("value", 0) < min_value:
            return False
        
        # Фильтр по типу события
        event_types = filters.get("event_types", [])
        if event_types and event.get("type") not in event_types:
            return False
        
        # Фильтр по направлению (incoming/outgoing)
        direction = filters.get("direction")
        if direction:
            address = self.active_monitors.get(event.get("monitor_id"), {}).get("address", "").lower()
            if direction == "incoming" and event.get("to", "").lower() != address:
                return False
            if direction == "outgoing" and event.get("from", "").lower() != address:
                return False
        
        return True
    
    def get_monitor_stats(self, monitor_id: str) -> Optional[Dict[str, Any]]:
        """Получить статистику монитора"""
        
        return self.active_monitors.get(monitor_id)
    
    def get_all_monitors(self) -> Dict[str, Any]:
        """Получить все активные мониторы"""
        
        return self.active_monitors


class NotificationManager:
    """Менеджер уведомлений"""
    
    def __init__(self):
        self.notification_channels = {}
    
    def add_telegram_channel(
        self,
        bot_token: str,
        chat_id: str
    ):
        """Добавить Telegram канал"""
        
        self.notification_channels["telegram"] = {
            "type": "telegram",
            "bot_token": bot_token,
            "chat_id": chat_id,
        }
    
    def add_discord_channel(
        self,
        webhook_url: str
    ):
        """Добавить Discord канал"""
        
        self.notification_channels["discord"] = {
            "type": "discord",
            "webhook_url": webhook_url,
        }
    
    def add_email_channel(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        to_email: str
    ):
        """Добавить Email канал"""
        
        self.notification_channels["email"] = {
            "type": "email",
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "to_email": to_email,
        }
    
    async def send_notification(
        self,
        event: Dict[str, Any],
        channels: Optional[List[str]] = None
    ):
        """Отправить уведомление"""
        
        if channels is None:
            channels = list(self.notification_channels.keys())
        
        tasks = []
        for channel in channels:
            if channel in self.notification_channels:
                task = self._send_to_channel(event, channel)
                tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_channel(
        self,
        event: Dict[str, Any],
        channel: str
    ):
        """Отправить в канал"""
        
        channel_data = self.notification_channels.get(channel)
        if not channel_data:
            return
        
        channel_type = channel_data["type"]
        
        if channel_type == "telegram":
            await self._send_telegram(event, channel_data)
        elif channel_type == "discord":
            await self._send_discord(event, channel_data)
        elif channel_type == "email":
            await self._send_email(event, channel_data)
    
    async def _send_telegram(
        self,
        event: Dict[str, Any],
        channel_data: Dict[str, Any]
    ):
        """Отправить в Telegram"""
        
        bot_token = channel_data["bot_token"]
        chat_id = channel_data["chat_id"]
        
        # Форматируем сообщение
        message = self._format_telegram_message(event)
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        print(f"Failed to send Telegram notification: {resp.status}")
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")
    
    async def _send_discord(
        self,
        event: Dict[str, Any],
        channel_data: Dict[str, Any]
    ):
        """Отправить в Discord"""
        
        webhook_url = channel_data["webhook_url"]
        
        # Форматируем сообщение
        message = self._format_discord_message(event)
        
        payload = {
            "content": message,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status not in [200, 204]:
                        print(f"Failed to send Discord notification: {resp.status}")
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
    
    async def _send_email(
        self,
        event: Dict[str, Any],
        channel_data: Dict[str, Any]
    ):
        """Отправить Email"""
        
        # Здесь должна быть реализация отправки email
        # Для примера просто выводим в консоль
        print(f"Email notification: {event}")
    
    def _format_telegram_message(self, event: Dict[str, Any]) -> str:
        """Форматировать сообщение для Telegram"""
        
        event_type = event.get("type", "unknown")
        
        if event_type == "transaction":
            chain = event.get("chain", "unknown")
            tx_hash = event.get("tx_hash", "")
            from_addr = event.get("from", "")
            to_addr = event.get("to", "")
            value = event.get("value", 0)
            
            message = f"🔔 <b>New Transaction on {chain.upper()}</b>\n\n"
            message += f"💰 Value: {value:.6f}\n"
            message += f"📤 From: <code>{from_addr[:10]}...{from_addr[-8:]}</code>\n"
            message += f"📥 To: <code>{to_addr[:10]}...{to_addr[-8:]}</code>\n"
            message += f"🔗 TX: <code>{tx_hash[:10]}...{tx_hash[-8:]}</code>\n"
            
            return message
        
        return str(event)
    
    def _format_discord_message(self, event: Dict[str, Any]) -> str:
        """Форматировать сообщение для Discord"""
        
        event_type = event.get("type", "unknown")
        
        if event_type == "transaction":
            chain = event.get("chain", "unknown")
            tx_hash = event.get("tx_hash", "")
            from_addr = event.get("from", "")
            to_addr = event.get("to", "")
            value = event.get("value", 0)
            
            message = f"🔔 **New Transaction on {chain.upper()}**\n\n"
            message += f"💰 Value: {value:.6f}\n"
            message += f"📤 From: `{from_addr[:10]}...{from_addr[-8:]}`\n"
            message += f"📥 To: `{to_addr[:10]}...{to_addr[-8:]}`\n"
            message += f"🔗 TX: `{tx_hash[:10]}...{tx_hash[-8:]}`\n"
            
            return message
        
        return str(event)


class AlertManager:
    """Менеджер алертов"""
    
    def __init__(self):
        self.alerts = {}
    
    def add_alert(
        self,
        alert_id: str,
        condition: Callable,
        action: Callable,
        description: str = ""
    ):
        """Добавить алерт"""
        
        self.alerts[alert_id] = {
            "condition": condition,
            "action": action,
            "description": description,
            "triggered_count": 0,
            "last_triggered": None,
        }
    
    async def check_alerts(self, event: Dict[str, Any]):
        """Проверить алерты"""
        
        for alert_id, alert_data in self.alerts.items():
            condition = alert_data["condition"]
            
            try:
                # Проверяем условие
                if condition(event):
                    # Выполняем действие
                    action = alert_data["action"]
                    
                    if asyncio.iscoroutinefunction(action):
                        await action(event)
                    else:
                        action(event)
                    
                    # Обновляем статистику
                    alert_data["triggered_count"] += 1
                    alert_data["last_triggered"] = datetime.now().isoformat()
            
            except Exception as e:
                print(f"Error checking alert {alert_id}: {e}")
    
    def remove_alert(self, alert_id: str):
        """Удалить алерт"""
        
        if alert_id in self.alerts:
            del self.alerts[alert_id]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Получить статистику алертов"""
        
        return {
            alert_id: {
                "description": data["description"],
                "triggered_count": data["triggered_count"],
                "last_triggered": data["last_triggered"],
            }
            for alert_id, data in self.alerts.items()
        }
