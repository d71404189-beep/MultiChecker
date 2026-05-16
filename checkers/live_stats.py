# -*- coding: utf-8 -*-
"""
Live Statistics v1.0.65
Живая статистика в реальном времени
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time


class LiveStatistics:
    """Живая статистика с обновлением в реальном времени"""
    
    def __init__(self):
        self.stats = {
            "total_checked": 0,
            "total_valid": 0,
            "total_invalid": 0,
            "total_errors": 0,
            "total_with_balance": 0,
            "total_usd": 0.0,
            "start_time": None,
            "current_speed": 0.0,  # адресов/сек
            "avg_speed": 0.0,
            "eta_seconds": 0,
            "top_finds": [],  # Топ-10 находок
            "recent_finds": [],  # Последние 5 находок
            "balance_distribution": {  # Распределение по балансу
                "0-10": 0,
                "10-100": 0,
                "100-1000": 0,
                "1000-10000": 0,
                "10000+": 0,
            },
            "by_chain": {},
        }
        
        self.callbacks = []  # Колбэки для обновления UI
        self.last_update_time = 0
        self.update_interval = 0.5  # Обновлять каждые 0.5 сек
    
    def start(self):
        """Начать отслеживание"""
        self.stats["start_time"] = time.time()
    
    def update(self, result: Dict[str, Any]):
        """
        Обновить статистику после проверки
        
        Args:
            result: Результат проверки одного адреса
        """
        
        # Обновляем счетчики
        self.stats["total_checked"] += 1
        
        if result.get("exists") or not result.get("info", {}).get("error"):
            self.stats["total_valid"] += 1
        else:
            if result.get("info", {}).get("error"):
                self.stats["total_errors"] += 1
            else:
                self.stats["total_invalid"] += 1
        
        # Баланс
        balance_usd = self._extract_balance(result)
        
        if balance_usd > 0:
            self.stats["total_with_balance"] += 1
            self.stats["total_usd"] += balance_usd
            
            # Добавляем в топ находки
            self._add_to_top_finds(result, balance_usd)
            
            # Добавляем в последние находки
            self._add_to_recent_finds(result, balance_usd)
            
            # Обновляем распределение по балансу
            self._update_balance_distribution(balance_usd)
        
        # Статистика по сетям
        chain = result.get("wallet_type") or result.get("type") or "unknown"
        if chain not in self.stats["by_chain"]:
            self.stats["by_chain"][chain] = {
                "count": 0,
                "with_balance": 0,
                "total_usd": 0.0,
            }
        
        self.stats["by_chain"][chain]["count"] += 1
        if balance_usd > 0:
            self.stats["by_chain"][chain]["with_balance"] += 1
            self.stats["by_chain"][chain]["total_usd"] += balance_usd
        
        # Вычисляем скорость
        self._calculate_speed()
        
        # Вызываем колбэки для обновления UI
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self._trigger_callbacks()
            self.last_update_time = current_time
    
    def _extract_balance(self, result: Dict[str, Any]) -> float:
        """Извлечь баланс из результата"""
        
        info = result.get("info", {})
        
        if "total_usd" in info:
            return float(info.get("total_usd", 0))
        elif "balance_usd" in info:
            return float(info.get("balance_usd", 0))
        
        return 0.0
    
    def _add_to_top_finds(self, result: Dict[str, Any], balance_usd: float):
        """Добавить в топ находки"""
        
        find = {
            "address": result.get("input", "")[:50],
            "balance_usd": balance_usd,
            "chain": result.get("wallet_type", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }
        
        self.stats["top_finds"].append(find)
        
        # Сортируем по балансу и оставляем топ-10
        self.stats["top_finds"].sort(key=lambda x: x["balance_usd"], reverse=True)
        self.stats["top_finds"] = self.stats["top_finds"][:10]
    
    def _add_to_recent_finds(self, result: Dict[str, Any], balance_usd: float):
        """Добавить в последние находки"""
        
        find = {
            "address": result.get("input", "")[:50],
            "balance_usd": balance_usd,
            "chain": result.get("wallet_type", "unknown"),
            "timestamp": datetime.now().isoformat(),
        }
        
        self.stats["recent_finds"].insert(0, find)
        
        # Оставляем только последние 5
        self.stats["recent_finds"] = self.stats["recent_finds"][:5]
    
    def _update_balance_distribution(self, balance_usd: float):
        """Обновить распределение по балансу"""
        
        if balance_usd < 10:
            self.stats["balance_distribution"]["0-10"] += 1
        elif balance_usd < 100:
            self.stats["balance_distribution"]["10-100"] += 1
        elif balance_usd < 1000:
            self.stats["balance_distribution"]["100-1000"] += 1
        elif balance_usd < 10000:
            self.stats["balance_distribution"]["1000-10000"] += 1
        else:
            self.stats["balance_distribution"]["10000+"] += 1
    
    def _calculate_speed(self):
        """Вычислить скорость проверки"""
        
        if not self.stats["start_time"]:
            return
        
        elapsed = time.time() - self.stats["start_time"]
        
        if elapsed > 0:
            self.stats["avg_speed"] = self.stats["total_checked"] / elapsed
            
            # Текущая скорость (за последние 10 секунд)
            # Упрощенная версия - используем среднюю
            self.stats["current_speed"] = self.stats["avg_speed"]
    
    def calculate_eta(self, total_items: int):
        """
        Вычислить ETA (оставшееся время)
        
        Args:
            total_items: Общее количество элементов для проверки
        """
        
        remaining = total_items - self.stats["total_checked"]
        
        if self.stats["current_speed"] > 0:
            self.stats["eta_seconds"] = remaining / self.stats["current_speed"]
        else:
            self.stats["eta_seconds"] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить текущую статистику"""
        return self.stats.copy()
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Зарегистрировать колбэк для обновления UI
        
        Args:
            callback: Функция которая будет вызвана при обновлении статистики
        """
        self.callbacks.append(callback)
    
    def _trigger_callbacks(self):
        """Вызвать все зарегистрированные колбэки"""
        
        stats = self.get_stats()
        
        for callback in self.callbacks:
            try:
                callback(stats)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    def format_eta(self) -> str:
        """Форматировать ETA в читаемый вид"""
        
        seconds = int(self.stats["eta_seconds"])
        
        if seconds < 60:
            return f"{seconds}с"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}м {secs}с"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}ч {minutes}м"
    
    def get_progress_percentage(self, total_items: int) -> float:
        """Получить процент выполнения"""
        
        if total_items == 0:
            return 0.0
        
        return (self.stats["total_checked"] / total_items) * 100
    
    def reset(self):
        """Сбросить статистику"""
        
        self.stats = {
            "total_checked": 0,
            "total_valid": 0,
            "total_invalid": 0,
            "total_errors": 0,
            "total_with_balance": 0,
            "total_usd": 0.0,
            "start_time": None,
            "current_speed": 0.0,
            "avg_speed": 0.0,
            "eta_seconds": 0,
            "top_finds": [],
            "recent_finds": [],
            "balance_distribution": {
                "0-10": 0,
                "10-100": 0,
                "100-1000": 0,
                "1000-10000": 0,
                "10000+": 0,
            },
            "by_chain": {},
        }
        
        self.last_update_time = 0
