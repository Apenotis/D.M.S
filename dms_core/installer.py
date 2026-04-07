import csv
import os
import shutil
import time
import zipfile

import dms_core.config as cfg
from dms_core.config import Colors
from dms_core.database import get_next_id, reorganize_map_indices

# ============================================================================
# INSTALLER-MODUL (VERSION: ORIGINAL-STEUERUNG)
# ============================================================================


def run_installer() -> None:
    INSTALL_DIR = os.path.join(cfg.BASE_DIR, "Install")

    # Exakte Matrix aus deiner alten Doom.py
    # Kat: IWAD -> Spalte 1 | Kat: EXTRA -> Spalte 4
    OFFICIAL_MAPPING = {
        "doom.wad": {
            "Name": "Ultimate Doom",
            "IWAD": "doom.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "doom2.wad": {
            "Name": "Doom II: Hell on Earth",
            "IWAD": "doom2.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "tnt.wad": {
            "Name": "Final Doom: TNT:Evilution",
            "IWAD": "tnt.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "plutonia.wad": {
            "Name": "Final Doom: Plutonia",
            "IWAD": "plutonia.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "masterlevels.wad": {
            "Name": "Doom II: Masterlevels",
            "IWAD": "doom2.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "sigil.wad": {
            "Name": "Sigil",
            "IWAD": "doom.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "sigil2.wad": {
            "Name": "Sigil 2",
            "IWAD": "doom.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "nerve.wad": {
            "Name": "No Rest for the Living",
            "IWAD": "doom2.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        "id1.wad": {
            "Name": "Legacy of Rust",
            "IWAD": "doom2.wad",
            "Kat": "IWAD",
            "Type": "DOOM",
        },
        # --- EXTRAS (Spalte 4 mit H/X IDs) ---
        "heretic.wad": {
            "Name": "Heretic: Shadow of the Serpent Riders",
            "IWAD": "heretic.wad",
            "Kat": "EXTRA",
            "Type": "HERETIC",
        },
        "hexen.wad": {
            "Name": "Hexen: Beyond Heretic",
            "IWAD": "hexen.wad",
            "Kat": "EXTRA",
            "Type": "HEXEN",
        },
        "hexdd.wad": {
            "Name": "Hexen: Deathkings of the Dark Citadel",
            "IWAD": "hexen.wad",
            "Kat": "EXTRA",
            "Type": "HEXEN",
        },
    }

    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)
        return

    items = os.listdir(INSTALL_DIR)
    if not items:
        print(
            f"\n  {Colors.YELLOW}Keine Dateien zum Installieren gefunden.{Colors.WHITE}"
        )
        time.sleep(1)
        return

    print(
        f"\n {Colors.CYAN}--- D.M.S. INSTALLATION (Strikte Kategorisierung) ---{Colors.WHITE}"
    )
    installed_count = 0

    for item in items:
        item_path = os.path.join(INSTALL_DIR, item)
        if not os.path.isfile(item_path):
            continue
        fname_lower = item.lower()

        # --- FALL 1: DAS IST EIN ORIGINAL-SPIEL (WAD direkt verschieben) ---
        if fname_lower in OFFICIAL_MAPPING:
            data = OFFICIAL_MAPPING[fname_lower]
            target_path = os.path.join(cfg.IWAD_DIR, item)

            print(
                f"  {Colors.CYAN}[SYSTEM]{Colors.WHITE} Installiere Original: {Colors.GREEN}{data['Name']}{Colors.WHITE}"
            )

            # In IWAD-Ordner schieben
            if not os.path.exists(target_path):
                shutil.move(item_path, target_path)
            else:
                os.remove(item_path)

            # In CSV registrieren
            _register_to_csv(data["Name"], data["IWAD"], "", data["Kat"], data["Type"])
            installed_count += 1
            continue

        # --- FALL 2: DAS IST EINE USER-MOD (Unterordner erstellen) ---
        ext = fname_lower.rsplit(".", 1)[-1] if "." in item else ""
        folder_name = item.rsplit(".", 1)[0]
        mod_target_dir = os.path.join(cfg.PWAD_DIR, folder_name)

        if ext in ["zip", "7z", "wad", "pk3", "pk7"]:
            print(
                f"  {Colors.MAGENTA}[MOD]{Colors.WHITE} Installiere Mod-Ordner: {Colors.YELLOW}{folder_name}{Colors.WHITE}"
            )
            os.makedirs(mod_target_dir, exist_ok=True)

            if ext == "zip":
                with zipfile.ZipFile(item_path, "r") as z:
                    z.extractall(mod_target_dir)
                os.remove(item_path)
            elif ext in ["wad", "pk3", "pk7"]:
                shutil.move(item_path, os.path.join(mod_target_dir, item))

            # Standard: Doom 2 PWAD (Spalte 2/3)
            display_name = folder_name.replace("_", " ")
            m_core, kat, g_type = "doom2.wad", "PWAD", "DOOM"

            # Check via Readme auf Heretic/Hexen Mods
            for f in os.listdir(mod_target_dir):
                if f.lower().endswith(".txt"):
                    try:
                        with open(
                            os.path.join(mod_target_dir, f), "r", errors="ignore"
                        ) as t:
                            txt = t.read().lower()
                            if "heretic" in txt:
                                m_core, kat, g_type = "heretic.wad", "EXTRA", "HERETIC"
                            elif "hexen" in txt:
                                m_core, kat, g_type = "hexen.wad", "EXTRA", "HEXEN"
                    except Exception:
                        pass

            _register_to_csv(display_name, m_core, folder_name, kat, g_type)
            installed_count += 1

    if installed_count > 0:
        reorganize_map_indices()
    time.sleep(2)


def _register_to_csv(name, iwad, folder, kat, g_type):
    """Fordert die ID basierend auf dem Typ an (H1 für HERETIC, X1 für HEXEN, Nummer für DOOM)."""
    # WICHTIG: g_type steuert das Präfix in der database.py!
    new_id = get_next_id(g_type)
    with open(cfg.CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ID",
                "Name",
                "IWAD",
                "Ordner",
                "MOD",
                "ARGS",
                "Kategorie",
                "Playtime",
                "LastPlayed",
            ],
        )
        writer.writerow(
            {
                "ID": new_id,
                "Name": name,
                "IWAD": iwad,
                "Ordner": folder,
                "MOD": "0",
                "ARGS": "",
                "Kategorie": kat,
                "Playtime": "0",
                "LastPlayed": "-",
            }
        )
