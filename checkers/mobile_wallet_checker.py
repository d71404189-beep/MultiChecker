# -*- coding: utf-8 -*-
"""
Mobile Wallet Checker v1.0.55
Проверка backup файлов мобильных кошельков: Trust Wallet, MetaMask Mobile, Coinbase Wallet
"""

import json
import base64
import hashlib
from typing import Dict, List, Any, Optional
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2


# ═══════════════════════════════════════════════════════════════════════════
#  TRUST WALLET BACKUP
# ═══════════════════════════════════════════════════════════════════════════

class TrustWalletChecker:
    """Проверка Trust Wallet backup файлов"""
    
    @staticmethod
    def check_backup(backup_data: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Проверить Trust Wallet backup
        
        Args:
            backup_data: JSON строка или путь к файлу
            password: Пароль для расшифровки (если зашифрован)
        
        Returns:
            Dict: {
                "valid": True,
                "wallet_type": "Trust Wallet",
                "encrypted": False,
                "mnemonic": "word1 word2 ...",
                "addresses": {
                    "ethereum": "0x...",
                    "bitcoin": "bc1...",
                    ...
                },
                "accounts": 5
            }
        """
        
        result = {
            "valid": False,
            "wallet_type": "Trust Wallet",
            "encrypted": False,
            "mnemonic": None,
            "addresses": {},
            "accounts": 0,
            "error": None
        }
        
        try:
            # Пробуем распарсить JSON
            if backup_data.startswith("{"):
                data = json.loads(backup_data)
            else:
                # Читаем из файла
                with open(backup_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Trust Wallet backup структура
            if "wallets" in data:
                result["valid"] = True
                
                for wallet in data["wallets"]:
                    # Проверяем зашифрован ли
                    if "encryptedData" in wallet:
                        result["encrypted"] = True
                        
                        if password:
                            # Пробуем расшифровать
                            decrypted = TrustWalletChecker._decrypt_wallet(
                                wallet["encryptedData"],
                                password
                            )
                            if decrypted:
                                result["mnemonic"] = decrypted.get("mnemonic")
                        else:
                            result["error"] = "Wallet is encrypted, password required"
                    
                    elif "mnemonic" in wallet:
                        result["mnemonic"] = wallet["mnemonic"]
                    
                    # Извлекаем адреса
                    if "accounts" in wallet:
                        result["accounts"] = len(wallet["accounts"])
                        
                        for account in wallet["accounts"]:
                            coin = account.get("coin", "unknown")
                            address = account.get("address")
                            
                            if address:
                                result["addresses"][coin.lower()] = address
            
            else:
                result["error"] = "Invalid Trust Wallet backup format"
        
        except json.JSONDecodeError:
            result["error"] = "Invalid JSON format"
        except FileNotFoundError:
            result["error"] = "Backup file not found"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    @staticmethod
    def _decrypt_wallet(encrypted_data: str, password: str) -> Optional[Dict]:
        """Расшифровать Trust Wallet данные"""
        
        try:
            # Trust Wallet использует AES-256-CBC с PBKDF2
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Извлекаем salt (первые 8 байт)
            salt = encrypted_bytes[:8]
            iv = encrypted_bytes[8:24]
            ciphertext = encrypted_bytes[24:]
            
            # Генерируем ключ через PBKDF2
            key = PBKDF2(password, salt, dkLen=32, count=10000)
            
            # Расшифровываем
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            
            # Убираем padding
            padding_length = decrypted[-1]
            decrypted = decrypted[:-padding_length]
            
            # Парсим JSON
            return json.loads(decrypted.decode('utf-8'))
        
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════
#  METAMASK MOBILE BACKUP
# ═══════════════════════════════════════════════════════════════════════════

class MetaMaskMobileChecker:
    """Проверка MetaMask Mobile backup"""
    
    @staticmethod
    def check_backup(backup_data: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Проверить MetaMask Mobile backup
        
        MetaMask Mobile хранит данные в:
        - Android: /data/data/io.metamask/files/
        - iOS: Library/Application Support/
        
        Формат: JSON с зашифрованным vault
        """
        
        result = {
            "valid": False,
            "wallet_type": "MetaMask Mobile",
            "encrypted": True,
            "mnemonic": None,
            "addresses": {},
            "accounts": 0,
            "error": None
        }
        
        try:
            # Пробуем распарсить JSON
            if backup_data.startswith("{"):
                data = json.loads(backup_data)
            else:
                with open(backup_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # MetaMask структура
            if "vault" in data or "KeyringController" in data:
                result["valid"] = True
                
                vault = data.get("vault") or data.get("KeyringController", {}).get("vault")
                
                if vault and password:
                    # Пробуем расшифровать
                    decrypted = MetaMaskMobileChecker._decrypt_vault(vault, password)
                    
                    if decrypted:
                        # Извлекаем мнемонику
                        for keyring in decrypted:
                            if keyring.get("type") == "HD Key Tree":
                                result["mnemonic"] = keyring.get("data", {}).get("mnemonic")
                                result["accounts"] = len(keyring.get("data", {}).get("accounts", []))
                                
                                # Извлекаем адреса
                                for i, account in enumerate(keyring.get("data", {}).get("accounts", [])):
                                    result["addresses"][f"account_{i}"] = account
                    else:
                        result["error"] = "Failed to decrypt vault (wrong password?)"
                else:
                    result["error"] = "Vault is encrypted, password required"
            
            else:
                result["error"] = "Invalid MetaMask backup format"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    @staticmethod
    def _decrypt_vault(vault: str, password: str) -> Optional[List]:
        """Расшифровать MetaMask vault"""
        
        try:
            # MetaMask использует eth-sig-util encryption
            # Это упрощенная версия, реальная расшифровка сложнее
            
            vault_data = json.loads(vault) if isinstance(vault, str) else vault
            
            # Извлекаем параметры
            iv = bytes.fromhex(vault_data["iv"])
            salt = bytes.fromhex(vault_data["salt"])
            ciphertext = bytes.fromhex(vault_data["data"])
            
            # Генерируем ключ
            key = PBKDF2(password, salt, dkLen=32, count=10000)
            
            # Расшифровываем
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            decrypted = cipher.decrypt(ciphertext)
            
            return json.loads(decrypted.decode('utf-8'))
        
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════
#  COINBASE WALLET BACKUP
# ═══════════════════════════════════════════════════════════════════════════

class CoinbaseWalletChecker:
    """Проверка Coinbase Wallet backup"""
    
    @staticmethod
    def check_backup(backup_data: str) -> Dict[str, Any]:
        """
        Проверить Coinbase Wallet backup
        
        Coinbase Wallet использует cloud backup (iCloud/Google Drive)
        Формат: зашифрованный JSON
        """
        
        result = {
            "valid": False,
            "wallet_type": "Coinbase Wallet",
            "encrypted": True,
            "mnemonic": None,
            "error": "Coinbase Wallet backups are encrypted with device key"
        }
        
        # Coinbase Wallet использует device-specific encryption
        # Расшифровка возможна только на оригинальном устройстве
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED MOBILE WALLET CHECKER
# ═══════════════════════════════════════════════════════════════════════════

class MobileWalletChecker:
    """Универсальный чекер мобильных кошельков"""
    
    SUPPORTED_WALLETS = {
        "trust": TrustWalletChecker,
        "metamask": MetaMaskMobileChecker,
        "coinbase": CoinbaseWalletChecker,
    }
    
    @staticmethod
    def detect_wallet_type(backup_data: str) -> Optional[str]:
        """
        Автоматически определить тип кошелька
        
        Returns:
            str: "trust" | "metamask" | "coinbase" | None
        """
        
        try:
            if backup_data.startswith("{"):
                data = json.loads(backup_data)
            else:
                with open(backup_data, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Trust Wallet
            if "wallets" in data and isinstance(data["wallets"], list):
                return "trust"
            
            # MetaMask
            if "vault" in data or "KeyringController" in data:
                return "metamask"
            
            # Coinbase Wallet
            if "coinbase" in str(data).lower():
                return "coinbase"
        
        except:
            pass
        
        return None
    
    @staticmethod
    def check_backup(
        backup_data: str,
        wallet_type: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Универсальная проверка backup
        
        Args:
            backup_data: JSON строка или путь к файлу
            wallet_type: "trust" | "metamask" | "coinbase" (auto-detect if None)
            password: Пароль для расшифровки
        
        Returns:
            Dict: результат проверки
        """
        
        # Автоопределение типа
        if not wallet_type:
            wallet_type = MobileWalletChecker.detect_wallet_type(backup_data)
        
        if not wallet_type:
            return {
                "valid": False,
                "error": "Unknown wallet type"
            }
        
        if wallet_type not in MobileWalletChecker.SUPPORTED_WALLETS:
            return {
                "valid": False,
                "error": f"Wallet type {wallet_type} not supported"
            }
        
        checker_class = MobileWalletChecker.SUPPORTED_WALLETS[wallet_type]
        
        # Проверяем backup
        if wallet_type == "coinbase":
            return checker_class.check_backup(backup_data)
        else:
            return checker_class.check_backup(backup_data, password)
    
    @staticmethod
    def format_result(result: Dict) -> str:
        """
        Форматировать результат для вывода
        
        Returns:
            str: "Trust Wallet: ✅ 12 words | 5 accounts | ETH: 0x..."
        """
        
        if not result.get("valid"):
            error = result.get("error", "Unknown error")
            return f"{result.get('wallet_type', 'Unknown')}: ❌ {error}"
        
        parts = [f"{result['wallet_type']}: ✅"]
        
        # Mnemonic
        mnemonic = result.get("mnemonic")
        if mnemonic:
            word_count = len(mnemonic.split())
            parts.append(f"{word_count} words")
        elif result.get("encrypted"):
            parts.append("🔒 Encrypted")
        
        # Accounts
        accounts = result.get("accounts", 0)
        if accounts > 0:
            parts.append(f"{accounts} accounts")
        
        # Addresses
        addresses = result.get("addresses", {})
        if addresses:
            addr_str = ", ".join([f"{coin.upper()}: {addr[:10]}..." for coin, addr in list(addresses.items())[:3]])
            parts.append(addr_str)
        
        return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
#  BACKUP FILE FORMATS
# ═══════════════════════════════════════════════════════════════════════════

class BackupFormats:
    """Информация о форматах backup файлов"""
    
    FORMATS = {
        "trust_wallet": {
            "name": "Trust Wallet",
            "file_name": "backup.json",
            "location_android": "/sdcard/TrustWallet/",
            "location_ios": "iCloud Drive/Trust/",
            "encrypted": True,
            "format": "JSON",
            "example": {
                "wallets": [
                    {
                        "id": "...",
                        "name": "Wallet 1",
                        "mnemonic": "word1 word2 ...",
                        "accounts": [
                            {"coin": "ethereum", "address": "0x..."},
                            {"coin": "bitcoin", "address": "bc1..."}
                        ]
                    }
                ]
            }
        },
        "metamask_mobile": {
            "name": "MetaMask Mobile",
            "file_name": "persist-root",
            "location_android": "/data/data/io.metamask/files/",
            "location_ios": "Library/Application Support/",
            "encrypted": True,
            "format": "JSON with encrypted vault",
            "example": {
                "KeyringController": {
                    "vault": "{encrypted_data}"
                }
            }
        },
        "coinbase_wallet": {
            "name": "Coinbase Wallet",
            "file_name": "backup.json",
            "location_android": "Google Drive",
            "location_ios": "iCloud",
            "encrypted": True,
            "format": "Device-encrypted JSON",
            "note": "Can only be decrypted on original device"
        }
    }
    
    @staticmethod
    def get_format_info(wallet_type: str) -> Dict:
        """Получить информацию о формате"""
        return BackupFormats.FORMATS.get(wallet_type, {})
    
    @staticmethod
    def list_formats() -> List[str]:
        """Список поддерживаемых форматов"""
        return list(BackupFormats.FORMATS.keys())
