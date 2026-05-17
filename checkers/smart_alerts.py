# -*- coding: utf-8 -*-
"""
Smart Alerts - Умные уведомления о находках
Автоматические алерты при обнаружении балансов, китов, редких NFT и т.д.
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json


class AlertRule:
    """Правило для алерта"""
    
    def __init__(self, name: str, condition: Callable, priority: str = "medium",
                 message_template: str = "", enabled: bool = True):
        """
        Args:
            name: название правила
            condition: функция проверки условия (принимает result dict)
            priority: приоритет (low, medium, high, critical)
            message_template: шаблон сообщения
            enabled: включено ли правило
        """
        self.name = name
        self.condition = condition
        self.priority = priority
        self.message_template = message_template
        self.enabled = enabled
        self.triggered_count = 0
        self.last_triggered = None


class SmartAlertManager:
    """Менеджер умных алертов"""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.alerts_history: List[Dict[str, Any]] = []
        self.telegram_enabled = False
        self.telegram_token = ""
        self.telegram_chat_id = ""
        self.discord_enabled = False
        self.discord_webhook = ""
        self.sound_enabled = True
        self.desktop_notifications = True
        
        # Статистика
        self.stats = {
            "total_alerts": 0,
            "by_priority": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "by_rule": {},
        }
        
        # Инициализируем стандартные правила
        self._init_default_rules()
    
    def _init_default_rules(self):
        """Инициализировать стандартные правила алертов"""
        
        # 🐋 Кит обнаружен (баланс > $10,000)
        self.add_rule(AlertRule(
            name="Whale Alert",
            condition=lambda r: self._get_balance_usd(r) >= 10000,
            priority="critical",
            message_template="🐋 КИТ ОБНАРУЖЕН!\n💰 Баланс: ${balance_usd:,.2f}\n🔑 Адрес: {address}\n⛓️ Сеть: {chain}",
            enabled=True
        ))
        
        # 💎 Высокий баланс ($1,000 - $10,000)
        self.add_rule(AlertRule(
            name="High Balance",
            condition=lambda r: 1000 <= self._get_balance_usd(r) < 10000,
            priority="high",
            message_template="💎 Высокий баланс найден!\n💰 ${balance_usd:,.2f}\n🔑 {address}\n⛓️ {chain}",
            enabled=True
        ))
        
        # 💰 Средний баланс ($100 - $1,000)
        self.add_rule(AlertRule(
            name="Medium Balance",
            condition=lambda r: 100 <= self._get_balance_usd(r) < 1000,
            priority="medium",
            message_template="💰 Баланс найден: ${balance_usd:,.2f}\n🔑 {address}",
            enabled=True
        ))
        
        # 🎨 NFT обнаружены
        self.add_rule(AlertRule(
            name="NFT Found",
            condition=lambda r: self._has_nfts(r),
            priority="high",
            message_template="🎨 NFT обнаружены!\n📦 Количество: {nft_count}\n🔑 {address}",
            enabled=True
        ))
        
        # 🪂 Airdrop доступен
        self.add_rule(AlertRule(
            name="Airdrop Eligible",
            condition=lambda r: self._has_airdrop(r),
            priority="medium",
            message_template="🪂 Доступен Airdrop!\n💵 Примерно: ${airdrop_value:,.2f}\n🔑 {address}",
            enabled=True
        ))
        
        # 📊 DeFi позиции найдены
        self.add_rule(AlertRule(
            name="DeFi Positions",
            condition=lambda r: self._has_defi(r),
            priority="medium",
            message_template="📊 DeFi позиции: ${defi_value:,.2f}\n🔑 {address}",
            enabled=True
        ))
        
        # 🔥 Активный кошелек (много транзакций)
        self.add_rule(AlertRule(
            name="Active Wallet",
            condition=lambda r: self._is_active_wallet(r),
            priority="low",
            message_template="🔥 Активный кошелек\n📈 Транзакций: {tx_count}\n🔑 {address}",
            enabled=True
        ))
        
        # 🎰 Редкий токен обнаружен
        self.add_rule(AlertRule(
            name="Rare Token",
            condition=lambda r: self._has_rare_token(r),
            priority="high",
            message_template="🎰 Редкий токен: {token_name}\n💰 ${token_value:,.2f}\n🔑 {address}",
            enabled=True
        ))
    
    def _get_balance_usd(self, result: dict) -> float:
        """Получить баланс в USD из результата"""
        info = result.get("info", {})
        
        # Пробуем разные поля
        if "total_usd" in info:
            return float(info.get("total_usd", 0))
        elif "balance_usd" in info:
            return float(info.get("balance_usd", 0))
        elif "value_usd" in info:
            return float(info.get("value_usd", 0))
        
        return 0.0
    
    def _has_nfts(self, result: dict) -> bool:
        """Проверить наличие NFT"""
        info = result.get("info", {})
        return "nfts" in info or "nft_count" in info
    
    def _has_airdrop(self, result: dict) -> bool:
        """Проверить доступность airdrop"""
        info = result.get("info", {})
        return "airdrop" in info or "airdrop_eligible" in info
    
    def _has_defi(self, result: dict) -> bool:
        """Проверить наличие DeFi позиций"""
        info = result.get("info", {})
        return "defi" in info or "defi_positions" in info
    
    def _is_active_wallet(self, result: dict) -> bool:
        """Проверить активность кошелька"""
        info = result.get("info", {})
        tx_count = info.get("tx_count", 0)
        return tx_count > 100
    
    def _has_rare_token(self, result: dict) -> bool:
        """Проверить наличие редких токенов"""
        info = result.get("info", {})
        tokens = info.get("tokens", [])
        
        # Список редких токенов (можно расширить)
        rare_tokens = ["PEPE", "SHIB", "FLOKI", "DOGE", "BONK"]
        
        for token in tokens:
            if isinstance(token, dict):
                symbol = token.get("symbol", "").upper()
                if symbol in rare_tokens:
                    return True
        
        return False
    
    def add_rule(self, rule: AlertRule):
        """Добавить правило алерта"""
        self.rules.append(rule)
        self.stats["by_rule"][rule.name] = 0
    
    def remove_rule(self, rule_name: str):
        """Удалить правило по имени"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        if rule_name in self.stats["by_rule"]:
            del self.stats["by_rule"][rule_name]
    
    def enable_rule(self, rule_name: str):
        """Включить правило"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                break
    
    def disable_rule(self, rule_name: str):
        """Выключить правило"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                break
    
    async def check_alerts(self, result: dict) -> List[Dict[str, Any]]:
        """
        Проверить результат на соответствие правилам алертов
        
        Returns:
            список сработавших алертов
        """
        triggered_alerts = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Проверяем условие
                if rule.condition(result):
                    # Формируем алерт
                    alert = self._create_alert(rule, result)
                    triggered_alerts.append(alert)
                    
                    # Обновляем статистику
                    rule.triggered_count += 1
                    rule.last_triggered = time.time()
                    self.stats["total_alerts"] += 1
                    self.stats["by_priority"][rule.priority] += 1
                    self.stats["by_rule"][rule.name] += 1
                    
                    # Сохраняем в историю
                    self.alerts_history.append(alert)
                    
                    # Отправляем уведомления
                    await self._send_notifications(alert)
            
            except Exception as e:
                print(f"❌ Ошибка проверки правила {rule.name}: {e}")
        
        return triggered_alerts
    
    def _create_alert(self, rule: AlertRule, result: dict) -> Dict[str, Any]:
        """Создать алерт из правила и результата"""
        info = result.get("info", {})
        
        # Извлекаем данные для шаблона
        template_data = {
            "balance_usd": self._get_balance_usd(result),
            "address": result.get("input", "")[:50],
            "chain": result.get("wallet_type", result.get("type", "unknown")),
            "nft_count": info.get("nft_count", 0),
            "airdrop_value": info.get("airdrop_value", 0),
            "defi_value": info.get("defi_value", 0),
            "tx_count": info.get("tx_count", 0),
            "token_name": "",
            "token_value": 0,
        }
        
        # Форматируем сообщение
        try:
            message = rule.message_template.format(**template_data)
        except:
            message = f"{rule.name}: {template_data['address']}"
        
        return {
            "rule_name": rule.name,
            "priority": rule.priority,
            "message": message,
            "timestamp": time.time(),
            "result": result,
            "data": template_data,
        }
    
    async def _send_notifications(self, alert: Dict[str, Any]):
        """Отправить уведомления о алерте"""
        tasks = []
        
        # Telegram
        if self.telegram_enabled and self.telegram_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(alert))
        
        # Discord
        if self.discord_enabled and self.discord_webhook:
            tasks.append(self._send_discord(alert))
        
        # Desktop notification
        if self.desktop_notifications:
            self._send_desktop_notification(alert)
        
        # Sound
        if self.sound_enabled:
            self._play_alert_sound(alert["priority"])
        
        # Отправляем все уведомления параллельно
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_telegram(self, alert: Dict[str, Any]):
        """Отправить уведомление в Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            # Добавляем эмодзи приоритета
            priority_emoji = {
                "low": "ℹ️",
                "medium": "⚠️",
                "high": "🔥",
                "critical": "🚨"
            }
            
            emoji = priority_emoji.get(alert["priority"], "📢")
            message = f"{emoji} {alert['message']}"
            
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=10) as resp:
                    if resp.status != 200:
                        print(f"❌ Ошибка отправки в Telegram: {resp.status}")
        
        except Exception as e:
            print(f"❌ Ошибка Telegram: {e}")
    
    async def _send_discord(self, alert: Dict[str, Any]):
        """Отправить уведомление в Discord"""
        try:
            # Цвета для разных приоритетов
            priority_colors = {
                "low": 0x3498db,      # синий
                "medium": 0xf39c12,   # оранжевый
                "high": 0xe74c3c,     # красный
                "critical": 0x9b59b6  # фиолетовый
            }
            
            embed = {
                "title": f"🔔 {alert['rule_name']}",
                "description": alert["message"],
                "color": priority_colors.get(alert["priority"], 0x3498db),
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "MultiChecker Pro"
                }
            }
            
            data = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=data, timeout=10) as resp:
                    if resp.status not in (200, 204):
                        print(f"❌ Ошибка отправки в Discord: {resp.status}")
        
        except Exception as e:
            print(f"❌ Ошибка Discord: {e}")
    
    def _send_desktop_notification(self, alert: Dict[str, Any]):
        """Отправить desktop уведомление"""
        try:
            # Используем plyer для кроссплатформенных уведомлений
            try:
                from plyer import notification
                
                notification.notify(
                    title=f"MultiChecker - {alert['rule_name']}",
                    message=alert["message"][:200],  # Ограничение длины
                    app_name="MultiChecker Pro",
                    timeout=10
                )
            except ImportError:
                # Если plyer не установлен, используем системные команды
                import platform
                system = platform.system()
                
                if system == "Windows":
                    # Windows toast notification
                    try:
                        from win10toast import ToastNotifier
                        toaster = ToastNotifier()
                        toaster.show_toast(
                            "MultiChecker Pro",
                            alert["message"][:200],
                            duration=10,
                            threaded=True
                        )
                    except:
                        pass
        
        except Exception as e:
            print(f"❌ Ошибка desktop notification: {e}")
    
    def _play_alert_sound(self, priority: str):
        """Воспроизвести звук алерта"""
        try:
            import winsound
            
            # Разные звуки для разных приоритетов
            if priority == "critical":
                # Критический - 3 коротких сигнала
                for _ in range(3):
                    winsound.Beep(1000, 200)
            elif priority == "high":
                # Высокий - 2 сигнала
                for _ in range(2):
                    winsound.Beep(800, 200)
            elif priority == "medium":
                # Средний - 1 сигнал
                winsound.Beep(600, 300)
            else:
                # Низкий - короткий сигнал
                winsound.Beep(400, 150)
        
        except Exception:
            # Если winsound недоступен (не Windows), используем print
            print(f"\a")  # Системный beep
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику алертов"""
        return {
            "total_alerts": self.stats["total_alerts"],
            "by_priority": self.stats["by_priority"].copy(),
            "by_rule": self.stats["by_rule"].copy(),
            "rules_count": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "recent_alerts": self.alerts_history[-10:] if self.alerts_history else []
        }
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Получить список всех правил"""
        return [
            {
                "name": rule.name,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "triggered_count": rule.triggered_count,
                "last_triggered": rule.last_triggered
            }
            for rule in self.rules
        ]
    
    def clear_history(self):
        """Очистить историю алертов"""
        self.alerts_history.clear()
    
    def export_history(self, filepath: str):
        """Экспортировать историю алертов в JSON"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.alerts_history, f, indent=2, ensure_ascii=False)
            print(f"✓ История алертов экспортирована: {filepath}")
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")


# Глобальный экземпляр менеджера алертов
global_alert_manager = SmartAlertManager()
