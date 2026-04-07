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
    Speichert die Spielzeit global und in der CSV
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

    # 2.3 Speichern
    with open(cfg.CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delim)
        writer.writerow(header)
        writer.writerows(rows)

    print(
        f"\n  {Colors.CYAN}Session beendet. Spielzeit hinzugefügt: {Colors.WHITE}{utils.format_time(session_time)}"
    )
    time.sleep(1.5)


def _select_additional_mods(target_dir):
    """Zeigt ein Menü an, um gezielt Dateien aus dem Mod-Ordner zu wählen."""
    if not target_dir or not os.path.exists(target_dir):
        return []

    extensions = (".wad", ".pk3", ".pk7", ".zip", ".7z")
    files = [f for f in os.listdir(target_dir) if f.lower().endswith(extensions)]

    if not files:
        return []

    selected_indices = []

    while True:
        utils.clear_screen()
        print(f"\n  {Colors.CYAN}--- MOD-SELEKTOR ---{Colors.WHITE}")
        print(f"  {Colors.GRAY}Ordner: {os.path.basename(target_dir)}{Colors.WHITE}\n")

        for i, f in enumerate(files):
            mark = (
                f"{Colors.GREEN}[X]{Colors.WHITE}" if i in selected_indices else "[ ]"
            )
            print(f"  {mark} {i+1:2} - {f}")

        print(
            f"\n  {Colors.YELLOW}Tippe die Nummer zum Togglen, 'A' für Alle, ENTER zum Starten.{Colors.WHITE}"
        )
        # FIX F541: f-string entfernt
        choice = input("  Selection: ").strip().lower()

        if choice == "":
            break
        if choice == "a":
            if len(selected_indices) == len(files):
                selected_indices = []
            else:
                selected_indices = list(range(len(files)))
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                if idx in selected_indices:
                    selected_indices.remove(idx)
                else:
                    selected_indices.append(idx)
        except Exception:  # FIX E722: Bare except entfernt
            pass

    return [os.path.join(target_dir, files[i]) for i in selected_indices]


def launch_game(map_data: tuple) -> None:
    """
    Bereitet den Start der ausgewählten Map vor.
    """
    utils.resize_terminal(70, 30)
    utils.clear_screen()

    # --- DATEN ENTPAKKEN ---
    _, map_id, core, mapname, remaining, _ = map_data
    core = core.replace(" ", "").strip()
    iwad_filename = core.lower()

    engine_path = engines.get_engine_path()
    # FIX F841: engine_name entfernt (ungenutzt)
    current_engine_exe = os.path.basename(engine_path).lower()

    # Konfiguration
    MOD_COMPATIBLE_ENGINES = ["gzdoom", "lzdoom", "zandronum", "uzdoom"]
    DOOM_ONLY_ENGINES = ["woof", "nugget", "odamex", "dsda", "nugget-doom"]
    NON_DOOM_GAMES = ["heretic.wad", "hexen.wad", "hexdd.wad", "strife1.wad"]

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
    if iwad_filename == "heretic.wad":
        sub_folder = "heretic"
    elif iwad_filename == "hexen.wad":
        sub_folder = "hexen"

    # ========================================================================
    # 1. KOMPATIBILITÄTS-CHECK
    # ========================================================================
    is_non_doom = iwad_filename in NON_DOOM_GAMES
    engine_is_restricted = any(eng in current_engine_exe for eng in DOOM_ONLY_ENGINES)

    if is_non_doom and engine_is_restricted:
        box_w = 100
        utils.resize_terminal(box_w + 10, 32)
        utils.clear_screen()
        inner_w_err = box_w - 2

        def print_err_line(text, color=Colors.WHITE, align="left"):
            v_len = utils.real_len(text)
            pad = inner_w_err - v_len
            if align == "center":
                pl = pad // 2
                pr = pad - pl
                content = f"{' ' * pl}{text}{' ' * pr}"
            else:
                content = f" {text}{' ' * (pad - 1)}"
            print(f"  {Colors.RED}║{color}{content}{Colors.RED}║")

        print(f"\n  {Colors.RED}╔{'═' * inner_w_err}╗")
        print_err_line("INKOMPATIBILITÄTS-WARNUNG", Colors.WHITE, "center")
        print(f"  {Colors.RED}╠{'═' * inner_w_err}╣")
        print_err_line(f"Spiel:       {Colors.YELLOW}{mapname}")
        print_err_line(f"Engine:      {Colors.YELLOW}{cfg.CURRENT_ENGINE}")
        print_err_line("")
        print_err_line("Diese Engine ist ein spezialisierter Doom-Port und unterstützt")
        print_err_line("Heretic oder Hexen technisch nicht.")
        print_err_line("")
        print_err_line(
            "LÖSUNG: Bitte im Menü [E] drücken und GZDoom oder Zandronum wählen.",
            Colors.CYAN,
        )
        print(f"  {Colors.RED}╚{'═' * inner_w_err}╝{Colors.WHITE}")
        input(
            f"\n    {Colors.GRAY}Drücke ENTER, um zum Menü zurückzukehren...{Colors.WHITE}"
        )
        utils.resize_terminal(cfg.TERMINAL_WIDTH, 50)
        return

    # ========================================================================
    # 2. PARAMETER PARSEN (0=MODS AN / 1=MODS AUS)
    # ========================================================================
    file_params, extra_params = [], []
    mod_flag = True  # Standardmäßig True (wegen Installer-0)
    auto_mod = None
    found_files_list = []
    target_dir_display = "Kein Ordner definiert (Basis-IWAD)"
    selected_mod_name = ""

    i = 0
    while i < len(remaining):
        item = str(remaining[i]).strip()
        if not item:
            i += 1
            continue
        # --- LOGIK-UMKEHR ---
        if item == "0":
            mod_flag = True
            i += 1
        elif item == "1":
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
                target_dir_display = target_path
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
    # 3. MOD-AUSWAHLMENÜ
    # ========================================================================
    mod_params = []
    if (
        mod_flag
        and cfg.USE_MODS
        and any(eng in current_engine_exe for eng in MOD_COMPATIBLE_ENGINES)
    ):
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
                selected_mod_name = selected_mod
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
    # 4. BEFEHL ZUSAMMENBAUEN
    # ========================================================================
    iwad_full_path = os.path.join(cfg.IWAD_DIR, core)
    cmd = (
        [engine_path, "-iwad", iwad_full_path] + file_params + mod_params + extra_params
    )

    if not engine_is_restricted:
        if iwad_filename == "heretic.wad":
            if "-heretic" not in cmd:
                cmd.append("-heretic")
        elif iwad_filename in ["hexen.wad", "hexdd.wad"]:
            if "-hexen" not in cmd:
                cmd.append("-hexen")

    db.save_last_id(map_id)

    # ========================================================================
    # 5. DEBUG-MENÜ
    # ========================================================================
    if cfg.DEBUG_MODE:
        import textwrap

        inner_w_debug = 140
        utils.resize_terminal(inner_w_debug + 8, 48)
        utils.clear_screen()
        BORD, LABL, TEXT = Colors.RED, Colors.CYAN, Colors.WHITE

        def print_line(char="═"):
            # FIX E225: Leerzeichen um das Minus (-)
            print(
                f"  {BORD}{('╔' if char == '═' else '╠')}{char * (inner_w_debug - 4)}{('╗' if char == '═' else '╣')}"
            )

        def print_row(label, value, val_color=TEXT):
            content = f"{LABL}{label:<14} {BORD}│ {val_color}{value}"
            # FIX E225: Leerzeichen um das Minus (-)
            pad = (inner_w_debug - 6) - utils.real_len(content)
            print(f"  {BORD}║ {content}{' ' * pad} {BORD}║")

        print_line("═")
        # FIX E225: Leerzeichen um das Minus (-)
        print(
            f"  {BORD}║ {Colors.YELLOW}{'D.M.S. PRE-FLIGHT DIAGNOSTICS':^{inner_w_debug - 6}} {BORD}║"
        )
        print_line("─")
        print_row("SYSTEM", "DOOM MANAGEMENT SYSTEM - KERNEL BRIDGE", Colors.GREEN)
        print_row("GAME-ID", f"[{map_id}]")
        print_row("TITELEINTRAG", mapname)
        print_row("BASIS-IWAD", core)
        print_row("ENGINE-PFAD", engine_path, Colors.BLUE)
        print_line("─")
        print_row("MOD-ORDNER", target_dir_display)

        if found_files_list:
            for i, f in enumerate(found_files_list):
                print_row("DATEIEN" if i == 0 else "", f"▶ {f}", Colors.GREEN)

        if selected_mod_name:
            print_row("ZUSATZ-MOD", selected_mod_name, Colors.YELLOW)

        if extra_params:
            print_row("PARAMETER", " ".join(extra_params), Colors.MAGENTA)

        print_line("─")
        # FIX E225: Leerzeichen um das Minus (-)
        print(f"  {BORD}║ {LABL}RAW COMMAND LINE:{' ' * (inner_w_debug - 23)} {BORD}║")

        full_cmd = " ".join(f'"{x}"' if " " in x else x for x in cmd)
        # FIX E225: Leerzeichen um das Minus (-)
        for line in textwrap.wrap(full_cmd, width=inner_w_debug - 10):
            print(f"  {BORD}║ {Colors.YELLOW}  {line:<{inner_w_debug - 8}} {BORD}║")

        # FIX E225: Leerzeichen um das Minus (-)
        print(f"  {BORD}╚{('═' * (inner_w_debug - 4))}╝{Colors.WHITE}")

        try:
            import msvcrt

            while msvcrt.kbhit():
                msvcrt.getch()
        except Exception:
            pass

        # FIX: Symmetrischer Input-Check
        choice = input(
            f"\n  {Colors.GREEN}[ENTER]{Colors.WHITE} Starten  {Colors.RED}[0]{Colors.WHITE} Abbrechen: "
        ).strip()
        if choice == "0":
            utils.resize_terminal(cfg.TERMINAL_WIDTH, 50)
            return

    # ========================================================================
    # 6. START & LOGGING
    # ========================================================================
    LOG_DIR = os.path.join(cfg.BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file_path = os.path.join(LOG_DIR, "engine_output.log")

    if not cfg.DEBUG_MODE:
        utils.clear_screen()
        print(f"\n  {Colors.GREEN}Starte {mapname}...{Colors.WHITE}")

    start_time = time.time()
    try:
        with open(log_file_path, "w", encoding="utf-8") as log_file:
            # FIX E225: Leerzeichen um das Minus (-)
            log_file.write(f"D.M.S. COMMAND: {' '.join(cmd)}\n{'-' * 80}\n\n")
            log_file.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=os.path.dirname(engine_path),
                stdout=log_file,
                stderr=log_file,
                text=True,
            )
            proc.wait()
    except Exception as e:
        print(f"\n  {Colors.RED}START-FEHLER: {e}{Colors.WHITE}")
        input()
        return

    session_time = int(time.time() - start_time)
    _analyze_session(session_time, map_id, mapname)
