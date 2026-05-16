# -*- coding: utf-8 -*-
"""
Cross-Chain Bridge Finder v1.0.65
Поиск токенов на других сетях
"""

import aiohttp
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class CrossChainChecker:
    """Проверка адреса на всех сетях одновременно"""
    
    # Все поддерживаемые EVM сети
    EVM_CHAINS = {
        "ethereum": {
            "name": "Ethereum",
            "rpc": "https://cloudflare-eth.com",
            "explorer": "https://etherscan.io",
            "native": "ETH",
            "chain_id": 1,
        },
        "bsc": {
            "name": "BNB Smart Chain",
            "rpc": "https://bsc-dataseed.binance.org",
            "explorer": "https://bscscan.com",
            "native": "BNB",
            "chain_id": 56,
        },
        "polygon": {
            "name": "Polygon",
            "rpc": "https://polygon-rpc.com",
            "explorer": "https://polygonscan.com",
            "native": "MATIC",
            "chain_id": 137,
        },
        "avalanche": {
            "name": "Avalanche C-Chain",
            "rpc": "https://api.avax.network/ext/bc/C/rpc",
            "explorer": "https://snowtrace.io",
            "native": "AVAX",
            "chain_id": 43114,
        },
        "arbitrum": {
            "name": "Arbitrum One",
            "rpc": "https://arb1.arbitrum.io/rpc",
            "explorer": "https://arbiscan.io",
            "native": "ETH",
            "chain_id": 42161,
        },
        "optimism": {
            "name": "Optimism",
            "rpc": "https://mainnet.optimism.io",
            "explorer": "https://optimistic.etherscan.io",
            "native": "ETH",
            "chain_id": 10,
        },
        "base": {
            "name": "Base",
            "rpc": "https://mainnet.base.org",
            "explorer": "https://basescan.org",
            "native": "ETH",
            "chain_id": 8453,
        },
        "fantom": {
            "name": "Fantom",
            "rpc": "https://rpc.ftm.tools",
            "explorer": "https://ftmscan.com",
            "native": "FTM",
            "chain_id": 250,
        },
        "cronos": {
            "name": "Cronos",
            "rpc": "https://evm.cronos.org",
            "explorer": "https://cronoscan.com",
            "native": "CRO",
            "chain_id": 25,
        },
        "zksync": {
            "name": "zkSync Era",
            "rpc": "https://mainnet.era.zksync.io",
            "explorer": "https://explorer.zksync.io",
            "native": "ETH",
            "chain_id": 324,
        },
        "linea": {
            "name": "Linea",
            "rpc": "https://rpc.linea.build",
            "explorer": "https://lineascan.build",
            "native": "ETH",
            "chain_id": 59144,
        },
        "scroll": {
            "name": "Scroll",
            "rpc": "https://rpc.scroll.io",
            "explorer": "https://scrollscan.com",
            "native": "ETH",
            "chain_id": 534352,
        },
        "mantle": {
            "name": "Mantle",
            "rpc": "https://rpc.mantle.xyz",
            "explorer": "https://explorer.mantle.xyz",
            "native": "MNT",
            "chain_id": 5000,
        },
        "celo": {
            "name": "Celo",
            "rpc": "https://forno.celo.org",
            "explorer": "https://celoscan.io",
            "native": "CELO",
            "chain_id": 42220,
        },
        "gnosis": {
            "name": "Gnosis Chain",
            "rpc": "https://rpc.gnosischain.com",
            "explorer": "https://gnosisscan.io",
            "native": "xDAI",
            "chain_id": 100,
        },
    }
    
    # Популярные bridges
    BRIDGES = {
        "ethereum_to_bsc": {
            "name": "Binance Bridge",
            "fee": 0.001,
            "time": "5-10 min",
        },
        "ethereum_to_polygon": {
            "name": "Polygon Bridge",
            "fee": 0.0005,
            "time": "7-8 min",
        },
        "ethereum_to_arbitrum": {
            "name": "Arbitrum Bridge",
            "fee": 0.0003,
            "time": "10-15 min",
        },
        "ethereum_to_optimism": {
            "name": "Optimism Bridge",
            "fee": 0.0003,
            "time": "10-15 min",
        },
    }
    
    def __init__(self):
        self.price_cache = {}
    
    async def check_all_chains(
        self,
        address: str,
        session: Optional[aiohttp.ClientSession] = None
    ) -> Dict[str, Any]:
        """
        Проверить адрес на всех сетях одновременно
        
        Args:
            address: EVM адрес (0x...)
            session: aiohttp сессия
        
        Returns:
            Словарь с балансами на всех сетях
        """
        
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            result = {
                "address": address,
                "chains": {},
                "total_usd": 0.0,
                "chains_with_balance": 0,
                "best_chain": None,
                "best_balance": 0.0,
            }
            
            # Проверяем все сети параллельно
            tasks = []
            for chain_id, chain_info in self.EVM_CHAINS.items():
                task = self._check_chain_balance(address, chain_id, chain_info, session)
                tasks.append((chain_id, task))
            
            # Ждем все результаты
            for chain_id, task in tasks:
                try:
                    chain_result = await task
                    result["chains"][chain_id] = chain_result
                    
                    balance_usd = chain_result.get("balance_usd", 0)
                    if balance_usd > 0:
                        result["chains_with_balance"] += 1
                        result["total_usd"] += balance_usd
                        
                        # Обновляем лучшую сеть
                        if balance_usd > result["best_balance"]:
                            result["best_balance"] = balance_usd
                            result["best_chain"] = chain_id
                
                except Exception as e:
                    result["chains"][chain_id] = {"error": str(e)}
            
            return result
        
        finally:
            if own_session:
                await session.close()
    
    async def _check_chain_balance(
        self,
        address: str,
        chain_id: str,
        chain_info: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Проверить баланс на одной сети"""
        
        result = {
            "chain": chain_info["name"],
            "native_token": chain_info["native"],
            "balance": 0.0,
            "balance_usd": 0.0,
            "tokens": [],
            "total_tokens_usd": 0.0,
        }
        
        try:
            # Получаем нативный баланс
            rpc_url = chain_info["rpc"]
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": 1
            }
            
            async with session.post(rpc_url, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balance_hex = data.get("result", "0x0")
                    balance_wei = int(balance_hex, 16)
                    balance_eth = balance_wei / 1e18
                    
                    result["balance"] = balance_eth
                    
                    # Конвертируем в USD
                    price = await self._get_token_price(chain_info["native"])
                    result["balance_usd"] = balance_eth * price
            
            # TODO: Проверка ERC-20 токенов (требует больше запросов)
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _get_token_price(self, symbol: str) -> float:
        """Получить цену токена"""
        
        # Кэш
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if (datetime.now().timestamp() - timestamp) < 300:  # 5 минут
                return price
        
        # Примерные цены (в реальности нужен CoinGecko API)
        prices = {
            "ETH": 2500,
            "BNB": 300,
            "MATIC": 0.8,
            "AVAX": 35,
            "FTM": 0.5,
            "CRO": 0.1,
            "MNT": 0.5,
            "CELO": 0.6,
            "xDAI": 1.0,
        }
        
        price = prices.get(symbol, 0)
        self.price_cache[symbol] = (price, datetime.now().timestamp())
        
        return price
    
    def find_best_bridge(
        self,
        from_chain: str,
        to_chain: str
    ) -> Optional[Dict[str, Any]]:
        """Найти лучший bridge для перевода"""
        
        bridge_key = f"{from_chain}_to_{to_chain}"
        
        if bridge_key in self.BRIDGES:
            return self.BRIDGES[bridge_key]
        
        # Обратный bridge
        reverse_key = f"{to_chain}_to_{from_chain}"
        if reverse_key in self.BRIDGES:
            return self.BRIDGES[reverse_key]
        
        return None
    
    def format_crosschain_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о балансах на всех сетях"""
        
        lines = []
        
        lines.append("=" * 70)
        lines.append("CROSS-CHAIN BALANCE REPORT")
        lines.append("=" * 70)
        
        lines.append(f"\nAddress: {result['address']}")
        lines.append(f"Total Balance: ${result['total_usd']:,.2f}")
        lines.append(f"Chains with Balance: {result['chains_with_balance']}/{len(result['chains'])}")
        
        if result['best_chain']:
            lines.append(f"Best Chain: {result['best_chain'].upper()} (${result['best_balance']:,.2f})")
        
        # Балансы по сетям
        lines.append(f"\n{'=' * 70}")
        lines.append("BALANCES BY CHAIN:")
        lines.append("=" * 70)
        
        # Сортируем по балансу
        sorted_chains = sorted(
            result['chains'].items(),
            key=lambda x: x[1].get('balance_usd', 0),
            reverse=True
        )
        
        for chain_id, chain_data in sorted_chains:
            if chain_data.get('error'):
                continue
            
            balance_usd = chain_data.get('balance_usd', 0)
            
            if balance_usd > 0:
                chain_name = chain_data.get('chain', chain_id.upper())
                balance = chain_data.get('balance', 0)
                native = chain_data.get('native_token', '')
                
                lines.append(f"\n{chain_name}:")
                lines.append(f"  Balance: {balance:.6f} {native}")
                lines.append(f"  USD Value: ${balance_usd:,.2f}")
                
                # Токены
                tokens = chain_data.get('tokens', [])
                if tokens:
                    lines.append(f"  Tokens: {len(tokens)}")
        
        return "\n".join(lines)
    
    def suggest_consolidation(self, result: Dict[str, Any]) -> List[str]:
        """Предложить план консолидации балансов"""
        
        suggestions = []
        
        # Находим сети с балансом
        chains_with_balance = []
        for chain_id, chain_data in result['chains'].items():
            balance_usd = chain_data.get('balance_usd', 0)
            if balance_usd > 0:
                chains_with_balance.append((chain_id, balance_usd, chain_data))
        
        if len(chains_with_balance) <= 1:
            return ["Баланс только на одной сети, консолидация не требуется"]
        
        # Сортируем по балансу
        chains_with_balance.sort(key=lambda x: x[1], reverse=True)
        
        best_chain = chains_with_balance[0][0]
        best_balance = chains_with_balance[0][1]
        
        suggestions.append(f"Рекомендуется консолидировать все средства на {best_chain.upper()}")
        suggestions.append(f"Текущий баланс на {best_chain.upper()}: ${best_balance:,.2f}")
        suggestions.append("")
        suggestions.append("План действий:")
        
        for i, (chain_id, balance_usd, chain_data) in enumerate(chains_with_balance[1:], 1):
            if chain_id == best_chain:
                continue
            
            bridge = self.find_best_bridge(chain_id, best_chain)
            
            if bridge:
                suggestions.append(f"{i}. {chain_id.upper()} → {best_chain.upper()}")
                suggestions.append(f"   Сумма: ${balance_usd:,.2f}")
                suggestions.append(f"   Bridge: {bridge['name']}")
                suggestions.append(f"   Комиссия: ~{bridge['fee']} ETH")
                suggestions.append(f"   Время: {bridge['time']}")
            else:
                suggestions.append(f"{i}. {chain_id.upper()} → {best_chain.upper()}")
                suggestions.append(f"   Сумма: ${balance_usd:,.2f}")
                suggestions.append(f"   Bridge: Используйте Stargate или LayerZero")
        
        return suggestions
