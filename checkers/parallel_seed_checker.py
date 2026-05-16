# -*- coding: utf-8 -*-
"""
Parallel Seed Checker v1.0.58
Мультипоточная проверка сид-фраз с оптимизацией
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import time


class ParallelSeedChecker:
    """Параллельная проверка сид-фраз"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results_cache = {}
        self.active_checks = 0
        self.total_checks = 0
        self.progress_callback = None
    
    async def check_seeds_parallel(
        self,
        seed_phrases: List[str],
        checker_func: Callable,
        timeout: int = 10,
        proxy: str = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Параллельная проверка списка сид-фраз
        
        Args:
            seed_phrases: Список сид-фраз
            checker_func: Функция проверки (async)
            timeout: Таймаут для каждой проверки
            proxy: Прокси
            progress_callback: Callback для обновления прогресса
        
        Returns:
            Список результатов
        """
        
        self.progress_callback = progress_callback
        self.total_checks = len(seed_phrases)
        self.active_checks = 0
        
        results = []
        
        # Создаем сессию
        async with aiohttp.ClientSession() as session:
            # Создаем семафор для ограничения параллельных запросов
            semaphore = asyncio.Semaphore(self.max_workers)
            
            # Создаем задачи
            tasks = []
            for i, seed in enumerate(seed_phrases):
                task = self._check_seed_with_semaphore(
                    seed,
                    checker_func,
                    session,
                    timeout,
                    proxy,
                    semaphore,
                    i
                )
                tasks.append(task)
            
            # Запускаем все задачи параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем исключения
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "input": seed_phrases[i][:20] + "...",
                        "type": "seed",
                        "exists": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
    
    async def _check_seed_with_semaphore(
        self,
        seed: str,
        checker_func: Callable,
        session: aiohttp.ClientSession,
        timeout: int,
        proxy: str,
        semaphore: asyncio.Semaphore,
        index: int
    ) -> Dict[str, Any]:
        """Проверка сид-фразы с семафором"""
        
        async with semaphore:
            self.active_checks += 1
            
            # Обновляем прогресс
            if self.progress_callback:
                await self.progress_callback(index + 1, self.total_checks)
            
            try:
                # Вызываем функцию проверки
                result = await checker_func(seed, timeout, proxy, session)
                return result
            
            finally:
                self.active_checks -= 1
    
    async def check_seeds_batch(
        self,
        seed_phrases: List[str],
        checker_func: Callable,
        batch_size: int = 10,
        timeout: int = 10,
        proxy: str = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Пакетная проверка сид-фраз (по batch_size за раз)
        
        Более контролируемый подход для больших списков
        """
        
        self.progress_callback = progress_callback
        self.total_checks = len(seed_phrases)
        
        all_results = []
        
        # Разбиваем на батчи
        for i in range(0, len(seed_phrases), batch_size):
            batch = seed_phrases[i:i + batch_size]
            
            # Проверяем батч
            batch_results = await self.check_seeds_parallel(
                batch,
                checker_func,
                timeout,
                proxy,
                progress_callback
            )
            
            all_results.extend(batch_results)
            
            # Небольшая задержка между батчами
            await asyncio.sleep(0.5)
        
        return all_results
    
    def optimize_seed_check(
        self,
        seed: str,
        derivation_paths: List[str] = None
    ) -> List[str]:
        """
        Оптимизация проверки сид-фразы
        
        Возвращает только наиболее вероятные пути деривации
        
        Args:
            seed: Сид-фраза
            derivation_paths: Список путей для проверки
        
        Returns:
            Оптимизированный список путей
        """
        
        if derivation_paths is None:
            # Стандартные пути (наиболее популярные)
            derivation_paths = [
                # Bitcoin
                "m/44'/0'/0'/0/0",   # BTC Legacy (первый адрес)
                "m/49'/0'/0'/0/0",   # BTC SegWit
                "m/84'/0'/0'/0/0",   # BTC Native SegWit
                
                # Ethereum
                "m/44'/60'/0'/0/0",  # ETH (первый адрес)
                "m/44'/60'/0'/0/1",  # ETH (второй адрес)
                
                # Другие популярные
                "m/44'/501'/0'/0'",  # Solana
                "m/44'/195'/0'/0/0", # Tron
                "m/44'/714'/0'/0/0", # Binance Chain
            ]
        
        # Можно добавить логику для определения наиболее вероятных путей
        # на основе статистики или эвристик
        
        return derivation_paths
    
    async def smart_seed_check(
        self,
        seed: str,
        checker_func: Callable,
        session: aiohttp.ClientSession,
        timeout: int = 10,
        proxy: str = None
    ) -> Dict[str, Any]:
        """
        Умная проверка сид-фразы
        
        1. Проверяет только первые адреса каждой сети
        2. Если находит баланс - проверяет больше адресов
        3. Кэширует результаты
        """
        
        # Проверяем кэш
        cache_key = seed[:20]
        if cache_key in self.results_cache:
            return self.results_cache[cache_key]
        
        # Быстрая проверка (только первые адреса)
        result = await checker_func(seed, timeout, proxy, session)
        
        # Кэшируем
        self.results_cache[cache_key] = result
        
        # Если нашли баланс - можно расширить проверку
        if result.get("exists"):
            # Здесь можно добавить дополнительную проверку
            pass
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику проверок"""
        
        return {
            "total_checks": self.total_checks,
            "active_checks": self.active_checks,
            "cache_size": len(self.results_cache),
            "max_workers": self.max_workers,
        }
    
    def clear_cache(self) -> None:
        """Очистить кэш результатов"""
        self.results_cache.clear()


class SeedDerivationOptimizer:
    """Оптимизатор деривации адресов из сид-фразы"""
    
    def __init__(self):
        # Статистика популярности путей деривации
        self.path_popularity = {
            "m/44'/0'/0'/0/0": 100,    # BTC Legacy - очень популярный
            "m/84'/0'/0'/0/0": 95,     # BTC Native SegWit - очень популярный
            "m/44'/60'/0'/0/0": 100,   # ETH - очень популярный
            "m/49'/0'/0'/0/0": 80,     # BTC SegWit - популярный
            "m/44'/501'/0'/0'": 70,    # Solana - популярный
            "m/44'/195'/0'/0/0": 60,   # Tron - средний
            "m/44'/714'/0'/0/0": 50,   # BNB - средний
        }
    
    def get_priority_paths(self, max_paths: int = 10) -> List[str]:
        """
        Получить приоритетные пути деривации
        
        Args:
            max_paths: Максимальное количество путей
        
        Returns:
            Список путей, отсортированных по популярности
        """
        
        # Сортируем по популярности
        sorted_paths = sorted(
            self.path_popularity.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [path for path, _ in sorted_paths[:max_paths]]
    
    def should_check_more_addresses(
        self,
        found_balance: bool,
        current_index: int,
        max_index: int = 20
    ) -> bool:
        """
        Определить, нужно ли проверять больше адресов
        
        Args:
            found_balance: Найден ли баланс на текущем адресе
            current_index: Текущий индекс адреса
            max_index: Максимальный индекс для проверки
        
        Returns:
            True если нужно продолжать проверку
        """
        
        # Если нашли баланс - проверяем больше адресов
        if found_balance:
            return current_index < max_index
        
        # Если не нашли баланс на первых 3 адресах - останавливаемся
        if current_index >= 3:
            return False
        
        return True
    
    def estimate_check_time(
        self,
        num_seeds: int,
        addresses_per_seed: int = 10,
        time_per_address: float = 0.5
    ) -> float:
        """
        Оценить время проверки
        
        Args:
            num_seeds: Количество сид-фраз
            addresses_per_seed: Адресов на сид-фразу
            time_per_address: Время проверки одного адреса (сек)
        
        Returns:
            Примерное время в секундах
        """
        
        total_addresses = num_seeds * addresses_per_seed
        estimated_time = total_addresses * time_per_address
        
        return estimated_time


class ProgressTracker:
    """Трекер прогресса проверки"""
    
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.found_with_balance = 0
    
    def update(self, current: int, found_balance: bool = False) -> None:
        """Обновить прогресс"""
        self.current = current
        
        if found_balance:
            self.found_with_balance += 1
    
    def get_progress(self) -> Dict[str, Any]:
        """Получить информацию о прогрессе"""
        
        elapsed = time.time() - self.start_time
        progress_pct = (self.current / self.total * 100) if self.total > 0 else 0
        
        # Оценка оставшегося времени
        if self.current > 0:
            time_per_item = elapsed / self.current
            remaining_items = self.total - self.current
            eta_seconds = time_per_item * remaining_items
        else:
            eta_seconds = 0
        
        return {
            "current": self.current,
            "total": self.total,
            "progress_pct": progress_pct,
            "elapsed_seconds": elapsed,
            "eta_seconds": eta_seconds,
            "found_with_balance": self.found_with_balance,
            "speed": self.current / elapsed if elapsed > 0 else 0,  # items/sec
        }
    
    def format_progress(self) -> str:
        """Форматировать прогресс для отображения"""
        
        progress = self.get_progress()
        
        return (
            f"Progress: {progress['current']}/{progress['total']} "
            f"({progress['progress_pct']:.1f}%) | "
            f"Found: {progress['found_with_balance']} | "
            f"Speed: {progress['speed']:.1f}/s | "
            f"ETA: {int(progress['eta_seconds'])}s"
        )
