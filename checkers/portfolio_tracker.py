# -*- coding: utf-8 -*-
"""
Portfolio Tracker - Отслеживание портфеля в реальном времени
Мониторинг балансов, изменений цен, P&L
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class PortfolioAsset:
    """Актив в портфеле"""
    
    def __init__(self, address: str, chain: str, balance: float, 
                 symbol: str, price_usd: float = 0):
        self.address = address
        self.chain = chain
        self.balance = balance
        self.symbol = symbol
        self.price_usd = price_usd
        self.value_usd = balance * price_usd
        self.initial_price = price_usd
        self.initial_value = self.value_usd
        self.last_updated = time.time()
        self.price_history = [(time.time(), price_usd)]
    
    def update_price(self, new_price: float):
        """Обновить цену актива"""
        self.price_usd = new_price
        self.value_usd = self.balance * new_price
        self.last_updated = time.time()
        self.price_history.append((time.time(), new_price))
        
        # Храним только последние 100 записей
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
    
    def get_pnl(self) -> Dict[str, float]:
        """Получить P&L (прибыль/убыток)"""
        pnl_usd = self.value_usd - self.initial_value
        pnl_percent = ((self.value_usd / self.initial_value) - 1) * 100 if self.initial_value > 0 else 0
        
        return {
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "current_value": self.value_usd,
            "initial_value": self.initial_value
        }
    
    def to_dict(self) -> dict:
        """Конвертировать в словарь"""
        return {
            "address": self.address,
            "chain": self.chain,
            "balance": self.balance,
            "symbol": self.symbol,
            "price_usd": self.price_usd,
            "value_usd": self.value_usd,
            "pnl": self.get_pnl(),
            "last_updated": self.last_updated
        }


class Portfolio:
    """Портфель активов"""
    
    def __init__(self, name: str = "Main Portfolio"):
        self.name = name
        self.assets: List[PortfolioAsset] = []
        self.created_at = time.time()
        self.last_updated = time.time()
    
    def add_asset(self, asset: PortfolioAsset):
        """Добавить актив в портфель"""
        # Проверяем, нет ли уже такого актива
        existing = self.find_asset(asset.address, asset.chain, asset.symbol)
        if existing:
            # Обновляем существующий
            existing.balance += asset.balance
            existing.update_price(asset.price_usd)
        else:
            # Добавляем новый
            self.assets.append(asset)
        
        self.last_updated = time.time()
    
    def find_asset(self, address: str, chain: str, symbol: str) -> Optional[PortfolioAsset]:
        """Найти актив в портфеле"""
        for asset in self.assets:
            if asset.address == address and asset.chain == chain and asset.symbol == symbol:
                return asset
        return None
    
    def remove_asset(self, address: str, chain: str, symbol: str):
        """Удалить актив из портфеля"""
        self.assets = [
            a for a in self.assets 
            if not (a.address == address and a.chain == chain and a.symbol == symbol)
        ]
        self.last_updated = time.time()
    
    def get_total_value(self) -> float:
        """Получить общую стоимость портфеля"""
        return sum(asset.value_usd for asset in self.assets)
    
    def get_total_pnl(self) -> Dict[str, float]:
        """Получить общий P&L портфеля"""
        total_current = sum(asset.value_usd for asset in self.assets)
        total_initial = sum(asset.initial_value for asset in self.assets)
        
        pnl_usd = total_current - total_initial
        pnl_percent = ((total_current / total_initial) - 1) * 100 if total_initial > 0 else 0
        
        return {
            "pnl_usd": pnl_usd,
            "pnl_percent": pnl_percent,
            "current_value": total_current,
            "initial_value": total_initial
        }
    
    def get_allocation(self) -> Dict[str, float]:
        """Получить распределение активов по сетям"""
        total_value = self.get_total_value()
        if total_value == 0:
            return {}
        
        allocation = {}
        for asset in self.assets:
            chain = asset.chain
            if chain not in allocation:
                allocation[chain] = 0
            allocation[chain] += asset.value_usd
        
        # Конвертируем в проценты
        return {
            chain: (value / total_value) * 100
            for chain, value in allocation.items()
        }
    
    def get_top_assets(self, limit: int = 10) -> List[PortfolioAsset]:
        """Получить топ активов по стоимости"""
        return sorted(self.assets, key=lambda a: a.value_usd, reverse=True)[:limit]
    
    def to_dict(self) -> dict:
        """Конвертировать в словарь"""
        return {
            "name": self.name,
            "total_value": self.get_total_value(),
            "total_pnl": self.get_total_pnl(),
            "allocation": self.get_allocation(),
            "assets_count": len(self.assets),
            "assets": [asset.to_dict() for asset in self.assets],
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }


class PortfolioTracker:
    """Трекер портфелей"""
    
    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.price_cache: Dict[str, float] = {}
        self.price_cache_ttl = 60  # 1 минута
        self.last_price_update = 0
        self.auto_update_enabled = False
        self.update_interval = 300  # 5 минут
        self._update_task = None
    
    def create_portfolio(self, name: str) -> Portfolio:
        """Создать новый портфель"""
        portfolio = Portfolio(name)
        self.portfolios[name] = portfolio
        return portfolio
    
    def get_portfolio(self, name: str) -> Optional[Portfolio]:
        """Получить портфель по имени"""
        return self.portfolios.get(name)
    
    def delete_portfolio(self, name: str):
        """Удалить портфель"""
        if name in self.portfolios:
            del self.portfolios[name]
    
    def add_from_result(self, result: dict, portfolio_name: str = "Main Portfolio"):
        """Добавить активы из результата проверки в портфель"""
        # Получаем или создаем портфель
        portfolio = self.get_portfolio(portfolio_name)
        if not portfolio:
            portfolio = self.create_portfolio(portfolio_name)
        
        # Извлекаем данные из результата
        address = result.get("input", "")
        chain = result.get("wallet_type", result.get("type", "unknown"))
        info = result.get("info", {})
        
        # Основной баланс
        balance = info.get("balance", 0)
        if balance > 0:
            symbol = self._get_chain_symbol(chain)
            price = self.price_cache.get(chain, 0)
            
            asset = PortfolioAsset(
                address=address,
                chain=chain,
                balance=balance,
                symbol=symbol,
                price_usd=price
            )
            portfolio.add_asset(asset)
        
        # Токены
        tokens = info.get("tokens", [])
        for token in tokens:
            if isinstance(token, dict):
                token_balance = token.get("balance", 0)
                token_symbol = token.get("symbol", "")
                token_price = token.get("price_usd", 0)
                
                if token_balance > 0:
                    asset = PortfolioAsset(
                        address=address,
                        chain=chain,
                        balance=token_balance,
                        symbol=token_symbol,
                        price_usd=token_price
                    )
                    portfolio.add_asset(asset)
    
    def _get_chain_symbol(self, chain: str) -> str:
        """Получить символ монеты для сети"""
        symbols = {
            "ethereum": "ETH",
            "bitcoin": "BTC",
            "bsc": "BNB",
            "polygon": "MATIC",
            "solana": "SOL",
            "tron": "TRX",
            "avalanche": "AVAX",
            "arbitrum": "ETH",
            "optimism": "ETH",
            "base": "ETH",
        }
        return symbols.get(chain, chain.upper())
    
    async def update_prices(self):
        """Обновить цены всех активов"""
        try:
            # Собираем уникальные символы
            symbols_to_update = set()
            for portfolio in self.portfolios.values():
                for asset in portfolio.assets:
                    symbols_to_update.add(asset.chain)
            
            if not symbols_to_update:
                return
            
            # Получаем цены с CoinGecko
            prices = await self._fetch_prices(list(symbols_to_update))
            
            # Обновляем кэш
            self.price_cache.update(prices)
            self.last_price_update = time.time()
            
            # Обновляем цены в активах
            for portfolio in self.portfolios.values():
                for asset in portfolio.assets:
                    if asset.chain in prices:
                        asset.update_price(prices[asset.chain])
        
        except Exception as e:
            print(f"❌ Ошибка обновления цен: {e}")
    
    async def _fetch_prices(self, chains: List[str]) -> Dict[str, float]:
        """Получить цены с CoinGecko"""
        # Маппинг сетей на CoinGecko IDs
        coingecko_ids = {
            "ethereum": "ethereum",
            "bitcoin": "bitcoin",
            "bsc": "binancecoin",
            "polygon": "matic-network",
            "solana": "solana",
            "tron": "tron",
            "avalanche": "avalanche-2",
            "arbitrum": "ethereum",
            "optimism": "ethereum",
            "base": "ethereum",
        }
        
        # Собираем уникальные IDs
        ids = list(set(coingecko_ids.get(chain, chain) for chain in chains))
        ids_str = ",".join(ids)
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Конвертируем обратно в наши символы
                        prices = {}
                        for chain in chains:
                            cg_id = coingecko_ids.get(chain, chain)
                            if cg_id in data:
                                prices[chain] = data[cg_id].get("usd", 0)
                        
                        return prices
        except Exception as e:
            print(f"❌ Ошибка получения цен: {e}")
        
        return {}
    
    def start_auto_update(self):
        """Запустить автоматическое обновление цен"""
        if self._update_task is None or self._update_task.done():
            self.auto_update_enabled = True
            self._update_task = asyncio.create_task(self._auto_update_loop())
    
    def stop_auto_update(self):
        """Остановить автоматическое обновление"""
        self.auto_update_enabled = False
        if self._update_task:
            self._update_task.cancel()
    
    async def _auto_update_loop(self):
        """Цикл автоматического обновления"""
        while self.auto_update_enabled:
            try:
                await self.update_prices()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Ошибка в auto-update: {e}")
                await asyncio.sleep(60)
    
    def get_summary(self) -> Dict[str, Any]:
        """Получить общую сводку по всем портфелям"""
        total_value = sum(p.get_total_value() for p in self.portfolios.values())
        total_assets = sum(len(p.assets) for p in self.portfolios.values())
        
        # Общий P&L
        total_current = sum(p.get_total_value() for p in self.portfolios.values())
        total_initial = sum(
            sum(a.initial_value for a in p.assets)
            for p in self.portfolios.values()
        )
        
        total_pnl_usd = total_current - total_initial
        total_pnl_percent = ((total_current / total_initial) - 1) * 100 if total_initial > 0 else 0
        
        return {
            "portfolios_count": len(self.portfolios),
            "total_value": total_value,
            "total_assets": total_assets,
            "total_pnl": {
                "pnl_usd": total_pnl_usd,
                "pnl_percent": total_pnl_percent,
                "current_value": total_current,
                "initial_value": total_initial
            },
            "portfolios": {
                name: portfolio.to_dict()
                for name, portfolio in self.portfolios.items()
            }
        }
    
    def export_to_json(self, filepath: str):
        """Экспортировать все портфели в JSON"""
        try:
            data = self.get_summary()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✓ Портфели экспортированы: {filepath}")
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
    
    def import_from_json(self, filepath: str):
        """Импортировать портфели из JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            portfolios_data = data.get("portfolios", {})
            for name, portfolio_data in portfolios_data.items():
                portfolio = self.create_portfolio(name)
                
                for asset_data in portfolio_data.get("assets", []):
                    asset = PortfolioAsset(
                        address=asset_data["address"],
                        chain=asset_data["chain"],
                        balance=asset_data["balance"],
                        symbol=asset_data["symbol"],
                        price_usd=asset_data["price_usd"]
                    )
                    portfolio.add_asset(asset)
            
            print(f"✓ Портфели импортированы: {filepath}")
        except Exception as e:
            print(f"❌ Ошибка импорта: {e}")


# Глобальный экземпляр трекера
global_portfolio_tracker = PortfolioTracker()
