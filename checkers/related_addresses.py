# -*- coding: utf-8 -*-
"""
Related Addresses Finder v1.0.64
Поиск связанных адресов (один владелец)
"""

import re
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime


class RelatedAddressFinder:
    """Поиск связанных адресов и кошельков"""
    
    def __init__(self):
        self.address_groups = defaultdict(set)  # {group_id: {addresses}}
        self.address_to_group = {}  # {address: group_id}
        self.group_metadata = {}  # {group_id: metadata}
        self.next_group_id = 1
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Анализировать результаты и найти связанные адреса
        
        Args:
            results: Список результатов проверки
        
        Returns:
            Словарь с группами связанных адресов
        """
        
        # Очищаем предыдущие данные
        self.address_groups.clear()
        self.address_to_group.clear()
        self.group_metadata.clear()
        self.next_group_id = 1
        
        # 1. Группировка по seed фразе
        self._group_by_seed(results)
        
        # 2. Группировка по приватному ключу
        self._group_by_privkey(results)
        
        # 3. Группировка по email
        self._group_by_email(results)
        
        # 4. Группировка по паролю (одинаковые пароли)
        self._group_by_password(results)
        
        # 5. Группировка по паттернам адресов
        self._group_by_address_pattern(results)
        
        # 6. Группировка по времени создания (близкие по времени)
        self._group_by_creation_time(results)
        
        # Формируем отчет
        return self._generate_report()
    
    def _group_by_seed(self, results: List[Dict[str, Any]]):
        """Группировка по seed фразе"""
        
        seed_to_addresses = defaultdict(list)
        
        for result in results:
            seed = result.get("seed") or result.get("mnemonic") or result.get("phrase")
            address = result.get("address")
            
            if seed and address:
                # Нормализуем seed (убираем лишние пробелы)
                seed_normalized = " ".join(seed.split())
                seed_to_addresses[seed_normalized].append((address, result))
        
        # Создаем группы
        for seed, addr_list in seed_to_addresses.items():
            if len(addr_list) > 1:
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_seed",
                    metadata={
                        "seed": seed,
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
    
    def _group_by_privkey(self, results: List[Dict[str, Any]]):
        """Группировка по приватному ключу"""
        
        privkey_to_addresses = defaultdict(list)
        
        for result in results:
            privkey = result.get("privkey") or result.get("private_key") or result.get("key")
            address = result.get("address")
            
            if privkey and address:
                privkey_to_addresses[privkey].append((address, result))
        
        # Создаем группы
        for privkey, addr_list in privkey_to_addresses.items():
            if len(addr_list) > 1:
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_privkey",
                    metadata={
                        "privkey_preview": privkey[:10] + "..." + privkey[-10:] if len(privkey) > 20 else privkey,
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
    
    def _group_by_email(self, results: List[Dict[str, Any]]):
        """Группировка по email"""
        
        email_to_addresses = defaultdict(list)
        
        for result in results:
            email = result.get("email")
            address = result.get("address")
            
            if email and address:
                email_to_addresses[email.lower()].append((address, result))
        
        # Создаем группы
        for email, addr_list in email_to_addresses.items():
            if len(addr_list) > 1:
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_email",
                    metadata={
                        "email": email,
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
    
    def _group_by_password(self, results: List[Dict[str, Any]]):
        """Группировка по паролю (одинаковые пароли могут указывать на одного владельца)"""
        
        password_to_addresses = defaultdict(list)
        
        for result in results:
            password = result.get("password")
            address = result.get("address")
            
            if password and address and len(password) >= 8:  # Только длинные пароли
                password_to_addresses[password].append((address, result))
        
        # Создаем группы
        for password, addr_list in password_to_addresses.items():
            if len(addr_list) > 1:
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_password",
                    metadata={
                        "password_preview": password[:3] + "*" * (len(password) - 6) + password[-3:],
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
    
    def _group_by_address_pattern(self, results: List[Dict[str, Any]]):
        """Группировка по паттернам адресов (похожие адреса)"""
        
        # Ищем адреса с одинаковыми префиксами/суффиксами
        prefix_to_addresses = defaultdict(list)
        suffix_to_addresses = defaultdict(list)
        
        for result in results:
            address = result.get("address")
            
            if address and len(address) >= 20:
                # Префикс (первые 10 символов после 0x)
                if address.startswith("0x"):
                    prefix = address[:12]  # 0x + 10 символов
                    prefix_to_addresses[prefix].append((address, result))
                
                # Суффикс (последние 8 символов)
                suffix = address[-8:]
                suffix_to_addresses[suffix].append((address, result))
        
        # Создаем группы по префиксу
        for prefix, addr_list in prefix_to_addresses.items():
            if len(addr_list) >= 3:  # Минимум 3 адреса с одинаковым префиксом
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_prefix",
                    metadata={
                        "prefix": prefix,
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
        
        # Создаем группы по суффиксу
        for suffix, addr_list in suffix_to_addresses.items():
            if len(addr_list) >= 3:  # Минимум 3 адреса с одинаковым суффиксом
                group_id = self._create_group(
                    addresses=[addr for addr, _ in addr_list],
                    reason="same_suffix",
                    metadata={
                        "suffix": suffix,
                        "count": len(addr_list),
                        "results": [r for _, r in addr_list]
                    }
                )
    
    def _group_by_creation_time(self, results: List[Dict[str, Any]]):
        """Группировка по времени создания (близкие по времени могут быть связаны)"""
        
        # Сортируем по времени
        timed_results = []
        for result in results:
            timestamp = result.get("timestamp") or result.get("created_at")
            address = result.get("address")
            
            if timestamp and address:
                timed_results.append((timestamp, address, result))
        
        if not timed_results:
            return
        
        timed_results.sort(key=lambda x: x[0])
        
        # Ищем кластеры (адреса созданные в течение 1 минуты)
        TIME_THRESHOLD = 60  # секунд
        
        current_cluster = []
        last_timestamp = None
        
        for timestamp, address, result in timed_results:
            if last_timestamp is None or (timestamp - last_timestamp) <= TIME_THRESHOLD:
                current_cluster.append((address, result))
                last_timestamp = timestamp
            else:
                # Сохраняем текущий кластер
                if len(current_cluster) >= 2:
                    group_id = self._create_group(
                        addresses=[addr for addr, _ in current_cluster],
                        reason="close_creation_time",
                        metadata={
                            "time_range": f"{current_cluster[0][1].get('timestamp')} - {current_cluster[-1][1].get('timestamp')}",
                            "count": len(current_cluster),
                            "results": [r for _, r in current_cluster]
                        }
                    )
                
                # Начинаем новый кластер
                current_cluster = [(address, result)]
                last_timestamp = timestamp
        
        # Сохраняем последний кластер
        if len(current_cluster) >= 2:
            group_id = self._create_group(
                addresses=[addr for addr, _ in current_cluster],
                reason="close_creation_time",
                metadata={
                    "time_range": f"{current_cluster[0][1].get('timestamp')} - {current_cluster[-1][1].get('timestamp')}",
                    "count": len(current_cluster),
                    "results": [r for _, r in current_cluster]
                }
            )
    
    def _create_group(
        self,
        addresses: List[str],
        reason: str,
        metadata: Dict[str, Any]
    ) -> int:
        """Создать новую группу связанных адресов"""
        
        group_id = self.next_group_id
        self.next_group_id += 1
        
        # Добавляем адреса в группу
        for address in addresses:
            self.address_groups[group_id].add(address)
            self.address_to_group[address] = group_id
        
        # Сохраняем метаданные
        self.group_metadata[group_id] = {
            "reason": reason,
            "addresses": list(addresses),
            **metadata
        }
        
        return group_id
    
    def _generate_report(self) -> Dict[str, Any]:
        """Сгенерировать отчет о связанных адресах"""
        
        report = {
            "total_groups": len(self.address_groups),
            "total_addresses": len(self.address_to_group),
            "groups": [],
            "by_reason": defaultdict(int),
        }
        
        # Сортируем группы по размеру (от большей к меньшей)
        sorted_groups = sorted(
            self.address_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for group_id, addresses in sorted_groups:
            metadata = self.group_metadata.get(group_id, {})
            reason = metadata.get("reason", "unknown")
            
            # Считаем общий баланс группы
            total_balance = 0.0
            results = metadata.get("results", [])
            for result in results:
                balance_usd = result.get("balance_usd", 0)
                if balance_usd:
                    total_balance += float(balance_usd)
            
            group_info = {
                "group_id": group_id,
                "reason": reason,
                "reason_text": self._get_reason_text(reason),
                "addresses": list(addresses),
                "count": len(addresses),
                "total_balance_usd": total_balance,
                "metadata": {k: v for k, v in metadata.items() if k not in ["results"]}
            }
            
            report["groups"].append(group_info)
            report["by_reason"][reason] += 1
        
        return report
    
    def _get_reason_text(self, reason: str) -> str:
        """Получить текстовое описание причины связи"""
        
        reason_texts = {
            "same_seed": "Одна seed фраза",
            "same_privkey": "Один приватный ключ",
            "same_email": "Один email",
            "same_password": "Одинаковый пароль",
            "same_prefix": "Похожие адреса (префикс)",
            "same_suffix": "Похожие адреса (суффикс)",
            "close_creation_time": "Созданы в одно время",
        }
        
        return reason_texts.get(reason, reason)
    
    def export_to_txt(self, report: Dict[str, Any], output_file: str) -> bool:
        """Экспортировать отчет в TXT"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("СВЯЗАННЫЕ АДРЕСА - ОТЧЕТ\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Всего групп: {report['total_groups']}\n")
                f.write(f"Всего адресов: {report['total_addresses']}\n\n")
                
                # Статистика по причинам
                f.write("=" * 70 + "\n")
                f.write("СТАТИСТИКА ПО ТИПАМ СВЯЗЕЙ:\n")
                f.write("=" * 70 + "\n\n")
                
                for reason, count in sorted(report['by_reason'].items(), key=lambda x: x[1], reverse=True):
                    reason_text = self._get_reason_text(reason)
                    f.write(f"  • {reason_text}: {count} групп\n")
                
                f.write("\n" + "=" * 70 + "\n")
                f.write("ГРУППЫ СВЯЗАННЫХ АДРЕСОВ:\n")
                f.write("=" * 70 + "\n\n")
                
                # Группы
                for i, group in enumerate(report['groups'], 1):
                    f.write(f"{'=' * 70}\n")
                    f.write(f"ГРУППА #{i}\n")
                    f.write(f"{'=' * 70}\n\n")
                    
                    f.write(f"🔗 Причина связи: {group['reason_text']}\n")
                    f.write(f"📊 Количество адресов: {group['count']}\n")
                    f.write(f"💰 Общий баланс: ${group['total_balance_usd']:,.2f}\n\n")
                    
                    # Метаданные
                    metadata = group.get('metadata', {})
                    if metadata:
                        f.write("📋 Детали:\n")
                        for key, value in metadata.items():
                            if key not in ['results', 'addresses']:
                                f.write(f"  • {key}: {value}\n")
                        f.write("\n")
                    
                    # Адреса
                    f.write("📍 Адреса:\n")
                    for j, address in enumerate(group['addresses'], 1):
                        f.write(f"  {j}. {address}\n")
                    
                    f.write("\n\n")
            
            return True
        
        except Exception as e:
            print(f"Error exporting to TXT: {e}")
            return False
    
    def export_to_json(self, report: Dict[str, Any], output_file: str) -> bool:
        """Экспортировать отчет в JSON"""
        
        try:
            import json
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def get_related_addresses(self, address: str) -> Optional[List[str]]:
        """Получить все адреса связанные с данным адресом"""
        
        group_id = self.address_to_group.get(address)
        
        if group_id is None:
            return None
        
        return list(self.address_groups[group_id])
    
    def format_summary(self, report: Dict[str, Any], max_groups: int = 10) -> str:
        """Форматировать краткий отчет"""
        
        lines = []
        
        lines.append("🔗 СВЯЗАННЫЕ АДРЕСА - КРАТКИЙ ОТЧЕТ")
        lines.append("=" * 50)
        
        lines.append(f"\n📊 СТАТИСТИКА:")
        lines.append(f"  Всего групп: {report['total_groups']}")
        lines.append(f"  Всего адресов: {report['total_addresses']}")
        
        # По типам
        if report['by_reason']:
            lines.append(f"\n🔍 ПО ТИПАМ СВЯЗЕЙ:")
            for reason, count in sorted(report['by_reason'].items(), key=lambda x: x[1], reverse=True):
                reason_text = self._get_reason_text(reason)
                lines.append(f"  • {reason_text}: {count} групп")
        
        # Топ группы
        if report['groups']:
            lines.append(f"\n💎 ТОП-{max_groups} ГРУПП:")
            
            for i, group in enumerate(report['groups'][:max_groups], 1):
                lines.append(f"\n  {i}. {group['reason_text']}")
                lines.append(f"     Адресов: {group['count']}")
                lines.append(f"     Баланс: ${group['total_balance_usd']:,.2f}")
        
        return "\n".join(lines)
