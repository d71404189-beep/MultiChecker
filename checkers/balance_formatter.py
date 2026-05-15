# -*- coding: utf-8 -*-
"""
Balance Formatter v1.0.57
Улучшенное отображение балансов: читаемый формат, цветовая подсветка
"""

from typing import Dict, Any, Optional


# ═══════════════════════════════════════════════════════════════════════════
#  BALANCE FORMATTING
# ═══════════════════════════════════════════════════════════════════════════

class BalanceFormatter:
    """Форматирование балансов для читаемого отображения"""
    
    # Минимальные значимые балансы (в USD)
    MIN_SIGNIFICANT_USD = 0.01
    
    # Цены монет для быстрого расчета (примерные)
    APPROXIMATE_PRICES = {
        "BTC": 45000,
        "ETH": 2500,
        "BNB": 300,
        "SOL": 100,
        "MATIC": 0.8,
        "AVAX": 35,
        "TRX": 0.1,
        "USDT": 1.0,
        "USDC": 1.0,
        "DAI": 1.0,
    }
    
    @staticmethod
    def format_balance(
        amount: float,
        symbol: str,
        show_usd: bool = True,
        price_usd: Optional[float] = None
    ) -> str:
        """
        Форматировать баланс в читаемый вид
        
        Args:
            amount: Количество (может быть в научной нотации)
            symbol: Символ монеты (BTC, ETH, ...)
            show_usd: Показывать USD эквивалент
            price_usd: Цена в USD (если None - используется примерная)
        
        Returns:
            str: "0.00000718 BTC (~$0.32)" или "1,234.56 USDT (~$1,234.56)"
        
        Examples:
            >>> format_balance(7.18e-06, "BTC")
            "0.00000718 BTC (~$0.32)"
            
            >>> format_balance(0.000001, "ETH")
            "0.000001 ETH (~$0.0025)"
            
            >>> format_balance(1234.56, "USDT")
            "1,234.56 USDT (~$1,234.56)"
        """
        
        # Определяем цену
        if price_usd is None:
            price_usd = BalanceFormatter.APPROXIMATE_PRICES.get(symbol.upper(), 0)
        
        # Рассчитываем USD
        usd_value = amount * price_usd
        
        # Форматируем количество
        if amount >= 1000:
            # Большие числа с запятыми: 1,234.56
            amount_str = f"{amount:,.8f}".rstrip('0').rstrip('.')
        elif amount >= 1:
            # Средние числа: 12.345678
            amount_str = f"{amount:.8f}".rstrip('0').rstrip('.')
        elif amount >= 0.0001:
            # Малые числа: 0.00012345
            amount_str = f"{amount:.8f}".rstrip('0').rstrip('.')
        else:
            # Очень малые числа: 0.00000718
            # Показываем все значимые цифры
            amount_str = f"{amount:.12f}".rstrip('0').rstrip('.')
        
        # Базовая строка
        result = f"{amount_str} {symbol.upper()}"
        
        # Добавляем USD если нужно
        if show_usd and price_usd > 0:
            if usd_value >= 1:
                usd_str = f"${usd_value:,.2f}"
            elif usd_value >= 0.01:
                usd_str = f"${usd_value:.4f}"
            else:
                usd_str = f"${usd_value:.6f}"
            
            result += f" (~{usd_str})"
        
        return result
    
    @staticmethod
    def format_balance_with_emoji(
        amount: float,
        symbol: str,
        price_usd: Optional[float] = None
    ) -> str:
        """
        Форматировать баланс с emoji индикатором ценности
        
        Returns:
            str: "💰 0.00000718 BTC (~$0.32)" или "🐋 1.5 BTC (~$67,500)"
        """
        
        if price_usd is None:
            price_usd = BalanceFormatter.APPROXIMATE_PRICES.get(symbol.upper(), 0)
        
        usd_value = amount * price_usd
        
        # Выбираем emoji по ценности
        if usd_value >= 100000:
            emoji = "🐋"  # Whale
        elif usd_value >= 10000:
            emoji = "💎"  # Diamond
        elif usd_value >= 1000:
            emoji = "💰"  # Money bag
        elif usd_value >= 100:
            emoji = "💵"  # Dollar
        elif usd_value >= 10:
            emoji = "💸"  # Money with wings
        elif usd_value >= 1:
            emoji = "🪙"  # Coin
        else:
            emoji = "🔸"  # Small diamond
        
        formatted = BalanceFormatter.format_balance(amount, symbol, True, price_usd)
        
        return f"{emoji} {formatted}"
    
    @staticmethod
    def format_scientific_notation(value: float) -> str:
        """
        Конвертировать научную нотацию в обычную
        
        Args:
            value: Число (может быть 7.18e-06)
        
        Returns:
            str: "0.00000718"
        
        Examples:
            >>> format_scientific_notation(7.18e-06)
            "0.00000718"
            
            >>> format_scientific_notation(1.5e-08)
            "0.000000015"
        """
        
        if value >= 1:
            return f"{value:.8f}".rstrip('0').rstrip('.')
        else:
            # Для малых чисел показываем все значимые цифры
            return f"{value:.12f}".rstrip('0').rstrip('.')
    
    @staticmethod
    def is_significant_balance(
        amount: float,
        symbol: str,
        price_usd: Optional[float] = None
    ) -> bool:
        """
        Проверить, является ли баланс значимым (> $0.01)
        
        Returns:
            bool: True если баланс > $0.01
        """
        
        if price_usd is None:
            price_usd = BalanceFormatter.APPROXIMATE_PRICES.get(symbol.upper(), 0)
        
        usd_value = amount * price_usd
        
        return usd_value >= BalanceFormatter.MIN_SIGNIFICANT_USD
    
    @staticmethod
    def format_multiple_balances(
        balances: Dict[str, float],
        prices: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Форматировать несколько балансов
        
        Args:
            balances: {"BTC": 0.00000718, "ETH": 0.5, "USDT": 1000}
            prices: {"BTC": 45000, "ETH": 2500, ...}
        
        Returns:
            str: Многострочный форматированный вывод
        """
        
        if not balances:
            return "No balances"
        
        lines = []
        total_usd = 0
        
        # Сортируем по USD ценности (от большего к меньшему)
        sorted_balances = []
        for symbol, amount in balances.items():
            price = prices.get(symbol) if prices else None
            if price is None:
                price = BalanceFormatter.APPROXIMATE_PRICES.get(symbol.upper(), 0)
            
            usd_value = amount * price
            sorted_balances.append((symbol, amount, price, usd_value))
        
        sorted_balances.sort(key=lambda x: x[3], reverse=True)
        
        # Форматируем каждый баланс
        for symbol, amount, price, usd_value in sorted_balances:
            # Пропускаем незначимые балансы
            if usd_value < BalanceFormatter.MIN_SIGNIFICANT_USD:
                continue
            
            formatted = BalanceFormatter.format_balance_with_emoji(amount, symbol, price)
            lines.append(formatted)
            total_usd += usd_value
        
        # Добавляем итого
        if len(lines) > 1:
            lines.append("")
            lines.append(f"💵 TOTAL: ${total_usd:,.2f}")
        
        return "\n".join(lines) if lines else "No significant balances"


# ═══════════════════════════════════════════════════════════════════════════
#  LOG COLORIZER
# ═══════════════════════════════════════════════════════════════════════════

class LogColorizer:
    """Цветовая подсветка логов"""
    
    # Цвета для разных типов событий
    COLORS = {
        "balance_found": "#3fb950",      # Зеленый - найден баланс
        "transfer_detected": "#f85149",  # Красный - обнаружен перевод
        "whale": "#ffd700",              # Золотой - whale кошелек
        "error": "#d29922",              # Желтый - ошибка
        "info": "#58a6ff",               # Синий - информация
        "success": "#3fb950",            # Зеленый - успех
        "warning": "#f0883e",            # Оранжевый - предупреждение
        "muted": "#8b949e",              # Серый - неважное
    }
    
    # Теги для CustomTkinter textbox
    TAG_CONFIGS = {
        "balance_found": {"foreground": COLORS["balance_found"], "font": ("Consolas", 12, "bold")},
        "transfer_detected": {"foreground": COLORS["transfer_detected"], "font": ("Consolas", 12, "bold")},
        "whale": {"foreground": COLORS["whale"], "font": ("Consolas", 12, "bold")},
        "error": {"foreground": COLORS["error"]},
        "info": {"foreground": COLORS["info"]},
        "success": {"foreground": COLORS["success"]},
        "warning": {"foreground": COLORS["warning"]},
        "muted": {"foreground": COLORS["muted"]},
    }
    
    @staticmethod
    def detect_log_type(message: str) -> str:
        """
        Определить тип лога по содержимому
        
        Args:
            message: Текст сообщения
        
        Returns:
            str: Тип лога ("balance_found", "transfer_detected", ...)
        """
        
        message_lower = message.lower()
        
        # Проверяем на перевод (самый важный!)
        transfer_keywords = [
            "transfer", "перевод", "sent", "отправлено",
            "transaction", "транзакция", "tx", "moved"
        ]
        if any(keyword in message_lower for keyword in transfer_keywords):
            return "transfer_detected"
        
        # Проверяем на whale
        whale_keywords = ["whale", "кит", "🐋", "high balance", "большой баланс"]
        if any(keyword in message_lower for keyword in whale_keywords):
            return "whale"
        
        # Проверяем на баланс
        balance_keywords = ["balance", "баланс", "found", "найден", "💰", "~$"]
        if any(keyword in message_lower for keyword in balance_keywords):
            # Проверяем что это не нулевой баланс
            if "0.00" not in message and "empty" not in message_lower:
                return "balance_found"
        
        # Проверяем на ошибку
        error_keywords = ["error", "ошибка", "failed", "провалено", "❌"]
        if any(keyword in message_lower for keyword in error_keywords):
            return "error"
        
        # Проверяем на успех
        success_keywords = ["success", "успех", "✅", "completed", "завершено"]
        if any(keyword in message_lower for keyword in success_keywords):
            return "success"
        
        # Проверяем на предупреждение
        warning_keywords = ["warning", "предупреждение", "⚠️", "caution"]
        if any(keyword in message_lower for keyword in warning_keywords):
            return "warning"
        
        # По умолчанию - info
        return "info"
    
    @staticmethod
    def colorize_message(message: str) -> tuple[str, str]:
        """
        Определить цвет для сообщения
        
        Returns:
            tuple: (message, tag_name)
        """
        
        log_type = LogColorizer.detect_log_type(message)
        return (message, log_type)
    
    @staticmethod
    def setup_textbox_tags(textbox) -> None:
        """
        Настроить теги для CustomTkinter textbox
        
        Args:
            textbox: CustomTkinter CTkTextbox виджет
        """
        
        for tag_name, config in LogColorizer.TAG_CONFIGS.items():
            textbox.tag_config(tag_name, **config)
    
    @staticmethod
    def insert_colored_text(textbox, message: str, end: str = "\n") -> None:
        """
        Вставить цветной текст в textbox
        
        Args:
            textbox: CustomTkinter CTkTextbox виджет
            message: Текст сообщения
            end: Окончание строки
        """
        
        # Определяем тип и цвет
        log_type = LogColorizer.detect_log_type(message)
        
        # Вставляем с тегом
        textbox.insert("end", message + end, log_type)
        
        # Автоскролл вниз
        textbox.see("end")


# ═══════════════════════════════════════════════════════════════════════════
#  BALANCE HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════════════════

class BalanceHighlighter:
    """Подсветка балансов в тексте"""
    
    @staticmethod
    def highlight_balances_in_text(text: str) -> str:
        """
        Добавить emoji и форматирование к балансам в тексте
        
        Args:
            text: Исходный текст с балансами
        
        Returns:
            str: Текст с улучшенным форматированием
        
        Examples:
            >>> highlight_balances_in_text("Balance: 7.18e-06 BTC")
            "Balance: 💸 0.00000718 BTC (~$0.32)"
        """
        
        import re
        
        # Паттерн для научной нотации: 7.18e-06
        scientific_pattern = r'(\d+\.?\d*)[eE]([-+]?\d+)'
        
        def replace_scientific(match):
            value = float(match.group(0))
            return BalanceFormatter.format_scientific_notation(value)
        
        # Заменяем научную нотацию
        text = re.sub(scientific_pattern, replace_scientific, text)
        
        return text
    
    @staticmethod
    def format_result_message(result: Dict[str, Any]) -> str:
        """
        Форматировать результат проверки с улучшенным отображением
        
        Args:
            result: Результат от checker
        
        Returns:
            str: Форматированное сообщение
        """
        
        message_parts = []
        
        # Адрес/логин
        input_data = result.get("input", "")
        if len(input_data) > 50:
            input_data = input_data[:25] + "..." + input_data[-20:]
        
        message_parts.append(f"📍 {input_data}")
        
        # Статус
        if result.get("exists"):
            message_parts.append("✅ VALID")
        else:
            message_parts.append("❌ INVALID")
        
        # Платформа
        platform = result.get("platform", result.get("wallet_type", ""))
        if platform:
            message_parts.append(f"🔗 {platform.upper()}")
        
        # Балансы
        info = result.get("info", {})
        
        # Основной баланс
        if "balance" in info and info["balance"]:
            balance = info["balance"]
            symbol = result.get("wallet_type", "").upper()
            
            # Форматируем с emoji
            formatted = BalanceFormatter.format_balance_with_emoji(
                balance,
                symbol,
                info.get("price")
            )
            message_parts.append(formatted)
        
        # USD баланс
        if "balance_usd" in info and info["balance_usd"]:
            usd = info["balance_usd"]
            if usd >= 100000:
                message_parts.append(f"🐋 WHALE: ${usd:,.2f}")
            elif usd >= 10000:
                message_parts.append(f"💎 ${usd:,.2f}")
            elif usd >= 1000:
                message_parts.append(f"💰 ${usd:,.2f}")
            elif usd >= 1:
                message_parts.append(f"💵 ${usd:,.2f}")
        
        # Токены
        if "tokens" in info and info["tokens"]:
            tokens = info["tokens"]
            if isinstance(tokens, dict):
                # Форматируем токены
                token_lines = []
                for symbol, amount in list(tokens.items())[:5]:  # Первые 5
                    formatted = BalanceFormatter.format_balance(amount, symbol)
                    token_lines.append(f"  └─ {formatted}")
                
                if token_lines:
                    message_parts.append("🪙 Tokens:")
                    message_parts.extend(token_lines)
                
                if len(tokens) > 5:
                    message_parts.append(f"  └─ ... и еще {len(tokens) - 5} токенов")
        
        # Сообщение об ошибке
        if "error" in info and info["error"]:
            message_parts.append(f"⚠️ {info['error']}")
        
        return "\n".join(message_parts)
