# -*- coding: utf-8 -*-
"""
Dump Parser v1.0.67
Парсинг дампов различных форматов
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class DumpParser:
    """Парсер дампов различных форматов"""
    
    # Регулярные выражения для определения типов данных
    EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    SEED_RE = re.compile(r'\b([a-z]+\s){11,23}[a-z]+\b', re.IGNORECASE)
    PRIVKEY_HEX_RE = re.compile(r'\b(0x)?[a-fA-F0-9]{64}\b')
    ETH_ADDRESS_RE = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
    BTC_ADDRESS_RE = re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b')
    
    # Разделители
    SEPARATORS = [':', '|', ';', '\t', ',']
    
    def __init__(self):
        self.stats = {
            "total_lines": 0,
            "parsed_lines": 0,
            "failed_lines": 0,
            "found_seeds": 0,
            "found_privkeys": 0,
            "found_addresses": 0,
            "found_credentials": 0,
        }
    
    def parse_dump(self, text: str) -> List[Dict[str, Any]]:
        """
        Парсит дамп и возвращает список распарсенных записей
        
        Args:
            text: Текст дампа (многострочный)
        
        Returns:
            Список словарей с распарсенными данными
        """
        
        results = []
        lines = text.strip().split('\n')
        
        self.stats["total_lines"] = len(lines)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parsed = self._parse_line(line)
            
            if parsed:
                results.append(parsed)
                self.stats["parsed_lines"] += 1
            else:
                self.stats["failed_lines"] += 1
        
        return results
    
    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Парсит одну строку дампа"""
        
        # Определяем разделитель
        separator = self._detect_separator(line)
        
        if separator:
            # Разбиваем по разделителю
            parts = [p.strip() for p in line.split(separator) if p.strip()]
        else:
            # Пробуем найти данные без разделителя
            parts = [line]
        
        # Пытаемся распарсить
        result = {
            "original": line,
            "email": None,
            "password": None,
            "seed": None,
            "privkey": None,
            "address": None,
            "extra": [],
        }
        
        # Ищем email
        email_match = self.EMAIL_RE.search(line)
        if email_match:
            result["email"] = email_match.group(0)
        
        # Ищем seed фразу
        seed_match = self.SEED_RE.search(line)
        if seed_match:
            seed = seed_match.group(0).strip()
            words = seed.split()
            if len(words) in [12, 15, 18, 21, 24]:
                result["seed"] = seed
                self.stats["found_seeds"] += 1
        
        # Ищем приватный ключ
        privkey_match = self.PRIVKEY_HEX_RE.search(line)
        if privkey_match:
            result["privkey"] = privkey_match.group(0)
            self.stats["found_privkeys"] += 1
        
        # Ищем адрес
        eth_match = self.ETH_ADDRESS_RE.search(line)
        if eth_match:
            result["address"] = eth_match.group(0)
            self.stats["found_addresses"] += 1
        else:
            btc_match = self.BTC_ADDRESS_RE.search(line)
            if btc_match:
                result["address"] = btc_match.group(0)
                self.stats["found_addresses"] += 1
        
        # Ищем пароль (всё что не email, не seed, не privkey, не address)
        if separator and len(parts) >= 2:
            for part in parts:
                part_clean = part.strip()
                
                # Пропускаем уже найденные данные
                if result["email"] and part_clean == result["email"]:
                    continue
                if result["seed"] and part_clean in result["seed"]:
                    continue
                if result["privkey"] and part_clean == result["privkey"]:
                    continue
                if result["address"] and part_clean == result["address"]:
                    continue
                
                # Если это похоже на пароль (не слишком длинное, не seed)
                if len(part_clean) > 3 and len(part_clean) < 100:
                    words = part_clean.split()
                    if len(words) < 5:  # Не seed фраза
                        if not result["password"]:
                            result["password"] = part_clean
                            if result["email"]:
                                self.stats["found_credentials"] += 1
                        else:
                            result["extra"].append(part_clean)
        
        # Проверяем что хоть что-то нашли
        if any([result["email"], result["seed"], result["privkey"], result["address"]]):
            return result
        
        return None
    
    def _detect_separator(self, line: str) -> Optional[str]:
        """Определяет разделитель в строке"""
        
        # Подсчитываем количество каждого разделителя
        counts = {}
        for sep in self.SEPARATORS:
            counts[sep] = line.count(sep)
        
        # Выбираем самый частый (если есть)
        max_count = max(counts.values())
        if max_count > 0:
            for sep, count in counts.items():
                if count == max_count:
                    return sep
        
        return None
    
    def extract_for_checker(self, parsed_data: List[Dict[str, Any]]) -> List[str]:
        """
        Извлекает данные для проверки чекером
        
        Args:
            parsed_data: Список распарсенных записей
        
        Returns:
            Список строк для проверки (seed, privkey, address)
        """
        
        results = []
        
        for item in parsed_data:
            # Приоритет: seed > privkey > address
            if item["seed"]:
                results.append(item["seed"])
            elif item["privkey"]:
                results.append(item["privkey"])
            elif item["address"]:
                results.append(item["address"])
        
        return results
    
    def format_for_display(self, parsed_data: List[Dict[str, Any]]) -> str:
        """Форматирует распарсенные данные для отображения"""
        
        lines = []
        
        lines.append("=" * 70)
        lines.append("📋 РЕЗУЛЬТАТЫ ПАРСИНГА ДАМПА")
        lines.append("=" * 70)
        lines.append("")
        
        lines.append(f"📊 Статистика:")
        lines.append(f"  Всего строк: {self.stats['total_lines']}")
        lines.append(f"  Распарсено: {self.stats['parsed_lines']}")
        lines.append(f"  Не удалось: {self.stats['failed_lines']}")
        lines.append(f"  Найдено seed: {self.stats['found_seeds']}")
        lines.append(f"  Найдено privkey: {self.stats['found_privkeys']}")
        lines.append(f"  Найдено адресов: {self.stats['found_addresses']}")
        lines.append(f"  Найдено credentials: {self.stats['found_credentials']}")
        lines.append("")
        
        lines.append("=" * 70)
        lines.append("📝 РАСПАРСЕННЫЕ ДАННЫЕ:")
        lines.append("=" * 70)
        lines.append("")
        
        for i, item in enumerate(parsed_data[:10], 1):  # Показываем первые 10
            lines.append(f"Запись #{i}:")
            
            if item["email"]:
                lines.append(f"  📧 Email: {item['email']}")
            
            if item["password"]:
                lines.append(f"  🔒 Password: {item['password']}")
            
            if item["seed"]:
                lines.append(f"  🌱 Seed: {item['seed'][:50]}...")
            
            if item["privkey"]:
                lines.append(f"  🔑 Privkey: {item['privkey'][:20]}...{item['privkey'][-10:]}")
            
            if item["address"]:
                lines.append(f"  📍 Address: {item['address']}")
            
            if item["extra"]:
                lines.append(f"  ℹ️ Extra: {', '.join(item['extra'][:3])}")
            
            lines.append("")
        
        if len(parsed_data) > 10:
            lines.append(f"... и еще {len(parsed_data) - 10} записей")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику парсинга"""
        return self.stats.copy()


# Примеры использования
def example_usage():
    """Примеры использования парсера"""
    
    parser = DumpParser()
    
    # Пример 1: email:password:seed
    dump1 = """
user1@mail.com:pass123:word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
user2@mail.com:pass456:0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
user3@mail.com:pass789:0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
"""
    
    # Пример 2: email|password|privkey|address
    dump2 = """
user1@mail.com|pass123|0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890|0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
user2@mail.com|pass456|word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12|0x123456789abcdef
"""
    
    # Пример 3: смешанный формат
    dump3 = """
email@test.com:password123
word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
user@mail.com:pass:0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
"""
    
    print("Пример 1: email:password:seed")
    print("=" * 70)
    parsed1 = parser.parse_dump(dump1)
    print(parser.format_for_display(parsed1))
    
    print("\n\nПример 2: email|password|privkey|address")
    print("=" * 70)
    parser2 = DumpParser()
    parsed2 = parser2.parse_dump(dump2)
    print(parser2.format_for_display(parsed2))
    
    print("\n\nПример 3: смешанный формат")
    print("=" * 70)
    parser3 = DumpParser()
    parsed3 = parser3.parse_dump(dump3)
    print(parser3.format_for_display(parsed3))
    
    # Извлекаем для чекера
    print("\n\nДанные для чекера:")
    print("=" * 70)
    for_checker = parser3.extract_for_checker(parsed3)
    for item in for_checker:
        print(item)


if __name__ == "__main__":
    example_usage()
