import csv
import os
import re

import dms_core.config as cfg
from dms_core.config import Colors

# ============================================================================
# MAPS LADEN & KATEGORISIEREN
# ============================================================================


def load_maps() -> dict[int, list]:
    """
    Lädt alle Maps aus der CSV-Datei und teilt sie in drei Anzeigeblöcke (Spalten) auf:
      - Block 1: Basis-Spiele (IWADs)
      - Block 2: Modifikationen/Custom Maps (PWADs)
      - Block 3: Extras (Heretic, Hexen, Wolfenstein, Testmaps etc.)

    Gibt ein Dictionary zurück, das als Keys die Blocknummern (1, 2, 3)
    und als Values die dazugehörigen Listen an Map-Tuples enthält.
    """

    blocks: dict[int, list] = {1: [], 2: [], 3: []}

    if not os.path.exists(cfg.CSV_FILE):
        return blocks

    with open(cfg.CSV_FILE, "r", encoding="utf-8-sig") as f:
        content = f.read()
        if not content.strip():
            return blocks

        # Cursor wieder an den Anfang der Datei setzen für den Reader
        f.seek(0)

        # CSV-Format (Trennzeichen) automatisch erkennen
        try:
            dialect = csv.Sniffer().sniff(content[:2048], delimiters=",;")
        except csv.Error:
            dialect = "excel"

        reader = csv.DictReader(f, dialect=dialect)

        for row in reader:

            def safe_get(keys, default: str = "") -> str:
                """Hilfsfunktion: Prüft mehrere Spaltennamen und gibt den ersten gefundenen Wert zurück."""
                if isinstance(keys, str):
                    keys = [keys]
                for k in keys:
                    val = row.get(k)
                    if val is not None:
                        return str(val).strip()
                return default

            # Werte aus der CSV auslesen
            entry_id = safe_get("ID")
            name = safe_get("Name", "Unbekannt")
            core = safe_get(["Core", "IWAD"])
            ordner = safe_get(["Ordner_oder_Datei", "Ordner", "PWAD"])
            mods = safe_get(["ModsErlaubt", "MOD"], "1")

            if not mods:
                mods = "1"

            extra = safe_get(["Extra", "ARGS"])
            cat = safe_get("Kategorie").upper()

            # Kategorie bestimmen, falls sie leer ist
            if not cat:
                if "heretic" in core.lower() or "hexen" in core.lower():
                    cat = "EXTRA"
                elif "doom2" in core.lower() and ordner:
                    cat = "PWAD"
                else:
                    cat = "IWAD"

            # Spielzeit auslesen und formatieren
            try:
                play_val = row.get("Playtime", "0")
                playtime_min = (
                    int(play_val) if play_val and str(play_val).isdigit() else 0
                )
            except (ValueError, TypeError):
                playtime_min = 0

            playtime_str = ""
            if playtime_min > 0:
                if playtime_min >= 60:
                    h = playtime_min // 60
                    m = playtime_min % 60
                    playtime_str = f"[{h}h {m}m]"
                else:
                    playtime_str = f"[{playtime_min}m]"

            # Anzeige-String (mit Mod-Icon und Spielzeit) zusammenbauen
            mod_icon = "[M] " if mods == "1" else ""
            base_str = f"{entry_id} - {name} {mod_icon}"

            if playtime_str:
                display_text = (
                    f"{base_str}__L__ {Colors.GRAY}{playtime_str}{Colors.WHITE}"
                )
            else:
                display_text = f"{base_str}__L__"

            # Restliche Parameter für den Engine-Start sammeln
            remaining = []
            if ordner:
                remaining.append(ordner)
            remaining.append(mods)
            if extra:
                remaining.extend(extra.split())

            # Tuple für die spätere Verarbeitung erstellen
            # Aufbau: (Anzeigetext, ID, Core/IWAD, Name, Startparameter, Block-ID)
            item_tuple = (display_text, entry_id, core, name, remaining, 0)

            if cat == "IWAD":
                blocks[1].append((*item_tuple[:5], 1))
            elif cat == "PWAD":
                blocks[2].append((*item_tuple[:5], 2))
            elif cat in ["EXTRA", "HERETIC", "HEXEN"]:
                blocks[3].append((*item_tuple[:5], 3))

        # --- Sortierung für Block 3 (Extras) ---
        def natural_sort_key(item: tuple) -> tuple[int, int]:
            """Sortiert die IDs in der richtigen Reihenfolge (z.B. H2 vor H10)"""
            eid = str(item[1]).upper()
            priorities = {
                "H": 1,
                "X": 2,
                "W": 3,
                "T": 4,
            }

            prefix_match = re.match(r"([A-Z]+)", eid)
            prefix = prefix_match.group(1) if prefix_match else ""

            first_char = prefix[0] if prefix else ""
            weight = priorities.get(first_char, 99)

            num_match = re.search(r"(\d+)", eid)
            num = int(num_match.group(1)) if num_match else 0

            return (weight, num)

        if blocks[3]:
            blocks[3].sort(key=natural_sort_key)

            formatted_col4 = []
            last_prefix = None

            # Visuelle Trennlinien (leere Zeilen) zwischen verschiedenen Spiel-Typen einfügen
            for item in blocks[3]:
                current_id = str(item[1]).upper()
                prefix_match = re.match(r"([A-Z]+)", current_id)
                current_prefix = prefix_match.group(1) if prefix_match else ""

                if last_prefix is not None and current_prefix != last_prefix:
                    formatted_col4.append(("EMPTY", "EMPTY", "", "", [], 3))

                formatted_col4.append(item)
                last_prefix = current_prefix

            blocks[3] = formatted_col4

    return blocks
