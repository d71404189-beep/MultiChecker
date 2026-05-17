# -*- coding: utf-8 -*-
"""
Balance Cache v1.0.88
Кэш балансов — один адрес не проверяется дважды за 5 минут.
Потокобезопасный, async-совместимый.
"""

import time
import asyncio
from typing import Optional, Dict, Any


class BalanceCache:
    """
    Кэш результатов проверки балансов.
    TTL по умолчанию 300 секунд (5 минут).
    """

    def __init__(self, ttl: float = 300.0):
        self._ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _key(self, address: str, network: str) -> str:
        return f"{network}:{address.lower()}"

    async def get(self, address: str, network: str) -> Optional[dict]:
        """Вернуть кэшированный результат или None."""
        k = self._key(address, network)
        async with self._lock:
            entry = self._cache.get(k)
            if entry and (time.time() - entry["ts"]) < self._ttl:
                return entry["result"]
            # Устаревший — удаляем
            if entry:
                del self._cache[k]
        return None

    async def set(self, address: str, network: str, result: dict) -> None:
        """Сохранить результат в кэш."""
        k = self._key(address, network)
        async with self._lock:
            self._cache[k] = {"ts": time.time(), "result": result}

    async def invalidate(self, address: str, network: str) -> None:
        """Удалить запись из кэша."""
        k = self._key(address, network)
        async with self._lock:
            self._cache.pop(k, None)

    async def clear(self) -> None:
        """Очистить весь кэш."""
        async with self._lock:
            self._cache.clear()

    def size(self) -> int:
        return len(self._cache)

    async def cleanup_expired(self) -> int:
        """Удалить устаревшие записи. Возвращает количество удалённых."""
        now = time.time()
        async with self._lock:
            expired = [k for k, v in self._cache.items() if (now - v["ts"]) >= self._ttl]
            for k in expired:
                del self._cache[k]
        return len(expired)


# Глобальный кэш (один на всё приложение)
global_balance_cache = BalanceCache(ttl=300.0)
