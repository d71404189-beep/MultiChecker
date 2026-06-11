# -*- coding: utf-8 -*-
"""
Price Service - Централизованный сервис получения цен
Решает все TODO связанные с получением цен и расчетом USD
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from functools import lru_cache


class PriceService:
    """Сервис для получения и кэширования цен криптовалют"""
    
    def __init__(self, cache_ttl: int = 300):
        """
        Args:
            cache_ttl: время жизни кэша в секундах (по умолчанию 5 минут)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = cache_ttl
        self.last_update = 0
        
        # Маппинг символов на CoinGecko IDs
        self.coingecko_map = {
            # Основные монеты
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "TRX": "tron",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "TON": "the-open-network",
            "ADA": "cardano",
            "LTC": "litecoin",
            "DASH": "dash",
            "XMR": "monero",
            "XRP": "ripple",
            "DOGE": "dogecoin",
            
            # Стейблкоины
            "USDT": "tether",
            "USDC": "usd-coin",
            "DAI": "dai",
            "BUSD": "binance-usd",
            "USDD": "usdd",
            
            # Популярные токены
            "LINK": "chainlink",
            "UNI": "uniswap",
            "SHIB": "shiba-inu",
            "PEPE": "pepe",
            "WETH": "weth",
            "WBTC": "wrapped-bitcoin",
            "APE": "apecoin",
            "SAND": "the-sandbox",
            "MANA": "decentraland",
            "CRV": "curve-dao-token",
            "AAVE": "aave",
            "COMP": "compound-governance-token",
            "MKR": "maker",
            "SNX": "havven",
            "YFI": "yearn-finance",
            "SUSHI": "sushi",
            "1INCH": "1inch",
            "BAL": "balancer",
            "LDO": "lido-dao",
            "RPL": "rocket-pool",
            "FTM": "fantom",
            "CRO": "crypto-com-chain",
            "OP": "optimism",
            "ARB": "arbitrum",
            "RNDR": "render-token",
            "IMX": "immutable-x",
            "GALA": "gala",
            "AXS": "axie-infinity",
            "FLOW": "flow",
            "APT": "aptos",
            "SUI": "sui",
            "INJ": "injective-protocol",
            "STX": "blockstack",
            "NEAR": "near",
            "ATOM": "cosmos",
            "DOT": "polkadot",
            "ALGO": "algorand",
            "XLM": "stellar",
            "VET": "vechain",
            "ICP": "internet-computer",
            "FIL": "filecoin",
            "HBAR": "hedera-hashgraph",
            "ETC": "ethereum-classic",
            "XTZ": "tezos",
            "THETA": "theta-token",
            "EOS": "eos",
            "KAVA": "kava",
            "RUNE": "thorchain",
            "LUNA": "terra-luna-2",
            "LUNC": "terra-luna",

            # v1.0.92: новые сети
            "MNT": "mantle",
            "GLMR": "moonbeam",
            "XDAI": "xdai",
            "CELO": "celo",
        }
        
        # Обратный маппинг (chain -> symbol)
        self.chain_to_symbol = {
            "ethereum": "ETH",
            "bitcoin": "BTC",
            "bsc": "BNB",
            "polygon": "MATIC",
            "solana": "SOL",
            "tron": "TRX",
            "avalanche": "AVAX",
            "ton": "TON",
            "cardano": "ADA",
            "litecoin": "LTC",
            "dash": "DASH",
            "monero": "XMR",
            "ripple": "XRP",
            "dogecoin": "DOGE",
            "arbitrum": "ETH",
            "optimism": "ETH",
            "base": "ETH",
            "fantom": "FTM",
            "cronos": "CRO",
            "zksync": "ETH",
            "linea": "ETH",
            "scroll": "ETH",
            # v1.0.92: новые сети
            "blast": "ETH",
            "mantle": "MNT",
            "gnosis": "XDAI",
            "celo": "CELO",
            "moonbeam": "GLMR",
            "opbnb": "BNB",
        }
    
    async def get_price(self, symbol: str) -> float:
        """
        Получить цену одной монеты
        
        Args:
            symbol: символ монеты (BTC, ETH, USDT и т.д.)
            
        Returns:
            цена в USD
        """
        symbol = symbol.upper()
        
        # Проверяем кэш
        if self._is_cache_valid() and symbol in self.cache:
            return self.cache[symbol].get("price", 0)
        
        # Обновляем кэш
        await self.update_prices([symbol])
        
        return self.cache.get(symbol, {}).get("price", 0)
    
    async def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Получить цены нескольких монет
        
        Args:
            symbols: список символов
            
        Returns:
            словарь {symbol: price}
        """
        symbols = [s.upper() for s in symbols]
        
        # Проверяем кэш
        if self._is_cache_valid():
            cached_symbols = set(self.cache.keys())
            if all(s in cached_symbols for s in symbols):
                return {s: self.cache[s].get("price", 0) for s in symbols}
        
        # Обновляем кэш
        await self.update_prices(symbols)
        
        return {s: self.cache.get(s, {}).get("price", 0) for s in symbols}
    
    async def get_price_by_chain(self, chain: str) -> float:
        """
        Получить цену нативной монеты сети
        
        Args:
            chain: название сети (ethereum, bitcoin, bsc и т.д.)
            
        Returns:
            цена в USD
        """
        symbol = self.chain_to_symbol.get(chain.lower(), chain.upper())
        return await self.get_price(symbol)
    
    async def update_prices(self, symbols: Optional[List[str]] = None):
        """
        Обновить цены из CoinGecko
        
        Args:
            symbols: список символов для обновления (None = все)
        """
        try:
            # Если символы не указаны, обновляем все популярные
            if symbols is None:
                symbols = list(self.coingecko_map.keys())
            
            # Конвертируем символы в CoinGecko IDs
            ids = []
            symbol_to_id = {}
            for symbol in symbols:
                symbol = symbol.upper()
                cg_id = self.coingecko_map.get(symbol)
                if cg_id:
                    ids.append(cg_id)
                    symbol_to_id[symbol] = cg_id
            
            if not ids:
                return
            
            # Получаем цены с CoinGecko
            ids_str = ",".join(ids)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Обновляем кэш
                        for symbol, cg_id in symbol_to_id.items():
                            if cg_id in data:
                                self.cache[symbol] = {
                                    "price": data[cg_id].get("usd", 0),
                                    "change_24h": data[cg_id].get("usd_24h_change", 0),
                                    "market_cap": data[cg_id].get("usd_market_cap", 0),
                                    "timestamp": time.time()
                                }
                        
                        self.last_update = time.time()
                    else:
                        print(f"⚠️ CoinGecko API вернул статус {resp.status}")
        
        except Exception as e:
            print(f"❌ Ошибка обновления цен: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Проверить валидность кэша"""
        return (time.time() - self.last_update) < self.cache_ttl
    
    def get_price_info(self, symbol: str) -> Dict[str, Any]:
        """
        Получить полную информацию о цене
        
        Returns:
            {price, change_24h, market_cap, timestamp}
        """
        symbol = symbol.upper()
        return self.cache.get(symbol, {
            "price": 0,
            "change_24h": 0,
            "market_cap": 0,
            "timestamp": 0
        })
    
    def calculate_value(self, amount: float, symbol: str) -> float:
        """
        Рассчитать стоимость в USD
        
        Args:
            amount: количество монет
            symbol: символ монеты
            
        Returns:
            стоимость в USD
        """
        symbol = symbol.upper()
        price = self.cache.get(symbol, {}).get("price", 0)
        return amount * price
    
    def format_price_change(self, symbol: str) -> str:
        """
        Форматировать изменение цены за 24ч
        
        Returns:
            строка вида "+5.2%" или "-3.1%"
        """
        symbol = symbol.upper()
        change = self.cache.get(symbol, {}).get("change_24h", 0)
        
        if change > 0:
            return f"+{change:.1f}%"
        elif change < 0:
            return f"{change:.1f}%"
        else:
            return "0.0%"
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        return {
            "cached_symbols": len(self.cache),
            "last_update": self.last_update,
            "cache_age_seconds": time.time() - self.last_update,
            "is_valid": self._is_cache_valid(),
            "ttl": self.cache_ttl
        }
    
    def clear_cache(self):
        """Очистить кэш"""
        self.cache.clear()
        self.last_update = 0
    
    async def get_token_price_by_address(self, address: str, chain: str = "ethereum") -> float:
        """
        Получить цену токена по адресу контракта
        
        Args:
            address: адрес контракта токена
            chain: сеть (ethereum, bsc, polygon)
            
        Returns:
            цена в USD
        """
        try:
            # Маппинг сетей на CoinGecko platform IDs
            platform_map = {
                "ethereum": "ethereum",
                "bsc": "binance-smart-chain",
                "polygon": "polygon-pos",
                "avalanche": "avalanche",
                "arbitrum": "arbitrum-one",
                "optimism": "optimistic-ethereum",
                "base": "base",
            }
            
            platform = platform_map.get(chain.lower(), "ethereum")
            url = f"https://api.coingecko.com/api/v3/simple/token_price/{platform}?contract_addresses={address}&vs_currencies=usd"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        address_lower = address.lower()
                        if address_lower in data:
                            return data[address_lower].get("usd", 0)
        
        except Exception as e:
            print(f"❌ Ошибка получения цены токена: {e}")
        
        return 0
    
    async def get_historical_price(self, symbol: str, days_ago: int = 1) -> float:
        """
        Получить историческую цену
        
        Args:
            symbol: символ монеты
            days_ago: сколько дней назад
            
        Returns:
            цена в USD
        """
        try:
            symbol = symbol.upper()
            cg_id = self.coingecko_map.get(symbol)
            if not cg_id:
                return 0
            
            # CoinGecko API для исторических данных
            url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days={days_ago}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        prices = data.get("prices", [])
                        if prices:
                            # Берем первую цену (самую старую в диапазоне)
                            return prices[0][1]
        
        except Exception as e:
            print(f"❌ Ошибка получения исторической цены: {e}")
        
        return 0


# Глобальный экземпляр сервиса
global_price_service = PriceService()


# Вспомогательные функции для быстрого доступа
async def get_price(symbol: str) -> float:
    """Быстрый доступ к получению цены"""
    return await global_price_service.get_price(symbol)


async def get_prices(symbols: List[str]) -> Dict[str, float]:
    """Быстрый доступ к получению нескольких цен"""
    return await global_price_service.get_prices(symbols)


async def calculate_usd(amount: float, symbol: str) -> float:
    """Быстрый расчет стоимости в USD"""
    price = await get_price(symbol)
    return amount * price


def format_usd(amount: float, symbol: str = "") -> str:
    """
    Форматировать сумму в USD
    
    Args:
        amount: сумма в USD
        symbol: опциональный символ монеты для отображения изменения
        
    Returns:
        отформатированная строка
    """
    formatted = f"${amount:,.2f}"
    
    if symbol:
        change = global_price_service.format_price_change(symbol)
        if change != "0.0%":
            formatted += f" ({change})"
    
    return formatted
