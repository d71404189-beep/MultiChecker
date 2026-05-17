# -*- coding: utf-8 -*-
"""
Wallet Exporter v1.0.89
Экспорт найденных кошельков с балансом в удобные форматы.

Форматы:
  - found_wallets.txt  — детальный отчёт
  - found_wallets.csv  — для Excel
  - found_wallets.json — полные данные
  - found_seeds.txt    — только seed фразы с балансом
  - found_keys.txt     — только приватные ключи с балансом
"""

import json
import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


# Минимальный баланс для попадания в экспорт (USD)
DEFAULT_MIN_USD = 0.0


def _estimate_usd(result: dict) -> float:
    """Извлекает USD баланс из результата проверки."""
    info = result.get("info", {})
    # Прямые поля
    for field in ("total_usd", "balance_usd"):
        val = info.get(field)
        if val and float(val) > 0:
            return float(val)
    # Балансы монет с примерными ценами
    approx = {
        "balance_btc": 78000, "balance_eth": 2500, "balance_sol": 150,
        "balance_bnb": 300,   "balance_trx": 0.12, "balance_ton": 5,
        "balance_ltc": 80,    "balance_xrp": 0.6,  "balance_doge": 0.15,
        "balance_ada": 0.5,   "balance_dash": 30,
    }
    total = 0.0
    for key, price in approx.items():
        val = info.get(key)
        if val and isinstance(val, (int, float)) and val > 0:
            total += float(val) * price
    # Токены
    total += float(info.get("token_usd", 0) or 0)
    # Мультичейн
    for chain_data in info.get("multichain", {}).values():
        if isinstance(chain_data, dict):
            total += float(chain_data.get("usd", 0) or 0)
    return total


def _get_credential(result: dict) -> str:
    """Извлекает основной credential (seed/privkey/address) из результата."""
    rtype = result.get("type", "")
    info  = result.get("info", {})
    inp   = result.get("input", "")

    if rtype == "seed":
        return info.get("mnemonic", inp)
    elif rtype in ("privkey_hex", "privkey_wif"):
        return info.get("formats", {}).get("hex_with_0x", inp)
    elif rtype == "wallet":
        return inp
    elif rtype == "exchange":
        login = info.get("login", "")
        pwd   = info.get("password", "")
        ex    = info.get("exchange", "")
        return f"{ex}:{login}:{pwd}" if ex else f"{login}:{pwd}"
    return inp


def _get_auth_instruction(result: dict) -> str:
    """Возвращает инструкцию по входу в кошелёк."""
    auth = result.get("info", {}).get("auth", {})
    if not auth:
        return ""
    return (
        f"Тип: {auth.get('auth_type', '')} | "
        f"Кошельки: {auth.get('wallets', '')} | "
        f"Как: {auth.get('how', '')}"
    )


class WalletExporter:
    """Собирает результаты с балансом и экспортирует в файлы."""

    def __init__(self, min_usd: float = DEFAULT_MIN_USD):
        self.min_usd = min_usd
        self._results: List[Dict[str, Any]] = []

    def add_result(self, result: dict) -> bool:
        """
        Добавить результат если у него есть баланс.
        Возвращает True если добавлен.
        """
        if not result or not result.get("exists"):
            return False
        usd = _estimate_usd(result)
        if usd < self.min_usd:
            return False
        self._results.append({
            "result":    result,
            "usd":       usd,
            "timestamp": datetime.now().isoformat(),
        })
        return True

    def add_all(self, results: List[dict]) -> int:
        """Добавить список результатов. Возвращает количество добавленных."""
        return sum(1 for r in results if self.add_result(r))

    @property
    def count(self) -> int:
        return len(self._results)

    @property
    def total_usd(self) -> float:
        return sum(e["usd"] for e in self._results)

    def sorted_results(self) -> List[Dict]:
        """Результаты отсортированные по убыванию баланса."""
        return sorted(self._results, key=lambda x: -x["usd"])

    # ── Экспорт ───────────────────────────────────────────────────────────

    def export_txt(self, path: str) -> int:
        """Детальный TXT отчёт."""
        entries = self.sorted_results()
        if not entries:
            return 0
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("🔑 НАЙДЕННЫЕ КОШЕЛЬКИ С БАЛАНСОМ\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего: {len(entries)} | Суммарно: ~${self.total_usd:,.2f}\n")
            f.write("=" * 70 + "\n\n")
            for i, entry in enumerate(entries, 1):
                r    = entry["result"]
                usd  = entry["usd"]
                cred = _get_credential(r)
                auth = _get_auth_instruction(r)
                msg  = r.get("info", {}).get("message", "")
                wtype = r.get("wallet_type") or r.get("type", "")
                f.write(f"{'─'*70}\n")
                f.write(f"#{i} | {wtype.upper()} | ~${usd:,.2f}\n")
                f.write(f"Credential: {cred}\n")
                f.write(f"Баланс:     {msg}\n")
                if auth:
                    f.write(f"Вход:       {auth}\n")
                f.write(f"Время:      {entry['timestamp']}\n\n")
        return len(entries)

    def export_csv(self, path: str) -> int:
        """CSV для Excel."""
        entries = self.sorted_results()
        if not entries:
            return 0
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Type", "Credential", "Balance USD",
                "Message", "Auth Type", "Wallets", "Timestamp"
            ])
            for entry in entries:
                r    = entry["result"]
                auth = r.get("info", {}).get("auth", {})
                writer.writerow([
                    r.get("wallet_type") or r.get("type", ""),
                    _get_credential(r),
                    f"{entry['usd']:.2f}",
                    r.get("info", {}).get("message", ""),
                    auth.get("auth_type", ""),
                    auth.get("wallets", ""),
                    entry["timestamp"],
                ])
        return len(entries)

    def export_json(self, path: str) -> int:
        """JSON с полными данными."""
        entries = self.sorted_results()
        if not entries:
            return 0
        data = {
            "exported_at":    datetime.now().isoformat(),
            "total_wallets":  len(entries),
            "total_usd":      self.total_usd,
            "wallets": [
                {
                    "type":       e["result"].get("wallet_type") or e["result"].get("type", ""),
                    "credential": _get_credential(e["result"]),
                    "usd":        e["usd"],
                    "message":    e["result"].get("info", {}).get("message", ""),
                    "auth":       e["result"].get("info", {}).get("auth", {}),
                    "timestamp":  e["timestamp"],
                    "raw":        e["result"],
                }
                for e in entries
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return len(entries)

    def export_seeds_only(self, path: str) -> int:
        """Только seed фразы с балансом — для быстрого импорта."""
        entries = [e for e in self.sorted_results() if e["result"].get("type") == "seed"]
        if not entries:
            return 0
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Seed фразы с балансом | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Всего: {len(entries)} | Суммарно: ~${sum(e['usd'] for e in entries):,.2f}\n\n")
            for entry in entries:
                r    = entry["result"]
                seed = r.get("info", {}).get("mnemonic") or r.get("input", "")
                usd  = entry["usd"]
                msg  = r.get("info", {}).get("message", "")
                f.write(f"# ~${usd:,.2f} | {msg[:80]}\n")
                f.write(f"{seed}\n\n")
        return len(entries)

    def export_keys_only(self, path: str) -> int:
        """Только приватные ключи с балансом."""
        entries = [
            e for e in self.sorted_results()
            if e["result"].get("type") in ("privkey_hex", "privkey_wif")
        ]
        if not entries:
            return 0
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Приватные ключи с балансом | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Всего: {len(entries)} | Суммарно: ~${sum(e['usd'] for e in entries):,.2f}\n\n")
            for entry in entries:
                r   = entry["result"]
                key = _get_credential(r)
                usd = entry["usd"]
                msg = r.get("info", {}).get("message", "")
                f.write(f"# ~${usd:,.2f} | {msg[:80]}\n")
                f.write(f"{key}\n\n")
        return len(entries)

    def export_all(self, prefix: str = "found") -> Dict[str, int]:
        """
        Экспортирует все форматы сразу.
        Возвращает {filename: count}.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}

        fn_txt = f"{prefix}_wallets_{ts}.txt"
        results[fn_txt] = self.export_txt(fn_txt)

        fn_csv = f"{prefix}_wallets_{ts}.csv"
        results[fn_csv] = self.export_csv(fn_csv)

        fn_json = f"{prefix}_wallets_{ts}.json"
        results[fn_json] = self.export_json(fn_json)

        fn_seeds = f"{prefix}_seeds_{ts}.txt"
        cnt = self.export_seeds_only(fn_seeds)
        if cnt > 0:
            results[fn_seeds] = cnt

        fn_keys = f"{prefix}_keys_{ts}.txt"
        cnt = self.export_keys_only(fn_keys)
        if cnt > 0:
            results[fn_keys] = cnt

        return results

    def summary(self) -> str:
        if not self._results:
            return "Нет кошельков с балансом"
        by_type: Dict[str, int] = {}
        for e in self._results:
            t = e["result"].get("wallet_type") or e["result"].get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        type_str = ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items()))
        return (
            f"💰 Найдено: {self.count} кошельков | "
            f"Суммарно: ~${self.total_usd:,.2f} | {type_str}"
        )


# Глобальный экспортер (используется из main.py)
global_wallet_exporter = WalletExporter(min_usd=0.0)
