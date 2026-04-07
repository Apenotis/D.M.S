import configparser
import csv
import os
import shutil
from datetime import datetime

import dms_core.config as cfg

# ============================================================================
# SESSION & LAST SELECTION (NEU: Fix für den hängenden Pfeil)
# ============================================================================


def get_last_id() -> str:
    """Liest die absolut letzte Auswahl aus der Config."""
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
            if "SESSION" in config:
                return config["SESSION"].get("last_id", "1")
        except Exception:
            pass
    return "1"


def save_last_id(map_id: str) -> None:
    """Speichert die aktuelle Auswahl sofort in der Config."""
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
        except Exception:
            pass
    if "SESSION" not in config:
        config["SESSION"] = {}
    config["SESSION"]["last_id"] = str(map_id)
    with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
        config.write(f)


# ============================================================================
# STATISTIKEN & SETTINGS
# ============================================================================


def get_total_seconds() -> int:
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
            return config.getint("STATS", "total_seconds", fallback=0)
        except Exception:
            pass
    return 0


def save_total_seconds(seconds: int) -> None:
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
        except Exception:
            pass
    if "STATS" not in config:
        config["STATS"] = {}
    config["STATS"]["total_seconds"] = str(seconds)
    with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
        config.write(f)


def load_settings() -> None:
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
            if "ENGINE" in config:
                cfg.CURRENT_ENGINE = config["ENGINE"].get("current", cfg.CURRENT_ENGINE)
            if "OPTIONS" in config:
                cfg.SHOW_STATS = config["OPTIONS"].getboolean(
                    "showstats", fallback=False
                )
                cfg.USE_MODS = config["OPTIONS"].getboolean("usemods", fallback=False)
                cfg.DEBUG_MODE = config["OPTIONS"].getboolean(
                    "debugmode", fallback=False
                )
        except Exception:
            pass


def save_settings() -> None:
    config = configparser.ConfigParser()
    if os.path.exists(cfg.CONFIG_FILE):
        try:
            config.read(cfg.CONFIG_FILE, encoding="utf-8-sig")
        except Exception:
            pass
    if "ENGINE" not in config:
        config["ENGINE"] = {}
    config["ENGINE"]["current"] = cfg.CURRENT_ENGINE
    config["OPTIONS"] = {
        "showstats": str(cfg.SHOW_STATS),
        "usemods": str(cfg.USE_MODS),
        "debugmode": str(cfg.DEBUG_MODE),
        "terminalwidth": str(cfg.TERMINAL_WIDTH),
    }
    with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
        config.write(f)


# ============================================================================
# MAP-MANAGEMENT (OPTIMIERT & VOLLSTÄNDIG)
# ============================================================================


def update_last_played(map_id):
    """Aktualisiert das Datum in der CSV und speichert die Last-ID in der Config."""
    if not os.path.exists(cfg.CSV_FILE):
        return
    rows = []
    today = datetime.now().strftime("%d.%m.%Y")

    # Trenner sicher erkennen
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        delim = ";" if ";" in f.read(100) else ","

    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        f.seek(0)
        reader = list(csv.reader(f, delimiter=delim))
        header = reader[0]
        for row in reader[1:]:
            if row and row[0] == str(map_id):
                while len(row) < 9:
                    row.append("-")
                row[8] = today
            rows.append(row)

    with open(cfg.CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delim)
        writer.writerow(header)
        writer.writerows(rows)

    # Parallel dazu die Last-ID sichern
    save_last_id(map_id)


def get_last_played_id_from_csv():
    """Backup-Funktion: Sucht die ID mit dem neuesten Datum."""
    if not os.path.exists(cfg.CSV_FILE):
        return "1"
    last_id, latest_date = "1", None
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        delim = ";" if ";" in f.read(100) else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            lp = row.get("LastPlayed", "").strip()
            if lp and lp not in ["0", "-", ""]:
                try:
                    current_date = datetime.strptime(lp, "%d.%m.%Y")
                    if latest_date is None or current_date >= latest_date:
                        latest_date, last_id = current_date, row.get("ID", "1")
                except Exception:
                    pass
    return last_id


def toggle_map_clear(map_id: str) -> bool:
    rows, found = [], False
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        delim = ";" if ";" in f.read(100) else ","
        f.seek(0)
        reader = list(csv.reader(f, delimiter=delim))
        header = reader[0]
        for row in reader[1:]:
            if row and row[0].strip().upper() == map_id.upper():
                found = True
                row[1] = (
                    row[1].replace(" [C]", "") if " [C]" in row[1] else row[1] + " [C]"
                )
            rows.append(row)
    if found:
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=delim)
            writer.writerow(header)
            writer.writerows(rows)
    return found


def toggle_mod_skip(map_id: str) -> bool:
    rows, found = [], False
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        delim = ";" if ";" in f.read(100) else ","
        f.seek(0)
        reader = list(csv.DictReader(f, delimiter=delim))
        fieldnames = list(reader[0].keys())
        for row in reader:
            if row["ID"].strip().upper() == map_id.upper():
                found = True
                row["MOD"] = "0" if row.get("MOD") == "1" else "1"
            rows.append(row)
    if found:
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delim)
            writer.writeheader()
            writer.writerows(rows)
    return found


def uninstall_map(map_id: str) -> bool:
    rows, to_del, header = [], None, []
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        delim = ";" if ";" in f.read(100) else ","
        f.seek(0)
        reader = csv.reader(f, delimiter=delim)
        header = next(reader)
        for row in reader:
            if row[0].strip().upper() == map_id.upper():
                to_del = row
            else:
                rows.append(row)
    if not to_del or to_del[6].upper() == "IWAD":
        return False
    print(f"\n  Lösche '{to_del[1]}'? (JA zum Bestätigen)")
    if input("> ").strip() == "JA":
        shutil.rmtree(os.path.join(cfg.PWAD_DIR, to_del[3]), ignore_errors=True)
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=delim)
            writer.writerow(header)
            writer.writerows(rows)
        reorganize_map_indices()
    return True


# ============================================================================
# REORGANIZE (ID-LOGIK)
# ============================================================================


def reorganize_map_indices() -> None:
    if not os.path.exists(cfg.CSV_FILE):
        return

    rows = []
    # 1. Trenner ermitteln und Daten einlesen
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        content = f.read(100)
        delim = ";" if ";" in content else ","
        f.seek(0)
        reader = list(csv.DictReader(f, delimiter=delim))
        # Filter: EMPTY-Einträge entfernen
        rows = [
            r for r in reader if r.get("ID") != "EMPTY" and r.get("Name") != "EMPTY"
        ]

    if not rows:
        return

    # 2. Kategorien trennen
    iwads = [r for r in rows if r["Kategorie"].upper() == "IWAD"]
    pwads = [r for r in rows if r["Kategorie"].upper() == "PWAD"]
    extras_raw = [r for r in rows if r["Kategorie"].upper() == "EXTRA"]

    # 3. FORTLAUFENDE NUMMERIERUNG (Der Fix)
    # Ein gemeinsamer Counter für IWADs und PWADs
    counter = 1

    for r in iwads:
        r["ID"] = str(counter)
        counter += 1

    for r in pwads:
        r["ID"] = str(counter)
        counter += 1

    # 4. Extras (Heretic/Hexen) wie gehabt mit H/X
    final_extras = []
    heretics = [r for r in extras_raw if "heretic" in r["IWAD"].lower()]
    hexens = [
        r
        for r in extras_raw
        if "hexen" in r["IWAD"].lower() or "hexdd" in r["IWAD"].lower()
    ]
    others = [r for r in extras_raw if r not in heretics and r not in hexens]

    for i, r in enumerate(heretics, 1):
        r["ID"] = f"H{i}"
        final_extras.append(r)

    for i, r in enumerate(hexens, 1):
        r["ID"] = f"X{i}"
        final_extras.append(r)

    final_extras.extend(others)

    # 5. Speichern
    fieldnames = [
        "ID",
        "Name",
        "IWAD",
        "Ordner",
        "MOD",
        "ARGS",
        "Kategorie",
        "Playtime",
        "LastPlayed",
    ]
    with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delim)
        writer.writeheader()
        writer.writerows(iwads + pwads + final_extras)


def get_next_id(category: str) -> str:
    # Diese Funktion wird oft vom Installer genutzt, um eine provisorische ID zu vergeben
    if category == "HERETIC":
        return "H99"
    if category == "HEXEN":
        return "X99"
    return "99"
