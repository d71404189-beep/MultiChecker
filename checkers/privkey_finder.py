# -*- coding: utf-8 -*-
"""
Private Key Finder v1.0.62
Поиск приватных ключей в различных источниках
"""

import re
import os
import json
from typing import Dict, Any, Optional, List, Set
from pathlib import Path


class PrivateKeyFinder:
    """Поиск приватных ключей"""
    
    # Паттерны для поиска приватных ключей
    PATTERNS = {
        "hex_with_prefix": r"0x[a-fA-F0-9]{64}",
        "hex_without_prefix": r"\b[a-fA-F0-9]{64}\b",
        "wif_compressed": r"\b[KL][1-9A-HJ-NP-Za-km-z]{51}\b",
        "wif_uncompressed": r"\b5[1-9A-HJ-NP-Za-km-z]{50}\b",
        "base58": r"\b[1-9A-HJ-NP-Za-km-z]{44,88}\b",
    }
    
    # Ключевые слова для контекстного поиска
    CONTEXT_KEYWORDS = [
        "private", "privkey", "secret", "key", "wallet",
        "приватный", "ключ", "секрет", "кошелек",
        "mnemonic", "seed", "phrase", "мнемоника", "фраза",
        "password", "pass", "pwd", "пароль",
    ]
    
    def __init__(self):
        self.found_keys = []
        self.scanned_files = 0
        self.scanned_lines = 0
    
    def find_in_text(self, text: str, source: str = "text") -> List[Dict[str, Any]]:
        """
        Найти приватные ключи в тексте
        
        Args:
            text: Текст для поиска
            source: Источник текста
        
        Returns:
            Список найденных ключей
        """
        
        found = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            self.scanned_lines += 1
            
            # Проверяем каждый паттерн
            for key_type, pattern in self.PATTERNS.items():
                matches = re.finditer(pattern, line)
                
                for match in matches:
                    key = match.group(0)
                    
                    # Проверяем валидность
                    if self._is_valid_key(key, key_type):
                        # Проверяем контекст
                        has_context = self._check_context(line)
                        
                        found.append({
                            "key": key,
                            "type": key_type,
                            "source": source,
                            "line_number": line_num,
                            "context": line.strip(),
                            "has_context": has_context,
                            "confidence": "high" if has_context else "medium",
                        })
        
        self.found_keys.extend(found)
        return found
    
    def find_in_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Найти приватные ключи в файле
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            Список найденных ключей
        """
        
        self.scanned_files += 1
        
        try:
            # Определяем кодировку
            encodings = ['utf-8', 'cp1251', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Не удалось прочитать ни с одной кодировкой
                return []
            
            return self.find_in_text(text, source=file_path)
        
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []
    
    def find_in_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        max_files: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Найти приватные ключи в директории
        
        Args:
            directory: Путь к директории
            extensions: Расширения файлов для поиска (None = все текстовые)
            recursive: Рекурсивный поиск
            max_files: Максимум файлов для сканирования
        
        Returns:
            Список найденных ключей
        """
        
        if extensions is None:
            extensions = [
                '.txt', '.json', '.csv', '.log', '.conf', '.config',
                '.env', '.ini', '.yaml', '.yml', '.xml',
                '.js', '.py', '.java', '.cpp', '.c', '.h',
                '.md', '.html', '.sql', '.sh', '.bat',
            ]
        
        found = []
        files_scanned = 0
        
        path = Path(directory)
        
        if not path.exists():
            return []
        
        # Получаем список файлов
        if recursive:
            files = path.rglob('*')
        else:
            files = path.glob('*')
        
        for file_path in files:
            if files_scanned >= max_files:
                break
            
            if not file_path.is_file():
                continue
            
            # Проверяем расширение
            if file_path.suffix.lower() not in extensions:
                continue
            
            # Пропускаем большие файлы (> 10 MB)
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
            
            # Ищем в файле
            file_found = self.find_in_file(str(file_path))
            found.extend(file_found)
            
            files_scanned += 1
        
        return found
    
    def find_in_clipboard(self) -> List[Dict[str, Any]]:
        """
        Найти приватные ключи в буфере обмена
        
        Returns:
            Список найденных ключей
        """
        
        try:
            import pyperclip
            text = pyperclip.paste()
            return self.find_in_text(text, source="clipboard")
        except ImportError:
            print("pyperclip not installed. Install: pip install pyperclip")
            return []
        except Exception as e:
            print(f"Error reading clipboard: {e}")
            return []
    
    def find_in_browser_data(self) -> List[Dict[str, Any]]:
        """
        Найти приватные ключи в данных браузера
        (история, закладки, локальное хранилище)
        
        Returns:
            Список найденных ключей
        """
        
        found = []
        
        # Пути к данным браузеров
        browser_paths = self._get_browser_paths()
        
        for browser_name, paths in browser_paths.items():
            for path in paths:
                if os.path.exists(path):
                    # Ищем в файлах браузера
                    browser_found = self.find_in_directory(
                        path,
                        extensions=['.json', '.txt', '.log'],
                        recursive=True,
                        max_files=100
                    )
                    
                    # Помечаем источник
                    for item in browser_found:
                        item["browser"] = browser_name
                    
                    found.extend(browser_found)
        
        return found
    
    def _get_browser_paths(self) -> Dict[str, List[str]]:
        """Получить пути к данным браузеров"""
        
        home = str(Path.home())
        
        paths = {
            "Chrome": [
                os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data"),
            ],
            "Firefox": [
                os.path.join(home, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles"),
            ],
            "Edge": [
                os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data"),
            ],
            "Brave": [
                os.path.join(home, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data"),
            ],
        }
        
        return paths
    
    def _is_valid_key(self, key: str, key_type: str) -> bool:
        """Проверить валидность ключа"""
        
        # Базовые проверки
        if not key or len(key) < 32:
            return False
        
        # Проверка на паттерны-исключения
        # (например, все нули, все единицы)
        if key_type.startswith("hex"):
            hex_part = key.replace("0x", "")
            
            # Все нули
            if hex_part == "0" * len(hex_part):
                return False
            
            # Все F
            if hex_part.upper() == "F" * len(hex_part):
                return False
            
            # Слишком мало уникальных символов
            unique_chars = len(set(hex_part))
            if unique_chars < 10:
                return False
        
        return True
    
    def _check_context(self, line: str) -> bool:
        """Проверить контекст строки"""
        
        line_lower = line.lower()
        
        for keyword in self.CONTEXT_KEYWORDS:
            if keyword in line_lower:
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику поиска"""
        
        return {
            "scanned_files": self.scanned_files,
            "scanned_lines": self.scanned_lines,
            "found_keys": len(self.found_keys),
            "by_type": self._count_by_type(),
            "by_confidence": self._count_by_confidence(),
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Подсчитать по типам"""
        
        counts = {}
        for item in self.found_keys:
            key_type = item["type"]
            counts[key_type] = counts.get(key_type, 0) + 1
        
        return counts
    
    def _count_by_confidence(self) -> Dict[str, int]:
        """Подсчитать по уверенности"""
        
        counts = {}
        for item in self.found_keys:
            confidence = item["confidence"]
            counts[confidence] = counts.get(confidence, 0) + 1
        
        return counts
    
    def export_results(
        self,
        output_file: str,
        format: str = "json",
        include_keys: bool = True
    ) -> bool:
        """
        Экспортировать результаты
        
        Args:
            output_file: Путь к файлу
            format: Формат (json, txt, csv)
            include_keys: Включать ли сами ключи
        
        Returns:
            True если успешно
        """
        
        try:
            if format == "json":
                data = {
                    "statistics": self.get_statistics(),
                    "results": self.found_keys if include_keys else [],
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            elif format == "txt":
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("PRIVATE KEY FINDER RESULTS\n")
                    f.write("=" * 50 + "\n\n")
                    
                    stats = self.get_statistics()
                    f.write(f"Scanned Files: {stats['scanned_files']}\n")
                    f.write(f"Scanned Lines: {stats['scanned_lines']}\n")
                    f.write(f"Found Keys: {stats['found_keys']}\n\n")
                    
                    if include_keys:
                        f.write("FOUND KEYS:\n")
                        f.write("-" * 50 + "\n\n")
                        
                        for i, item in enumerate(self.found_keys, 1):
                            f.write(f"{i}. Type: {item['type']}\n")
                            f.write(f"   Key: {item['key']}\n")
                            f.write(f"   Source: {item['source']}\n")
                            f.write(f"   Line: {item['line_number']}\n")
                            f.write(f"   Confidence: {item['confidence']}\n")
                            f.write(f"   Context: {item['context'][:100]}...\n\n")
            
            elif format == "csv":
                import csv
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if include_keys and self.found_keys:
                        fieldnames = self.found_keys[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        
                        writer.writeheader()
                        writer.writerows(self.found_keys)
            
            return True
        
        except Exception as e:
            print(f"Error exporting results: {e}")
            return False
    
    def format_report(self, max_results: int = 10) -> str:
        """Форматировать отчет"""
        
        lines = []
        
        lines.append("🔍 PRIVATE KEY FINDER REPORT")
        lines.append("=" * 50)
        
        # Статистика
        stats = self.get_statistics()
        lines.append(f"\n📊 STATISTICS:")
        lines.append(f"  Scanned Files: {stats['scanned_files']}")
        lines.append(f"  Scanned Lines: {stats['scanned_lines']}")
        lines.append(f"  Found Keys: {stats['found_keys']}")
        
        # По типам
        by_type = stats.get("by_type", {})
        if by_type:
            lines.append(f"\n📋 BY TYPE:")
            for key_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  • {key_type}: {count}")
        
        # По уверенности
        by_confidence = stats.get("by_confidence", {})
        if by_confidence:
            lines.append(f"\n🎯 BY CONFIDENCE:")
            for confidence, count in sorted(by_confidence.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  • {confidence}: {count}")
        
        # Результаты
        if self.found_keys:
            lines.append(f"\n🔑 FOUND KEYS (showing first {max_results}):")
            
            for i, item in enumerate(self.found_keys[:max_results], 1):
                key_type = item["type"]
                key = item["key"]
                source = item["source"]
                confidence = item["confidence"]
                
                # Маскируем ключ
                if len(key) > 20:
                    masked_key = key[:10] + "..." + key[-10:]
                else:
                    masked_key = key[:5] + "..." + key[-5:]
                
                conf_icon = "🔴" if confidence == "high" else "🟡"
                
                lines.append(f"\n  {i}. {conf_icon} {key_type}")
                lines.append(f"     Key: {masked_key}")
                lines.append(f"     Source: {source}")
                lines.append(f"     Confidence: {confidence}")
        
        return "\n".join(lines)


class SmartKeyExtractor:
    """Умный экстрактор ключей с дополнительными возможностями"""
    
    def __init__(self):
        self.finder = PrivateKeyFinder()
    
    def extract_from_metamask_backup(self, backup_file: str) -> List[Dict[str, Any]]:
        """
        Извлечь ключи из бэкапа MetaMask
        
        Args:
            backup_file: Путь к файлу бэкапа
        
        Returns:
            Список найденных ключей
        """
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # MetaMask хранит зашифрованные данные
            # Здесь нужна расшифровка, но для примера просто ищем паттерны
            text = json.dumps(data)
            
            return self.finder.find_in_text(text, source=f"metamask_backup:{backup_file}")
        
        except Exception as e:
            print(f"Error reading MetaMask backup: {e}")
            return []
    
    def extract_from_wallet_dat(self, wallet_file: str) -> List[Dict[str, Any]]:
        """
        Извлечь ключи из wallet.dat (Bitcoin Core)
        
        Args:
            wallet_file: Путь к wallet.dat
        
        Returns:
            Список найденных ключей
        """
        
        # wallet.dat - бинарный файл, требует специальной обработки
        # Для примера просто пытаемся найти паттерны
        
        try:
            with open(wallet_file, 'rb') as f:
                data = f.read()
            
            # Конвертируем в hex и ищем паттерны
            hex_data = data.hex()
            
            return self.finder.find_in_text(hex_data, source=f"wallet_dat:{wallet_file}")
        
        except Exception as e:
            print(f"Error reading wallet.dat: {e}")
            return []
    
    def extract_from_keystore(self, keystore_file: str, password: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Извлечь ключи из keystore файла (Ethereum)
        
        Args:
            keystore_file: Путь к keystore файлу
            password: Пароль для расшифровки (опционально)
        
        Returns:
            Список найденных ключей
        """
        
        try:
            with open(keystore_file, 'r', encoding='utf-8') as f:
                keystore = json.load(f)
            
            # Keystore содержит зашифрованный приватный ключ
            # Для расшифровки нужен пароль
            
            if password:
                # Здесь должна быть логика расшифровки
                # Для примера просто возвращаем информацию
                return [{
                    "key": "encrypted",
                    "type": "keystore",
                    "source": keystore_file,
                    "address": keystore.get("address", "unknown"),
                    "needs_password": True,
                }]
            else:
                # Без пароля просто ищем паттерны в JSON
                text = json.dumps(keystore)
                return self.finder.find_in_text(text, source=f"keystore:{keystore_file}")
        
        except Exception as e:
            print(f"Error reading keystore: {e}")
            return []
    
    def extract_from_mnemonic(self, mnemonic: str, derivation_path: str = "m/44'/60'/0'/0/0") -> Dict[str, Any]:
        """
        Извлечь приватный ключ из мнемонической фразы
        
        Args:
            mnemonic: Мнемоническая фраза (12/24 слова)
            derivation_path: Путь деривации
        
        Returns:
            Информация о ключе
        """
        
        # Для полной реализации нужна библиотека bip32/bip39
        # Здесь просто пример структуры
        
        words = mnemonic.strip().split()
        
        if len(words) not in [12, 15, 18, 21, 24]:
            return {
                "valid": False,
                "error": "Invalid mnemonic length",
            }
        
        return {
            "valid": True,
            "mnemonic": mnemonic,
            "word_count": len(words),
            "derivation_path": derivation_path,
            "note": "Use proper BIP39/BIP32 library for actual key derivation",
        }
    
    def scan_common_locations(self) -> List[Dict[str, Any]]:
        """
        Сканировать общие места хранения ключей
        
        Returns:
            Список найденных ключей
        """
        
        found = []
        home = str(Path.home())
        
        # Общие места
        common_locations = [
            # Desktop
            os.path.join(home, "Desktop"),
            
            # Documents
            os.path.join(home, "Documents"),
            
            # Downloads
            os.path.join(home, "Downloads"),
            
            # Crypto wallets
            os.path.join(home, ".ethereum"),
            os.path.join(home, "AppData", "Roaming", "Ethereum"),
            os.path.join(home, "AppData", "Roaming", "Bitcoin"),
            
            # Browser extensions
            os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Local Extension Settings"),
        ]
        
        for location in common_locations:
            if os.path.exists(location):
                location_found = self.finder.find_in_directory(
                    location,
                    recursive=True,
                    max_files=100
                )
                found.extend(location_found)
        
        return found


class KeyValidator:
    """Валидатор приватных ключей"""
    
    @staticmethod
    def validate_ethereum_key(key: str) -> Dict[str, Any]:
        """Валидировать Ethereum приватный ключ"""
        
        # Убираем 0x если есть
        if key.startswith("0x"):
            key = key[2:]
        
        result = {
            "valid": False,
            "format": "ethereum",
            "issues": [],
        }
        
        # Проверка длины
        if len(key) != 64:
            result["issues"].append(f"Invalid length: {len(key)} (expected 64)")
            return result
        
        # Проверка hex
        try:
            int(key, 16)
        except ValueError:
            result["issues"].append("Not a valid hex string")
            return result
        
        # Проверка диапазона
        key_int = int(key, 16)
        if key_int == 0:
            result["issues"].append("Key is zero")
            return result
        
        # Максимальное значение для secp256k1
        max_key = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140", 16)
        if key_int >= max_key:
            result["issues"].append("Key exceeds secp256k1 curve order")
            return result
        
        result["valid"] = True
        return result
    
    @staticmethod
    def validate_bitcoin_wif(wif: str) -> Dict[str, Any]:
        """Валидировать Bitcoin WIF ключ"""
        
        result = {
            "valid": False,
            "format": "bitcoin_wif",
            "compressed": False,
            "issues": [],
        }
        
        # Проверка длины
        if len(wif) == 51:
            result["compressed"] = True
        elif len(wif) == 52:
            result["compressed"] = False
        else:
            result["issues"].append(f"Invalid length: {len(wif)}")
            return result
        
        # Проверка первого символа
        if wif[0] not in ['5', 'K', 'L']:
            result["issues"].append(f"Invalid prefix: {wif[0]}")
            return result
        
        result["valid"] = True
        return result
