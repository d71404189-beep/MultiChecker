# -*- coding: utf-8 -*-
"""
Email Domain Grouper v1.0.64
Группировка по email доменам
"""

import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime


class EmailDomainGrouper:
    """Группировка аккаунтов по email доменам"""
    
    def __init__(self):
        self.domain_groups = defaultdict(list)  # {domain: [results]}
        self.email_to_result = {}  # {email: result}
        self.statistics = {}
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Анализировать результаты и сгруппировать по доменам
        
        Args:
            results: Список результатов проверки
        
        Returns:
            Словарь с группами по доменам
        """
        
        # Очищаем предыдущие данные
        self.domain_groups.clear()
        self.email_to_result.clear()
        
        # Группируем по доменам
        for result in results:
            email = result.get("email")
            
            if not email:
                continue
            
            # Извлекаем домен
            domain = self._extract_domain(email)
            
            if domain:
                self.domain_groups[domain].append(result)
                self.email_to_result[email.lower()] = result
        
        # Вычисляем статистику
        self._calculate_statistics()
        
        # Формируем отчет
        return self._generate_report()
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """Извлечь домен из email"""
        
        try:
            # Нормализуем email
            email = email.lower().strip()
            
            # Проверяем формат
            if "@" not in email:
                return None
            
            # Извлекаем домен
            domain = email.split("@")[1]
            
            # Убираем лишние символы
            domain = domain.strip()
            
            return domain
        
        except Exception:
            return None
    
    def _calculate_statistics(self):
        """Вычислить статистику по доменам"""
        
        self.statistics = {}
        
        for domain, results in self.domain_groups.items():
            # Считаем балансы
            total_balance = 0.0
            with_balance = 0
            valid_count = 0
            
            for result in results:
                # Баланс
                balance_usd = result.get("balance_usd", 0)
                if balance_usd:
                    total_balance += float(balance_usd)
                    with_balance += 1
                
                # Валидность
                if result.get("exists") or result.get("valid"):
                    valid_count += 1
            
            self.statistics[domain] = {
                "total_accounts": len(results),
                "valid_accounts": valid_count,
                "with_balance": with_balance,
                "total_balance_usd": total_balance,
                "avg_balance_usd": total_balance / with_balance if with_balance > 0 else 0,
            }
    
    def _generate_report(self) -> Dict[str, Any]:
        """Сгенерировать отчет"""
        
        report = {
            "total_domains": len(self.domain_groups),
            "total_emails": len(self.email_to_result),
            "domains": [],
            "top_domains": [],
            "statistics": {
                "total_balance_usd": 0.0,
                "total_valid": 0,
                "total_with_balance": 0,
            }
        }
        
        # Сортируем домены по количеству аккаунтов
        sorted_domains = sorted(
            self.domain_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for domain, results in sorted_domains:
            stats = self.statistics.get(domain, {})
            
            domain_info = {
                "domain": domain,
                "total_accounts": len(results),
                "valid_accounts": stats.get("valid_accounts", 0),
                "with_balance": stats.get("with_balance", 0),
                "total_balance_usd": stats.get("total_balance_usd", 0),
                "avg_balance_usd": stats.get("avg_balance_usd", 0),
                "domain_type": self._classify_domain(domain),
                "emails": [r.get("email") for r in results if r.get("email")],
            }
            
            report["domains"].append(domain_info)
            
            # Обновляем общую статистику
            report["statistics"]["total_balance_usd"] += domain_info["total_balance_usd"]
            report["statistics"]["total_valid"] += domain_info["valid_accounts"]
            report["statistics"]["total_with_balance"] += domain_info["with_balance"]
        
        # Топ-10 доменов по балансу
        report["top_domains"] = sorted(
            report["domains"],
            key=lambda x: x["total_balance_usd"],
            reverse=True
        )[:10]
        
        return report
    
    def _classify_domain(self, domain: str) -> str:
        """Классифицировать домен"""
        
        # Популярные почтовые сервисы
        popular_providers = {
            "gmail.com": "Gmail",
            "yahoo.com": "Yahoo",
            "outlook.com": "Outlook",
            "hotmail.com": "Hotmail",
            "icloud.com": "iCloud",
            "mail.ru": "Mail.ru",
            "yandex.ru": "Yandex",
            "protonmail.com": "ProtonMail",
            "aol.com": "AOL",
            "zoho.com": "Zoho",
        }
        
        if domain in popular_providers:
            return f"Popular ({popular_providers[domain]})"
        
        # Временные email
        temp_domains = [
            "tempmail", "guerrillamail", "10minutemail", "throwaway",
            "mailinator", "maildrop", "temp-mail"
        ]
        
        if any(temp in domain for temp in temp_domains):
            return "Temporary"
        
        # Корпоративные (содержат название компании)
        if any(corp in domain for corp in ["company", "corp", "inc", "ltd"]):
            return "Corporate"
        
        # Образовательные
        if domain.endswith(".edu") or "university" in domain or "college" in domain:
            return "Educational"
        
        # Правительственные
        if domain.endswith(".gov") or "government" in domain:
            return "Government"
        
        # Кастомные домены
        return "Custom"
    
    def export_to_txt(self, report: Dict[str, Any], output_file: str) -> bool:
        """Экспортировать отчет в TXT"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("ГРУППИРОВКА ПО EMAIL ДОМЕНАМ - ОТЧЕТ\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Всего доменов: {report['total_domains']}\n")
                f.write(f"Всего email: {report['total_emails']}\n\n")
                
                # Общая статистика
                stats = report["statistics"]
                f.write("=" * 70 + "\n")
                f.write("ОБЩАЯ СТАТИСТИКА:\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"  💰 Общий баланс: ${stats['total_balance_usd']:,.2f}\n")
                f.write(f"  ✅ Валидных аккаунтов: {stats['total_valid']}\n")
                f.write(f"  💵 С балансом: {stats['total_with_balance']}\n\n")
                
                # Топ-10 доменов
                f.write("=" * 70 + "\n")
                f.write("ТОП-10 ДОМЕНОВ ПО БАЛАНСУ:\n")
                f.write("=" * 70 + "\n\n")
                
                for i, domain_info in enumerate(report['top_domains'], 1):
                    f.write(f"{i}. {domain_info['domain']}\n")
                    f.write(f"   Тип: {domain_info['domain_type']}\n")
                    f.write(f"   Аккаунтов: {domain_info['total_accounts']}\n")
                    f.write(f"   Валидных: {domain_info['valid_accounts']}\n")
                    f.write(f"   С балансом: {domain_info['with_balance']}\n")
                    f.write(f"   Баланс: ${domain_info['total_balance_usd']:,.2f}\n")
                    f.write(f"   Средний баланс: ${domain_info['avg_balance_usd']:,.2f}\n\n")
                
                # Все домены
                f.write("=" * 70 + "\n")
                f.write("ВСЕ ДОМЕНЫ:\n")
                f.write("=" * 70 + "\n\n")
                
                for domain_info in report['domains']:
                    f.write(f"{'=' * 70}\n")
                    f.write(f"ДОМЕН: {domain_info['domain']}\n")
                    f.write(f"{'=' * 70}\n\n")
                    
                    f.write(f"📊 Тип: {domain_info['domain_type']}\n")
                    f.write(f"📧 Всего аккаунтов: {domain_info['total_accounts']}\n")
                    f.write(f"✅ Валидных: {domain_info['valid_accounts']}\n")
                    f.write(f"💰 С балансом: {domain_info['with_balance']}\n")
                    f.write(f"💵 Общий баланс: ${domain_info['total_balance_usd']:,.2f}\n")
                    f.write(f"📈 Средний баланс: ${domain_info['avg_balance_usd']:,.2f}\n\n")
                    
                    # Email адреса
                    f.write("📧 Email адреса:\n")
                    for j, email in enumerate(domain_info['emails'][:20], 1):  # Первые 20
                        f.write(f"  {j}. {email}\n")
                    
                    if len(domain_info['emails']) > 20:
                        f.write(f"  ... и еще {len(domain_info['emails']) - 20} email\n")
                    
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
    
    def export_by_domain(
        self,
        domain: str,
        output_file: str,
        format_type: str = "txt"
    ) -> bool:
        """
        Экспортировать аккаунты конкретного домена
        
        Args:
            domain: Домен для экспорта
            output_file: Путь к файлу
            format_type: Формат (txt, json, csv)
        
        Returns:
            True если успешно
        """
        
        results = self.domain_groups.get(domain, [])
        
        if not results:
            return False
        
        try:
            if format_type == "txt":
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"АККАУНТЫ ДОМЕНА: {domain}\n")
                    f.write("=" * 70 + "\n\n")
                    
                    for i, result in enumerate(results, 1):
                        email = result.get("email", "N/A")
                        password = result.get("password", "N/A")
                        balance = result.get("balance_usd", 0)
                        
                        f.write(f"{i}. {email}:{password}\n")
                        if balance > 0:
                            f.write(f"   Баланс: ${balance:,.2f}\n")
                        f.write("\n")
            
            elif format_type == "json":
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
            
            elif format_type == "csv":
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Email', 'Password', 'Balance USD', 'Valid'])
                    
                    for result in results:
                        writer.writerow([
                            result.get("email", ""),
                            result.get("password", ""),
                            result.get("balance_usd", 0),
                            result.get("exists", False)
                        ])
            
            return True
        
        except Exception as e:
            print(f"Error exporting domain: {e}")
            return False
    
    def format_summary(self, report: Dict[str, Any], max_domains: int = 10) -> str:
        """Форматировать краткий отчет"""
        
        lines = []
        
        lines.append("📧 ГРУППИРОВКА ПО EMAIL ДОМЕНАМ")
        lines.append("=" * 50)
        
        lines.append(f"\n📊 СТАТИСТИКА:")
        lines.append(f"  Всего доменов: {report['total_domains']}")
        lines.append(f"  Всего email: {report['total_emails']}")
        
        stats = report["statistics"]
        lines.append(f"  Общий баланс: ${stats['total_balance_usd']:,.2f}")
        lines.append(f"  Валидных: {stats['total_valid']}")
        lines.append(f"  С балансом: {stats['total_with_balance']}")
        
        # Топ домены
        if report['top_domains']:
            lines.append(f"\n💎 ТОП-{max_domains} ДОМЕНОВ:")
            
            for i, domain_info in enumerate(report['top_domains'][:max_domains], 1):
                lines.append(f"\n  {i}. {domain_info['domain']} ({domain_info['domain_type']})")
                lines.append(f"     Аккаунтов: {domain_info['total_accounts']}")
                lines.append(f"     Баланс: ${domain_info['total_balance_usd']:,.2f}")
        
        return "\n".join(lines)
