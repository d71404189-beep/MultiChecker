LANG = {
    "en": {
        "title": "Multi Checker Pro",
        "email": "Email",
        "social": "Social",
        "crypto": "Crypto",
        "games": "Games",
        "ai": "AI",
        "input_label": "Input (one per line):",
        "threads": "Threads:",
        "timeout": "Timeout:",
        "proxy": "Proxy:",
        "proxy_placeholder": "http://ip:port or file:proxy.txt",
        "start": "Start Check",
        "stop": "Stop",
        "clear": "Clear",
        "export": "Export Valid",
        "ready": "Ready",
        "no_data": "No data to check!",
        "starting": "Starting check for {} items with {} threads...",
        "completed": "Completed! Valid: {}/{}",
        "exported": "Exported to {}",
        "no_results": "No valid results to export!",
        "stopped": "Stopped!",
    },
    "ru": {
        "title": "Multi Checker Pro",
        "email": "Почта",
        "social": "Соцсети",
        "crypto": "Крипта",
        "games": "Игры",
        "ai": "ИИ",
        "input_label": "Ввод (по одному в строке):",
        "threads": "Потоки:",
        "timeout": "Таймаут:",
        "proxy": "Прокси:",
        "proxy_placeholder": "http://ip:port или файл:proxy.txt",
        "start": "Начать проверку",
        "stop": "Стоп",
        "clear": "Очистить",
        "export": "Экспорт валидных",
        "ready": "Готов",
        "no_data": "Нет данных для проверки!",
        "starting": "Начинаю проверку {} элементов с {} потоками...",
        "completed": "Завершено! Валидных: {}/{}",
        "exported": "Экспортировано в {}",
        "no_results": "Нет валидных результатов для экспорта!",
        "stopped": "Остановлено!",
    }
}

current_lang = "ru"

def t(key):
    return LANG[current_lang].get(key, key)

def set_lang(lang):
    global current_lang
    if lang in LANG:
        current_lang = lang
