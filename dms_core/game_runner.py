import csv
import os
import subprocess
import time
from datetime import datetime

import dms_core.config as cfg
import dms_core.database as db
import dms_core.engine_manager as engines
import dms_core.utils as utils
from dms_core.config import Colors


def _analyze_session(session_time: int, map_id: str, mapname: str) -> None:
    """
    Speichert die Spielzeit global und in der CSV (1:1 Wie im Original).
    Wird nach dem Beenden des Spiels aufgerufen.
    """
    if session_time < 5:
        return

    # 1. Globale Zeit aktualisieren
    current_total = db.get_total_seconds()
    db.save_total_seconds(current_total + session_time)

    # 2. CSV aktualisieren (Playtime & LastPlayed)
    if not os.path.exists(cfg.CSV_FILE):
        return

    today = datetime.today().strftime("%d.%m.%Y")
    rows = []

    # 2.1 Trennzeichen der CSV sicher ermitteln
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        first_line = f.readline()
        delim = ";" if ";" in first_line else ","

    # 2.2 Daten einlesen und aktualisieren
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delim)
        header = next(reader)
        for row in reader:
            if row and row[0] == str(map_id):
                while len(row) < 9:
                    row.append("0" if len(row) == 7 else "-")
                try:
                    old_playtime = int(row[7])
                except ValueError:
                    old_playtime = 0
                row[7] = str(old_playtime + session_time)
                row[8] = today
            rows.append(row)

    # 2.3 Speichern (Mit dem ermittelten Original-Trennzeichen!)
    with open(cfg.CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delim)
        writer.writerow(header)
        writer.writerows(rows)

    print(
        f"\n  {Colors.CYAN}Session beendet. Spielzeit hinzugefügt: {Colors.WHITE}{utils.format_time(session_time)}"
    )
    time.sleep(1.5)


def launch_game(map_data: tuple) -> None:
    """
    Bereitet den Start der ausgewählten Map vor.
    Enthält die exakte 1:1 Logik aus der originalen Doom.py,
    aber mit einem optisch stark aufgewerteten Debug-Menü.
    """
    utils.resize_terminal(70, 30)
    utils.clear_screen()

    _, map_id, core, mapname, remaining, _ = map_data
    core = core.replace(" ", "").strip()

    engine_path = engines.get_engine_path()
    engine_name = cfg.CURRENT_ENGINE.lower()

    MOD_COMPATIBLE_ENGINES = ["gzdoom", "lzdoom", "zandronum", "uzdoom"]
    VALID_EXTS = (
        ".wad",
        ".pk3",
        ".pk7",
        ".zip",
        ".deh",
        ".bex",
        ".ipk3",
        ".pke",
        ".kpf",
    )

    sub_folder = "doom"
    if core.lower() == "heretic.wad":
        sub_folder = "heretic"
    elif core.lower() == "hexen.wad":
        sub_folder = "hexen"

    file_params, extra_params = [], []
    mod_flag = False
    auto_mod = None

    # --- Tracking Variablen für das schöne Debug-Menü ---
    found_files_list = []
    target_dir_display = "Kein Ordner definiert (Basis-IWAD)"
    selected_mod_name = ""

    # ========================================================================
    # 1. PARAMETER PARSEN (1:1 Original Doom.py Logik)
    # ========================================================================
    i = 0
    while i < len(remaining):
        item = str(remaining[i]).strip()
        if not item:
            i += 1
            continue

        if item == "1":
            mod_flag = True
            i += 1
        elif item == "0":
            mod_flag = False
            i += 1
        elif item.startswith("-") or item.startswith("+"):
            extra_params.append(item)
            i += 1
            while i < len(remaining):
                next_val = str(remaining[i]).strip()
                if next_val and not (
                    next_val.startswith("-") or next_val.startswith("+")
                ):
                    if item.lower() == "-config":
                        extra_params.append(os.path.join(cfg.BASE_DIR, next_val))
                    else:
                        extra_params.append(next_val)
                    i += 1
                else:
                    break
        else:
            target_path = None
            potential_paths = [
                os.path.join(cfg.PWAD_DIR, item),
                os.path.join(cfg.IWAD_DIR, item),
                os.path.join(cfg.PWAD_DIR, item + ".wad"),
            ]
            for p in potential_paths:
                if os.path.exists(p):
                    target_path = p
                    break

            if target_path:
                target_dir_display = target_path  # Für Debug sichern
                if os.path.isdir(target_path):
                    for f in os.listdir(target_path):
                        if f.lower().endswith(VALID_EXTS):
                            file_params.extend(["-file", os.path.join(target_path, f)])
                            found_files_list.append(f)
                else:
                    file_params.extend(["-file", target_path])
                    found_files_list.append(os.path.basename(target_path))
            else:
                if item.lower() not in ["doom", "heretic", "hexen"]:
                    if os.path.isdir(
                        os.path.join(cfg.BASE_DIR, "mods", sub_folder, item)
                    ):
                        auto_mod = os.path.join(sub_folder, item)
                    elif os.path.isdir(os.path.join(cfg.BASE_DIR, "mods", item)):
                        auto_mod = item
            i += 1

    # ========================================================================
    # 2. MOD-AUSWAHLMENÜ
    # ========================================================================
    mod_params = []
    if mod_flag and cfg.USE_MODS and engine_name in MOD_COMPATIBLE_ENGINES:
        mod_options = ["Keine Mods"]
        if auto_mod:
            mod_options.append(f"[AUTO] {auto_mod}")

        mod_base = os.path.join(cfg.BASE_DIR, "mods", sub_folder)
        if os.path.exists(mod_base):
            for d in os.listdir(mod_base):
                if os.path.isdir(os.path.join(mod_base, d)) and d not in str(auto_mod):
                    mod_options.append(d)

        if len(mod_options) > 1:
            utils.clear_screen()
            print(
                f"\n  {Colors.CYAN}╭──────────────────────────────────────────────────╮"
            )
            print(f"  │ {Colors.WHITE}{'MODIFIKATIONEN':^48} {Colors.CYAN}│")
            print(
                f"  ╰──────────────────────────────────────────────────╯{Colors.WHITE}\n"
            )

            for idx, m_opt in enumerate(mod_options):
                print(f"  {Colors.YELLOW}[{idx}]{Colors.WHITE} {m_opt}")

            choice = input(
                f"\n  {Colors.YELLOW}Wahl (ENTER = Keine): {Colors.WHITE}"
            ).strip()
            if choice.isdigit() and 0 < int(choice) < len(mod_options):
                selected_mod = mod_options[int(choice)]
                selected_mod_name = selected_mod  # Für Debug sichern

                if selected_mod.startswith("[AUTO] "):
                    mod_folder_path = os.path.join(
                        cfg.BASE_DIR, "mods", selected_mod.replace("[AUTO] ", "")
                    )
                else:
                    mod_folder_path = os.path.join(mod_base, selected_mod)

                if os.path.exists(mod_folder_path):
                    for f in os.listdir(mod_folder_path):
                        if f.lower().endswith(VALID_EXTS):
                            mod_params.extend(
                                ["-file", os.path.join(mod_folder_path, f)]
                            )

    # ========================================================================
    # 3. BEFEHL ZUSAMMENBAUEN
    # ========================================================================
    iwad_full_path = os.path.join(cfg.IWAD_DIR, core)
    cmd = (
        [engine_path, "-iwad", iwad_full_path] + file_params + mod_params + extra_params
    )

    # ========================================================================
    # 4. DAS AUFGEHÜBSCHTE DEBUG-MENÜ
    # ========================================================================
    if cfg.DEBUG_MODE:
        utils.clear_screen()
        inner_w = 80
        print(f"\n  {Colors.RED}╭{'─' * inner_w}╮")
        print(
            f"  │ {Colors.WHITE}{'SYSTEM-CHECK VOR SPIELSTART (DEBUG)':^{inner_w-2}} {Colors.RED}│"
        )
        print(f"  ╰{'─' * inner_w}╯{Colors.WHITE}")

        # Sektion 1: Metadaten
        print(f"\n  {Colors.CYAN}[ ÜBERSICHT ]")
        print(f"  {Colors.GRAY}ID:      {Colors.WHITE}{map_id}")
        print(f"  {Colors.GRAY}NAME:    {Colors.WHITE}{mapname}")
        print(f"  {Colors.GRAY}IWAD:    {Colors.WHITE}{core}")
        print(
            f"  {Colors.GRAY}ENGINE:  {Colors.BLUE}{cfg.CURRENT_ENGINE}{Colors.WHITE} ({os.path.basename(engine_path)})"
        )

        # Sektion 2: Datei-Check (Ordner, WADs, Mods, Args)
        print(f"\n  {Colors.CYAN}[ DATEI-CHECK ]")
        print(f"  {Colors.GRAY}ORDNER:  {Colors.WHITE}{target_dir_display}")

        if found_files_list:
            for f in found_files_list:
                print(f"  {Colors.GREEN}  ▶ MAP: {Colors.WHITE}{f}")
        elif target_dir_display != "Kein Ordner definiert (Basis-IWAD)":
            print(
                f"  {Colors.RED}  [!] KEINE ZUSATZDATEIEN (PWADS) IM ORDNER GEFUNDEN!"
            )

        if selected_mod_name:
            print(f"  {Colors.YELLOW}  ▶ MOD: {Colors.WHITE}{selected_mod_name}")

        if extra_params:
            print(f"  {Colors.MAGENTA}  ▶ ARGS:{Colors.WHITE} {' '.join(extra_params)}")

        # Sektion 3: Kommando
        print(f"\n  {Colors.CYAN}[ RAW COMMAND LINE ]")
        display_cmd = " ".join(f'"{x}"' if " " in x else x for x in cmd)

        if len(display_cmd) > inner_w:
            print(f"  {Colors.YELLOW}{display_cmd[:inner_w-5]}...")
            print(f"  {Colors.YELLOW}  {display_cmd[inner_w-5:inner_w*2-10]}")
        else:
            print(f"  {Colors.YELLOW}{display_cmd}")

        print(f"\n  {Colors.YELLOW}Möchtest du das Spiel starten?{Colors.WHITE}")
        choice = input(
            f"  {Colors.GREEN}ENTER zum Starten{Colors.WHITE} / {Colors.RED}0 zum Abbruch: {Colors.WHITE}"
        ).strip()

        if choice == "0":
            return

    # ========================================================================
    # 5. START & SESSION TRACKING
    # ========================================================================
    if not cfg.DEBUG_MODE:
        utils.clear_screen()
        print(f"\n  {Colors.GREEN}Starte {mapname}...{Colors.WHITE}")

    start_time = time.time()
    try:
        proc = subprocess.Popen(cmd, cwd=os.path.dirname(engine_path))
        proc.wait()  # Wartet, bis die Engine geschlossen wird
    except Exception as e:
        print(f"\n  {Colors.RED}FEHLER BEIM STARTEN: {e}{Colors.WHITE}")
        input("  ENTER drücken...")
        return

    end_time = time.time()
    session_time = int(end_time - start_time)

    _analyze_session(session_time, map_id, mapname)
