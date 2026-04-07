import os
import shutil
import zipfile
import csv
import time
import sys
import subprocess

import dms_core.config as cfg
from dms_core.config import Colors
from dms_core.database import get_next_id, reorganize_map_indices

# ============================================================================
# INSTALLER-MODUL
# ============================================================================

def run_installer() -> None:
    """
    Überprüft den Ordner 'Install' auf neue Dateien.
    Erkennt Original-IWADs, entpackt Mods, scannt Readmes und pflegt alles in die CSV ein.
    """
    INSTALL_DIR = os.path.join(cfg.BASE_DIR, "Install")

    # Erkennungs-Matrix für offizielle Files
    OFFICIAL_MAPPING = {
        "doom.wad": {"Name": "Ultimate Doom", "IWAD": "doom.wad", "Ordner": "", "Kat": "IWAD"},
        "doom2.wad": {"Name": "Doom II: Hell on Earth", "IWAD": "doom2.wad", "Ordner": "", "Kat": "IWAD"},
        "tnt.wad": {"Name": "Final Doom: TNT:Evilution", "IWAD": "tnt.wad", "Ordner": "", "Kat": "IWAD"},
        "plutonia.wad": {"Name": "Final Doom: The Plutonia Experiment", "IWAD": "plutonia.wad", "Ordner": "", "Kat": "IWAD"},
        "sigil.wad": {"Name": "Sigil", "IWAD": "doom.wad", "Ordner": "sigil.wad", "Kat": "IWAD"},
        "sigil2.wad": {"Name": "Sigil 2", "IWAD": "doom.wad", "Ordner": "sigil2.wad", "Kat": "IWAD"},
        "masterlevels.wad": {"Name": "Doom II: Masterlevels", "IWAD": "doom2.wad", "Ordner": "masterlevels.wad", "Kat": "IWAD"},
        "nerve.wad": {"Name": "Doom II: No Rest for the Living", "IWAD": "doom2.wad", "Ordner": "nerve.wad", "Kat": "IWAD"},
        "id1.wad": {"Name": "Doom II: Legacy of Rust", "IWAD": "doom2.wad", "Ordner": "id1.wad", "Kat": "IWAD"},
    }

    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)
        print(f"\n  {Colors.YELLOW}[!] Ordner 'Install' wurde erstellt. WADs dort ablegen.{Colors.WHITE}")
        time.sleep(2)
        return

    items = os.listdir(INSTALL_DIR)
    if not items:
        print(f"\n  {Colors.YELLOW}Keine Dateien im Install-Ordner gefunden.{Colors.WHITE}")
        time.sleep(1.5)
        return

    print(f"\n {Colors.CYAN}--- INSTALLATION LÄUFT ---{Colors.WHITE}")
    installed_count = 0

    # 1. DURCHGANG: Entpacken & IWAD-Check
    for item in items:
        item_path = os.path.join(INSTALL_DIR, item)
        if not os.path.isfile(item_path):
            continue

        fname_lower = item.lower()

        # Check auf Original-Spiele
        if fname_lower in OFFICIAL_MAPPING:
            data = OFFICIAL_MAPPING[fname_lower]
            print(f"  {Colors.CYAN}[*]{Colors.WHITE} Original-Spiel erkannt: {Colors.GREEN}{data['Name']}{Colors.WHITE}")

            target_path = os.path.join(cfg.IWAD_DIR, item)
            if not os.path.exists(target_path):
                shutil.move(item_path, target_path)
                
                with open(cfg.CSV_FILE, "a", newline="", encoding="utf-8-sig") as csvfile:
                    fieldnames = ["ID", "Name", "IWAD", "Ordner", "MOD", "ARGS", "Kategorie", "Playtime", "LastPlayed"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    if os.path.getsize(cfg.CSV_FILE) == 0:
                        writer.writeheader()

                    writer.writerow({
                        "ID": "TEMP", "Name": data["Name"], "IWAD": data["IWAD"],
                        "Ordner": data["Ordner"], "MOD": "0", "ARGS": "",
                        "Kategorie": data["Kat"], "Playtime": "0", "LastPlayed": "-"
                    })
                installed_count += 1
                continue
            else:
                print(f"  {Colors.RED}[!] {item} existiert bereits im iwad-Ordner.{Colors.WHITE}")
                os.remove(item_path)
                continue

        # Mod-Installer (Archive/WADs)
        ext = item.rsplit(".", 1)[-1].lower() if "." in item else ""
        folder_name = item.rsplit(".", 1)[0]
        tmp_f = os.path.join(INSTALL_DIR, folder_name)

        if ext == "zip":
            print(f"  {Colors.MAGENTA}[*]{Colors.WHITE} Entpacke ZIP: {item}...")
            os.makedirs(tmp_f, exist_ok=True)
            try:
                with zipfile.ZipFile(item_path, "r") as z:
                    z.extractall(tmp_f)
                os.remove(item_path)
            except Exception as e:
                print(f"  {Colors.RED}[!] ZIP-Fehler: {e}{Colors.WHITE}")

        elif ext == "7z":
            print(f"  {Colors.MAGENTA}[*]{Colors.WHITE} Entpacke 7Z: {item}...")
            os.makedirs(tmp_f, exist_ok=True)
            try:
                import py7zr
            except ImportError:
                print(f"  {Colors.YELLOW}[!] py7zr fehlt. Installiere...{Colors.WHITE}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "py7zr", "--quiet"])
                import py7zr

            try:
                with py7zr.SevenZipFile(item_path, mode="r") as z:
                    z.extractall(path=tmp_f)
                os.remove(item_path)
            except Exception as e:
                print(f"  {Colors.RED}[!] 7Z-Fehler: {e}{Colors.WHITE}")

        elif ext in ["wad", "pk3", "pk7"]:
            print(f"  {Colors.MAGENTA}[*]{Colors.WHITE} Verpacke Mod-Datei: {item}...")
            os.makedirs(tmp_f, exist_ok=True)
            shutil.move(item_path, os.path.join(tmp_f, item))

    # 2. DURCHGANG: Ordner verarbeiten & CSV füllen
    folders = [d for d in os.listdir(INSTALL_DIR) if os.path.isdir(os.path.join(INSTALL_DIR, d))]

    for folder in folders:
        full_path = os.path.join(INSTALL_DIR, folder)
        game_files = [f for f in os.listdir(full_path) if f.lower().endswith((".wad", ".pk3", ".pk7"))]

        # Korrektur für doppelte Unterordner
        if not game_files:
            for item in os.listdir(full_path):
                sub_path = os.path.join(full_path, item)
                if os.path.isdir(sub_path):
                    for sub_item in os.listdir(sub_path):
                        shutil.move(os.path.join(sub_path, sub_item), full_path)
                    os.rmdir(sub_path)
                    break

        m_name = folder.replace("_", " ")
        m_core, kat, game_type = "doom2.wad", "PWAD", "DOOM"

        # Readme Scan
        txt_files = [f for f in os.listdir(full_path) if f.lower().endswith(".txt")]
        if txt_files:
            try:
                with open(os.path.join(full_path, txt_files[0]), "r", encoding="utf-8-sig", errors="ignore") as txt:
                    content = txt.read().lower()
                    if "heretic" in content: m_core, kat, game_type = "heretic.wad", "EXTRA", "HERETIC"
                    elif "hexen" in content: m_core, kat, game_type = "hexen.wad", "EXTRA", "HEXEN"
                    elif "plutonia" in content: m_core = "plutonia.wad"
                    elif "tnt" in content: m_core = "tnt.wad"
                    elif "doom.wad" in content: m_core = "doom.wad"
            except:
                pass

        # Finales Verschieben
        target_name = folder.replace(" ", "_")
        target_path = os.path.join(cfg.PWAD_DIR, target_name)

        if not os.path.exists(target_path):
            shutil.move(full_path, target_path)
            new_id = get_next_id(game_type)

            with open(cfg.CSV_FILE, "a", newline="", encoding="utf-8-sig") as csvfile:
                fieldnames = ["ID", "Name", "IWAD", "Ordner", "MOD", "ARGS", "Kategorie", "Playtime", "LastPlayed"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow({
                    "ID": new_id, "Name": m_name, "IWAD": m_core, "Ordner": target_name,
                    "MOD": "0", "ARGS": "", "Kategorie": kat, "Playtime": "0", "LastPlayed": "-"
                })
            print(f"  {Colors.GREEN}[+]{Colors.WHITE} Mod installiert: {Colors.YELLOW}{m_name}{Colors.WHITE}")
            installed_count += 1
        else:
            shutil.rmtree(full_path)

    if installed_count > 0:
        reorganize_map_indices()
        print(f"\n  {Colors.GREEN}Installation von {installed_count} Element(en) erfolgreich!{Colors.WHITE}")
    time.sleep(2)