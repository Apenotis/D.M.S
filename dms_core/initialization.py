import configparser
import os

import dms_core.config as cfg
from dms_core.config import Colors
from dms_core.engine_manager import download_engine, get_engine_path
from dms_core.utils import clear_screen


def initial_setup() -> None:
    """Systemprüfung. Überspringt die Engine-Wahl, wenn bereits konfiguriert."""
    setup_activity = False

    # 1. Ordner prüfen
    required_dirs = [
        "iwad",
        "pwad",
        "mods",
        "Install",
        "Engines",
        os.path.join("mods", "doom"),
        os.path.join("mods", "heretic"),
        os.path.join("mods", "hexen"),
    ]
    for d in required_dirs:
        path = os.path.join(cfg.BASE_DIR, d)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            setup_activity = True

    # 2. Datenbank prüfen
    if not os.path.exists(cfg.CSV_FILE):
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            f.write("ID,Name,IWAD,Ordner,MOD,ARGS,Kategorie,Playtime,LastPlayed\n")
        setup_activity = True

    # 3. Engine-Check (Die wichtige Korrektur!)
    current_exe = get_engine_path()
    if not os.path.exists(current_exe):
        clear_screen()
        print(f"\n  {Colors.RED}[!] Keine aktive Engine gefunden!{Colors.WHITE}\n")
        for i, eng in enumerate(cfg.SUPPORTED_ENGINES):
            check_path = os.path.join(cfg.ENGINE_BASE_DIR, eng, f"{eng}.exe")
            status = (
                f"{Colors.GREEN}[Bereit]{Colors.WHITE}"
                if os.path.exists(check_path)
                else ""
            )
            print(f"  {Colors.YELLOW}[{i+1}]{Colors.WHITE} {eng:<15} {status}")

        eng_choice = (
            input("\n  Engine wählen (Zahl) oder N für manuell: ").strip().lower()
        )
        if eng_choice.isdigit() and 1 <= int(eng_choice) <= len(cfg.SUPPORTED_ENGINES):
            selected = cfg.SUPPORTED_ENGINES[int(eng_choice) - 1]
            cfg.CURRENT_ENGINE = selected
            os.makedirs(os.path.join(cfg.ENGINE_BASE_DIR, selected), exist_ok=True)
            download_engine(selected)
            setup_activity = True

    # 4. Config-Datei initialisieren
    if not os.path.exists(cfg.CONFIG_FILE):
        config = configparser.ConfigParser()
        config["STATS"] = {"total_seconds": "0"}
        config["ENGINE"] = {"current": cfg.CURRENT_ENGINE}
        config["OPTIONS"] = {
            "showstats": "False",
            "usemods": "False",
            "debugmode": "False",
            "terminalwidth": "166",
        }
        with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
            config.write(f)
        setup_activity = True

    if setup_activity:
        print(f"\n {Colors.CYAN}--- System ist bereit ---{Colors.WHITE}")
        input(" ENTER zum Starten...")
