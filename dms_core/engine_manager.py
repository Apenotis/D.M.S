import os
import json
import time
import shutil
import zipfile
import ctypes
import urllib.request
import webbrowser
import subprocess
from datetime import datetime

import dms_core.config as cfg
from dms_core.config import Colors
from dms_core.utils import resize_terminal, clear_screen
from dms_core.database import save_settings

# ============================================================================
# ENGINE-MANAGEMENT
# ============================================================================

def get_engine_path(engine_name: str = None) -> str:
    eng = engine_name if engine_name else cfg.CURRENT_ENGINE
    exe_name = f"{eng}.exe"

    path = os.path.join(cfg.ENGINE_BASE_DIR, eng, exe_name)
    fallback = os.path.join(cfg.ENGINE_BASE_DIR, exe_name)

    if os.path.exists(path):
        return path
    if os.path.exists(fallback):
        return fallback

    return path


def get_engine_version(engine_path: str) -> str:
    if not engine_path or not os.path.exists(engine_path):
        return "N/A"

    try:
        filename = os.path.abspath(engine_path)
        size = ctypes.windll.version.GetFileVersionInfoSizeW(filename, None)
        if size <= 0:
            return "Bereit"

        res = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(filename, None, size, res)
        fixed_info = ctypes.POINTER(ctypes.c_uint16)()
        fixed_size = ctypes.c_uint()

        if ctypes.windll.version.VerQueryValueW(
            res, "\\", ctypes.byref(fixed_info), ctypes.byref(fixed_size)
        ):
            if fixed_size.value:
                major, minor, build = fixed_info[9], fixed_info[8], fixed_info[11]
                return f"{major}.{minor}.{build}"

        mtime = os.path.getmtime(engine_path)
        return datetime.fromtimestamp(mtime).strftime("%d.%m.%y")
    except Exception:
        return "Aktiv"


def download_engine(engine_name: str) -> None:
    print(f"\n  {Colors.MAGENTA}>>> Bereite Download für {engine_name} vor... <<<{Colors.WHITE}")

    zip_path = os.path.join(cfg.BASE_DIR, f"{engine_name}_temp.zip")
    download_url = ""

    if engine_name in cfg.DIRECT_DOWNLOADS:
        download_url = cfg.DIRECT_DOWNLOADS[engine_name]
    elif engine_name in cfg.ENGINE_REPOS:
        repo = cfg.ENGINE_REPOS[engine_name]
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            req = urllib.request.Request(api_url)
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if any(x in name for x in ["sources", "dev", "debug", "pdb"]):
                        continue

                    is_windows = any(x in name for x in ["win64", "windows", "x64", "w64"])

                    if is_windows and name.endswith(".zip"):
                        download_url = asset.get("browser_download_url")
                        print(f"  {Colors.GREEN}[Found]{Colors.WHITE} Version: {asset.get('name')}")
                        break
        except Exception as e:
            print(f"  {Colors.RED}[!] API-Fehler (GitHub): {e}{Colors.WHITE}")
            input(f"\n  Drücke {Colors.GREEN}ENTER{Colors.WHITE} zum Fortfahren...")
            return

    if download_url:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"  {Colors.GRAY}(Lade: {download_url.split('/')[-1]} - Versuch {attempt+1}/{max_retries}){Colors.WHITE}")
                req = urllib.request.Request(download_url)
                req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

                with urllib.request.urlopen(req, timeout=15) as response, open(zip_path, "wb") as out_file:
                    shutil.copyfileobj(response, out_file)

                if not zipfile.is_zipfile(zip_path):
                    raise ValueError("Datei ist kein gültiges ZIP.")

                target_dir = os.path.join(cfg.ENGINE_BASE_DIR, engine_name)
                os.makedirs(target_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(target_dir)

                if os.path.exists(zip_path):
                    os.remove(zip_path)

                exe_to_find = f"{engine_name}.exe"
                for root, _, files in os.walk(target_dir):
                    if exe_to_find in files:
                        for f in os.listdir(root):
                            src = os.path.join(root, f)
                            dst = os.path.join(target_dir, f)
                            if not os.path.exists(dst):
                                os.replace(src, dst)
                        break

                print(f"  {Colors.GREEN}[+] {engine_name} erfolgreich installiert!{Colors.WHITE}")
                time.sleep(1.5)
                return

            except Exception as e:
                if os.path.exists(zip_path):
                    try:
                        os.remove(zip_path)
                    except Exception:
                        pass
                print(f"  {Colors.YELLOW}[!] Fehler: {e}{Colors.WHITE}")
                time.sleep(1)

    print(f"\n  {Colors.RED}Automatischer Download fehlgeschlagen.{Colors.WHITE}")
    print("  Ich öffne jetzt die Download-Seite für dich.")
    print("  Bitte lade die ZIP manuell herunter und entpacke sie nach:")
    print(f"  {Colors.CYAN}{os.path.join(cfg.ENGINE_BASE_DIR, engine_name)}{Colors.WHITE}")

    fallback_site = (
        "https://zandronum.com/download"
        if engine_name == "zandronum"
        else "https://github.com"
    )
    webbrowser.open(fallback_site)
    input(f"\n  Drücke {Colors.GREEN}ENTER{Colors.WHITE} wenn du fertig bist...")


def select_engine() -> None:
    SMALL_WIDTH = 70
    dynamic_height = 12 + len(cfg.SUPPORTED_ENGINES)

    resize_terminal(SMALL_WIDTH, dynamic_height)

    while True:
        clear_screen()
        print(f"\n  {Colors.MAGENTA}--- ENGINE-VERWALTUNG ---{Colors.WHITE}")
        print(f"  Aktuell aktiv: {Colors.CYAN}{cfg.CURRENT_ENGINE}{Colors.WHITE}")
        print(f"  {'-' * (SMALL_WIDTH - 4)}")

        engines_status = []
        for i, eng in enumerate(cfg.SUPPORTED_ENGINES):
            path_check = get_engine_path(eng)
            is_ready = os.path.exists(path_check)

            status = (
                f"{Colors.GREEN}[BEREIT]{Colors.WHITE}"
                if is_ready
                else f"{Colors.GRAY}[NICHT INSTALLIERT]{Colors.WHITE}"
            )

            print(f"  {Colors.YELLOW}[{i+1}]{Colors.WHITE} {eng:<15} {status}")
            engines_status.append({"name": eng, "ready": is_ready})

        print(f"  {'-' * (SMALL_WIDTH - 4)}")
        print(f"  {Colors.YELLOW}[0]{Colors.WHITE} Zurück")

        choice = input(f"\n  {Colors.CYAN}Wahl:{Colors.WHITE} ").strip()

        if choice == "0" or not choice:
            resize_terminal(cfg.TERMINAL_WIDTH, 60)
            break

        if choice.isdigit() and 0 < int(choice) <= len(engines_status):
            selected = engines_status[int(choice) - 1]

            if not selected["ready"]:
                resize_terminal(SMALL_WIDTH, 20)
                print(f"\n  {Colors.YELLOW}[!]{Colors.WHITE} {selected['name']} fehlt.")
                confirm = input("  Jetzt laden? (j/n): ").lower()
                if confirm == "j":
                    download_engine(selected["name"])

                resize_terminal(SMALL_WIDTH, dynamic_height)
                continue

            # Engine wechseln und direkt über database.py speichern
            cfg.CURRENT_ENGINE = selected["name"]
            save_settings()

            print(f"\n  {Colors.GREEN}[+] Wechsel zu {cfg.CURRENT_ENGINE}!{Colors.WHITE}")
            time.sleep(1)

            resize_terminal(cfg.TERMINAL_WIDTH, 60)
            break