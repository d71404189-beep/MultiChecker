# -*- coding: utf-8 -*-
"""
Private Key Formats v1.0.59
Проверка приватных ключей разных форматов с автоопределением
"""

import re
import base58
import hashlib
from typing import Dict, Any, Optional, Tuple


class PrivateKeyFormats:
    """Работа с приватными ключами разных форматов"""
    
    # Паттерны для определения форматов
    PATTERNS = {
        "hex_with_prefix": re.compile(r'^0x[a-fA-F0-9]{64}$'),
        "hex_without_prefix": re.compile(r'^[a-fA-F0-9]{64}$'),
        "wif_compressed": re.compile(r'^[KL][1-9A-HJ-NP-Za-km-z]{51}$'),
        "wif_uncompressed": re.compile(r'^5[1-9A-HJ-NP-Za-km-z]{50}$'),
        "base58": re.compile(r'^[1-9A-HJ-NP-Za-km-z]{44,88}$'),
    }
    
    def detect_format(self, privkey: str) -> Optional[str]:
        """
        Определить формат приватного ключа
        
        Args:
            privkey: Приватный ключ
        
        Returns:
            Название формата или None
        """
        
        privkey = privkey.strip()
        
        # Проверяем каждый паттерн
        for format_name, pattern in self.PATTERNS.items():
            if pattern.match(privkey):
                return format_name
        
        return None
    
    def convert_to_hex(self, privkey: str, format_type: Optional[str] = None) -> Optional[str]:
        """
        Конвертировать приватный ключ в HEX формат
        
        Args:
            privkey: Приватный ключ
            format_type: Тип формата (если известен)
        
        Returns:
            HEX строка (64 символа) или None
        """
        
        privkey = privkey.strip()
        
        # Автоопределение формата если не указан
        if format_type is None:
            format_type = self.detect_format(privkey)
        
        if format_type is None:
            return None
        
        try:
            if format_type == "hex_with_prefix":
                # Убираем 0x
                return privkey[2:].lower()
            
            elif format_type == "hex_without_prefix":
                return privkey.lower()
            
            elif format_type in ["wif_compressed", "wif_uncompressed"]:
                # Декодируем WIF
                decoded = base58.b58decode_check(privkey)
                # Первый байт - версия (0x80 для mainnet)
                # Последний байт - флаг compressed (0x01) если есть
                if format_type == "wif_compressed":
                    # Убираем версию и флаг compressed
                    hex_key = decoded[1:-1].hex()
                else:
                    # Убираем только версию
                    hex_key = decoded[1:].hex()
                
                return hex_key
            
            elif format_type == "base58":
                # Пытаемся декодировать как Base58
                decoded = base58.b58decode(privkey)
                return decoded.hex()
        
        except Exception:
            return None
        
        return None
    
    def convert_hex_to_wif(
        self,
        hex_key: str,
        compressed: bool = True,
        testnet: bool = False
    ) -> str:
        """
        Конвертировать HEX в WIF формат
        
        Args:
            hex_key: HEX приватный ключ (64 символа)
            compressed: Compressed формат
            testnet: Testnet или mainnet
        
        Returns:
            WIF строка
        """
        
        # Версия байт
        version = b'\xef' if testnet else b'\x80'
        
        # Приватный ключ в байтах
        privkey_bytes = bytes.fromhex(hex_key)
        
        # Добавляем версию
        extended = version + privkey_bytes
        
        # Добавляем флаг compressed если нужно
        if compressed:
            extended += b'\x01'
        
        # Вычисляем checksum
        checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]
        
        # Кодируем в Base58
        wif = base58.b58encode(extended + checksum).decode()
        
        return wif
    
    def validate_privkey(self, privkey: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Валидировать приватный ключ
        
        Args:
            privkey: Приватный ключ
        
        Returns:
            (valid, format, hex_key)
        """
        
        format_type = self.detect_format(privkey)
        
        if format_type is None:
            return (False, None, None)
        
        hex_key = self.convert_to_hex(privkey, format_type)
        
        if hex_key is None:
            return (False, format_type, None)
        
        # Проверяем что HEX ключ валидный (64 символа, hex)
        if len(hex_key) != 64:
            return (False, format_type, None)
        
        try:
            int(hex_key, 16)
        except ValueError:
            return (False, format_type, None)
        
        return (True, format_type, hex_key)
    
    def get_all_formats(self, hex_key: str) -> Dict[str, str]:
        """
        Получить все форматы для HEX ключа
        
        Args:
            hex_key: HEX приватный ключ
        
        Returns:
            Словарь с разными форматами
        """
        
        formats = {
            "hex": hex_key,
            "hex_with_prefix": f"0x{hex_key}",
            "wif_compressed": self.convert_hex_to_wif(hex_key, compressed=True),
            "wif_uncompressed": self.convert_hex_to_wif(hex_key, compressed=False),
        }
        
        return formats
    
    def analyze_privkey(self, privkey: str) -> Dict[str, Any]:
        """
        Полный анализ приватного ключа
        
        Returns:
            {
                "valid": bool,
                "original_format": str,
                "hex": str,
                "all_formats": {...},
                "blockchain_compatibility": [...],
            }
        """
        
        analysis = {
            "valid": False,
            "original_format": None,
            "hex": None,
            "all_formats": {},
            "blockchain_compatibility": [],
        }
        
        # Валидация
        valid, format_type, hex_key = self.validate_privkey(privkey)
        
        analysis["valid"] = valid
        analysis["original_format"] = format_type
        analysis["hex"] = hex_key
        
        if not valid:
            return analysis
        
        # Получаем все форматы
        analysis["all_formats"] = self.get_all_formats(hex_key)
        
        # Определяем совместимость с блокчейнами
        if format_type in ["wif_compressed", "wif_uncompressed"]:
            analysis["blockchain_compatibility"].append("Bitcoin")
            analysis["blockchain_compatibility"].append("Litecoin")
            analysis["blockchain_compatibility"].append("Dogecoin")
            analysis["blockchain_compatibility"].append("Dash")
        
        if format_type in ["hex_with_prefix", "hex_without_prefix"]:
            analysis["blockchain_compatibility"].append("Ethereum")
            analysis["blockchain_compatibility"].append("BSC")
            analysis["blockchain_compatibility"].append("Polygon")
            analysis["blockchain_compatibility"].append("Arbitrum")
            analysis["blockchain_compatibility"].append("Optimism")
            analysis["blockchain_compatibility"].append("Avalanche")
        
        return analysis
    
    def format_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """Форматировать отчет анализа"""
        
        if not analysis["valid"]:
            return "❌ Invalid private key format"
        
        lines = []
        
        lines.append("🔑 PRIVATE KEY ANALYSIS")
        lines.append("=" * 50)
        
        # Оригинальный формат
        original = analysis["original_format"]
        lines.append(f"📋 Original Format: {original}")
        
        # HEX
        hex_key = analysis["hex"]
        lines.append(f"🔢 HEX: {hex_key[:16]}...{hex_key[-16:]}")
        
        # Все форматы
        lines.append("\n📦 Available Formats:")
        all_formats = analysis["all_formats"]
        
        for format_name, value in all_formats.items():
            if len(value) > 50:
                display = f"{value[:25]}...{value[-20:]}"
            else:
                display = value
            lines.append(f"  • {format_name}: {display}")
        
        # Совместимость
        compatibility = analysis["blockchain_compatibility"]
        if compatibility:
            lines.append(f"\n🔗 Compatible Blockchains:")
            for blockchain in compatibility:
                lines.append(f"  ✓ {blockchain}")
        
        return "\n".join(lines)


class PrivateKeyConverter:
    """Конвертер между форматами приватных ключей"""
    
    def __init__(self):
        self.formats_handler = PrivateKeyFormats()
    
    def convert(
        self,
        privkey: str,
        target_format: str,
        compressed: bool = True
    ) -> Optional[str]:
        """
        Конвертировать приватный ключ в целевой формат
        
        Args:
            privkey: Исходный приватный ключ
            target_format: Целевой формат (hex, wif_compressed, wif_uncompressed)
            compressed: Для WIF формата
        
        Returns:
            Конвертированный ключ или None
        """
        
        # Сначала конвертируем в HEX
        hex_key = self.formats_handler.convert_to_hex(privkey)
        
        if hex_key is None:
            return None
        
        # Конвертируем в целевой формат
        if target_format == "hex":
            return hex_key
        
        elif target_format == "hex_with_prefix":
            return f"0x{hex_key}"
        
        elif target_format == "wif_compressed":
            return self.formats_handler.convert_hex_to_wif(hex_key, compressed=True)
        
        elif target_format == "wif_uncompressed":
            return self.formats_handler.convert_hex_to_wif(hex_key, compressed=False)
        
        return None
    
    def batch_convert(
        self,
        privkeys: list,
        target_format: str
    ) -> Dict[str, str]:
        """
        Пакетная конвертация приватных ключей
        
        Args:
            privkeys: Список приватных ключей
            target_format: Целевой формат
        
        Returns:
            Словарь {original: converted}
        """
        
        results = {}
        
        for privkey in privkeys:
            converted = self.convert(privkey, target_format)
            if converted:
                results[privkey] = converted
        
        return results


class PrivateKeyValidator:
    """Валидатор приватных ключей"""
    
    def __init__(self):
        self.formats_handler = PrivateKeyFormats()
    
    def validate_batch(self, privkeys: list) -> Dict[str, Any]:
        """
        Валидировать список приватных ключей
        
        Returns:
            {
                "total": int,
                "valid": int,
                "invalid": int,
                "by_format": {...},
                "results": [...]
            }
        """
        
        stats = {
            "total": len(privkeys),
            "valid": 0,
            "invalid": 0,
            "by_format": {},
            "results": []
        }
        
        for privkey in privkeys:
            valid, format_type, hex_key = self.formats_handler.validate_privkey(privkey)
            
            result = {
                "privkey": privkey[:20] + "..." if len(privkey) > 20 else privkey,
                "valid": valid,
                "format": format_type,
                "hex": hex_key[:16] + "..." if hex_key else None
            }
            
            stats["results"].append(result)
            
            if valid:
                stats["valid"] += 1
                
                # Подсчитываем по форматам
                if format_type not in stats["by_format"]:
                    stats["by_format"][format_type] = 0
                stats["by_format"][format_type] += 1
            else:
                stats["invalid"] += 1
        
        return stats
    
    def format_validation_report(self, stats: Dict[str, Any]) -> str:
        """Форматировать отчет валидации"""
        
        lines = []
        
        lines.append("🔍 PRIVATE KEY VALIDATION REPORT")
        lines.append("=" * 50)
        
        # Общая статистика
        lines.append(f"📊 Total: {stats['total']}")
        lines.append(f"✅ Valid: {stats['valid']}")
        lines.append(f"❌ Invalid: {stats['invalid']}")
        
        # По форматам
        by_format = stats["by_format"]
        if by_format:
            lines.append("\n📋 By Format:")
            for format_name, count in by_format.items():
                lines.append(f"  • {format_name}: {count}")
        
        # Детали (первые 10)
        results = stats["results"]
        if results:
            lines.append("\n📝 Details (first 10):")
            for result in results[:10]:
                status = "✅" if result["valid"] else "❌"
                privkey = result["privkey"]
                format_type = result["format"] or "unknown"
                lines.append(f"  {status} {privkey} ({format_type})")
        
        return "\n".join(lines)
