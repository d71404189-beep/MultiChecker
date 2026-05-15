# -*- coding: utf-8 -*-
"""
Multichain Checker v1.0.54
Одновременная проверка балансов во всех EVM сетях + оптимизация
"""

import asyncio
import aiohttp
from typing import Dict, List, Tuple, Any
import time

# ═══════════════════════════════════════════════════════════════════════════
#  EVM CHAINS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

EVM_CHAINS = [
    {
        "name": "ethereum",
        "rpc": "https://cloudflare-eth.com",
        "symbol": "ETH",
        "chain_id": 1,
        "explorer": "https://etherscan.io",
        "gas_multiplier": 1.0,
    },
    {
        "name": "bsc",
        "rpc": "https://bsc-dataseed.binance.org/",
        "symbol": "BNB",
        "chain_id": 56,
        "explorer": "https://bscscan.com",
        "gas_multiplier": 0.05,  # BSC дешевле
    },
    {
        "name": "polygon",
        "rpc": "https://polygon-rpc.com",
        "symbol": "MATIC",
        "chain_id": 137,
        "explorer": "https://polygonscan.com",
        "gas_multiplier": 0.01,  # Polygon очень дешевый
    },
    {
        "name": "avalanche",
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "symbol": "AVAX",
        "chain_id": 43114,
        "explorer": "https://snowtrace.io",
        "gas_multiplier": 0.3,
    },
    {
        "name": "base",
        "rpc": "https://mainnet.base.org",
        "symbol": "ETH",
        "chain_id": 8453,
        "explorer": "https://basescan.org",
        "gas_multiplier": 0.1,  # L2 дешевле
    },
    {
        "name": "arbitrum",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "symbol": "ETH",
        "chain_id": 42161,
        "explorer": "https://arbiscan.io",
        "gas_multiplier": 0.1,
    },
    {
        "name": "optimism",
        "rpc": "https://mainnet.optimism.io",
        "symbol": "ETH",
        "chain_id": 10,
        "explorer": "https://optimistic.etherscan.io",
        "gas_multiplier": 0.1,
    },
    {
        "name": "fantom",
        "rpc": "https://rpc.ftm.tools",
        "symbol": "FTM",
        "chain_id": 250,
        "explorer": "https://ftmscan.com",
        "gas_multiplier": 0.02,
    },
    {
        "name": "cronos",
        "rpc": "https://evm.cronos.org",
        "symbol": "CRO",
        "chain_id": 25,
        "explorer": "https://cronoscan.com",
        "gas_multiplier": 0.05,
    },
    {
        "name": "zksync",
        "rpc": "https://mainnet.era.zksync.io",
        "symbol": "ETH",
        "chain_id": 324,
        "explorer": "https://explorer.zksync.io",
        "gas_multiplier": 0.05,
    },
    {
        "name": "linea",
        "rpc": "https://rpc.linea.build",
        "symbol": "ETH",
        "chain_id": 59144,
        "explorer": "https://lineascan.build",
        "gas_multiplier": 0.08,
    },
    {
        "name": "scroll",
        "rpc": "https://rpc.scroll.io",
        "symbol": "ETH",
        "chain_id": 534352,
        "explorer": "https://scrollscan.com",
        "gas_multiplier": 0.08,
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  MULTICHAIN BALANCE CHECKER
# ═══════════════════════════════════════════════════════════════════════════

async def check_multichain_balance(
    address: str,
    session: aiohttp.ClientSession,
    timeout: int = 10,
    proxy: str = None
) -> Dict[str, Any]:
    """
    Проверить баланс адреса во всех EVM сетях одновременно
    
    Args:
        address: EVM адрес (0x...)
        session: aiohttp сессия
        timeout: таймаут запроса
        proxy: прокси (опционально)
    
    Returns:
        Dict: {
            "total_usd": 5000.0,
            "chains": {
                "ethereum": {"balance": 1.5, "usd": 3000, "gas_cost": 0.002},
                "bsc": {"balance": 10, "usd": 2000, "gas_cost": 0.0001},
                ...
            },
            "best_chain": "ethereum",  # Самая выгодная для вывода
            "recommendations": ["Выводить с Ethereum", "Bridge с BSC через Stargate"]
        }
    """
    
    # Проверяем все сети параллельно
    tasks = []
    for chain in EVM_CHAINS:
        task = _check_chain_balance(address, chain, session, timeout, proxy)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Обрабатываем результаты
    chains_data = {}
    total_usd = 0.0
    
    for chain, result in zip(EVM_CHAINS, results):
        if isinstance(result, Exception):
            chains_data[chain["name"]] = {
                "balance": 0,
                "usd": 0,
                "error": str(result),
                "gas_cost": 0
            }
            continue
        
        chains_data[chain["name"]] = result
        total_usd += result.get("usd", 0)
    
    # Определяем лучшую сеть для вывода
    best_chain = _find_best_chain_for_withdrawal(chains_data)
    
    # Генерируем рекомендации
    recommendations = _generate_recommendations(chains_data, best_chain)
    
    return {
        "total_usd": total_usd,
        "chains": chains_data,
        "best_chain": best_chain,
        "recommendations": recommendations,
        "timestamp": time.time()
    }


async def _check_chain_balance(
    address: str,
    chain: Dict,
    session: aiohttp.ClientSession,
    timeout: int,
    proxy: str
) -> Dict[str, Any]:
    """
    Проверить баланс в одной сети
    """
    try:
        # JSON-RPC запрос баланса
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }
        
        async with session.post(
            chain["rpc"],
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
            proxy=proxy
        ) as resp:
            if resp.status != 200:
                return {"balance": 0, "usd": 0, "error": f"HTTP {resp.status}", "gas_cost": 0}
            
            data = await resp.json()
            balance_wei = int(data.get("result", "0x0"), 16)
            balance = balance_wei / 1e18
            
            # Получаем цену токена
            price = await _get_token_price(chain["symbol"], session, timeout)
            usd_value = balance * price
            
            # Оцениваем стоимость газа для вывода
            gas_cost = await _estimate_gas_cost(chain, session, timeout)
            
            return {
                "balance": balance,
                "usd": usd_value,
                "price": price,
                "gas_cost": gas_cost,
                "gas_cost_usd": gas_cost * price,
                "net_usd": usd_value - (gas_cost * price),  # После вычета газа
                "chain_id": chain["chain_id"],
                "explorer": chain["explorer"]
            }
    
    except Exception as e:
        return {"balance": 0, "usd": 0, "error": str(e), "gas_cost": 0}


async def _get_token_price(symbol: str, session: aiohttp.ClientSession, timeout: int) -> float:
    """
    Получить цену токена через CoinGecko
    """
    symbol_map = {
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "MATIC": "matic-network",
        "AVAX": "avalanche-2",
        "FTM": "fantom",
        "CRO": "crypto-com-chain",
    }
    
    coin_id = symbol_map.get(symbol, symbol.lower())
    
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get(coin_id, {}).get("usd", 0)
    except:
        pass
    
    return 0


async def _estimate_gas_cost(chain: Dict, session: aiohttp.ClientSession, timeout: int) -> float:
    """
    Оценить стоимость газа для простого перевода
    """
    try:
        # Получаем текущую цену газа
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": [],
            "id": 1
        }
        
        async with session.post(
            chain["rpc"],
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                gas_price_wei = int(data.get("result", "0x0"), 16)
                
                # Простой перевод = 21000 gas
                gas_limit = 21000
                total_gas_wei = gas_price_wei * gas_limit
                total_gas_eth = total_gas_wei / 1e18
                
                # Применяем множитель сети
                return total_gas_eth * chain["gas_multiplier"]
    except:
        pass
    
    # Fallback значения
    return 0.001 * chain["gas_multiplier"]


def _find_best_chain_for_withdrawal(chains_data: Dict) -> str:
    """
    Найти лучшую сеть для вывода (максимальный net_usd)
    """
    best_chain = None
    best_net_usd = 0
    
    for chain_name, data in chains_data.items():
        net_usd = data.get("net_usd", 0)
        if net_usd > best_net_usd:
            best_net_usd = net_usd
            best_chain = chain_name
    
    return best_chain or "ethereum"


def _generate_recommendations(chains_data: Dict, best_chain: str) -> List[str]:
    """
    Генерировать рекомендации по выводу
    """
    recommendations = []
    
    # Рекомендация по лучшей сети
    best_data = chains_data.get(best_chain, {})
    if best_data.get("net_usd", 0) > 0:
        recommendations.append(
            f"✅ Выводить с {best_chain.upper()}: ${best_data['net_usd']:.2f} после газа"
        )
    
    # Рекомендации по bridge
    for chain_name, data in chains_data.items():
        if chain_name == best_chain:
            continue
        
        usd = data.get("usd", 0)
        if usd > 10:  # Если больше $10
            gas_cost_usd = data.get("gas_cost_usd", 0)
            if gas_cost_usd > usd * 0.1:  # Если газ > 10% от баланса
                recommendations.append(
                    f"⚠️ {chain_name.upper()}: Bridge на {best_chain.upper()} (газ ${gas_cost_usd:.2f})"
                )
    
    # Рекомендация по L2
    l2_chains = ["base", "arbitrum", "optimism", "zksync", "linea", "scroll"]
    l2_total = sum(chains_data.get(c, {}).get("usd", 0) for c in l2_chains)
    
    if l2_total > 50:
        recommendations.append(
            f"💡 L2 балансы: ${l2_total:.2f} - рассмотрите bridge на L1"
        )
    
    return recommendations


# ═══════════════════════════════════════════════════════════════════════════
#  GAS OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

async def get_optimal_gas_price(
    chain: Dict,
    session: aiohttp.ClientSession,
    timeout: int = 10,
    speed: str = "fast"
) -> Dict[str, int]:
    """
    Получить оптимальную цену газа (EIP-1559)
    
    Args:
        chain: Конфигурация сети
        session: aiohttp сессия
        timeout: таймаут
        speed: "slow" | "standard" | "fast" | "instant"
    
    Returns:
        Dict: {
            "maxFeePerGas": 30000000000,  # wei
            "maxPriorityFeePerGas": 2000000000,  # wei
            "gasPrice": 28000000000  # для legacy транзакций
        }
    """
    
    try:
        # Пробуем получить через eth_feeHistory (EIP-1559)
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_feeHistory",
            "params": [4, "latest", [25, 50, 75]],  # Последние 4 блока, перцентили
            "id": 1
        }
        
        async with session.post(
            chain["rpc"],
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                result = data.get("result", {})
                
                # Получаем базовую комиссию последнего блока
                base_fee_per_gas = int(result.get("baseFeePerGas", ["0x0"])[-1], 16)
                
                # Получаем priority fee из перцентилей
                rewards = result.get("reward", [])
                if rewards:
                    # Выбираем перцентиль в зависимости от скорости
                    speed_map = {"slow": 0, "standard": 1, "fast": 2, "instant": 2}
                    percentile_idx = speed_map.get(speed, 1)
                    
                    priority_fees = [int(r[percentile_idx], 16) for r in rewards if len(r) > percentile_idx]
                    avg_priority_fee = sum(priority_fees) // len(priority_fees) if priority_fees else 2_000_000_000
                else:
                    avg_priority_fee = 2_000_000_000  # 2 gwei default
                
                # Множители для разных скоростей
                speed_multipliers = {
                    "slow": 0.9,
                    "standard": 1.0,
                    "fast": 1.2,
                    "instant": 1.5
                }
                multiplier = speed_multipliers.get(speed, 1.0)
                
                max_priority_fee = int(avg_priority_fee * multiplier)
                max_fee = int((base_fee_per_gas * 2) + max_priority_fee)  # 2x base + priority
                
                return {
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority_fee,
                    "gasPrice": max_fee,  # для legacy
                    "baseFeePerGas": base_fee_per_gas
                }
    
    except Exception as e:
        print(f"Ошибка получения EIP-1559 gas: {e}")
    
    # Fallback: используем eth_gasPrice
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "params": [],
            "id": 1
        }
        
        async with session.post(
            chain["rpc"],
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                gas_price = int(data.get("result", "0x0"), 16)
                
                # Применяем множитель скорости
                speed_multipliers = {"slow": 0.9, "standard": 1.0, "fast": 1.2, "instant": 1.5}
                multiplier = speed_multipliers.get(speed, 1.0)
                adjusted_price = int(gas_price * multiplier)
                
                return {
                    "maxFeePerGas": adjusted_price,
                    "maxPriorityFeePerGas": adjusted_price // 10,  # 10% priority
                    "gasPrice": adjusted_price
                }
    
    except Exception as e:
        print(f"Ошибка получения gas price: {e}")
    
    # Последний fallback
    return {
        "maxFeePerGas": 30_000_000_000,  # 30 gwei
        "maxPriorityFeePerGas": 2_000_000_000,  # 2 gwei
        "gasPrice": 30_000_000_000
    }


async def monitor_gas_prices(
    chains: List[Dict],
    session: aiohttp.ClientSession,
    duration: int = 60,
    interval: int = 10
) -> Dict[str, List[int]]:
    """
    Мониторить цены газа в течение времени
    
    Args:
        chains: Список сетей для мониторинга
        session: aiohttp сессия
        duration: Длительность мониторинга (секунды)
        interval: Интервал проверки (секунды)
    
    Returns:
        Dict: {
            "ethereum": [30, 28, 32, 29, ...],  # gwei
            "bsc": [5, 5, 6, 5, ...],
            ...
        }
    """
    
    gas_history = {chain["name"]: [] for chain in chains}
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Проверяем все сети параллельно
        tasks = [get_optimal_gas_price(chain, session, 5, "standard") for chain in chains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for chain, result in zip(chains, results):
            if isinstance(result, Exception):
                continue
            
            gas_price_gwei = result.get("gasPrice", 0) / 1e9
            gas_history[chain["name"]].append(gas_price_gwei)
        
        await asyncio.sleep(interval)
    
    return gas_history


def find_best_gas_time(gas_history: Dict[str, List[int]], chain: str) -> Dict[str, Any]:
    """
    Найти лучшее время для транзакции (минимальный газ)
    
    Returns:
        Dict: {
            "min_gas": 25.5,  # gwei
            "avg_gas": 30.2,
            "max_gas": 35.8,
            "current_gas": 28.0,
            "recommendation": "Сейчас хорошее время" | "Подождите, газ высокий"
        }
    """
    
    history = gas_history.get(chain, [])
    if not history:
        return {"error": "No data"}
    
    min_gas = min(history)
    max_gas = max(history)
    avg_gas = sum(history) / len(history)
    current_gas = history[-1]
    
    # Рекомендация
    if current_gas <= min_gas * 1.1:  # В пределах 10% от минимума
        recommendation = "✅ Сейчас хорошее время для транзакции"
    elif current_gas >= avg_gas * 1.2:  # На 20% выше среднего
        recommendation = f"⏳ Подождите, газ высокий. Средний: {avg_gas:.1f} gwei"
    else:
        recommendation = f"⚠️ Газ в норме. Минимум был: {min_gas:.1f} gwei"
    
    return {
        "min_gas": min_gas,
        "avg_gas": avg_gas,
        "max_gas": max_gas,
        "current_gas": current_gas,
        "recommendation": recommendation,
        "savings_potential": ((current_gas - min_gas) / current_gas * 100) if current_gas > 0 else 0
    }
