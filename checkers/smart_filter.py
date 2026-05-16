# -*- coding: utf-8 -*-
"""
Smart Filter v1.0.58
Умная фильтрация результатов проверки
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional


class SmartFilter:
    """Умная фильтрация и автосохранение результатов"""
    
    def __init__(self):
        self.min_usd_threshold = 0.0  # Минимальный порог USD
        self.auto_save_enabled = True
        self.sound_enabled = True
        self.hot_finds_threshold = 1000.0  # Порог для "горячих" находок
        
        # Пути для автосохранения
        self.output_dir = "results"
        self.hot_finds_file = "hot_finds.json"
        self.valid_with_balance_file = "valid_with_balance.json"
        
        # Создаем директорию если не существует
        os.makedirs(self.output_dir, exist_ok=True)
    
    def filter_results(
        self,
        results: List[Dict[str, Any]],
        min_usd: float = 0.0,
        only_with_balance: bool = False,
        only_hot: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация результатов по критериям
        
        Args:
            results: Список результатов проверки
            min_usd: Минимальная сумма в USD
            only_with_balance: Только с балансом
            only_hot: Только "горячие" находки (>$1000)
        
        Returns:
            Отфильтрованный список результатов
        """
        filtered = []
        
        for result in results:
            # Пропускаем невалидные
            if not result.get("exists"):
                continue
            
            # Получаем USD ценность
            usd_value = self._get_usd_value(result)
            
            # Фильтр по минимальной сумме
            if min_usd > 0 and usd_value < min_usd:
                continue
            
            # Фильтр "только с балансом"
            if only_with_balance and usd_value <= 0:
                continue
            
            # Фильтр "только горячие"
            if only_hot and usd_value < self.hot_finds_threshold:
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _get_usd_value(self, result: Dict[str, Any]) -> float:
        """Получить USD ценность из результата"""
        info = result.get("info", {})
        
        # Прямое значение USD
        if "total_usd" in info:
            return float(info["total_usd"])
        
        if "balance_usd" in info:
            return float(info["balance_usd"])
        
        # Вычисляем из балансов
        total = 0.0
        
        # Примерные цены (можно обновлять)
        prices = {
            "balance_btc": 45000,
            "balance_eth": 2500,
            "balance_sol": 100,
            "balance_bnb": 300,
            "balance_trx": 0.1,
            "balance_ada": 0.5,
            "balance_ltc": 80,
            "balance_xrp": 0.6,
            "balance_doge": 0.15,
        }
        
        for key, price in prices.items():
            if key in info:
                balance = float(info[key])
                total += balance * price
        
        # Токены
        if "token_usd" in info:
            total += float(info["token_usd"])
        
        return total
    
    def auto_save_result(self, result: Dict[str, Any]) -> None:
        """
        Автоматическое сохранение результата
        
        Args:
            result: Результат проверки
        """
        if not self.auto_save_enabled:
            return
        
        if not result.get("exists"):
            return
        
        usd_value = self._get_usd_value(result)
        
        # Сохраняем все с балансом
        if usd_value > 0:
            self._append_to_file(
                os.path.join(self.output_dir, self.valid_with_balance_file),
                result
            )
        
        # Сохраняем "горячие" находки отдельно
        if usd_value >= self.hot_finds_threshold:
            self._append_to_file(
                os.path.join(self.output_dir, self.hot_finds_file),
                result
            )
            
            # Воспроизводим звук
            if self.sound_enabled:
                self._play_sound()
    
    def _append_to_file(self, filepath: str, result: Dict[str, Any]) -> None:
        """Добавить результат в файл"""
        try:
            # Читаем существующие
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Добавляем timestamp
            result_with_time = result.copy()
            result_with_time["saved_at"] = datetime.now().isoformat()
            
            # Добавляем новый
            data.append(result_with_time)
            
            # Сохраняем
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Error saving to {filepath}: {e}")
    
    def _play_sound(self) -> None:
        """Воспроизвести звуковое уведомление"""
        try:
            import winsound
            # Системный звук "восклицание"
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            # Если не Windows или ошибка - пропускаем
            pass
    
    def get_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Получить статистику по результатам
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            "total": len(results),
            "valid": 0,
            "with_balance": 0,
            "hot_finds": 0,
            "total_usd": 0.0,
            "by_threshold": {
                "0-10": 0,
                "10-100": 0,
                "100-1000": 0,
                "1000-10000": 0,
                "10000+": 0,
            },
            "top_finds": [],
        }
        
        valid_results = []
        
        for result in results:
            if result.get("exists"):
                stats["valid"] += 1
                usd_value = self._get_usd_value(result)
                
                if usd_value > 0:
                    stats["with_balance"] += 1
                    stats["total_usd"] += usd_value
                    
                    # Категоризация по порогам
                    if usd_value < 10:
                        stats["by_threshold"]["0-10"] += 1
                    elif usd_value < 100:
                        stats["by_threshold"]["10-100"] += 1
                    elif usd_value < 1000:
                        stats["by_threshold"]["100-1000"] += 1
                    elif usd_value < 10000:
                        stats["by_threshold"]["1000-10000"] += 1
                    else:
                        stats["by_threshold"]["10000+"] += 1
                    
                    if usd_value >= self.hot_finds_threshold:
                        stats["hot_finds"] += 1
                    
                    valid_results.append({
                        "input": result.get("input", ""),
                        "usd_value": usd_value,
                        "type": result.get("type", ""),
                        "wallet_type": result.get("wallet_type", ""),
                    })
        
        # Топ-10 находок
        valid_results.sort(key=lambda x: x["usd_value"], reverse=True)
        stats["top_finds"] = valid_results[:10]
        
        return stats
    
    def export_filtered(
        self,
        results: List[Dict[str, Any]],
        filepath: str,
        format: str = "json",
        min_usd: float = 0.0
    ) -> str:
        """
        Экспорт отфильтрованных результатов
        
        Args:
            results: Результаты
            filepath: Путь для сохранения
            format: Формат (json, txt, csv)
            min_usd: Минимальный порог USD
        
        Returns:
            Сообщение о результате
        """
        filtered = self.filter_results(results, min_usd=min_usd, only_with_balance=True)
        
        if not filtered:
            return "No results matching filter criteria"
        
        try:
            if format == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(filtered, f, indent=2, ensure_ascii=False)
            
            elif format == "txt":
                with open(filepath, 'w', encoding='utf-8') as f:
                    for result in filtered:
                        inp = result.get("input", "")
                        usd = self._get_usd_value(result)
                        msg = result.get("info", {}).get("message", "")
                        f.write(f"{inp} | ${usd:.2f} | {msg}\n")
            
            elif format == "csv":
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Input", "Type", "USD Value", "Message"])
                    for result in filtered:
                        writer.writerow([
                            result.get("input", ""),
                            result.get("type", ""),
                            f"{self._get_usd_value(result):.2f}",
                            result.get("info", {}).get("message", "")
                        ])
            
            return f"Exported {len(filtered)} results to {filepath}"
        
        except Exception as e:
            return f"Export error: {e}"
