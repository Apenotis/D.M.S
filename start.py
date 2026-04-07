import math
import msvcrt
import os
import random
import sys
import time
import traceback

import dms_core.api as api
import dms_core.config as cfg
import dms_core.database as db
import dms_core.engine_manager as engines
import dms_core.game_runner as runner
import dms_core.initialization as init
import dms_core.installer as installer
import dms_core.map_loader as loader
import dms_core.updater as updater
import dms_core.utils as utils
from dms_core.config import Colors


def print_banner(inner_w):
    banner = [
        "██████╗  ███╗   ███╗ ███████╗",
        "██╔══██╗ ████╗ ████║ ██╔════╝",
        "██║  ██║ ██╔████╔██║ ███████╗",
        "██║  ██║ ██║╚██╔╝██║ ╚════██║",
        "██████╔╝ ██║ ╚═╝ ██║ ███████║",
        "╚═════╝  ╚═╝     ╚═╝ ╚══════╝",
        "",
        "--- DOOM MANAGEMENT SYSTEM (D.M.S.) ---",
    ]
    for line in banner:
        centered = utils.ansi_center(f"{Colors.CYAN}{line}{Colors.WHITE}", inner_w)
        print(f"  {centered}")


def get_w(c, min_w=25):
    """Berechnet die EXAKTE visuelle Breite der längsten Karte in der Spalte"""
    m = min_w
    for i in c:
        if i and i[0] != "EMPTY":
            raw = str(i[0]).replace("\n", "").replace("\r", "")
            clean = (
                raw.split(" - ", 1)[-1].replace("__L__", "").replace("[L]", "").strip()
            )
            d_id = str(i[1]).upper().replace("\n", "").replace("\r", "")
            vis_len = utils.real_len(f"→[{d_id}] {clean}")
            if vis_len > m:
                m = vis_len
    return m


def format_entry_clean(item, width, l_id, name_color, is_col4=False):
    if not item or item[0] == "EMPTY":
        return " " * width

    raw_name = str(item[0]).replace("\n", "").replace("\r", "")
    d_id = str(item[1]).upper().replace("\n", "").replace("\r", "")

    id_col = Colors.YELLOW if is_col4 else Colors.CYAN
    n_col = Colors.YELLOW if is_col4 and d_id.startswith(("H", "X")) else name_color

    clean = raw_name.split(" - ", 1)[-1].replace("__L__", "").replace("[L]", "").strip()
    styled = clean.replace("[C]", f"{Colors.CYAN}[C]{n_col}").replace(
        "[M]", f"{Colors.RED}[M]{n_col}"
    )

    p = "→" if (l_id == d_id) else " "
    vis = f"{p}[{d_id}] {clean}"

    padding = max(0, width - utils.real_len(vis))
    return f"{Colors.CYAN}{p}{Colors.GRAY}[{id_col}{d_id}{Colors.GRAY}]{n_col} {styled}{Colors.WHITE}{' ' * padding}"


def main():
    db.load_settings()
    init.initial_setup()
    db.reorganize_map_indices()

    try:
        import configparser

        config = configparser.ConfigParser()
        config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")

        # Lese den Zeitpunkt für den nächsten Check (Standard ist 0 = sofort prüfen)
        next_check = float(config["UPDATE"].get("next_check", "0"))

        # Wenn die aktuelle Zeit in Sekunden größer ist als der gespeicherte Wert...
        if time.time() > next_check:
            # ...starte die Prüfung im Hintergrund!
            updater.check_launcher_update(auto=True)

            # Nachdem geprüft wurde (egal ob Update da oder nicht), setze den Timer auf +24 Stunden
            config["UPDATE"]["last_check"] = str(time.time())
            config["UPDATE"]["next_check"] = str(
                time.time() + 604800
            )  # 604800 Sek = 7 Tage

            with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
                config.write(f)
    except Exception:
        pass

    while True:
        blocks = loader.load_maps()
        col1, pwads, col4 = blocks[1], blocks[2], blocks[3]
        col2, col3 = [], []
        half = math.ceil(len(pwads) / 2)
        for i in range(half):
            col2.append(pwads[i])
            col3.append(pwads[i + half] if i + half < len(pwads) else None)

        # 1. Basis-Statistiken laden (für die Fußleiste benötigt)
        mod_count = sum(
            len(
                [
                    d
                    for d in os.listdir(os.path.join(cfg.BASE_DIR, "mods", s))
                    if os.path.isdir(os.path.join(cfg.BASE_DIR, "mods", s, d))
                ]
            )
            for s in ["doom", "heretic", "hexen"]
            if os.path.isdir(os.path.join(cfg.BASE_DIR, "mods", s))
        )
        total_m = (
            len(col1) + len(pwads) + len([x for x in col4 if x and x[0] != "EMPTY"])
        )
        done_c = sum(1 for m in (col1 + pwads + col4) if m and "[C]" in str(m[0]))
        done_p = (done_c / total_m * 100) if total_m > 0 else 0
        eng_ver = engines.get_engine_version(engines.get_engine_path())

        uz_upd, _ = updater.check_uzdoom_update()
        upd_icon = (
            f" {Colors.MAGENTA}[U]{Colors.WHITE}"
            if (uz_upd and cfg.CURRENT_ENGINE == "uzdoom")
            else ""
        )
        m_on = "ON" if cfg.USE_MODS else "OFF"
        s_on = "ON" if cfg.SHOW_STATS else "OFF"
        d_on = "ON" if cfg.DEBUG_MODE else "OFF"

        s1 = f"{Colors.CYAN}KARTEN:{Colors.WHITE} {total_m} {Colors.GRAY}| {Colors.RED}IWAD{Colors.WHITE} {len(col1)} {Colors.GRAY}│{Colors.WHITE} {Colors.GREEN}PWAD{Colors.WHITE} {len(pwads)} {Colors.GRAY}│{Colors.WHITE} {Colors.CYAN}Extras{Colors.WHITE} {len([x for x in col4 if x and x[0] != 'EMPTY'])}"
        s2 = f"{Colors.CYAN}DONE:{Colors.WHITE} {done_c} ({Colors.GREEN}{done_p:.1f}%{Colors.WHITE})"
        s3 = f"{Colors.CYAN}ZEIT:{Colors.WHITE} {utils.format_time(db.get_total_seconds())}"
        s4 = f"{Colors.CYAN}ENGINE:{Colors.WHITE} {Colors.BLUE}{cfg.CURRENT_ENGINE}{Colors.WHITE} {eng_ver}{upd_icon} {Colors.GRAY}│{Colors.WHITE} {Colors.CYAN}MODS:{Colors.WHITE} {mod_count}"
        s5 = f"{Colors.YELLOW}[/M]{Colors.WHITE} Mod {Colors.GREEN if cfg.USE_MODS else Colors.RED}{m_on}{Colors.WHITE} {Colors.YELLOW}[/S]{Colors.WHITE} Stats {Colors.GREEN if cfg.SHOW_STATS else Colors.RED}{s_on}{Colors.WHITE} {Colors.YELLOW}[/D]{Colors.WHITE} Debug {Colors.GREEN if cfg.DEBUG_MODE else Colors.RED}{d_on}{Colors.WHITE}"

        foot_core = f"{s1}  {Colors.GRAY}│{Colors.WHITE}  {s2}  {Colors.GRAY}│{Colors.WHITE}  {s3}  {Colors.GRAY}│{Colors.WHITE}  {s4}  {Colors.GRAY}│{Colors.WHITE}  {s5}"
        footer_len = utils.real_len(foot_core)

        # 2. Spaltenbreiten berechnen
        w1, w2, w3, w4 = (
            get_w(col1, 23),
            get_w(col2, 23),
            get_w(col3, 23),
            get_w(col4, 25),
        )
        base_content_w = w1 + w2 + w3 + w4 + 12

        # 3. Inner Width bestimmen und ausbalancieren
        inner_w = max(footer_len + 4, base_content_w)

        # Wenn der Footer breiter ist, verteilen wir den Platz GERECHT auf alle Spalten!
        if inner_w > base_content_w:
            extra = inner_w - base_content_w
            add_each = extra // 4
            w1 += add_each
            w2 += add_each
            w3 += add_each
            w4 += extra - (3 * add_each)  # Der Rest geht an Spalte 4

        cfg.TERMINAL_WIDTH = inner_w + 6
        utils.resize_terminal(cfg.TERMINAL_WIDTH, 50)

        utils.clear_screen()
        print_banner(inner_w)
        last_id = db.get_last_id()

        # --- HEADER ---
        h1 = utils.ansi_center(f"{Colors.CYAN}IWADS{Colors.WHITE}", w1)
        h2 = utils.ansi_center(f"{Colors.CYAN}PWADS (A-M){Colors.WHITE}", w2)
        h3 = utils.ansi_center(f"{Colors.CYAN}PWADS (N-Z){Colors.WHITE}", w3)
        h4 = utils.ansi_center(f"{Colors.CYAN}EXTRAS / CUSTOM{Colors.WHITE}", w4)

        h_line = f"  {h1} {Colors.GRAY}│{Colors.WHITE} {h2} {Colors.GRAY}│{Colors.WHITE} {h3} {Colors.GRAY}│{Colors.WHITE} {h4} "

        print(f" {Colors.GRAY}╭{'─' * inner_w}╮")
        print(f" {Colors.GRAY}│{Colors.WHITE}{h_line}{Colors.GRAY}│")
        print(f" {Colors.GRAY}├{'─' * inner_w}┤{Colors.WHITE}")

        # --- CONTENT ---
        max_rows = max(25, len(col1), len(col2), len(col3), len(col4))
        for i in range(max_rows):
            r1 = format_entry_clean(
                col1[i] if i < len(col1) else None, w1, last_id, Colors.RED
            )
            r2 = format_entry_clean(
                col2[i] if i < len(col2) else None, w2, last_id, Colors.GREEN
            )
            r3 = format_entry_clean(
                col3[i] if i < len(col3) else None, w3, last_id, Colors.GREEN
            )
            r4 = format_entry_clean(
                col4[i] if i < len(col4) else None, w4, last_id, Colors.WHITE, True
            )

            row_str = f"  {r1} {Colors.GRAY}│{Colors.WHITE} {r2} {Colors.GRAY}│{Colors.WHITE} {r3} {Colors.GRAY}│{Colors.WHITE} {r4} "
            print(f" {Colors.GRAY}│{Colors.WHITE}{row_str}{Colors.GRAY}│")

        # --- FUSSZEILE ---
        print(f" {Colors.GRAY}├{'─' * inner_w}┤")
        print(f" {Colors.GRAY}│{utils.ansi_center(foot_core, inner_w)}│")
        print(f" {Colors.GRAY}╰{'─' * inner_w}╯{Colors.WHITE}")

        # --- BEFEHLE & EINGABE ---
        cmds = [
            f"{Colors.YELLOW}[0]{Colors.WHITE} Beenden",
            f"{Colors.YELLOW}[?]{Colors.WHITE} Zufall",
            f"{Colors.YELLOW}[R]{Colors.WHITE} Reset",
            f"{Colors.YELLOW}[C]{Colors.WHITE} Installer",
            f"{Colors.YELLOW}[D]{Colors.WHITE} DoomWorld",
            f"{Colors.YELLOW}[ID]c{Colors.WHITE} Clear",
            f"{Colors.YELLOW}[ID]m{Colors.WHITE} Skip",
            f"{Colors.YELLOW}[ID]x{Colors.WHITE} Delete",
            f"{Colors.YELLOW}[E]{Colors.WHITE} Engine",
        ]
        cmd_line = "   ".join(cmds)
        pad = max(0, (inner_w - utils.real_len(cmd_line)) // 2 + 1)

        # Kompaktes Spacing: Eine Leerzeile, Menü, eine Leerzeile, Input.
        print()
        print(" " * pad + cmd_line)
        print()

        try:
            while msvcrt.kbhit():
                msvcrt.getch()
        except Exception:
            pass
        choice = (
            input(
                f"    {Colors.YELLOW}ID ODER ENTER ({Colors.MAGENTA}{last_id}{Colors.YELLOW}): {Colors.WHITE}"
            )
            .strip()
            .lower()
        )

        # --- VERARBEITUNG DER EINGABE ---
        if choice == "0":
            sys.exit(0)
        elif choice == "e":
            engines.select_engine()
            db.save_settings()
            continue
        elif choice == "c":
            installer.run_installer()
            continue
        elif choice == "d":
            api.search_doomworld()
            continue
        elif choice == "r":
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif choice == "/m":
            cfg.USE_MODS = not cfg.USE_MODS
            db.save_settings()
            continue
        elif choice == "/s":
            cfg.SHOW_STATS = not cfg.SHOW_STATS
            db.save_settings()
            continue
        elif choice == "/d":
            cfg.DEBUG_MODE = not cfg.DEBUG_MODE
            db.save_settings()
            continue
        elif choice == "?":
            all_m = [i for b in blocks.values() for i in b if i and i[0] != "EMPTY"]
            if all_m:
                runner.launch_game(random.choice(all_m))
            continue

        if choice == "" and last_id:
            choice = last_id.lower()
        if len(choice) > 1 and choice[-1] in "xcm":
            tid = choice[:-1].upper()
            if choice.endswith("m"):
                db.toggle_mod_skip(tid)
            elif choice.endswith("c"):
                db.toggle_map_clear(tid)
            elif choice.endswith("x"):
                db.uninstall_map(tid)
            continue

        found = None
        for b in blocks.values():
            for it in b:
                if it and str(it[1]).lower() == choice:
                    found = it
                    break
        if found:
            runner.launch_game(found)
        else:
            print(
                f"\n  {Colors.RED}Fehler: ID '{choice}' wurde nicht gefunden!{Colors.WHITE}"
            )
            time.sleep(1.5)


if __name__ == "__main__":
    os.system("")
    utils.set_terminal_title("D.M.S. - Doom Management System")
    db.load_settings()
    utils.resize_terminal(max(160, cfg.TERMINAL_WIDTH), 60)
    try:
        main()
    except KeyboardInterrupt:
        utils.clear_screen()
        print(
            f"\n\n  {Colors.YELLOW}D.M.S. wird beendet... Bis zum nächsten Mal!{Colors.WHITE}\n"
        )
        time.sleep(0.5)
        sys.exit(0)
    except Exception as e:
        print(f"[FEHLER] Ein unerwarteter Fehler ist aufgetreten: {e}")
        utils.clear_screen()
        print(f"{Colors.RED}KRITISCHER SYSTEMFEHLER:{Colors.WHITE}\n")
        traceback.print_exc()
        input(f"\n{Colors.YELLOW}Drücke ENTER zum Beenden...{Colors.WHITE}")
        sys.exit(1)
