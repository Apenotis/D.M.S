import os
import sys
import re
import json
import time
import shutil
import urllib.request
import zipfile

import dms_core.config as cfg
from dms_core.config import Colors
import dms_core.utils as utils

# ============================================================================
# LAUNCHER UPDATES (ZIP-BASIERT)
# ============================================================================

def check_uzdoom_update() -> tuple[bool, str]:
    """Prüft auf UZDoom Engine Updates."""
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/UZDoom/UZDoom/releases/latest"
        )
        req.add_header("User-Agent", "Python-Launcher")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            latest = data.get("tag_name", "")
            return latest != "4.14.3", latest
    except Exception:
        return False, "4.14.3"


def check_launcher_update(auto: bool = False) -> None:
    """
    Prüft auf GitHub, ob eine neuere Version (in config.py) vorliegt.
    Wenn ja, wird das gesamte Projekt als ZIP geladen, entpackt und geupdatet.
    """
    if not auto:
        utils.clear_screen()
        print(f"\n  {Colors.CYAN}Suche nach Updates für den D.M.S. Launcher...{Colors.WHITE}")

    try:
        # 1. Version checken
        req = urllib.request.Request(cfg.UPDATE_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=3) as response:
            online_code = response.read().decode("utf-8")
            
        match = re.search(r'APP_VERSION\s*=\s*"([\d\.]+)"', online_code)
        if not match:
            if not auto: 
                print(f"  {Colors.RED}Versionsnummer online nicht gefunden.{Colors.WHITE}"); time.sleep(2)
            return

        online_version = match.group(1)
        
        # Versionsvergleich (einfacher Float-Vergleich reicht meist für x.y)
        if float(online_version) > float(cfg.APP_VERSION):
            if auto:
                # Bei Auto-Update (im Hintergrund beim Start): Bildschirm kurz für den Hinweis nutzen
                utils.clear_screen()
                print(f"\n  {Colors.YELLOW}[!] EIN NEUES UPDATE (v{online_version}) IST VERFÜGBAR!{Colors.WHITE}\n")
            
            print(f"  {Colors.GREEN}Update gefunden: Version {online_version}{Colors.WHITE}")
            print(f"  {Colors.CYAN}Lade ZIP-Archiv von GitHub herunter...{Colors.WHITE}")
            
            _install_zip_update()
            
        else:
            if not auto:
                print(f"  {Colors.GREEN}Der Launcher ist auf dem neuesten Stand (v{cfg.APP_VERSION}).{Colors.WHITE}")
                time.sleep(2)

    except Exception as e:
        if not auto:
            print(f"  {Colors.RED}Fehler bei der Update-Prüfung: {e}{Colors.WHITE}")
            time.sleep(2)


def _install_zip_update() -> None:
    """Lädt die ZIP herunter, entpackt sie und überschreibt die Modul-Dateien."""
    zip_path = os.path.join(cfg.BASE_DIR, "update_temp.zip")
    extract_dir = os.path.join(cfg.BASE_DIR, "update_temp_extracted")
    
    try:
        # 1. ZIP Herunterladen
        urllib.request.urlretrieve(cfg.ZIP_DOWNLOAD_URL, zip_path)
        print(f"  {Colors.CYAN}Entpacke Dateien...{Colors.WHITE}")
        
        # 2. Ordner säubern/erstellen
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        
        # 3. ZIP Entpacken
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # 4. Den Hauptordner im entpackten ZIP finden (GitHub nennt ihn z.B. "UzDoom-Launcher-Mapinstaller-main")
        extracted_folders = os.listdir(extract_dir)
        if not extracted_folders:
            raise Exception("ZIP-Datei war leer.")
            
        repo_folder = os.path.join(extract_dir, extracted_folders[0])
        
        # 5. Dateien überschreiben
        print(f"  {Colors.CYAN}Installiere Update...{Colors.WHITE}")
        
        # a) start.py überschreiben
        src_start = os.path.join(repo_folder, "start.py")
        if os.path.exists(src_start):
            shutil.copy2(src_start, os.path.join(cfg.BASE_DIR, "start.py"))
            
        # b) dms_core Ordner überschreiben (dirs_exist_ok=True überschreibt existierende Dateien)
        src_core = os.path.join(repo_folder, "dms_core")
        if os.path.exists(src_core):
            shutil.copytree(src_core, os.path.join(cfg.BASE_DIR, "dms_core"), dirs_exist_ok=True)
            
        # 6. Aufräumen
        print(f"  {Colors.CYAN}Räume temporäre Dateien auf...{Colors.WHITE}")
        if os.path.exists(zip_path): os.remove(zip_path)
        if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
        
        print(f"\n  {Colors.GREEN}Update erfolgreich abgeschlossen! Launcher wird neu gestartet...{Colors.WHITE}")
        time.sleep(2)
        
        # 7. Neustart
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    except Exception as e:
        print(f"\n  {Colors.RED}FEHLER BEIM INSTALLIEREN DES UPDATES: {e}{Colors.WHITE}")
        print(f"  {Colors.YELLOW}Räume auf und breche ab...{Colors.WHITE}")
        if os.path.exists(zip_path): os.remove(zip_path)
        if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
        time.sleep(3)