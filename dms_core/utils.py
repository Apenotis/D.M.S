import ctypes
import os
import re
import sys
from ctypes import wintypes


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def real_len(text):
    if not text:
        return 0
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return len(ansi_escape.sub("", str(text)))


def ansi_center(text, width):
    visible_len = real_len(text)
    padding = max(0, width - visible_len)
    left_pad = padding // 2
    right_pad = padding - left_pad
    return (" " * left_pad) + text + (" " * right_pad)


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def resize_terminal(cols, lines):
    sys.stdout.write(f"\x1b[8;{lines};{cols}t")
    sys.stdout.flush()

    if os.name == "nt":
        try:
            # 2. Klassischer Windows CMD Befehl
            os.system(f"mode con: cols={cols} lines={lines}")

            # 3. Harter Windows API Call
            handle = ctypes.windll.kernel32.GetStdHandle(-11)
            coord = wintypes._COORD(cols, lines)
            rect = wintypes.SMALL_RECT(0, 0, cols - 1, lines - 1)
            ctypes.windll.kernel32.SetConsoleScreenBufferSize(handle, coord)
            ctypes.windll.kernel32.SetConsoleWindowInfo(
                handle, True, ctypes.byref(rect)
            )
        except Exception:
            pass


def set_terminal_title(title):
    if os.name == "nt":
        ctypes.windll.kernel32.SetConsoleTitleW(str(title))
