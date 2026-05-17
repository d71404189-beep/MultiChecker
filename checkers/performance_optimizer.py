# -*- coding: utf-8 -*-
"""
Performance Optimizer - Оптимизация производительности
Кэширование, rate limiting, параллельные запросы
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib
import json


class CacheManager:
    """Менеджер кэша для результатов проверок"""
    
    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: время жизни кэша в секундах (по умолчанию 1 час)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def _make_key(self, *args, **kwargs) -> str:
        """Создать ключ кэша из аргументов"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                # Кэш устарел
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Сохранить значение в кэш"""
        self.cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
    
    def clear(self):
        """Очистить весь кэш"""
        self.cache.clear()
    
    def clear_expired(self):
        """Очистить устаревшие записи"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry["timestamp"] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self.cache.values()
            if current_time - entry["timestamp"] < self.ttl
        )
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "memory_usage_mb": len(json.dumps(self.cache)) / 1024 / 1024
        }


class RateLimiter:
    """Rate limiter для API запросов"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: максимум запросов
            time_window: временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}
    
    async def acquire(self, key: str = "default"):
        """Получить разрешение на запрос"""
        current_time = time.time()
        
        # Инициализируем список запросов для ключа
        if key not in self.requests:
            self.requests[key] = []
        
        # Удаляем старые запросы
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if current_time - req_time < self.time_window
        ]
        
        # Проверяем лимит
        if len(self.requests[key]) >= self.max_requests:
            # Ждем до освобождения слота
            oldest_request = self.requests[key][0]
            wait_time = self.time_window - (current_time - oldest_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return await self.acquire(key)
        
        # Добавляем текущий запрос
        self.requests[key].append(current_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику rate limiter"""
        current_time = time.time()
        stats = {}
        
        for key, requests in self.requests.items():
            active_requests = [
                req for req in requests
                if current_time - req < self.time_window
            ]
            stats[key] = {
                "active_requests": len(active_requests),
                "max_requests": self.max_requests,
                "available_slots": self.max_requests - len(active_requests)
            }
        
        return stats


class BatchProcessor:
    """Пакетная обработка запросов"""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        """
        Args:
            batch_size: размер пакета
            max_concurrent: максимум одновременных задач
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(self, items: list, processor: Callable, 
                           progress_callback: Optional[Callable] = None) -> list:
        """
        Обработать список элементов пакетами
        
        Args:
            items: список элементов для обработки
            processor: async функция обработки одного элемента
            progress_callback: callback для отслеживания прогресса
            
        Returns:
            список результатов
        """
        results = []
        total = len(items)
        
        # Разбиваем на пакеты
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Обрабатываем пакет с ограничением concurrency
            batch_results = await self._process_batch_concurrent(
                batch, processor
            )
            
            results.extend(batch_results)
            
            # Вызываем callback прогресса
            if progress_callback:
                progress_callback(len(results), total)
            
            # Небольшая задержка между пакетами
            if i + self.batch_size < total:
                await asyncio.sleep(0.1)
        
        return results
    
    async def _process_batch_concurrent(self, batch: list, 
                                       processor: Callable) -> list:
        """Обработать пакет с ограничением concurrency"""
        
        async def process_with_semaphore(item):
            async with self.semaphore:
                try:
                    return await processor(item)
                except Exception as e:
                    return {"error": str(e), "item": item}
        
        tasks = [process_with_semaphore(item) for item in batch]
        return await asyncio.gather(*tasks)


class PerformanceMonitor:
    """Мониторинг производительности"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record(self, metric_name: str, value: float):
        """Записать метрику"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": time.time()
        })
        
        # Храним только последние 1000 записей
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Получить статистику по метрике"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        values = [m["value"] for m in self.metrics[metric_name]]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "total": sum(values)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Получить статистику по всем метрикам"""
        return {
            name: self.get_stats(name)
            for name in self.metrics.keys()
        }


def cached(cache_manager: CacheManager, ttl: Optional[int] = None):
    """Декоратор для кэширования результатов функций"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша
            cache_key = cache_manager._make_key(func.__name__, *args, **kwargs)
            
            # Проверяем кэш
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache_manager.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def rate_limited(rate_limiter: RateLimiter, key: str = "default"):
    """Декоратор для rate limiting"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Ждем разрешения
            await rate_limiter.acquire(key)
            
            # Выполняем функцию
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def timed(monitor: PerformanceMonitor, metric_name: str):
    """Декоратор для измерения времени выполнения"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                monitor.record(metric_name, elapsed)
        
        return wrapper
    return decorator


# Глобальные экземпляры для использования в других модулях
global_cache = CacheManager(ttl=3600)  # 1 час
global_rate_limiter = RateLimiter(max_requests=10, time_window=60)  # 10 req/min
global_batch_processor = BatchProcessor(batch_size=10, max_concurrent=5)
global_monitor = PerformanceMonitor()


def get_performance_stats() -> Dict[str, Any]:
    """Получить общую статистику производительности"""
    return {
        "cache": global_cache.get_stats(),
        "rate_limiter": global_rate_limiter.get_stats(),
        "performance": global_monitor.get_all_stats()
    }


def clear_all_caches():
    """Очистить все кэши"""
    global_cache.clear()
    print("✓ Все кэши очищены")


def optimize_memory():
    """Оптимизировать использование памяти"""
    global_cache.clear_expired()
    print("✓ Устаревшие записи кэша удалены")
