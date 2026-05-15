# -*- coding: utf-8 -*-
"""
CEX Checker v1.0.55
Проверка API ключей криптобирж: Binance, Bybit, OKX, Huobi, KuCoin, Gate.io, MEXC, Bitget
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time
import base64
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode


# ═══════════════════════════════════════════════════════════════════════════
#  BINANCE API
# ═══════════════════════════════════════════════════════════════════════════

class BinanceChecker:
    """Проверка Binance API ключей"""
    
    BASE_URL = "https://api.binance.com"
    
    @staticmethod
    async def check_api_key(
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить Binance API ключ
        
        Returns:
            Dict: {
                "valid": True,
                "spot_balance": {"BTC": 0.5, "USDT": 1000},
                "futures_balance": {"USDT": 500},
                "total_usd": 15000,
                "permissions": ["SPOT", "FUTURES"],
                "account_type": "SPOT"
            }
        """
        
        result = {
            "exchange": "Binance",
            "valid": False,
            "spot_balance": {},
            "futures_balance": {},
            "margin_balance": {},
            "total_usd": 0,
            "permissions": [],
            "account_type": "",
            "error": None
        }
        
        try:
            # Проверяем spot баланс
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            signature = hmac.new(
                api_secret.encode(),
                urlencode(params).encode(),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": api_key}
            url = f"{BinanceChecker.BASE_URL}/api/v3/account"
            
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["valid"] = True
                    result["account_type"] = data.get("accountType", "SPOT")
                    result["permissions"] = data.get("permissions", [])
                    
                    # Парсим балансы
                    for balance in data.get("balances", []):
                        asset = balance["asset"]
                        free = float(balance["free"])
                        locked = float(balance["locked"])
                        total = free + locked
                        
                        if total > 0:
                            result["spot_balance"][asset] = total
                    
                    # Проверяем futures баланс (если есть права)
                    if "FUTURES" in result["permissions"]:
                        futures_balance = await BinanceChecker._check_futures_balance(
                            api_key, api_secret, session, timeout
                        )
                        result["futures_balance"] = futures_balance
                    
                    # Рассчитываем total USD
                    result["total_usd"] = await BinanceChecker._calculate_total_usd(
                        result["spot_balance"],
                        result["futures_balance"],
                        session,
                        timeout
                    )
                    
                elif resp.status == 401:
                    result["error"] = "Invalid API key or signature"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    @staticmethod
    async def _check_futures_balance(
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, float]:
        """Проверить futures баланс"""
        
        try:
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            signature = hmac.new(
                api_secret.encode(),
                urlencode(params).encode(),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": api_key}
            url = "https://fapi.binance.com/fapi/v2/balance"
            
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balances = {}
                    
                    for balance in data:
                        asset = balance["asset"]
                        total = float(balance["balance"])
                        
                        if total > 0:
                            balances[asset] = total
                    
                    return balances
        
        except:
            pass
        
        return {}
    
    @staticmethod
    async def _calculate_total_usd(
        spot: Dict[str, float],
        futures: Dict[str, float],
        session: aiohttp.ClientSession,
        timeout: int
    ) -> float:
        """Рассчитать общую стоимость в USD"""
        
        # Объединяем все активы
        all_assets = {}
        for asset, amount in spot.items():
            all_assets[asset] = all_assets.get(asset, 0) + amount
        for asset, amount in futures.items():
            all_assets[asset] = all_assets.get(asset, 0) + amount
        
        # Получаем цены
        total_usd = 0
        
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    prices = await resp.json()
                    price_map = {p["symbol"]: float(p["price"]) for p in prices}
                    
                    for asset, amount in all_assets.items():
                        if asset == "USDT" or asset == "USDC" or asset == "BUSD":
                            total_usd += amount
                        else:
                            # Пробуем найти пару с USDT
                            symbol = f"{asset}USDT"
                            if symbol in price_map:
                                total_usd += amount * price_map[symbol]
        except:
            pass
        
        return total_usd


# ═══════════════════════════════════════════════════════════════════════════
#  BYBIT API
# ═══════════════════════════════════════════════════════════════════════════

class BybitChecker:
    """Проверка Bybit API ключей"""
    
    BASE_URL = "https://api.bybit.com"
    
    @staticmethod
    async def check_api_key(
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Проверить Bybit API ключ"""
        
        result = {
            "exchange": "Bybit",
            "valid": False,
            "spot_balance": {},
            "futures_balance": {},
            "total_usd": 0,
            "error": None
        }
        
        try:
            timestamp = str(int(time.time() * 1000))
            params = {"api_key": api_key, "timestamp": timestamp}
            
            # Создаем подпись
            param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                api_secret.encode(),
                param_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            params["sign"] = signature
            
            url = f"{BybitChecker.BASE_URL}/v5/account/wallet-balance"
            params["accountType"] = "UNIFIED"
            
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("retCode") == 0:
                        result["valid"] = True
                        
                        # Парсим балансы
                        wallet_list = data.get("result", {}).get("list", [])
                        for wallet in wallet_list:
                            for coin in wallet.get("coin", []):
                                asset = coin["coin"]
                                total = float(coin.get("walletBalance", 0))
                                
                                if total > 0:
                                    result["spot_balance"][asset] = total
                        
                        # Рассчитываем total USD
                        result["total_usd"] = sum(
                            float(coin.get("usdValue", 0))
                            for wallet in wallet_list
                            for coin in wallet.get("coin", [])
                        )
                    else:
                        result["error"] = data.get("retMsg", "Unknown error")
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  OKX API
# ═══════════════════════════════════════════════════════════════════════════

class OKXChecker:
    """Проверка OKX API ключей"""
    
    BASE_URL = "https://www.okx.com"
    
    @staticmethod
    async def check_api_key(
        api_key: str,
        api_secret: str,
        passphrase: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Проверить OKX API ключ (требуется passphrase)"""
        
        result = {
            "exchange": "OKX",
            "valid": False,
            "spot_balance": {},
            "futures_balance": {},
            "total_usd": 0,
            "error": None
        }
        
        try:
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            method = "GET"
            request_path = "/api/v5/account/balance"
            
            # Создаем подпись
            prehash = timestamp + method + request_path
            signature = base64.b64encode(
                hmac.new(
                    api_secret.encode(),
                    prehash.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            headers = {
                "OK-ACCESS-KEY": api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": passphrase,
                "Content-Type": "application/json"
            }
            
            url = f"{OKXChecker.BASE_URL}{request_path}"
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("code") == "0":
                        result["valid"] = True
                        
                        # Парсим балансы
                        for account in data.get("data", []):
                            for detail in account.get("details", []):
                                asset = detail["ccy"]
                                total = float(detail.get("cashBal", 0))
                                
                                if total > 0:
                                    result["spot_balance"][asset] = total
                                    
                                    # Добавляем к total USD
                                    eq_usd = float(detail.get("eqUsd", 0))
                                    result["total_usd"] += eq_usd
                    else:
                        result["error"] = data.get("msg", "Unknown error")
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  KUCOIN API
# ═══════════════════════════════════════════════════════════════════════════

class KuCoinChecker:
    """Проверка KuCoin API ключей"""
    
    BASE_URL = "https://api.kucoin.com"
    
    @staticmethod
    async def check_api_key(
        api_key: str,
        api_secret: str,
        passphrase: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Проверить KuCoin API ключ"""
        
        result = {
            "exchange": "KuCoin",
            "valid": False,
            "spot_balance": {},
            "total_usd": 0,
            "error": None
        }
        
        try:
            timestamp = str(int(time.time() * 1000))
            method = "GET"
            endpoint = "/api/v1/accounts"
            
            # Создаем подпись
            str_to_sign = timestamp + method + endpoint
            signature = base64.b64encode(
                hmac.new(
                    api_secret.encode(),
                    str_to_sign.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            # Passphrase тоже нужно подписать
            passphrase_signature = base64.b64encode(
                hmac.new(
                    api_secret.encode(),
                    passphrase.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            headers = {
                "KC-API-KEY": api_key,
                "KC-API-SIGN": signature,
                "KC-API-TIMESTAMP": timestamp,
                "KC-API-PASSPHRASE": passphrase_signature,
                "KC-API-KEY-VERSION": "2"
            }
            
            url = f"{KuCoinChecker.BASE_URL}{endpoint}"
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("code") == "200000":
                        result["valid"] = True
                        
                        # Парсим балансы
                        for account in data.get("data", []):
                            asset = account["currency"]
                            total = float(account.get("balance", 0))
                            
                            if total > 0:
                                result["spot_balance"][asset] = total
                        
                        # TODO: Получить цены и рассчитать USD
                        result["total_usd"] = 0
                    else:
                        result["error"] = data.get("msg", "Unknown error")
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED CEX CHECKER
# ═══════════════════════════════════════════════════════════════════════════

class CEXChecker:
    """Универсальный чекер для всех бирж"""
    
    SUPPORTED_EXCHANGES = {
        "binance": BinanceChecker,
        "bybit": BybitChecker,
        "okx": OKXChecker,
        "kucoin": KuCoinChecker,
    }
    
    @staticmethod
    async def check_api_key(
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Универсальная проверка API ключа
        
        Args:
            exchange: "binance" | "bybit" | "okx" | "kucoin" | ...
            api_key: API ключ
            api_secret: API секрет
            passphrase: Passphrase (для OKX, KuCoin)
            session: aiohttp сессия
            timeout: таймаут
        
        Returns:
            Dict: результат проверки
        """
        
        exchange = exchange.lower()
        
        if exchange not in CEXChecker.SUPPORTED_EXCHANGES:
            return {
                "exchange": exchange,
                "valid": False,
                "error": f"Exchange {exchange} not supported"
            }
        
        checker_class = CEXChecker.SUPPORTED_EXCHANGES[exchange]
        
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            # Для OKX и KuCoin нужен passphrase
            if exchange in ["okx", "kucoin"]:
                if not passphrase:
                    return {
                        "exchange": exchange,
                        "valid": False,
                        "error": "Passphrase required"
                    }
                result = await checker_class.check_api_key(
                    api_key, api_secret, passphrase, session, timeout
                )
            else:
                result = await checker_class.check_api_key(
                    api_key, api_secret, session, timeout
                )
            
            return result
        
        finally:
            if own_session:
                await session.close()
    
    @staticmethod
    async def check_multiple_exchanges(
        credentials: List[Dict],
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 10
    ) -> List[Dict]:
        """
        Проверить несколько бирж параллельно
        
        Args:
            credentials: [
                {
                    "exchange": "binance",
                    "api_key": "...",
                    "api_secret": "...",
                    "passphrase": "..."  # опционально
                },
                ...
            ]
        
        Returns:
            List[Dict]: результаты проверки
        """
        
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
        
        try:
            tasks = []
            for cred in credentials:
                task = CEXChecker.check_api_key(
                    exchange=cred["exchange"],
                    api_key=cred["api_key"],
                    api_secret=cred["api_secret"],
                    passphrase=cred.get("passphrase"),
                    session=session,
                    timeout=timeout
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем ошибки
            processed_results = []
            for cred, result in zip(credentials, results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "exchange": cred["exchange"],
                        "valid": False,
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        
        finally:
            if own_session:
                await session.close()
    
    @staticmethod
    def format_result(result: Dict) -> str:
        """
        Форматировать результат для вывода
        
        Returns:
            str: "Binance: $15,000 | Spot: BTC 0.5, USDT 1000 | Futures: USDT 500"
        """
        
        if not result.get("valid"):
            error = result.get("error", "Unknown error")
            return f"{result['exchange']}: ❌ {error}"
        
        parts = [f"{result['exchange']}: ✅"]
        
        # Total USD
        total_usd = result.get("total_usd", 0)
        if total_usd > 0:
            parts.append(f"${total_usd:,.2f}")
        
        # Spot balance
        spot = result.get("spot_balance", {})
        if spot:
            spot_str = ", ".join([f"{asset} {amount:.8g}" for asset, amount in list(spot.items())[:5]])
            if len(spot) > 5:
                spot_str += f" +{len(spot) - 5} more"
            parts.append(f"Spot: {spot_str}")
        
        # Futures balance
        futures = result.get("futures_balance", {})
        if futures:
            futures_str = ", ".join([f"{asset} {amount:.8g}" for asset, amount in list(futures.items())[:3]])
            parts.append(f"Futures: {futures_str}")
        
        # Permissions
        permissions = result.get("permissions", [])
        if permissions:
            parts.append(f"Permissions: {', '.join(permissions)}")
        
        return " | ".join(parts)
