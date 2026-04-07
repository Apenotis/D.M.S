import os
import json
import csv
import time
import shutil
import zipfile
import urllib.request
import urllib.parse
import sys

import dms_core.config as cfg
from dms_core.config import Colors
import dms_core.utils as utils
from dms_core.database import get_next_id, reorganize_map_indices

def get_installed_pwads():
    installed = []
    for d in [cfg.PWAD_DIR, cfg.IWAD_DIR]:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".wad", ".pk3", ".pk7", ".zip")):
                        installed.append(f.lower())
    return installed

def fetch_folder_files(folder_name):
    url = f"https://www.doomworld.com/idgames/api/api.php?action=getcontents&name={folder_name}&out=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DMS-Launcher"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8-sig"))
            content = data.get("content", {})
            if not content: return [], []
            f = content.get("file", [])
            if isinstance(f, dict): f = [f]
            d = content.get("dir", [])
            if isinstance(d, dict): d = [d]
            return f or [], d or []
    except: return [], []

def download_idgames(file_data):
    TEMP_BASE = os.path.join(cfg.BASE_DIR, "Install")
    os.makedirs(TEMP_BASE, exist_ok=True)
    
    filename = file_data.get("filename")
    folder_name = os.path.splitext(filename)[0]
    title = (file_data.get("title") or filename).replace(";", " ").replace(",", " ")

    api_dir = file_data.get("dir", "").lower()
    category = "PWAD"
    core_wad = "doom2.wad"
    if "heretic" in api_dir: core_wad, category = "heretic.wad", "EXTRA"
    elif "hexen" in api_dir: core_wad, category = "hexen.wad", "EXTRA"
    
    new_id = get_next_id(category)
    temp_extract_path = os.path.join(TEMP_BASE, folder_name)
    final_mod_path = os.path.join(cfg.PWAD_DIR, folder_name)

    if os.path.exists(final_mod_path):
        print(f"\n  {Colors.YELLOW}[{new_id}]{Colors.WHITE} '{folder_name}' ist bereits installiert.")
        time.sleep(1.5); return

    try:
        zip_temp_path = os.path.join(TEMP_BASE, filename)
        print(f"\n  {Colors.CYAN}[{new_id}] Lade herunter:{Colors.WHITE} {title}...")
        
        url = f"https://youfailit.net/pub/idgames/{file_data.get('dir')}{filename}"
        req = urllib.request.Request(url, headers={"User-Agent": "DMS-Launcher"})
        
        with urllib.request.urlopen(req) as response, open(zip_temp_path, "wb") as out_file:
            out_file.write(response.read())

        print(f"  {Colors.YELLOW}[{new_id}] Entpacke Dateien...{Colors.WHITE}")
        with zipfile.ZipFile(zip_temp_path, "r") as zip_ref:
            if os.path.exists(temp_extract_path): shutil.rmtree(temp_extract_path)
            zip_ref.extractall(temp_extract_path)
        os.remove(zip_temp_path)

        print(f"  {Colors.GREEN}[{new_id}] Installiere...{Colors.WHITE}")
        if os.path.exists(final_mod_path): shutil.rmtree(final_mod_path)
        shutil.move(temp_extract_path, final_mod_path)

        with open(cfg.CSV_FILE, "a+", newline="", encoding="utf-8-sig") as f:
            f.seek(0)
            header = f.read(100)
            delim = ";" if ";" in header else ","
            writer = csv.writer(f, delimiter=delim)
            writer.writerow([new_id, title, core_wad, folder_name, "0", "", category, "0", "-"])

        reorganize_map_indices()
        print(f"  {Colors.GREEN}[OK]{Colors.WHITE} Als {Colors.YELLOW}{new_id}{Colors.WHITE} registriert.")
        time.sleep(2)

    except Exception as e:
        print(f"  {Colors.RED}[!] Fehler: {e}{Colors.WHITE}")
        time.sleep(3)

def search_doomworld():
    """Das eigentliche Suchmenü."""
    try:
        utils.clear_screen()
        print(f"\n  {Colors.MAGENTA}--- DOOMWORLD (idgames) API SUCHE ---{Colors.WHITE}")
        print(f"  [{Colors.YELLOW}1{Colors.WHITE}] Stichwort-Suche")
        print(f"  [{Colors.YELLOW}2{Colors.WHITE}] Doom 1 Megawads")
        print(f"  [{Colors.YELLOW}3{Colors.WHITE}] Doom 2 Megawads")
        print(f"  [{Colors.YELLOW}4{Colors.WHITE}] Heretic")
        print(f"  [{Colors.YELLOW}5{Colors.WHITE}] Hexen")

        choice = input(f"\n  {Colors.YELLOW}WAHL (ENTER zum Abbrechen): {Colors.WHITE}").strip()
        if not choice: return

        all_results = []
        if choice == "1":
            q = input(f"  {Colors.CYAN}Suchbegriff: {Colors.WHITE}").strip()
            if not q: return
            url = f"https://www.doomworld.com/idgames/api/api.php?action=search&query={urllib.parse.quote(q)}&type=title&out=json"
            print(f"  {Colors.GRAY}Suche läuft...{Colors.WHITE}")
            req = urllib.request.Request(url, headers={"User-Agent": "DMS-Launcher"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8-sig"))
                res = data.get("content", {}).get("file", [])
                all_results = [res] if isinstance(res, dict) else (res or [])
        elif choice in ["2","3","4","5"]:
            paths = {"2":["levels/doom/megawads/"], "3":["levels/doom2/megawads/"], "4":["levels/heretic/"], "5":["levels/hexen/"]}
            print(f"  {Colors.GRAY}Lade Daten von DoomWorld...{Colors.WHITE}")
            for p in paths[choice]:
                files, _ = fetch_folder_files(p)
                all_results.extend(files)

        if not all_results:
            print(f"  {Colors.RED}Nichts gefunden!{Colors.WHITE}"); time.sleep(2); return

        all_results.sort(key=lambda x: float(x.get("rating", 0) or 0), reverse=True)
        
        idx = 0
        page = 20
        while True:
            utils.clear_screen()
            print(f"\n  {Colors.MAGENTA}--- ERGEBNISSE ({idx+1} bis {min(idx+page, len(all_results))}) ---{Colors.WHITE}")
            print(f"  {Colors.GRAY}{'ID':<4} {'Titel':<50} {'Größe':<12} {'Rating':<15} {'Status'}{Colors.WHITE}")
            print(f"  {'-' * 110}")
            
            installed = get_installed_pwads()
            for i in range(idx, min(idx+page, len(all_results))):
                r = all_results[i]
                title = (r.get("title") or r.get("filename"))[:48]
                size = f"{int(r.get('size',0))/1024/1024:.1f} MB"
                stars = "★" * int(float(r.get("rating",0)))
                
                is_ins = r.get("filename","").lower().split("/")[-1] in installed or (os.path.splitext(r.get("filename","").lower().split("/")[-1])[0] in str(installed))
                col = Colors.GREEN if is_ins else Colors.WHITE
                status = f"{Colors.GREEN}[INSTALL]{Colors.WHITE}" if is_ins else ""
                
                print(f"  {Colors.YELLOW}{i+1:<4}{col} {title:<50} {Colors.CYAN}{size:<12} {Colors.YELLOW}{stars:<15} {status}")

            cmd = input(f"\n  {Colors.YELLOW}[Nr] Install  [N] Weiter  [B] Zurück  [ENTER] Ende: {Colors.WHITE}").lower().strip()
            if cmd == "n" and idx+page < len(all_results): idx += page
            elif cmd == "b" and idx > 0: idx -= page
            elif cmd.isdigit():
                n = int(cmd)-1
                if 0 <= n < len(all_results): download_idgames(all_results[n]); break
            else: break

    except Exception as e:
        print(f"\n  {Colors.RED}API FEHLER: {e}{Colors.WHITE}")
        time.sleep(5)