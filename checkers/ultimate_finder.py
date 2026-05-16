# -*- coding: utf-8 -*-
"""
Ultimate Account Finder v1.0.66
Мощный поиск аккаунтов с seed/privkey и балансом
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
import re
import hashlib
from datetime import datetime


class UltimateAccountFinder:
    """Мощный поиск аккаунтов с возможностью входа"""
    
    def __init__(self):
        self.found_accounts = []
        self.high_value_threshold = 100.0  # $100+
        self.whale_threshold = 10000.0  # $10,000+
        
        # Статистика
        self.stats = {
            "total_scanned": 0,
            "with_auth": 0,
            "with_balance": 0,
            "high_value": 0,
            "whales": 0,
            "total_value_usd": 0.0,
        }
    
    async def scan_accounts(
        self,
        accounts: List[Dict[str, Any]],
        deep_check: bool = True,
        check_all_chains: bool = True
    ) -> Dict[str, Any]:
        """
        Сканировать аккаунты и найти с балансом + auth
        
        Args:
            accounts: Список аккаунтов для проверки
            deep_check: Глубокая проверка (все токены, NFT, DeFi)
            check_all_chains: Проверять на всех сетях
        
        Returns:
            Результаты сканирования
        """
        
        results = {
            "found_accounts": [],
            "high_value_accounts": [],
            "whale_accounts": [],
            "statistics": {},
        }
        
        for account in accounts:
            self.stats["total_scanned"] += 1
            
            # Проверяем наличие auth данных
            auth_data = self._extract_auth_data(account)
            
            if not auth_data:
                continue
            
            self.stats["with_auth"] += 1
            
            # Проверяем баланс
            balance_info = await self._check_balance(
                account,
                auth_data,
                deep_check,
                check_all_chains
            )
            
            if balance_info["total_usd"] > 0:
                self.stats["with_balance"] += 1
                self.stats["total_value_usd"] += balance_info["total_usd"]
                
                account_result = {
                    "auth_data": auth_data,
                    "balance_info": balance_info,
                    "account_data": account,
                    "found_at": datetime.now().isoformat(),
                }
                
                results["found_accounts"].append(account_result)
                
                # Высокая стоимость
                if balance_info["total_usd"] >= self.high_value_threshold:
                    self.stats["high_value"] += 1
                    results["high_value_accounts"].append(account_result)
                
                # Whale
                if balance_info["total_usd"] >= self.whale_threshold:
                    self.stats["whales"] += 1
                    results["whale_accounts"].append(account_result)
        
        results["statistics"] = self.stats.copy()
        
        return results
    
    def _extract_auth_data(self, account: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Извлечь данные для авторизации"""
        
        auth_data = {
            "type": None,
            "data": None,
            "address": None,
        }
        
        # 1. Проверяем seed фразу
        seed = account.get("seed") or account.get("mnemonic") or account.get("phrase")
        if seed:
            words = seed.split()
            if len(words) in [12, 15, 18, 21, 24]:
                auth_data["type"] = "seed"
                auth_data["data"] = seed
                auth_data["address"] = self._derive_address_from_seed(seed)
                return auth_data
        
        # 2. Проверяем приватный ключ
        privkey = account.get("privkey") or account.get("private_key") or account.get("key")
        if privkey and len(privkey) >= 64:
            auth_data["type"] = "privkey"
            auth_data["data"] = privkey
            auth_data["address"] = self._derive_address_from_privkey(privkey)
            return auth_data
        
        # 3. Проверяем email:password (для бирж)
        email = account.get("email")
        password = account.get("password")
        if email and password:
            auth_data["type"] = "email_password"
            auth_data["data"] = {"email": email, "password": password}
            auth_data["address"] = email
            return auth_data
        
        return None
    
    def _derive_address_from_seed(self, seed: str) -> str:
        """Получить адрес из seed фразы (упрощенно)"""
        
        # В реальности нужна библиотека bip39/bip32
        # Здесь упрощенная версия
        
        try:
            # Используем первые слова для генерации адреса
            words = seed.split()[:3]
            hash_input = " ".join(words).encode()
            address_hash = hashlib.sha256(hash_input).hexdigest()
            
            # Генерируем Ethereum-подобный адрес
            return "0x" + address_hash[:40]
        except:
            return "0x" + "0" * 40
    
    def _derive_address_from_privkey(self, privkey: str) -> str:
        """Получить адрес из приватного ключа (упрощенно)"""
        
        try:
            # Убираем 0x если есть
            if privkey.startswith("0x"):
                privkey = privkey[2:]
            
            # Генерируем адрес из ключа
            key_hash = hashlib.sha256(privkey.encode()).hexdigest()
            return "0x" + key_hash[:40]
        except:
            return "0x" + "0" * 40
    
    async def _check_balance(
        self,
        account: Dict[str, Any],
        auth_data: Dict[str, Any],
        deep_check: bool,
        check_all_chains: bool
    ) -> Dict[str, Any]:
        """Проверить баланс аккаунта"""
        
        balance_info = {
            "total_usd": 0.0,
            "native_balance": 0.0,
            "tokens": [],
            "nfts": [],
            "defi_positions": [],
            "chains": {},
        }
        
        # Получаем адрес
        address = auth_data.get("address")
        
        if not address or address == "0x" + "0" * 40:
            # Пытаемся получить из account
            address = account.get("address")
        
        if not address:
            return balance_info
        
        # Проверяем баланс из результатов (если уже есть)
        if "balance_usd" in account:
            balance_info["total_usd"] = float(account.get("balance_usd", 0))
            return balance_info
        
        if "total_usd" in account.get("info", {}):
            balance_info["total_usd"] = float(account["info"].get("total_usd", 0))
            return balance_info
        
        # Если нет готовых данных - возвращаем 0
        # (в реальности здесь нужна проверка через RPC)
        
        return balance_info
    
    def filter_by_value(
        self,
        accounts: List[Dict[str, Any]],
        min_value: float = 0.0,
        max_value: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Фильтровать по стоимости"""
        
        filtered = []
        
        for account in accounts:
            balance_usd = account.get("balance_info", {}).get("total_usd", 0)
            
            if balance_usd < min_value:
                continue
            
            if max_value and balance_usd > max_value:
                continue
            
            filtered.append(account)
        
        return filtered
    
    def sort_by_value(
        self,
        accounts: List[Dict[str, Any]],
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """Сортировать по стоимости"""
        
        return sorted(
            accounts,
            key=lambda x: x.get("balance_info", {}).get("total_usd", 0),
            reverse=reverse
        )
    
    def export_found_accounts(
        self,
        accounts: List[Dict[str, Any]],
        output_file: str,
        format_type: str = "detailed"
    ) -> bool:
        """Экспортировать найденные аккаунты"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("НАЙДЕННЫЕ АККАУНТЫ С ВОЗМОЖНОСТЬЮ ВХОДА\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Всего найдено: {len(accounts)}\n")
                
                total_value = sum(a.get("balance_info", {}).get("total_usd", 0) for a in accounts)
                f.write(f"Общая стоимость: ${total_value:,.2f}\n\n")
                
                f.write("=" * 70 + "\n\n")
                
                # Сортируем по балансу
                sorted_accounts = self.sort_by_value(accounts)
                
                for i, account in enumerate(sorted_accounts, 1):
                    auth_data = account.get("auth_data", {})
                    balance_info = account.get("balance_info", {})
                    
                    f.write(f"{'=' * 70}\n")
                    f.write(f"АККАУНТ #{i}\n")
                    f.write(f"{'=' * 70}\n\n")
                    
                    # Баланс
                    balance_usd = balance_info.get("total_usd", 0)
                    if balance_usd >= 10000:
                        f.write(f"💎 WHALE: ${balance_usd:,.2f}\n\n")
                    elif balance_usd >= 1000:
                        f.write(f"💰 HIGH VALUE: ${balance_usd:,.2f}\n\n")
                    else:
                        f.write(f"💵 Баланс: ${balance_usd:,.2f}\n\n")
                    
                    # Тип авторизации
                    auth_type = auth_data.get("type", "unknown")
                    f.write(f"🔐 Тип авторизации: {auth_type}\n\n")
                    
                    # Данные для входа
                    if auth_type == "seed":
                        f.write(f"🌱 Seed фраза:\n")
                        f.write(f"{auth_data.get('data', '')}\n\n")
                        f.write(f"📍 Адрес: {auth_data.get('address', '')}\n\n")
                    
                    elif auth_type == "privkey":
                        f.write(f"🔑 Приватный ключ:\n")
                        f.write(f"{auth_data.get('data', '')}\n\n")
                        f.write(f"📍 Адрес: {auth_data.get('address', '')}\n\n")
                    
                    elif auth_type == "email_password":
                        data = auth_data.get('data', {})
                        f.write(f"📧 Email: {data.get('email', '')}\n")
                        f.write(f"🔒 Password: {data.get('password', '')}\n\n")
                    
                    # Детали баланса
                    if format_type == "detailed":
                        chains = balance_info.get("chains", {})
                        if chains:
                            f.write(f"🌐 Балансы по сетям:\n")
                            for chain, data in chains.items():
                                f.write(f"  • {chain}: ${data.get('total_usd', 0):,.2f}\n")
                            f.write("\n")
                        
                        tokens = balance_info.get("tokens", [])
                        if tokens:
                            f.write(f"🪙 Токены:\n")
                            for token in tokens[:10]:
                                f.write(f"  • {token.get('symbol', '')}: {token.get('balance', 0)}\n")
                            f.write("\n")
                        
                        nfts = balance_info.get("nfts", [])
                        if nfts:
                            f.write(f"💎 NFT: {len(nfts)} шт.\n\n")
                    
                    f.write("\n")
            
            return True
        
        except Exception as e:
            print(f"Error exporting accounts: {e}")
            return False
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Сгенерировать отчет"""
        
        lines = []
        
        lines.append("=" * 60)
        lines.append("🎯 ULTIMATE ACCOUNT FINDER - ОТЧЕТ")
        lines.append("=" * 60)
        
        stats = results.get("statistics", {})
        
        lines.append(f"\n📊 СТАТИСТИКА:")
        lines.append(f"  Всего проверено: {stats.get('total_scanned', 0)}")
        lines.append(f"  С auth данными: {stats.get('with_auth', 0)}")
        lines.append(f"  С балансом: {stats.get('with_balance', 0)}")
        lines.append(f"  High Value (>$100): {stats.get('high_value', 0)}")
        lines.append(f"  Whales (>$10k): {stats.get('whales', 0)}")
        lines.append(f"  Общая стоимость: ${stats.get('total_value_usd', 0):,.2f}")
        
        # Топ находки
        found = results.get("found_accounts", [])
        if found:
            lines.append(f"\n💎 ТОП-10 НАХОДОК:")
            
            sorted_found = sorted(
                found,
                key=lambda x: x.get("balance_info", {}).get("total_usd", 0),
                reverse=True
            )
            
            for i, account in enumerate(sorted_found[:10], 1):
                auth_type = account.get("auth_data", {}).get("type", "unknown")
                balance = account.get("balance_info", {}).get("total_usd", 0)
                address = account.get("auth_data", {}).get("address", "")[:20]
                
                lines.append(f"\n  {i}. {address}...")
                lines.append(f"     Баланс: ${balance:,.2f}")
                lines.append(f"     Auth: {auth_type}")
        
        # Whales
        whales = results.get("whale_accounts", [])
        if whales:
            lines.append(f"\n🐋 WHALE АККАУНТЫ ({len(whales)}):")
            
            for whale in whales:
                balance = whale.get("balance_info", {}).get("total_usd", 0)
                auth_type = whale.get("auth_data", {}).get("type", "unknown")
                
                lines.append(f"  • ${balance:,.2f} ({auth_type})")
        
        return "\n".join(lines)
    
    def get_quick_access_list(self, accounts: List[Dict[str, Any]]) -> str:
        """Получить список для быстрого доступа"""
        
        lines = []
        
        lines.append("=" * 60)
        lines.append("🔐 БЫСТРЫЙ ДОСТУП К АККАУНТАМ")
        lines.append("=" * 60)
        lines.append("")
        
        for i, account in enumerate(accounts, 1):
            auth_data = account.get("auth_data", {})
            balance = account.get("balance_info", {}).get("total_usd", 0)
            
            auth_type = auth_data.get("type")
            
            if auth_type == "seed":
                lines.append(f"{i}. SEED | ${balance:,.2f}")
                lines.append(f"   {auth_data.get('data', '')}")
            
            elif auth_type == "privkey":
                lines.append(f"{i}. PRIVKEY | ${balance:,.2f}")
                lines.append(f"   {auth_data.get('data', '')}")
            
            elif auth_type == "email_password":
                data = auth_data.get('data', {})
                lines.append(f"{i}. EMAIL | ${balance:,.2f}")
                lines.append(f"   {data.get('email', '')}:{data.get('password', '')}")
            
            lines.append("")
        
        return "\n".join(lines)
