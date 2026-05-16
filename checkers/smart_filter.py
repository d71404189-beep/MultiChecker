# -*- coding: utf-8 -*-
"""
Smart Filter v1.0.64
Умная фильтрация результатов
"""

import re
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


class SmartFilter:
    """Умная фильтрация результатов проверки"""
    
    def __init__(self):
        self.filters = []
        self.saved_filters = {}
    
    def filter_results(
        self,
        results: List[Dict[str, Any]],
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Фильтровать результаты
        
        Args:
            results: Список результатов
            filters: Список фильтров для применения
        
        Returns:
            Отфильтрованный список
        """
        
        if not filters:
            filters = self.filters
        
        filtered = results
        
        for filter_config in filters:
            filter_type = filter_config.get("type")
            
            if filter_type == "balance":
                filtered = self._filter_by_balance(filtered, filter_config)
            elif filter_type == "network":
                filtered = self._filter_by_network(filtered, filter_config)
            elif filter_type == "auth_type":
                filtered = self._filter_by_auth_type(filtered, filter_config)
            elif filter_type == "platform":
                filtered = self._filter_by_platform(filtered, filter_config)
            elif filter_type == "email_domain":
                filtered = self._filter_by_email_domain(filtered, filter_config)
            elif filter_type == "validity":
                filtered = self._filter_by_validity(filtered, filter_config)
            elif filter_type == "date":
                filtered = self._filter_by_date(filtered, filter_config)
            elif filter_type == "custom":
                filtered = self._filter_custom(filtered, filter_config)
        
        return filtered
    
    def _filter_by_balance(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по балансу"""
        
        min_balance = config.get("min", 0)
        max_balance = config.get("max", float('inf'))
        
        filtered = []
        
        for result in results:
            balance = result.get("balance_usd", 0)
            
            if balance is None:
                balance = 0
            
            balance = float(balance)
            
            if min_balance <= balance <= max_balance:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_network(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по сети/блокчейну"""
        
        networks = config.get("networks", [])
        
        if not networks:
            return results
        
        # Нормализуем названия сетей
        networks_lower = [n.lower() for n in networks]
        
        filtered = []
        
        for result in results:
            network = result.get("network") or result.get("chain") or result.get("blockchain")
            
            if network and network.lower() in networks_lower:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_auth_type(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по типу авторизации"""
        
        auth_types = config.get("auth_types", [])
        
        if not auth_types:
            return results
        
        filtered = []
        
        for result in results:
            # Определяем тип авторизации
            has_seed = bool(result.get("seed") or result.get("mnemonic") or result.get("phrase"))
            has_privkey = bool(result.get("privkey") or result.get("private_key") or result.get("key"))
            has_email_pass = bool(result.get("email") and result.get("password"))
            has_api_keys = bool(result.get("api_key") and result.get("api_secret"))
            
            if "seed" in auth_types and has_seed:
                filtered.append(result)
            elif "privkey" in auth_types and has_privkey:
                filtered.append(result)
            elif "email_password" in auth_types and has_email_pass:
                filtered.append(result)
            elif "api_keys" in auth_types and has_api_keys:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_platform(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по платформе"""
        
        platforms = config.get("platforms", [])
        
        if not platforms:
            return results
        
        platforms_lower = [p.lower() for p in platforms]
        
        filtered = []
        
        for result in results:
            platform = result.get("platform") or result.get("wallet_type") or result.get("service")
            
            if platform and platform.lower() in platforms_lower:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_email_domain(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по email домену"""
        
        domains = config.get("domains", [])
        
        if not domains:
            return results
        
        domains_lower = [d.lower() for d in domains]
        
        filtered = []
        
        for result in results:
            email = result.get("email")
            
            if email and "@" in email:
                domain = email.split("@")[1].lower()
                
                if domain in domains_lower:
                    filtered.append(result)
        
        return filtered
    
    def _filter_by_validity(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по валидности"""
        
        valid_only = config.get("valid_only", False)
        invalid_only = config.get("invalid_only", False)
        
        if not valid_only and not invalid_only:
            return results
        
        filtered = []
        
        for result in results:
            is_valid = result.get("exists") or result.get("valid")
            
            if valid_only and is_valid:
                filtered.append(result)
            elif invalid_only and not is_valid:
                filtered.append(result)
        
        return filtered
    
    def _filter_by_date(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Фильтр по дате"""
        
        from_date = config.get("from")
        to_date = config.get("to")
        
        if not from_date and not to_date:
            return results
        
        filtered = []
        
        for result in results:
            timestamp = result.get("timestamp") or result.get("created_at") or result.get("checked_at")
            
            if not timestamp:
                continue
            
            # Конвертируем в datetime если нужно
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except:
                    continue
            
            # Проверяем диапазон
            if from_date and timestamp < from_date:
                continue
            
            if to_date and timestamp > to_date:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _filter_custom(
        self,
        results: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Кастомный фильтр"""
        
        field = config.get("field")
        operator = config.get("operator")
        value = config.get("value")
        
        if not field or not operator:
            return results
        
        filtered = []
        
        for result in results:
            field_value = result.get(field)
            
            if field_value is None:
                continue
            
            # Применяем оператор
            if operator == "equals":
                if field_value == value:
                    filtered.append(result)
            
            elif operator == "not_equals":
                if field_value != value:
                    filtered.append(result)
            
            elif operator == "contains":
                if value in str(field_value):
                    filtered.append(result)
            
            elif operator == "not_contains":
                if value not in str(field_value):
                    filtered.append(result)
            
            elif operator == "starts_with":
                if str(field_value).startswith(value):
                    filtered.append(result)
            
            elif operator == "ends_with":
                if str(field_value).endswith(value):
                    filtered.append(result)
            
            elif operator == "greater_than":
                try:
                    if float(field_value) > float(value):
                        filtered.append(result)
                except:
                    pass
            
            elif operator == "less_than":
                try:
                    if float(field_value) < float(value):
                        filtered.append(result)
                except:
                    pass
            
            elif operator == "regex":
                if re.search(value, str(field_value)):
                    filtered.append(result)
        
        return filtered
    
    def add_filter(self, filter_config: Dict[str, Any]):
        """Добавить фильтр"""
        self.filters.append(filter_config)
    
    def clear_filters(self):
        """Очистить все фильтры"""
        self.filters.clear()
    
    def save_filter(self, name: str, filters: List[Dict[str, Any]]):
        """Сохранить набор фильтров"""
        self.saved_filters[name] = filters
    
    def load_filter(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Загрузить сохраненный набор фильтров"""
        return self.saved_filters.get(name)
    
    def get_filter_presets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получить предустановленные фильтры"""
        
        return {
            "high_balance": [
                {"type": "balance", "min": 1000},
                {"type": "validity", "valid_only": True}
            ],
            
            "medium_balance": [
                {"type": "balance", "min": 100, "max": 1000},
                {"type": "validity", "valid_only": True}
            ],
            
            "low_balance": [
                {"type": "balance", "min": 1, "max": 100},
                {"type": "validity", "valid_only": True}
            ],
            
            "with_seed": [
                {"type": "auth_type", "auth_types": ["seed"]},
                {"type": "validity", "valid_only": True}
            ],
            
            "with_privkey": [
                {"type": "auth_type", "auth_types": ["privkey"]},
                {"type": "validity", "valid_only": True}
            ],
            
            "ethereum": [
                {"type": "network", "networks": ["ethereum", "eth"]},
                {"type": "validity", "valid_only": True}
            ],
            
            "bsc": [
                {"type": "network", "networks": ["bsc", "binance smart chain"]},
                {"type": "validity", "valid_only": True}
            ],
            
            "popular_emails": [
                {"type": "email_domain", "domains": ["gmail.com", "yahoo.com", "outlook.com"]},
                {"type": "validity", "valid_only": True}
            ],
            
            "valid_only": [
                {"type": "validity", "valid_only": True}
            ],
            
            "invalid_only": [
                {"type": "validity", "invalid_only": True}
            ],
        }
    
    def format_filter_summary(self, filters: List[Dict[str, Any]]) -> str:
        """Форматировать описание фильтров"""
        
        lines = []
        
        for i, filter_config in enumerate(filters, 1):
            filter_type = filter_config.get("type")
            
            if filter_type == "balance":
                min_bal = filter_config.get("min", 0)
                max_bal = filter_config.get("max", "∞")
                lines.append(f"{i}. Баланс: ${min_bal} - ${max_bal}")
            
            elif filter_type == "network":
                networks = ", ".join(filter_config.get("networks", []))
                lines.append(f"{i}. Сети: {networks}")
            
            elif filter_type == "auth_type":
                auth_types = ", ".join(filter_config.get("auth_types", []))
                lines.append(f"{i}. Тип авторизации: {auth_types}")
            
            elif filter_type == "platform":
                platforms = ", ".join(filter_config.get("platforms", []))
                lines.append(f"{i}. Платформы: {platforms}")
            
            elif filter_type == "email_domain":
                domains = ", ".join(filter_config.get("domains", []))
                lines.append(f"{i}. Email домены: {domains}")
            
            elif filter_type == "validity":
                if filter_config.get("valid_only"):
                    lines.append(f"{i}. Только валидные")
                elif filter_config.get("invalid_only"):
                    lines.append(f"{i}. Только невалидные")
            
            elif filter_type == "custom":
                field = filter_config.get("field")
                operator = filter_config.get("operator")
                value = filter_config.get("value")
                lines.append(f"{i}. {field} {operator} {value}")
        
        return "\n".join(lines) if lines else "Нет активных фильтров"
