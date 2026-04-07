import os

# ============================================================================
# KONFIGURATION & KONSTANTEN
# ============================================================================

APP_VERSION = "3.1"
UPDATE_URL = "https://raw.githubusercontent.com/Apenotis/UzDoom-Launcher-Mapinstaller/main/Doom.py"

# --- BASIS PFADE ---
# WICHTIG: Da diese Datei im Ordner dms_core liegt, gehen wir EINE Ebene nach oben!
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
CSV_FILE = os.path.join(BASE_DIR, "maps.csv")
IWAD_DIR = os.path.join(BASE_DIR, "iwad")
PWAD_DIR = os.path.join(BASE_DIR, "pwad")
ENGINE_BASE_DIR = os.path.join(BASE_DIR, "Engines")

# Legacy UzDoom Pfade (falls noch irgendwo zwingend benötigt)
UZ_DIR = os.path.join(BASE_DIR, "UzDoom")
UZ_EXE = os.path.join(UZ_DIR, "uzdoom.exe")

# --- ENGINE KONFIGURATION ---
SUPPORTED_ENGINES = [
    "gzdoom",
    "uzdoom",
    "dsda-doom",
    "woof",
    "nugget-doom",
    "odamex",
    "zandronum",
    "lzdoom",
]
DEFAULT_ENGINE = "gzdoom"

ENGINE_REPOS = {
    "gzdoom": "ZDoom/gzdoom",
    "uzdoom": "UZDoom/UZDoom",
    "dsda-doom": "kraflab/dsda-doom",
    "woof": "fabiangreffrath/woof",
    "nugget-doom": "MrAlaux/Nugget-Doom",
    "odamex": "odamex/odamex",
    "lzdoom": "ZDoom/lzdoom",
}

DIRECT_DOWNLOADS = {
    "zandronum": "https://zandronum.com/downloads/zandronum3.2.1-win32-base.zip"
}

# ============================================================================
# GLOBALE VARIABLEN (Startwerte)
# ============================================================================
CURRENT_ENGINE = DEFAULT_ENGINE
USE_MODS = False
SHOW_STATS = False
DEBUG_MODE = False
TERMINAL_WIDTH = 155
TERMINAL_HEIGHT = 60
# ============================================================================
# FARBEN (ANSI)
# ============================================================================
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[0m"
    GRAY = "\033[90m"
