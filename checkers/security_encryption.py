# -*- coding: utf-8 -*-
"""
Security & Encryption v1.0.61
Безопасность и шифрование данных
"""

import hashlib
import hmac
import secrets
import base64
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import os


class EncryptionManager:
    """Менеджер шифрования"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Args:
            master_key: Мастер-ключ для шифрования (если None, генерируется новый)
        """
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._generate_master_key()
    
    def _generate_master_key(self) -> bytes:
        """Генерировать мастер-ключ"""
        return secrets.token_bytes(32)  # 256 бит
    
    def encrypt_data(self, data: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """
        Шифровать данные (простое XOR шифрование для демонстрации)
        В продакшене использовать AES или другие стандартные алгоритмы
        
        Args:
            data: Данные для шифрования
            salt: Соль (если None, генерируется новая)
        
        Returns:
            {
                "encrypted": str (base64),
                "salt": str (base64),
                "algorithm": str
            }
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # Генерируем ключ из мастер-ключа и соли
        key = hashlib.pbkdf2_hmac('sha256', self.master_key, salt, 100000)
        
        # Простое XOR шифрование (для демонстрации)
        data_bytes = data.encode('utf-8')
        encrypted = bytearray()
        
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])
        
        return {
            "encrypted": base64.b64encode(bytes(encrypted)).decode('utf-8'),
            "salt": base64.b64encode(salt).decode('utf-8'),
            "algorithm": "PBKDF2-XOR",
        }
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> str:
        """
        Расшифровать данные
        
        Args:
            encrypted_data: Зашифрованные данные (из encrypt_data)
        
        Returns:
            Расшифрованная строка
        """
        encrypted = base64.b64decode(encrypted_data["encrypted"])
        salt = base64.b64decode(encrypted_data["salt"])
        
        # Генерируем тот же ключ
        key = hashlib.pbkdf2_hmac('sha256', self.master_key, salt, 100000)
        
        # Расшифровываем XOR
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])
        
        return bytes(decrypted).decode('utf-8')
    
    def encrypt_private_key(self, private_key: str, password: str) -> Dict[str, str]:
        """
        Шифровать приватный ключ с паролем
        
        Args:
            private_key: Приватный ключ
            password: Пароль для шифрования
        
        Returns:
            Зашифрованные данные
        """
        # Используем пароль как дополнительный ключ
        password_hash = hashlib.sha256(password.encode()).digest()
        
        # Комбинируем мастер-ключ и пароль
        combined_key = bytes(a ^ b for a, b in zip(self.master_key, password_hash))
        
        # Временно меняем мастер-ключ
        original_key = self.master_key
        self.master_key = combined_key
        
        # Шифруем
        encrypted = self.encrypt_data(private_key)
        encrypted["protected"] = True
        
        # Восстанавливаем мастер-ключ
        self.master_key = original_key
        
        return encrypted
    
    def decrypt_private_key(self, encrypted_data: Dict[str, str], password: str) -> str:
        """
        Расшифровать приватный ключ с паролем
        
        Args:
            encrypted_data: Зашифрованные данные
            password: Пароль для расшифровки
        
        Returns:
            Приватный ключ
        """
        # Используем пароль как дополнительный ключ
        password_hash = hashlib.sha256(password.encode()).digest()
        
        # Комбинируем мастер-ключ и пароль
        combined_key = bytes(a ^ b for a, b in zip(self.master_key, password_hash))
        
        # Временно меняем мастер-ключ
        original_key = self.master_key
        self.master_key = combined_key
        
        # Расшифровываем
        decrypted = self.decrypt_data(encrypted_data)
        
        # Восстанавливаем мастер-ключ
        self.master_key = original_key
        
        return decrypted
    
    def hash_password(self, password: str) -> Dict[str, str]:
        """
        Хешировать пароль
        
        Returns:
            {
                "hash": str,
                "salt": str,
                "algorithm": str
            }
        """
        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        return {
            "hash": base64.b64encode(password_hash).decode('utf-8'),
            "salt": base64.b64encode(salt).decode('utf-8'),
            "algorithm": "PBKDF2-SHA256",
        }
    
    def verify_password(self, password: str, stored_data: Dict[str, str]) -> bool:
        """Проверить пароль"""
        
        salt = base64.b64decode(stored_data["salt"])
        stored_hash = base64.b64decode(stored_data["hash"])
        
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        
        return hmac.compare_digest(password_hash, stored_hash)


class TwoFactorAuth:
    """Двухфакторная аутентификация"""
    
    def __init__(self):
        self.secrets = {}
        self.backup_codes = {}
    
    def generate_secret(self, user_id: str) -> str:
        """Генерировать секрет для 2FA"""
        
        secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
        self.secrets[user_id] = secret
        
        return secret
    
    def generate_backup_codes(self, user_id: str, count: int = 10) -> List[str]:
        """Генерировать резервные коды"""
        
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice('0123456789') for _ in range(8))
            codes.append(f"{code[:4]}-{code[4:]}")
        
        self.backup_codes[user_id] = codes
        
        return codes
    
    def generate_totp(self, secret: str, time_step: int = 30) -> str:
        """
        Генерировать TOTP код (Time-based One-Time Password)
        
        Args:
            secret: Секрет пользователя
            time_step: Временной шаг в секундах
        
        Returns:
            6-значный код
        """
        # Текущее время в шагах
        current_time = int(datetime.now().timestamp() / time_step)
        
        # Конвертируем в байты
        time_bytes = current_time.to_bytes(8, byteorder='big')
        secret_bytes = base64.b32decode(secret)
        
        # HMAC-SHA1
        hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
        
        # Динамическое усечение
        offset = hmac_hash[-1] & 0x0F
        code = int.from_bytes(hmac_hash[offset:offset+4], byteorder='big') & 0x7FFFFFFF
        
        # 6 цифр
        return str(code % 1000000).zfill(6)
    
    def verify_totp(self, user_id: str, code: str, window: int = 1) -> bool:
        """
        Проверить TOTP код
        
        Args:
            user_id: ID пользователя
            code: Введенный код
            window: Окно времени (количество шагов до/после текущего)
        
        Returns:
            True если код верный
        """
        if user_id not in self.secrets:
            return False
        
        secret = self.secrets[user_id]
        
        # Проверяем текущий код и соседние
        for i in range(-window, window + 1):
            time_step = 30
            current_time = int(datetime.now().timestamp() / time_step) + i
            
            time_bytes = current_time.to_bytes(8, byteorder='big')
            secret_bytes = base64.b32decode(secret)
            
            hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
            offset = hmac_hash[-1] & 0x0F
            expected_code = int.from_bytes(hmac_hash[offset:offset+4], byteorder='big') & 0x7FFFFFFF
            expected_code = str(expected_code % 1000000).zfill(6)
            
            if hmac.compare_digest(code, expected_code):
                return True
        
        return False
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Проверить резервный код"""
        
        if user_id not in self.backup_codes:
            return False
        
        if code in self.backup_codes[user_id]:
            # Удаляем использованный код
            self.backup_codes[user_id].remove(code)
            return True
        
        return False
    
    def get_qr_code_url(self, user_id: str, issuer: str = "MultiChecker") -> str:
        """Получить URL для QR кода"""
        
        if user_id not in self.secrets:
            return ""
        
        secret = self.secrets[user_id]
        
        # otpauth://totp/Issuer:user@example.com?secret=SECRET&issuer=Issuer
        url = f"otpauth://totp/{issuer}:{user_id}?secret={secret}&issuer={issuer}"
        
        return url


class SecureStorage:
    """Безопасное хранилище"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager
        self.storage = {}
    
    def store_sensitive_data(
        self,
        key: str,
        data: Any,
        password: Optional[str] = None
    ) -> bool:
        """
        Сохранить чувствительные данные
        
        Args:
            key: Ключ для хранения
            data: Данные (будут сериализованы в JSON)
            password: Дополнительный пароль (опционально)
        
        Returns:
            True если успешно
        """
        try:
            # Сериализуем данные
            json_data = json.dumps(data)
            
            # Шифруем
            if password:
                encrypted = self.encryption.encrypt_private_key(json_data, password)
            else:
                encrypted = self.encryption.encrypt_data(json_data)
            
            # Сохраняем
            self.storage[key] = {
                "encrypted": encrypted,
                "timestamp": datetime.now().isoformat(),
                "protected": password is not None,
            }
            
            return True
        
        except Exception:
            return False
    
    def retrieve_sensitive_data(
        self,
        key: str,
        password: Optional[str] = None
    ) -> Optional[Any]:
        """
        Получить чувствительные данные
        
        Args:
            key: Ключ хранения
            password: Пароль (если данные защищены)
        
        Returns:
            Расшифрованные данные или None
        """
        if key not in self.storage:
            return None
        
        try:
            stored = self.storage[key]
            encrypted = stored["encrypted"]
            
            # Расшифровываем
            if stored.get("protected") and password:
                json_data = self.encryption.decrypt_private_key(encrypted, password)
            else:
                json_data = self.encryption.decrypt_data(encrypted)
            
            # Десериализуем
            return json.loads(json_data)
        
        except Exception:
            return None
    
    def delete_sensitive_data(self, key: str) -> bool:
        """Удалить чувствительные данные"""
        
        if key in self.storage:
            del self.storage[key]
            return True
        
        return False
    
    def list_keys(self) -> List[str]:
        """Список всех ключей"""
        return list(self.storage.keys())


class AccessControl:
    """Контроль доступа"""
    
    def __init__(self):
        self.permissions = {}
        self.roles = {
            "admin": ["read", "write", "delete", "manage_users"],
            "user": ["read", "write"],
            "viewer": ["read"],
        }
    
    def assign_role(self, user_id: str, role: str):
        """Назначить роль пользователю"""
        
        if role in self.roles:
            self.permissions[user_id] = self.roles[role]
    
    def grant_permission(self, user_id: str, permission: str):
        """Выдать разрешение пользователю"""
        
        if user_id not in self.permissions:
            self.permissions[user_id] = []
        
        if permission not in self.permissions[user_id]:
            self.permissions[user_id].append(permission)
    
    def revoke_permission(self, user_id: str, permission: str):
        """Отозвать разрешение"""
        
        if user_id in self.permissions and permission in self.permissions[user_id]:
            self.permissions[user_id].remove(permission)
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Проверить разрешение"""
        
        if user_id not in self.permissions:
            return False
        
        return permission in self.permissions[user_id]
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Получить все разрешения пользователя"""
        
        return self.permissions.get(user_id, [])


class AuditLogger:
    """Логгер аудита"""
    
    def __init__(self):
        self.logs = []
    
    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Логировать действие
        
        Args:
            user_id: ID пользователя
            action: Действие (read, write, delete, etc.)
            resource: Ресурс (wallet, key, etc.)
            status: Статус (success, failed, denied)
            details: Дополнительные детали
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "status": status,
            "details": details or {},
        }
        
        self.logs.append(log_entry)
    
    def get_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Получить логи с фильтрацией"""
        
        filtered_logs = self.logs
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log["user_id"] == user_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if log["action"] == action]
        
        if start_time:
            filtered_logs = [
                log for log in filtered_logs
                if datetime.fromisoformat(log["timestamp"]) >= start_time
            ]
        
        if end_time:
            filtered_logs = [
                log for log in filtered_logs
                if datetime.fromisoformat(log["timestamp"]) <= end_time
            ]
        
        return filtered_logs
    
    def get_suspicious_activities(self) -> List[Dict[str, Any]]:
        """Получить подозрительные активности"""
        
        suspicious = []
        
        # Множественные неудачные попытки
        failed_attempts = {}
        for log in self.logs:
            if log["status"] == "failed":
                user_id = log["user_id"]
                if user_id not in failed_attempts:
                    failed_attempts[user_id] = []
                failed_attempts[user_id].append(log)
        
        for user_id, attempts in failed_attempts.items():
            if len(attempts) >= 5:
                suspicious.append({
                    "type": "multiple_failed_attempts",
                    "user_id": user_id,
                    "count": len(attempts),
                    "severity": "high",
                })
        
        # Доступ в необычное время
        for log in self.logs:
            timestamp = datetime.fromisoformat(log["timestamp"])
            hour = timestamp.hour
            
            if hour < 6 or hour > 23:  # Ночное время
                suspicious.append({
                    "type": "unusual_time_access",
                    "user_id": log["user_id"],
                    "timestamp": log["timestamp"],
                    "severity": "medium",
                })
        
        return suspicious


class SecurityScanner:
    """Сканер безопасности"""
    
    def __init__(self):
        pass
    
    def scan_private_key(self, private_key: str) -> Dict[str, Any]:
        """
        Сканировать приватный ключ на безопасность
        
        Returns:
            {
                "secure": bool,
                "issues": [...],
                "recommendations": [...]
            }
        """
        result = {
            "secure": True,
            "issues": [],
            "recommendations": [],
        }
        
        # 1. Проверка длины
        if len(private_key) < 64:
            result["secure"] = False
            result["issues"].append("Приватный ключ слишком короткий")
        
        # 2. Проверка на простые паттерны
        if private_key == "0" * len(private_key):
            result["secure"] = False
            result["issues"].append("Приватный ключ состоит только из нулей")
        
        if private_key == "1" * len(private_key):
            result["secure"] = False
            result["issues"].append("Приватный ключ состоит только из единиц")
        
        # 3. Проверка энтропии
        unique_chars = len(set(private_key))
        if unique_chars < 10:
            result["secure"] = False
            result["issues"].append("Низкая энтропия приватного ключа")
        
        # Рекомендации
        if not result["secure"]:
            result["recommendations"].append("Сгенерируйте новый приватный ключ")
            result["recommendations"].append("Используйте криптографически стойкий генератор")
        
        result["recommendations"].append("Храните приватный ключ в зашифрованном виде")
        result["recommendations"].append("Используйте аппаратный кошелек для больших сумм")
        
        return result
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Проверить силу пароля
        
        Returns:
            {
                "strength": str (weak, medium, strong),
                "score": int (0-100),
                "issues": [...],
                "recommendations": [...]
            }
        """
        result = {
            "strength": "weak",
            "score": 0,
            "issues": [],
            "recommendations": [],
        }
        
        score = 0
        
        # Длина
        if len(password) >= 8:
            score += 20
        else:
            result["issues"].append("Пароль слишком короткий (минимум 8 символов)")
        
        if len(password) >= 12:
            score += 10
        
        if len(password) >= 16:
            score += 10
        
        # Разнообразие символов
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if has_lower:
            score += 15
        else:
            result["issues"].append("Нет строчных букв")
        
        if has_upper:
            score += 15
        else:
            result["issues"].append("Нет заглавных букв")
        
        if has_digit:
            score += 15
        else:
            result["issues"].append("Нет цифр")
        
        if has_special:
            score += 15
        else:
            result["issues"].append("Нет специальных символов")
        
        # Общие пароли
        common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() in common_passwords:
            score = 0
            result["issues"].append("Используется распространенный пароль")
        
        result["score"] = score
        
        # Определение силы
        if score >= 80:
            result["strength"] = "strong"
        elif score >= 50:
            result["strength"] = "medium"
        else:
            result["strength"] = "weak"
        
        # Рекомендации
        if result["strength"] != "strong":
            result["recommendations"].append("Используйте минимум 12 символов")
            result["recommendations"].append("Комбинируйте буквы, цифры и спецсимволы")
            result["recommendations"].append("Избегайте распространенных паролей")
            result["recommendations"].append("Используйте менеджер паролей")
        
        return result
