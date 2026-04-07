import configparser
import csv
import os
import shutil
from datetime import datetime

import dms_core.config as cfg


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

            # --- Engine & Optionen laden ---
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

            if "UPDATE" in config:
                last_c = config["UPDATE"].get("last_check", "").strip()
                next_c = config["UPDATE"].get("next_check", "").strip()
                # Wenn das Feld leer ist, überschreiben wir es in der Config-Datei mit "0"
                if not last_c or not next_c:
                    config["UPDATE"]["last_check"] = last_c if last_c else "0"
                    config["UPDATE"]["next_check"] = next_c if next_c else "0"
                    with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
                        config.write(f)

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
    if "OPTIONS" not in config:
        config["OPTIONS"] = {}
    config["OPTIONS"] = {
        "showstats": str(cfg.SHOW_STATS),
        "usemods": str(cfg.USE_MODS),
        "debugmode": str(cfg.DEBUG_MODE),
        "terminalwidth": str(cfg.TERMINAL_WIDTH),
    }
    with open(cfg.CONFIG_FILE, "w", encoding="utf-8-sig") as f:
        config.write(f)


def update_last_played(map_id):
    """Aktualisiert das LastPlayed-Datum für die gegebene ID in der CSV."""
    if not os.path.exists(cfg.CSV_FILE):
        return

    rows = []
    today = datetime.now().strftime("%d.%m.%Y")

    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";" if ";" in f.read(100) else ",")
        f.seek(0)
        header = next(reader)
        for row in reader:
            if row and row[0] == str(map_id):
                # Index 8 ist 'LastPlayed' laut deiner CSV Struktur
                while len(row) < 9:
                    row.append("-")
                row[8] = today
            rows.append(row)

    with open(cfg.CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)


def get_last_played_id_from_csv():
    """Findet die ID, die das aktuellste Datum in der Spalte LastPlayed hat."""
    if not os.path.exists(cfg.CSV_FILE):
        return "1"

    last_id = "1"
    latest_date = None

    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        content = f.read(100)
        delim = ";" if ";" in content else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            lp = row.get("LastPlayed", "").strip()
            if lp and lp != "0" and lp != "-":
                try:
                    # Datum parsen (DD.MM.YYYY)
                    current_date = datetime.strptime(lp, "%d.%m.%Y")
                    if latest_date is None or current_date >= latest_date:
                        latest_date = current_date
                        last_id = row.get("ID", "1")
                except Exception:
                    pass
    return last_id


def toggle_map_clear(map_id: str) -> bool:
    rows = []
    found = False
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        header = reader[0]
        rows.append(header)
        for row in reader[1:]:
            if row[0].strip().upper() == map_id.upper():
                found = True
                row[1] = (
                    row[1].replace(" [C]", "") if " [C]" in row[1] else row[1] + " [C]"
                )
            rows.append(row)
    if found:
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(rows)
    return found


def toggle_mod_skip(map_id: str) -> bool:
    rows = []
    found = False
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        fieldnames = list(reader[0].keys())
        for row in reader:
            if row["ID"].strip().upper() == map_id.upper():
                found = True
                row["MOD"] = "0" if row.get("MOD") == "1" else "1"
            rows.append(row)
    if found:
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return found


def uninstall_map(map_id: str) -> bool:
    rows, to_del, header = [], None, []
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row[0].strip().upper() == map_id.upper():
                to_del = row
            else:
                rows.append(row)
    if not to_del:
        return False
    if to_del[6].upper() == "IWAD":
        return False
    print(f"\n  Lösche '{to_del[1]}'? (JA zum Bestätigen)")
    if input("> ").strip() == "JA":
        shutil.rmtree(os.path.join(cfg.PWAD_DIR, to_del[3]), ignore_errors=True)
        with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        reorganize_map_indices()
    return True


def reorganize_map_indices() -> None:
    if not os.path.exists(cfg.CSV_FILE):
        return
    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
    if not reader:
        return
    iwads = [r for r in reader if r["Kategorie"].upper() == "IWAD"]
    pwads = [r for r in reader if r["Kategorie"].upper() == "PWAD"]
    extras = [
        r for r in reader if r["Kategorie"].upper() in ["EXTRA", "HERETIC", "HEXEN"]
    ]

    for i, r in enumerate(iwads, 1):
        r["ID"] = str(i)
    for i, r in enumerate(pwads, len(iwads) + 1):
        r["ID"] = str(i)
    # Extras behalten ihre H/X Präfixe meistens bei, hier nur Sortierung
    with open(cfg.CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(reader[0].keys()))
        writer.writeheader()
        writer.writerows(iwads + pwads + extras)


def get_next_id(category):
    """Berechnet die nächste freie ID (I-xxx, P-xxx, E-xxx)."""
    prefix = "P"
    if category == "IWAD":
        prefix = "I"
    elif category in ["EXTRA", "HERETIC", "HEXEN"]:
        prefix = "E"

    ids = []
    if os.path.exists(cfg.CSV_FILE):
        with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
            content = f.read()
            delim = ";" if ";" in content else ","
            f.seek(0)
            reader = csv.reader(f, delimiter=delim)
            next(reader, None)  # Header überspringen
            for row in reader:
                if row and row[0].startswith(prefix):
                    try:
                        num = int(row[0].split("-")[1])
                        ids.append(num)
                    except Exception:
                        pass

    next_num = max(ids) + 1 if ids else 1
    return f"{prefix}-{next_num:03d}"
