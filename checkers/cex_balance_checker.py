# -*- coding: utf-8 -*-
"""
CEX Balance Checker v1.0.59
Реальная проверка балансов на криптобиржах через API
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode


class CEXBalanceChecker:
    """Проверка балансов на централизованных биржах"""
    
    def __init__(self):
        self.supported_exchanges = [
            "binance", "bybit", "okx", "gate", "mexc", "bitget",
            "huobi", "kucoin", "kraken", "coinbase"
        ]
    
    async def check_exchange_balance(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Проверить баланс на бирже
        
        Args:
            exchange: Название биржи (binance, bybit, okx, etc.)
            api_key: API ключ
            api_secret: API секрет
            session: aiohttp сессия
            timeout: Таймаут
        
        Returns:
            {
                "exchange": str,
                "valid": bool,
                "balances": {...},
                "total_usd": float,
                "spot": {...},
                "futures": {...},
                "staking": {...},
                "open_orders": [...],
            }
        """
        
        exchange = exchange.lower()
        
        if exchange not in self.supported_exchanges:
            return {
                "exchange": exchange,
                "valid": False,
                "error": f"Unsupported exchange: {exchange}"
            }
        
        # Вызываем соответствующий метод
        checker_method = getattr(self, f"_check_{exchange}", None)
        
        if checker_method:
            return await checker_method(api_key, api_secret, session, timeout)
        else:
            return {
                "exchange": exchange,
                "valid": False,
                "error": f"Checker not implemented for {exchange}"
            }
    
    # ═══════════════════════════════════════════════════════════════════════
    #  BINANCE
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_binance(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка Binance"""
        
        result = {
            "exchange": "binance",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
            "spot": {},
            "futures": {},
            "staking": {},
            "open_orders": [],
        }
        
        try:
            base_url = "https://api.binance.com"
            
            # Получаем spot баланс
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            signature = hmac.new(
                api_secret.encode(),
                urlencode(params).encode(),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": api_key}
            
            url = f"{base_url}/api/v3/account?{urlencode(params)}"
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["valid"] = True
                    
                    # Обрабатываем балансы
                    for balance in data.get("balances", []):
                        asset = balance.get("asset")
                        free = float(balance.get("free", 0))
                        locked = float(balance.get("locked", 0))
                        total = free + locked
                        
                        if total > 0:
                            result["spot"][asset] = {
                                "free": free,
                                "locked": locked,
                                "total": total
                            }
                            result["balances"][asset] = total
                    
                    # Получаем цены для расчета USD
                    prices = await self._get_binance_prices(session, timeout)
                    
                    for asset, amount in result["balances"].items():
                        if asset == "USDT":
                            result["total_usd"] += amount
                        elif asset in prices:
                            result["total_usd"] += amount * prices[asset]
                    
                    # Получаем открытые ордера
                    orders_url = f"{base_url}/api/v3/openOrders"
                    timestamp = int(time.time() * 1000)
                    params = {"timestamp": timestamp}
                    signature = hmac.new(
                        api_secret.encode(),
                        urlencode(params).encode(),
                        hashlib.sha256
                    ).hexdigest()
                    params["signature"] = signature
                    
                    orders_url += f"?{urlencode(params)}"
                    
                    async with session.get(
                        orders_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as resp_orders:
                        if resp_orders.status == 200:
                            orders = await resp_orders.json()
                            result["open_orders"] = orders
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key or signature"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def _get_binance_prices(
        self,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, float]:
        """Получить цены с Binance"""
        
        prices = {}
        
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for item in data:
                        symbol = item.get("symbol", "")
                        if symbol.endswith("USDT"):
                            asset = symbol[:-4]  # Убираем USDT
                            price = float(item.get("price", 0))
                            prices[asset] = price
        
        except Exception:
            pass
        
        return prices
    
    # ═══════════════════════════════════════════════════════════════════════
    #  BYBIT
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_bybit(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка Bybit"""
        
        result = {
            "exchange": "bybit",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
            "spot": {},
            "futures": {},
        }
        
        try:
            base_url = "https://api.bybit.com"
            
            # Получаем баланс
            timestamp = str(int(time.time() * 1000))
            params = {
                "api_key": api_key,
                "timestamp": timestamp
            }
            
            # Создаем подпись
            param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                api_secret.encode(),
                param_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            params["sign"] = signature
            
            url = f"{base_url}/v5/account/wallet-balance?{urlencode(params)}"
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("retCode") == 0:
                        result["valid"] = True
                        
                        # Обрабатываем балансы
                        wallet_list = data.get("result", {}).get("list", [])
                        
                        for wallet in wallet_list:
                            coins = wallet.get("coin", [])
                            
                            for coin in coins:
                                asset = coin.get("coin")
                                equity = float(coin.get("equity", 0))
                                
                                if equity > 0:
                                    result["balances"][asset] = equity
                                    
                                    if asset == "USDT":
                                        result["total_usd"] += equity
                    else:
                        result["error"] = data.get("retMsg", "Unknown error")
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    #  OKX
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_okx(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка OKX"""
        
        result = {
            "exchange": "okx",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
        }
        
        try:
            base_url = "https://www.okx.com"
            
            # OKX требует passphrase (обычно передается отдельно)
            # Здесь упрощенная версия
            
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            method = "GET"
            request_path = "/api/v5/account/balance"
            
            # Создаем подпись
            prehash = timestamp + method + request_path
            signature = hmac.new(
                api_secret.encode(),
                prehash.encode(),
                hashlib.sha256
            ).digest()
            signature_b64 = signature.hex()
            
            headers = {
                "OK-ACCESS-KEY": api_key,
                "OK-ACCESS-SIGN": signature_b64,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": "",  # Нужен passphrase
                "Content-Type": "application/json"
            }
            
            url = base_url + request_path
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("code") == "0":
                        result["valid"] = True
                        
                        # Обрабатываем балансы
                        balance_data = data.get("data", [])
                        
                        for account in balance_data:
                            details = account.get("details", [])
                            
                            for detail in details:
                                asset = detail.get("ccy")
                                available = float(detail.get("availBal", 0))
                                
                                if available > 0:
                                    result["balances"][asset] = available
                                    
                                    if asset == "USDT":
                                        result["total_usd"] += available
                    else:
                        result["error"] = data.get("msg", "Unknown error")
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    #  GATE.IO
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_gate(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка Gate.io"""
        
        result = {
            "exchange": "gate",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
        }
        
        try:
            base_url = "https://api.gateio.ws"
            
            timestamp = str(int(time.time()))
            method = "GET"
            request_path = "/api/v4/spot/accounts"
            
            # Создаем подпись
            body_hash = hashlib.sha512(b"").hexdigest()
            sign_string = f"{method}\n{request_path}\n\n{body_hash}\n{timestamp}"
            signature = hmac.new(
                api_secret.encode(),
                sign_string.encode(),
                hashlib.sha512
            ).hexdigest()
            
            headers = {
                "KEY": api_key,
                "SIGN": signature,
                "Timestamp": timestamp,
                "Content-Type": "application/json"
            }
            
            url = base_url + request_path
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["valid"] = True
                    
                    # Обрабатываем балансы
                    for account in data:
                        currency = account.get("currency")
                        available = float(account.get("available", 0))
                        
                        if available > 0:
                            result["balances"][currency] = available
                            
                            if currency == "USDT":
                                result["total_usd"] += available
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    #  MEXC
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_mexc(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка MEXC"""
        
        result = {
            "exchange": "mexc",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
        }
        
        try:
            base_url = "https://api.mexc.com"
            
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            
            # Создаем подпись
            query_string = urlencode(params)
            signature = hmac.new(
                api_secret.encode(),
                query_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            params["signature"] = signature
            
            headers = {"X-MEXC-APIKEY": api_key}
            
            url = f"{base_url}/api/v3/account?{urlencode(params)}"
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["valid"] = True
                    
                    # Обрабатываем балансы
                    for balance in data.get("balances", []):
                        asset = balance.get("asset")
                        free = float(balance.get("free", 0))
                        locked = float(balance.get("locked", 0))
                        total = free + locked
                        
                        if total > 0:
                            result["balances"][asset] = total
                            
                            if asset == "USDT":
                                result["total_usd"] += total
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    #  BITGET
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _check_bitget(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession,
        timeout: int
    ) -> Dict[str, Any]:
        """Проверка Bitget"""
        
        result = {
            "exchange": "bitget",
            "valid": False,
            "balances": {},
            "total_usd": 0.0,
        }
        
        try:
            base_url = "https://api.bitget.com"
            
            timestamp = str(int(time.time() * 1000))
            method = "GET"
            request_path = "/api/spot/v1/account/assets"
            
            # Создаем подпись
            prehash = timestamp + method + request_path
            signature = hmac.new(
                api_secret.encode(),
                prehash.encode(),
                hashlib.sha256
            ).digest()
            signature_b64 = signature.hex()
            
            headers = {
                "ACCESS-KEY": api_key,
                "ACCESS-SIGN": signature_b64,
                "ACCESS-TIMESTAMP": timestamp,
                "ACCESS-PASSPHRASE": "",  # Нужен passphrase
                "Content-Type": "application/json"
            }
            
            url = base_url + request_path
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get("code") == "00000":
                        result["valid"] = True
                        
                        # Обрабатываем балансы
                        assets = data.get("data", [])
                        
                        for asset in assets:
                            coin = asset.get("coinName")
                            available = float(asset.get("available", 0))
                            
                            if available > 0:
                                result["balances"][coin] = available
                                
                                if coin == "USDT":
                                    result["total_usd"] += available
                    else:
                        result["error"] = data.get("msg", "Unknown error")
                
                elif resp.status == 401:
                    result["error"] = "Invalid API key"
                else:
                    result["error"] = f"HTTP {resp.status}"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    #  HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════
    
    def format_balance_report(self, result: Dict[str, Any]) -> str:
        """Форматировать отчет о балансе"""
        
        if not result.get("valid"):
            error = result.get("error", "Unknown error")
            return f"❌ {result['exchange'].upper()}: {error}"
        
        lines = []
        
        lines.append(f"✅ {result['exchange'].upper()} - VALID")
        lines.append("=" * 50)
        
        # Общий баланс
        total_usd = result.get("total_usd", 0)
        if total_usd > 0:
            lines.append(f"💰 Total: ~${total_usd:,.2f}")
        
        # Балансы по монетам
        balances = result.get("balances", {})
        if balances:
            lines.append(f"\n📊 Balances ({len(balances)} assets):")
            
            # Сортируем по количеству
            sorted_balances = sorted(
                balances.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for asset, amount in sorted_balances[:10]:  # Топ-10
                lines.append(f"  • {asset}: {amount:.8f}")
            
            if len(balances) > 10:
                lines.append(f"  ... и еще {len(balances) - 10} активов")
        
        # Открытые ордера
        open_orders = result.get("open_orders", [])
        if open_orders:
            lines.append(f"\n📈 Open Orders: {len(open_orders)}")
        
        # Spot/Futures
        spot = result.get("spot", {})
        futures = result.get("futures", {})
        
        if spot:
            lines.append(f"\n💵 Spot: {len(spot)} assets")
        
        if futures:
            lines.append(f"📊 Futures: {len(futures)} positions")
        
        return "\n".join(lines)
