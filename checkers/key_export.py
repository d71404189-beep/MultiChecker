# -*- coding: utf-8 -*-
"""
Key Export v1.0.55
Экспорт приватных ключей в разные форматы: WIF, HEX, Keystore, зашифрованный
"""

import json
import hashlib
import base64
import os
from typing import Dict, List, Any, Optional
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2, scrypt
from Crypto.Random import get_random_bytes
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
#  WIF (Wallet Import Format)
# ═══════════════════════════════════════════════════════════════════════════

class WIFExporter:
    """Экспорт в WIF формат (Bitcoin)"""
    
    # Base58 alphabet
    BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    @staticmethod
    def private_key_to_wif(private_key_hex: str, compressed: bool = True, testnet: bool = False) -> str:
        """
        Конвертировать приватный ключ в WIF формат
        
        Args:
            private_key_hex: Приватный ключ в HEX (64 символа)
            compressed: Compressed WIF (True) или Uncompressed (False)
            testnet: Testnet (True) или Mainnet (False)
        
        Returns:
            str: WIF строка (начинается с 5/K/L для mainnet, 9/c для testnet)
        """
        
        # Убираем 0x если есть
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex[2:]
        
        # Проверяем длину
        if len(private_key_hex) != 64:
            raise ValueError("Private key must be 64 hex characters")
        
        # Prefix: 0x80 для mainnet, 0xEF для testnet
        prefix = b'\xef' if testnet else b'\x80'
        
        # Добавляем prefix
        extended_key = prefix + bytes.fromhex(private_key_hex)
        
        # Добавляем 0x01 для compressed
        if compressed:
            extended_key += b'\x01'
        
        # Double SHA256 для checksum
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        
        # Финальный ключ
        final_key = extended_key + checksum
        
        # Конвертируем в Base58
        wif = WIFExporter._base58_encode(final_key)
        
        return wif
    
    @staticmethod
    def wif_to_private_key(wif: str) -> Dict[str, Any]:
        """
        Конвертировать WIF в приватный ключ
        
        Returns:
            Dict: {
                "private_key": "0x...",
                "compressed": True,
                "testnet": False
            }
        """
        
        # Декодируем из Base58
        decoded = WIFExporter._base58_decode(wif)
        
        # Проверяем checksum
        checksum = decoded[-4:]
        payload = decoded[:-4]
        
        calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        if checksum != calculated_checksum:
            raise ValueError("Invalid WIF checksum")
        
        # Определяем testnet
        prefix = payload[0]
        testnet = (prefix == 0xef)
        
        # Определяем compressed
        if len(payload) == 34:  # 1 prefix + 32 key + 1 compressed flag
            compressed = True
            private_key = payload[1:-1]
        else:  # 1 prefix + 32 key
            compressed = False
            private_key = payload[1:]
        
        return {
            "private_key": "0x" + private_key.hex(),
            "compressed": compressed,
            "testnet": testnet
        }
    
    @staticmethod
    def _base58_encode(data: bytes) -> str:
        """Кодировать в Base58"""
        
        # Конвертируем в число
        num = int.from_bytes(data, 'big')
        
        # Кодируем
        encoded = ""
        while num > 0:
            num, remainder = divmod(num, 58)
            encoded = WIFExporter.BASE58_ALPHABET[remainder] + encoded
        
        # Добавляем leading zeros
        for byte in data:
            if byte == 0:
                encoded = '1' + encoded
            else:
                break
        
        return encoded
    
    @staticmethod
    def _base58_decode(encoded: str) -> bytes:
        """Декодировать из Base58"""
        
        # Декодируем в число
        num = 0
        for char in encoded:
            num = num * 58 + WIFExporter.BASE58_ALPHABET.index(char)
        
        # Конвертируем в bytes
        decoded = num.to_bytes((num.bit_length() + 7) // 8, 'big')
        
        # Добавляем leading zeros
        for char in encoded:
            if char == '1':
                decoded = b'\x00' + decoded
            else:
                break
        
        return decoded


# ═══════════════════════════════════════════════════════════════════════════
#  KEYSTORE (Ethereum JSON)
# ═══════════════════════════════════════════════════════════════════════════

class KeystoreExporter:
    """Экспорт в Keystore формат (Ethereum)"""
    
    @staticmethod
    def create_keystore(
        private_key_hex: str,
        password: str,
        kdf: str = "scrypt"
    ) -> Dict[str, Any]:
        """
        Создать Keystore файл (Ethereum JSON)
        
        Args:
            private_key_hex: Приватный ключ в HEX
            password: Пароль для шифрования
            kdf: "scrypt" или "pbkdf2"
        
        Returns:
            Dict: Keystore JSON
        """
        
        # Убираем 0x
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex[2:]
        
        private_key = bytes.fromhex(private_key_hex)
        
        # Генерируем соль и IV
        salt = get_random_bytes(32)
        iv = get_random_bytes(16)
        
        # Генерируем ключ шифрования
        if kdf == "scrypt":
            derived_key = scrypt(
                password.encode('utf-8'),
                salt,
                key_len=32,
                N=262144,  # 2^18
                r=8,
                p=1
            )
            kdf_params = {
                "dklen": 32,
                "n": 262144,
                "r": 8,
                "p": 1,
                "salt": salt.hex()
            }
        else:  # pbkdf2
            derived_key = PBKDF2(
                password.encode('utf-8'),
                salt,
                dkLen=32,
                count=262144
            )
            kdf_params = {
                "dklen": 32,
                "c": 262144,
                "prf": "hmac-sha256",
                "salt": salt.hex()
            }
        
        # Шифруем приватный ключ
        cipher = AES.new(derived_key[:16], AES.MODE_CTR, nonce=b'', initial_value=iv)
        ciphertext = cipher.encrypt(private_key)
        
        # MAC для проверки пароля
        mac = hashlib.sha256(derived_key[16:32] + ciphertext).digest()
        
        # Генерируем адрес (упрощенно)
        # В реальности нужно использовать eth_keys
        address = "0x" + hashlib.sha256(private_key).hexdigest()[:40]
        
        # Создаем Keystore JSON
        keystore = {
            "version": 3,
            "id": os.urandom(16).hex(),
            "address": address[2:],  # без 0x
            "crypto": {
                "ciphertext": ciphertext.hex(),
                "cipherparams": {
                    "iv": iv.hex()
                },
                "cipher": "aes-128-ctr",
                "kdf": kdf,
                "kdfparams": kdf_params,
                "mac": mac.hex()
            }
        }
        
        return keystore
    
    @staticmethod
    def decrypt_keystore(keystore: Dict, password: str) -> str:
        """
        Расшифровать Keystore файл
        
        Returns:
            str: Приватный ключ в HEX (0x...)
        """
        
        crypto = keystore["crypto"]
        
        # Извлекаем параметры
        ciphertext = bytes.fromhex(crypto["ciphertext"])
        iv = bytes.fromhex(crypto["cipherparams"]["iv"])
        mac = bytes.fromhex(crypto["mac"])
        kdf = crypto["kdf"]
        kdf_params = crypto["kdfparams"]
        
        # Генерируем ключ
        salt = bytes.fromhex(kdf_params["salt"])
        
        if kdf == "scrypt":
            derived_key = scrypt(
                password.encode('utf-8'),
                salt,
                key_len=kdf_params["dklen"],
                N=kdf_params["n"],
                r=kdf_params["r"],
                p=kdf_params["p"]
            )
        else:  # pbkdf2
            derived_key = PBKDF2(
                password.encode('utf-8'),
                salt,
                dkLen=kdf_params["dklen"],
                count=kdf_params["c"]
            )
        
        # Проверяем MAC
        calculated_mac = hashlib.sha256(derived_key[16:32] + ciphertext).digest()
        
        if calculated_mac != mac:
            raise ValueError("Invalid password")
        
        # Расшифровываем
        cipher = AES.new(derived_key[:16], AES.MODE_CTR, nonce=b'', initial_value=iv)
        private_key = cipher.decrypt(ciphertext)
        
        return "0x" + private_key.hex()


# ═══════════════════════════════════════════════════════════════════════════
#  ENCRYPTED EXPORT (AES-256)
# ═══════════════════════════════════════════════════════════════════════════

class EncryptedExporter:
    """Экспорт с шифрованием AES-256"""
    
    @staticmethod
    def encrypt_keys(
        keys: List[Dict],
        password: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Зашифровать список ключей
        
        Args:
            keys: [
                {
                    "type": "private_key" | "mnemonic",
                    "value": "...",
                    "address": "0x...",
                    "chain": "ethereum",
                    "balance": 1.5,
                    "balance_usd": 3000
                },
                ...
            ]
            password: Пароль для шифрования
            metadata: Дополнительные данные
        
        Returns:
            Dict: Зашифрованный файл
        """
        
        # Подготавливаем данные
        data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "keys_count": len(keys),
            "metadata": metadata or {},
            "keys": keys
        }
        
        # Конвертируем в JSON
        json_data = json.dumps(data, indent=2).encode('utf-8')
        
        # Генерируем соль и ключ
        salt = get_random_bytes(32)
        key = PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=100000)
        
        # Шифруем
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(json_data)
        
        # Создаем зашифрованный файл
        encrypted = {
            "version": "1.0",
            "encryption": "AES-256-GCM",
            "kdf": "PBKDF2",
            "kdf_params": {
                "iterations": 100000,
                "salt": base64.b64encode(salt).decode('utf-8')
            },
            "cipher_params": {
                "nonce": base64.b64encode(cipher.nonce).decode('utf-8'),
                "tag": base64.b64encode(tag).decode('utf-8')
            },
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "created_at": datetime.now().isoformat()
        }
        
        return encrypted
    
    @staticmethod
    def decrypt_keys(encrypted: Dict, password: str) -> List[Dict]:
        """
        Расшифровать ключи
        
        Returns:
            List[Dict]: Список ключей
        """
        
        # Извлекаем параметры
        salt = base64.b64decode(encrypted["kdf_params"]["salt"])
        nonce = base64.b64decode(encrypted["cipher_params"]["nonce"])
        tag = base64.b64decode(encrypted["cipher_params"]["tag"])
        ciphertext = base64.b64decode(encrypted["ciphertext"])
        
        # Генерируем ключ
        key = PBKDF2(
            password.encode('utf-8'),
            salt,
            dkLen=32,
            count=encrypted["kdf_params"]["iterations"]
        )
        
        # Расшифровываем
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        
        try:
            json_data = cipher.decrypt_and_verify(ciphertext, tag)
            data = json.loads(json_data.decode('utf-8'))
            return data["keys"]
        except ValueError:
            raise ValueError("Invalid password or corrupted data")


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED KEY EXPORTER
# ═══════════════════════════════════════════════════════════════════════════

class KeyExporter:
    """Универсальный экспортер ключей"""
    
    SUPPORTED_FORMATS = ["hex", "wif", "keystore", "encrypted"]
    
    @staticmethod
    def export_key(
        private_key: str,
        format: str,
        password: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Экспортировать ключ в указанный формат
        
        Args:
            private_key: Приватный ключ (HEX)
            format: "hex" | "wif" | "keystore" | "encrypted"
            password: Пароль (для keystore, encrypted)
            **kwargs: Дополнительные параметры
        
        Returns:
            str | Dict: Экспортированный ключ
        """
        
        if format == "hex":
            # Просто HEX формат
            if not private_key.startswith("0x"):
                return "0x" + private_key
            return private_key
        
        elif format == "wif":
            # WIF формат (Bitcoin)
            compressed = kwargs.get("compressed", True)
            testnet = kwargs.get("testnet", False)
            return WIFExporter.private_key_to_wif(private_key, compressed, testnet)
        
        elif format == "keystore":
            # Keystore JSON (Ethereum)
            if not password:
                raise ValueError("Password required for keystore format")
            kdf = kwargs.get("kdf", "scrypt")
            return KeystoreExporter.create_keystore(private_key, password, kdf)
        
        elif format == "encrypted":
            # Зашифрованный формат
            if not password:
                raise ValueError("Password required for encrypted format")
            
            keys = [{
                "type": "private_key",
                "value": private_key,
                "address": kwargs.get("address", ""),
                "chain": kwargs.get("chain", "ethereum"),
                "balance": kwargs.get("balance", 0),
                "balance_usd": kwargs.get("balance_usd", 0)
            }]
            
            return EncryptedExporter.encrypt_keys(keys, password, kwargs.get("metadata"))
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @staticmethod
    def export_multiple_keys(
        keys: List[Dict],
        format: str,
        password: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Any:
        """
        Экспортировать несколько ключей
        
        Args:
            keys: Список ключей
            format: Формат экспорта
            password: Пароль (если нужен)
            output_file: Путь к файлу (если нужно сохранить)
        
        Returns:
            List | Dict: Экспортированные ключи
        """
        
        if format == "encrypted":
            # Все ключи в один зашифрованный файл
            if not password:
                raise ValueError("Password required for encrypted format")
            
            result = EncryptedExporter.encrypt_keys(keys, password)
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            
            return result
        
        else:
            # Каждый ключ отдельно
            results = []
            
            for key_data in keys:
                private_key = key_data["value"]
                
                exported = KeyExporter.export_key(
                    private_key,
                    format,
                    password,
                    **key_data
                )
                
                results.append({
                    "address": key_data.get("address"),
                    "chain": key_data.get("chain"),
                    "exported": exported
                })
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
            
            return results
    
    @staticmethod
    def import_key(data: Any, format: str, password: Optional[str] = None) -> str:
        """
        Импортировать ключ из формата
        
        Returns:
            str: Приватный ключ в HEX (0x...)
        """
        
        if format == "hex":
            if not data.startswith("0x"):
                return "0x" + data
            return data
        
        elif format == "wif":
            result = WIFExporter.wif_to_private_key(data)
            return result["private_key"]
        
        elif format == "keystore":
            if not password:
                raise ValueError("Password required for keystore format")
            return KeystoreExporter.decrypt_keystore(data, password)
        
        elif format == "encrypted":
            if not password:
                raise ValueError("Password required for encrypted format")
            keys = EncryptedExporter.decrypt_keys(data, password)
            return keys[0]["value"] if keys else None
        
        else:
            raise ValueError(f"Unsupported format: {format}")
