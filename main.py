# MultiChecker Pro v1.0.94
# Runtime UI refresh loader.
# Loads stable v1.0.92 source, applies visual-only UI patches, then starts the app.

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

APP_VERSION = "1.0.94"
BASE_COMMIT = "4de3bcf08cf971fe8b362e379ad4401706254451"
BASE_URL = f"https://raw.githubusercontent.com/d71404189-beep/MultiChecker/{BASE_COMMIT}/main.py"
CACHE_FILE = Path(__file__).with_name(".multichecker_runtime_v1_0_94.py")


def _apply_ui_refresh(source: str) -> str:
    source = source.replace('APP_VERSION = "1.0.92"', 'APP_VERSION = "1.0.94"')

    start = source.find('#  U')
    # Fallback: replace known color constants one by one to avoid Unicode markers.
    colors = {
        'BG       = "#0a0e1a"': 'BG       = "#070B14"',
        'SIDEBAR  = "#0f1419"': 'SIDEBAR  = "#0B1220"',
        'CARD     = "#1a1f2e"': 'CARD     = "#111A2E"',
        'CARD2    = "#242938"': 'CARD2    = "#17223A"',
        'BORDER   = "#2d3548"': 'BORDER   = "#263550"',
        'ACCENT   = "#3b82f6"': 'ACCENT   = "#5B8CFF"',
        'ACCENT2  = "#60a5fa"': 'ACCENT2  = "#7AA2FF"',
        'GREEN    = "#10b981"': 'GREEN    = "#22C55E"',
        'GREEN2   = "#34d399"': 'GREEN2   = "#4ADE80"',
        'RED      = "#ef4444"': 'RED      = "#EF4444"',
        'RED2     = "#f87171"': 'RED2     = "#F87171"',
        'YELLOW   = "#f59e0b"': 'YELLOW   = "#F59E0B"',
        'YELLOW2  = "#fbbf24"': 'YELLOW2  = "#FBBF24"',
        'PURPLE   = "#8b5cf6"': 'PURPLE   = "#A855F7"',
        'PURPLE2  = "#a78bfa"': 'PURPLE2  = "#C084FC"',
        'ORANGE   = "#f97316"': 'ORANGE   = "#F97316"',
        'ORANGE2  = "#fb923c"': 'ORANGE2  = "#FB923C"',
        'CYAN     = "#06b6d4"': 'CYAN     = "#06B6D4"',
        'CYAN2    = "#22d3ee"': 'CYAN2    = "#22D3EE"',
        'PINK     = "#ec4899"': 'PINK     = "#EC4899"',
        'PINK2    = "#f472b6"': 'PINK2    = "#F472B6"',
        'TEXT     = "#f1f5f9"': 'TEXT     = "#EAF0FF"',
        'TEXT2    = "#cbd5e1"': 'TEXT2    = "#C7D2FE"',
        'MUTED    = "#94a3b8"': 'MUTED    = "#8D9BB8"',
        'HOVER    = "#1e293b"': 'HOVER    = "#1E2B46"',
    }
    for old, new in colors.items():
        source = source.replace(old, new)
    source = source.replace('SHADOW   = "#00000040"', 'SHADOW   = "#00000055"\nPANEL    = "#0E1628"\nINPUT_BG = "#0C1324"')

    replacements = {
        'self.geometry("1300x820")': 'self.geometry("1440x900")',
        'self.minsize(1100, 700)': 'self.minsize(1180, 760)',
        'sb = ctk.CTkFrame(self, width=240, fg_color=SIDEBAR, corner_radius=0)': 'sb = ctk.CTkFrame(self, width=268, fg_color=SIDEBAR, corner_radius=0)',
        'title_frame = ctk.CTkFrame(logo, fg_color=CARD, corner_radius=12)': 'title_frame = ctk.CTkFrame(logo, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER)',
        'bar = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=0, height=58)': 'bar = ctk.CTkFrame(frame, fg_color=PANEL, corner_radius=0, height=72)',
        'font=("Segoe UI", 17, "bold"), text_color=TEXT': 'font=("Segoe UI", 22, "bold"), text_color=TEXT',
        'height=108, font=("Consolas", 12),\n            fg_color=CARD2, border_color=BORDER,': 'height=138, font=("Consolas", 12),\n            fg_color=INPUT_BG, border_color=BORDER,',
        'height=300, font=("Consolas", 12),': 'height=340, font=("Consolas", 12),',
        'fg_color="#0d1117",': 'fg_color=INPUT_BG,',
        'corner_radius=10, \n                height=42,': 'corner_radius=14, \n                height=44,',
        'c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)': 'c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)',
        'font=("Segoe UI", 26, "bold")': 'font=("Segoe UI", 28, "bold")',
        'settings_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)': 'settings_frame = ctk.CTkFrame(sb, fg_color=PANEL, corner_radius=16, border_width=1, border_color=BORDER)',
        'theme_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)': 'theme_frame = ctk.CTkFrame(sb, fg_color=PANEL, corner_radius=16, border_width=1, border_color=BORDER)',
        'status_frame = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=12)': 'status_frame = ctk.CTkFrame(sb, fg_color=PANEL, corner_radius=16, border_width=1, border_color=BORDER)',
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    return source


def _load_source() -> str:
    if CACHE_FILE.exists():
        return CACHE_FILE.read_text(encoding="utf-8")
    with urllib.request.urlopen(BASE_URL, timeout=20) as response:
        base = response.read().decode("utf-8")
    patched = _apply_ui_refresh(base)
    CACHE_FILE.write_text(patched, encoding="utf-8")
    return patched


def main() -> None:
    code = _load_source()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    globals_dict = {
        "__name__": "__main__",
        "__file__": str(CACHE_FILE),
        "__package__": None,
        "__cached__": None,
    }
    exec(compile(code, str(CACHE_FILE), "exec"), globals_dict)


if __name__ == "__main__":
    main()
