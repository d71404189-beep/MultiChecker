# -*- coding: utf-8 -*-
"""
DeFi Checker v1.0.53
Проверка DeFi позиций: Aave, Compound, Uniswap V3 LP, Unclaimed rewards
"""

import aiohttp
from typing import Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════
#  AAVE ПОЗИЦИИ
# ═══════════════════════════════════════════════════════════════════════════

AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"  # Ethereum mainnet

async def check_aave_positions(address: str, session: aiohttp.ClientSession, timeout: int = 10) -> Dict:
    """
    Проверить позиции в Aave V3
    
    Returns:
        Dict: {
            "supplied": {"USDC": 1000, "ETH": 0.5},
            "borrowed": {"USDT": 500},
            "health_factor": 2.5,
            "total_supplied_usd": 2500,
            "total_borrowed_usd": 500,
            "unclaimed_rewards": 10.5
        }
    """
    result = {
        "supplied": {},
        "borrowed": {},
        "health_factor": 0,
        "total_supplied_usd": 0,
        "total_borrowed_usd": 0,
        "unclaimed_rewards": 0
    }
    
    try:
        # Используем Aave Subgraph API
        subgraph_url = "https://api.thegraph.com/subgraphs/name/aave/protocol-v3"
        
        query = """
        {
          userReserves(where: {user: "%s"}) {
            reserve {
              symbol
              decimals
              underlyingAsset
            }
            currentATokenBalance
            currentVariableDebt
            currentStableDebt
          }
          user(id: "%s") {
            id
          }
        }
        """ % (address.lower(), address.lower())
        
        async with session.post(subgraph_url, json={"query": query}, timeout=timeout) as resp:
            if resp.status != 200:
                return result
            
            data = await resp.json()
            user_reserves = data.get("data", {}).get("userReserves", [])
            
            for reserve in user_reserves:
                symbol = reserve["reserve"]["symbol"]
                decimals = int(reserve["reserve"]["decimals"])
                
                # Supplied (aToken balance)
                supplied = int(reserve["currentATokenBalance"]) / (10 ** decimals)
                if supplied > 0:
                    result["supplied"][symbol] = supplied
                
                # Borrowed
                variable_debt = int(reserve["currentVariableDebt"]) / (10 ** decimals)
                stable_debt = int(reserve["currentStableDebt"]) / (10 ** decimals)
                total_debt = variable_debt + stable_debt
                
                if total_debt > 0:
                    result["borrowed"][symbol] = total_debt
            
            return result
            
    except Exception as e:
        print(f"Ошибка проверки Aave: {e}")
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  COMPOUND ПОЗИЦИИ
# ═══════════════════════════════════════════════════════════════════════════

async def check_compound_positions(address: str, session: aiohttp.ClientSession, timeout: int = 10) -> Dict:
    """
    Проверить позиции в Compound V3
    
    Returns:
        Dict: {
            "supplied": {"USDC": 1000},
            "borrowed": {"USDC": 500},
            "collateral": {"ETH": 1.5},
            "unclaimed_comp": 5.2
        }
    """
    result = {
        "supplied": {},
        "borrowed": {},
        "collateral": {},
        "unclaimed_comp": 0
    }
    
    try:
        # Используем Compound API
        api_url = f"https://api.compound.finance/api/v2/account?addresses[]={address}"
        
        async with session.get(api_url, timeout=timeout) as resp:
            if resp.status != 200:
                return result
            
            data = await resp.json()
            accounts = data.get("accounts", [])
            
            if not accounts:
                return result
            
            account = accounts[0]
            tokens = account.get("tokens", [])
            
            for token in tokens:
                symbol = token.get("symbol", "").replace("c", "")  # cUSDC -> USDC
                supply_balance = float(token.get("supply_balance_underlying", {}).get("value", 0))
                borrow_balance = float(token.get("borrow_balance_underlying", {}).get("value", 0))
                
                if supply_balance > 0:
                    result["supplied"][symbol] = supply_balance
                
                if borrow_balance > 0:
                    result["borrowed"][symbol] = borrow_balance
            
            # Unclaimed COMP
            result["unclaimed_comp"] = float(account.get("total_collateral_value_in_eth", {}).get("value", 0))
            
            return result
            
    except Exception as e:
        print(f"Ошибка проверки Compound: {e}")
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  UNISWAP V3 LP ПОЗИЦИИ
# ═══════════════════════════════════════════════════════════════════════════

async def check_uniswap_v3_lp(address: str, session: aiohttp.ClientSession, timeout: int = 10) -> List[Dict]:
    """
    Проверить Uniswap V3 LP позиции
    
    Returns:
        List[Dict]: [
            {
                "token_id": 123456,
                "token0": "USDC",
                "token1": "ETH",
                "liquidity": 1000000,
                "fee_tier": 0.3,
                "in_range": True,
                "unclaimed_fees": {"USDC": 10, "ETH": 0.005}
            }
        ]
    """
    positions = []
    
    try:
        # Используем Uniswap V3 Subgraph
        subgraph_url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        
        query = """
        {
          positions(where: {owner: "%s"}) {
            id
            liquidity
            token0 {
              symbol
              decimals
            }
            token1 {
              symbol
              decimals
            }
            pool {
              feeTier
              tick
            }
            tickLower {
              tickIdx
            }
            tickUpper {
              tickIdx
            }
            collectedFeesToken0
            collectedFeesToken1
          }
        }
        """ % address.lower()
        
        async with session.post(subgraph_url, json={"query": query}, timeout=timeout) as resp:
            if resp.status != 200:
                return positions
            
            data = await resp.json()
            position_data = data.get("data", {}).get("positions", [])
            
            for pos in position_data:
                liquidity = int(pos.get("liquidity", 0))
                
                if liquidity == 0:
                    continue
                
                token0_symbol = pos["token0"]["symbol"]
                token1_symbol = pos["token1"]["symbol"]
                fee_tier = int(pos["pool"]["feeTier"]) / 10000  # 3000 -> 0.3%
                
                # Проверяем in range
                current_tick = int(pos["pool"]["tick"])
                tick_lower = int(pos["tickLower"]["tickIdx"])
                tick_upper = int(pos["tickUpper"]["tickIdx"])
                in_range = tick_lower <= current_tick <= tick_upper
                
                # Unclaimed fees
                fees_token0 = int(pos.get("collectedFeesToken0", 0)) / (10 ** int(pos["token0"]["decimals"]))
                fees_token1 = int(pos.get("collectedFeesToken1", 0)) / (10 ** int(pos["token1"]["decimals"]))
                
                positions.append({
                    "token_id": pos["id"],
                    "token0": token0_symbol,
                    "token1": token1_symbol,
                    "liquidity": liquidity,
                    "fee_tier": fee_tier,
                    "in_range": in_range,
                    "unclaimed_fees": {
                        token0_symbol: fees_token0,
                        token1_symbol: fees_token1
                    }
                })
            
            return positions
            
    except Exception as e:
        print(f"Ошибка проверки Uniswap V3: {e}")
        return positions


# ═══════════════════════════════════════════════════════════════════════════
#  UNCLAIMED REWARDS
# ═══════════════════════════════════════════════════════════════════════════

async def check_unclaimed_rewards(address: str, session: aiohttp.ClientSession, timeout: int = 10) -> Dict:
    """
    Проверить unclaimed rewards из разных протоколов
    
    Returns:
        Dict: {
            "aave": {"AAVE": 10.5},
            "compound": {"COMP": 5.2},
            "curve": {"CRV": 100},
            "total_usd": 250.75
        }
    """
    rewards = {
        "aave": {},
        "compound": {},
        "curve": {},
        "total_usd": 0
    }
    
    try:
        # Проверяем Aave rewards
        aave_rewards_url = f"https://api.aave.com/v1/incentives/users/{address}/unclaimed-rewards"
        try:
            async with session.get(aave_rewards_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for reward in data.get("rewards", []):
                        symbol = reward.get("symbol", "AAVE")
                        amount = float(reward.get("amount", 0))
                        if amount > 0:
                            rewards["aave"][symbol] = amount
        except:
            pass
        
        # Проверяем Compound COMP
        # (уже проверяется в check_compound_positions)
        
        # Проверяем Curve CRV
        curve_api_url = f"https://api.curve.fi/api/getGaugeRewards/{address}"
        try:
            async with session.get(curve_api_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    crv_amount = float(data.get("data", {}).get("claimable", 0))
                    if crv_amount > 0:
                        rewards["curve"]["CRV"] = crv_amount
        except:
            pass
        
        return rewards
        
    except Exception as e:
        print(f"Ошибка проверки rewards: {e}")
        return rewards


# ═══════════════════════════════════════════════════════════════════════════
#  СВОДНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════════

async def check_all_defi_positions(address: str, session: aiohttp.ClientSession, timeout: int = 10) -> Dict:
    """
    Проверить все DeFi позиции
    
    Returns:
        Dict: {
            "aave": {...},
            "compound": {...},
            "uniswap_v3": [...],
            "unclaimed_rewards": {...},
            "total_value_usd": 5000
        }
    """
    import asyncio
    
    # Проверяем все параллельно
    aave, compound, uni_v3, rewards = await asyncio.gather(
        check_aave_positions(address, session, timeout),
        check_compound_positions(address, session, timeout),
        check_uniswap_v3_lp(address, session, timeout),
        check_unclaimed_rewards(address, session, timeout),
        return_exceptions=True
    )
    
    # Обрабатываем ошибки
    if isinstance(aave, Exception):
        aave = {}
    if isinstance(compound, Exception):
        compound = {}
    if isinstance(uni_v3, Exception):
        uni_v3 = []
    if isinstance(rewards, Exception):
        rewards = {}
    
    return {
        "aave": aave,
        "compound": compound,
        "uniswap_v3": uni_v3,
        "unclaimed_rewards": rewards,
        "total_value_usd": 0  # TODO: Calculate total value
    }
