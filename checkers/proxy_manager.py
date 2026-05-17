# -*- coding: utf-8 -*-
"""
Proxy Manager v1.0.69
Управление прокси: загрузка из файла, ротация, валидация
"""

import os
import random
from typing import List, Optional


class ProxyManager:
    """Менеджер прокси с поддержкой загрузки из файла и ротации"""
    
    def __init__(self):
        self.proxies: List[str] = []
        self.current_index = 0
        self.rotation_mode = "sequential"  # sequential, random
        self.stats = {
            "total_loaded": 0,
            "valid_proxies": 0,
            "invalid_proxies": 0,
            "current_proxy": None,
        }
    
    def load_proxies(self, proxy_input: str) -> bool:
        """
        Загружает прокси из строки или файла
        
        Args:
            proxy_input: Прокси строка или путь к файлу
        
        Returns:
            True если прокси загружены успешно
        """
        
        if not proxy_input:
            return False
        
        proxy_input = proxy_input.strip()
        
        # Проверяем это файл или прокси строка
        if self._is_file(proxy_input):
            return self._load_from_file(proxy_input)
        else:
            # Одиночный прокси
            if self._validate_proxy(proxy_input):
                self.proxies = [proxy_input]
                self.stats["total_loaded"] = 1
                self.stats["valid_proxies"] = 1
                return True
            else:
                self.stats["invalid_proxies"] = 1
                return False
    
    def _is_file(self, path: str) -> bool:
        """Проверяет является ли строка путем к файлу"""
        
        # Проверяем расширения файлов
        if path.endswith(('.txt', '.list', '.proxy', '.proxies')):
            return True
        
        # Проверяем существование файла
        if os.path.isfile(path):
            return True
        
        # Проверяем наличие слэшей (путь к файлу)
        if '/' in path or '\\' in path:
            return True
        
        return False
    
    def _load_from_file(self, filepath: str) -> bool:
        """Загружает прокси из файла"""
        
        try:
            if not os.path.exists(filepath):
                print(f"❌ Файл не найден: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.proxies = []
            
            for line in lines:
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                
                # Валидируем прокси
                if self._validate_proxy(line):
                    self.proxies.append(line)
                    self.stats["valid_proxies"] += 1
                else:
                    self.stats["invalid_proxies"] += 1
            
            self.stats["total_loaded"] = len(self.proxies)
            
            if self.proxies:
                print(f"✅ Загружено {len(self.proxies)} прокси из {filepath}")
                return True
            else:
                print(f"❌ Не найдено валидных прокси в {filepath}")
                return False
        
        except Exception as e:
            print(f"❌ Ошибка загрузки прокси из файла: {e}")
            return False
    
    def _validate_proxy(self, proxy: str) -> bool:
        """Валидирует формат прокси"""
        
        if not proxy:
            return False
        
        # Базовая валидация
        # Должен содержать : (разделитель ip:port)
        if ':' not in proxy:
            return False
        
        # Проверяем поддерживаемые протоколы
        valid_protocols = ['http://', 'https://', 'socks4://', 'socks5://']
        
        # Если есть протокол - проверяем что он поддерживается
        if '://' in proxy:
            has_valid_protocol = any(proxy.startswith(p) for p in valid_protocols)
            if not has_valid_protocol:
                return False
        
        # Базовая проверка формата ip:port или protocol://ip:port
        parts = proxy.split(':')
        if len(parts) < 2:
            return False
        
        return True
    
    def get_next_proxy(self) -> Optional[str]:
        """
        Возвращает следующий прокси из списка
        
        Returns:
            Прокси строка или None если список пуст
        """
        
        if not self.proxies:
            return None
        
        if self.rotation_mode == "random":
            proxy = random.choice(self.proxies)
        else:  # sequential
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
        
        self.stats["current_proxy"] = proxy
        return proxy
    
    def get_random_proxy(self) -> Optional[str]:
        """Возвращает случайный прокси из списка"""
        
        if not self.proxies:
            return None
        
        proxy = random.choice(self.proxies)
        self.stats["current_proxy"] = proxy
        return proxy
    
    def set_rotation_mode(self, mode: str):
        """
        Устанавливает режим ротации прокси
        
        Args:
            mode: "sequential" или "random"
        """
        
        if mode in ["sequential", "random"]:
            self.rotation_mode = mode
    
    def get_proxy_count(self) -> int:
        """Возвращает количество загруженных прокси"""
        return len(self.proxies)
    
    def get_stats(self) -> dict:
        """Возвращает статистику"""
        return self.stats.copy()
    
    def reset(self):
        """Сбрасывает менеджер прокси"""
        self.proxies = []
        self.current_index = 0
        self.stats = {
            "total_loaded": 0,
            "valid_proxies": 0,
            "invalid_proxies": 0,
            "current_proxy": None,
        }


# Глобальный менеджер прокси
_proxy_manager = ProxyManager()


def load_proxies(proxy_input: str) -> bool:
    """
    Загружает прокси из строки или файла
    
    Args:
        proxy_input: Прокси строка или путь к файлу
    
    Returns:
        True если прокси загружены успешно
    """
    return _proxy_manager.load_proxies(proxy_input)


def get_next_proxy() -> Optional[str]:
    """Возвращает следующий прокси"""
    return _proxy_manager.get_next_proxy()


def get_random_proxy() -> Optional[str]:
    """Возвращает случайный прокси"""
    return _proxy_manager.get_random_proxy()


def get_proxy_count() -> int:
    """Возвращает количество загруженных прокси"""
    return _proxy_manager.get_proxy_count()


def get_stats() -> dict:
    """Возвращает статистику"""
    return _proxy_manager.get_stats()


def set_rotation_mode(mode: str):
    """Устанавливает режим ротации"""
    _proxy_manager.set_rotation_mode(mode)


def reset():
    """Сбрасывает менеджер прокси"""
    _proxy_manager.reset()


# Примеры использования
if __name__ == "__main__":
    print("=" * 70)
    print("PROXY MANAGER - ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ")
    print("=" * 70)
    
    # Пример 1: Загрузка одного прокси
    print("\n1. Загрузка одного прокси:")
    if load_proxies("socks5://123.45.67.89:1080"):
        print(f"   Загружено прокси: {get_proxy_count()}")
        print(f"   Текущий прокси: {get_next_proxy()}")
    
    # Пример 2: Загрузка из файла
    print("\n2. Загрузка из файла:")
    
    # Создаем тестовый файл
    with open("test_proxies.txt", "w") as f:
        f.write("# Тестовые прокси\n")
        f.write("http://123.45.67.89:8080\n")
        f.write("socks5://user:pass@98.76.54.32:1080\n")
        f.write("socks4://11.22.33.44:1080\n")
        f.write("\n")  # Пустая строка
        f.write("# Еще прокси\n")
        f.write("https://55.66.77.88:443\n")
    
    reset()  # Сбрасываем предыдущие прокси
    
    if load_proxies("test_proxies.txt"):
        stats = get_stats()
        print(f"   Всего загружено: {stats['total_loaded']}")
        print(f"   Валидных: {stats['valid_proxies']}")
        print(f"   Невалидных: {stats['invalid_proxies']}")
        
        print("\n   Ротация (sequential):")
        for i in range(5):
            print(f"   {i+1}. {get_next_proxy()}")
        
        print("\n   Ротация (random):")
        set_rotation_mode("random")
        for i in range(5):
            print(f"   {i+1}. {get_random_proxy()}")
    
    # Удаляем тестовый файл
    import os
    if os.path.exists("test_proxies.txt"):
        os.remove("test_proxies.txt")
    
    print("\n" + "=" * 70)
