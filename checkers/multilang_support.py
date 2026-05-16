# -*- coding: utf-8 -*-
"""
Multi-Language Support v1.0.64
Поддержка множества языков
"""

from typing import Dict, Any, Optional


class MultiLanguageSupport:
    """Поддержка множества языков"""
    
    # Словари переводов
    TRANSLATIONS = {
        "en": {
            "app_title": "MultiChecker Pro",
            "start": "Start",
            "stop": "Stop",
            "clear": "Clear",
            "export": "Export",
            "import": "Import File",
            "valid": "Valid",
            "invalid": "Invalid",
            "errors": "Errors",
            "total": "Total",
            "balance": "Balance",
            "address": "Address",
            "email": "Email",
            "password": "Password",
            "seed_phrase": "Seed Phrase",
            "private_key": "Private Key",
            "checking": "Checking...",
            "completed": "Completed",
            "found": "Found",
            "not_found": "Not Found",
            "error": "Error",
            "success": "Success",
            "warning": "Warning",
            "info": "Information",
            "settings": "Settings",
            "threads": "Threads",
            "timeout": "Timeout",
            "proxy": "Proxy",
            "results": "Results",
            "statistics": "Statistics",
            "filter": "Filter",
            "all": "All",
            "with_balance": "With Balance",
            "no_balance": "No Balance",
            "export_txt": "Export TXT",
            "export_json": "Export JSON",
            "export_csv": "Export CSV",
            "export_excel": "Export Excel",
        },
        
        "ru": {
            "app_title": "MultiChecker Pro",
            "start": "Старт",
            "stop": "Стоп",
            "clear": "Очистить",
            "export": "Экспорт",
            "import": "Импорт файла",
            "valid": "Валидных",
            "invalid": "Невалидных",
            "errors": "Ошибок",
            "total": "Всего",
            "balance": "Баланс",
            "address": "Адрес",
            "email": "Email",
            "password": "Пароль",
            "seed_phrase": "Seed фраза",
            "private_key": "Приватный ключ",
            "checking": "Проверка...",
            "completed": "Завершено",
            "found": "Найдено",
            "not_found": "Не найдено",
            "error": "Ошибка",
            "success": "Успех",
            "warning": "Предупреждение",
            "info": "Информация",
            "settings": "Настройки",
            "threads": "Потоки",
            "timeout": "Таймаут",
            "proxy": "Прокси",
            "results": "Результаты",
            "statistics": "Статистика",
            "filter": "Фильтр",
            "all": "Все",
            "with_balance": "С балансом",
            "no_balance": "Без баланса",
            "export_txt": "Экспорт TXT",
            "export_json": "Экспорт JSON",
            "export_csv": "Экспорт CSV",
            "export_excel": "Экспорт Excel",
        },
        
        "zh": {
            "app_title": "MultiChecker Pro",
            "start": "开始",
            "stop": "停止",
            "clear": "清除",
            "export": "导出",
            "import": "导入文件",
            "valid": "有效",
            "invalid": "无效",
            "errors": "错误",
            "total": "总计",
            "balance": "余额",
            "address": "地址",
            "email": "邮箱",
            "password": "密码",
            "seed_phrase": "助记词",
            "private_key": "私钥",
            "checking": "检查中...",
            "completed": "完成",
            "found": "找到",
            "not_found": "未找到",
            "error": "错误",
            "success": "成功",
            "warning": "警告",
            "info": "信息",
            "settings": "设置",
            "threads": "线程",
            "timeout": "超时",
            "proxy": "代理",
            "results": "结果",
            "statistics": "统计",
            "filter": "过滤",
            "all": "全部",
            "with_balance": "有余额",
            "no_balance": "无余额",
            "export_txt": "导出 TXT",
            "export_json": "导出 JSON",
            "export_csv": "导出 CSV",
            "export_excel": "导出 Excel",
        },
        
        "es": {
            "app_title": "MultiChecker Pro",
            "start": "Iniciar",
            "stop": "Detener",
            "clear": "Limpiar",
            "export": "Exportar",
            "import": "Importar archivo",
            "valid": "Válido",
            "invalid": "Inválido",
            "errors": "Errores",
            "total": "Total",
            "balance": "Saldo",
            "address": "Dirección",
            "email": "Correo",
            "password": "Contraseña",
            "seed_phrase": "Frase semilla",
            "private_key": "Clave privada",
            "checking": "Verificando...",
            "completed": "Completado",
            "found": "Encontrado",
            "not_found": "No encontrado",
            "error": "Error",
            "success": "Éxito",
            "warning": "Advertencia",
            "info": "Información",
            "settings": "Configuración",
            "threads": "Hilos",
            "timeout": "Tiempo de espera",
            "proxy": "Proxy",
            "results": "Resultados",
            "statistics": "Estadísticas",
            "filter": "Filtro",
            "all": "Todos",
            "with_balance": "Con saldo",
            "no_balance": "Sin saldo",
            "export_txt": "Exportar TXT",
            "export_json": "Exportar JSON",
            "export_csv": "Exportar CSV",
            "export_excel": "Exportar Excel",
        },
        
        "fr": {
            "app_title": "MultiChecker Pro",
            "start": "Démarrer",
            "stop": "Arrêter",
            "clear": "Effacer",
            "export": "Exporter",
            "import": "Importer fichier",
            "valid": "Valide",
            "invalid": "Invalide",
            "errors": "Erreurs",
            "total": "Total",
            "balance": "Solde",
            "address": "Adresse",
            "email": "Email",
            "password": "Mot de passe",
            "seed_phrase": "Phrase de récupération",
            "private_key": "Clé privée",
            "checking": "Vérification...",
            "completed": "Terminé",
            "found": "Trouvé",
            "not_found": "Non trouvé",
            "error": "Erreur",
            "success": "Succès",
            "warning": "Avertissement",
            "info": "Information",
            "settings": "Paramètres",
            "threads": "Threads",
            "timeout": "Délai d'attente",
            "proxy": "Proxy",
            "results": "Résultats",
            "statistics": "Statistiques",
            "filter": "Filtre",
            "all": "Tous",
            "with_balance": "Avec solde",
            "no_balance": "Sans solde",
            "export_txt": "Exporter TXT",
            "export_json": "Exporter JSON",
            "export_csv": "Exporter CSV",
            "export_excel": "Exporter Excel",
        },
        
        "de": {
            "app_title": "MultiChecker Pro",
            "start": "Start",
            "stop": "Stopp",
            "clear": "Löschen",
            "export": "Exportieren",
            "import": "Datei importieren",
            "valid": "Gültig",
            "invalid": "Ungültig",
            "errors": "Fehler",
            "total": "Gesamt",
            "balance": "Guthaben",
            "address": "Adresse",
            "email": "E-Mail",
            "password": "Passwort",
            "seed_phrase": "Seed-Phrase",
            "private_key": "Privater Schlüssel",
            "checking": "Überprüfung...",
            "completed": "Abgeschlossen",
            "found": "Gefunden",
            "not_found": "Nicht gefunden",
            "error": "Fehler",
            "success": "Erfolg",
            "warning": "Warnung",
            "info": "Information",
            "settings": "Einstellungen",
            "threads": "Threads",
            "timeout": "Zeitüberschreitung",
            "proxy": "Proxy",
            "results": "Ergebnisse",
            "statistics": "Statistiken",
            "filter": "Filter",
            "all": "Alle",
            "with_balance": "Mit Guthaben",
            "no_balance": "Ohne Guthaben",
            "export_txt": "TXT exportieren",
            "export_json": "JSON exportieren",
            "export_csv": "CSV exportieren",
            "export_excel": "Excel exportieren",
        },
    }
    
    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang
        self.available_languages = list(self.TRANSLATIONS.keys())
    
    def set_language(self, lang_code: str) -> bool:
        """
        Установить язык
        
        Args:
            lang_code: Код языка (en, ru, zh, es, fr, de)
        
        Returns:
            True если язык установлен успешно
        """
        
        if lang_code in self.TRANSLATIONS:
            self.current_lang = lang_code
            return True
        
        return False
    
    def get_text(self, key: str, lang: Optional[str] = None) -> str:
        """
        Получить перевод текста
        
        Args:
            key: Ключ перевода
            lang: Код языка (если None - используется текущий)
        
        Returns:
            Переведенный текст
        """
        
        if lang is None:
            lang = self.current_lang
        
        translations = self.TRANSLATIONS.get(lang, self.TRANSLATIONS["en"])
        
        return translations.get(key, key)
    
    def t(self, key: str) -> str:
        """Короткий алиас для get_text"""
        return self.get_text(key)
    
    def get_available_languages(self) -> Dict[str, str]:
        """Получить список доступных языков"""
        
        return {
            "en": "English",
            "ru": "Русский",
            "zh": "中文",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
        }
    
    def detect_system_language(self) -> str:
        """Определить язык системы"""
        
        import locale
        
        try:
            system_lang = locale.getdefaultlocale()[0]
            
            if system_lang:
                # Извлекаем код языка (первые 2 символа)
                lang_code = system_lang[:2].lower()
                
                # Проверяем поддерживается ли язык
                if lang_code in self.TRANSLATIONS:
                    return lang_code
        
        except Exception:
            pass
        
        # По умолчанию английский
        return "en"
    
    def translate_dict(self, data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Перевести ключи словаря
        
        Args:
            data: Исходный словарь
            mapping: Маппинг ключей {old_key: translation_key}
        
        Returns:
            Словарь с переведенными ключами
        """
        
        translated = {}
        
        for key, value in data.items():
            # Получаем ключ перевода
            trans_key = mapping.get(key, key)
            
            # Переводим
            translated_key = self.get_text(trans_key)
            
            translated[translated_key] = value
        
        return translated
    
    def format_number(self, number: float, decimals: int = 2) -> str:
        """Форматировать число с учетом локали"""
        
        # Разделители для разных языков
        separators = {
            "en": (",", "."),  # 1,000.50
            "ru": (" ", ","),  # 1 000,50
            "zh": (",", "."),  # 1,000.50
            "es": (".", ","),  # 1.000,50
            "fr": (" ", ","),  # 1 000,50
            "de": (".", ","),  # 1.000,50
        }
        
        thousands_sep, decimal_sep = separators.get(self.current_lang, (",", "."))
        
        # Форматируем число
        if decimals == 0:
            formatted = f"{int(number):,}".replace(",", thousands_sep)
        else:
            formatted = f"{number:,.{decimals}f}"
            formatted = formatted.replace(",", "TEMP").replace(".", decimal_sep).replace("TEMP", thousands_sep)
        
        return formatted
    
    def format_currency(self, amount: float, currency: str = "USD") -> str:
        """Форматировать валюту"""
        
        formatted_amount = self.format_number(amount, 2)
        
        # Позиция символа валюты
        currency_positions = {
            "en": f"${formatted_amount}",
            "ru": f"{formatted_amount} $",
            "zh": f"${formatted_amount}",
            "es": f"{formatted_amount} $",
            "fr": f"{formatted_amount} $",
            "de": f"{formatted_amount} $",
        }
        
        return currency_positions.get(self.current_lang, f"${formatted_amount}")


# Глобальный экземпляр
_ml_support = MultiLanguageSupport()


def set_language(lang_code: str) -> bool:
    """Установить язык (глобальная функция)"""
    return _ml_support.set_language(lang_code)


def t(key: str) -> str:
    """Получить перевод (глобальная функция)"""
    return _ml_support.get_text(key)


def get_current_language() -> str:
    """Получить текущий язык"""
    return _ml_support.current_lang


def get_available_languages() -> Dict[str, str]:
    """Получить список доступных языков"""
    return _ml_support.get_available_languages()
