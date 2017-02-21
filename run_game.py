#!/usr/bin/python3
import sys
import os

if sys.version_info < (3, 5):
    sys.exit("Python 3.5 or later is required.")



from pathlib import Path

Path(__file__).parent.cwd()
binary = 'pgzrun.exe' if sys.platform == 'win32' else 'pgzrun'

try:
    os.execvp(binary, [binary, 'murder.py'])
except FileNotFoundError:
    sys.exit(
        "Could not find {} binary. ".format(binary) +
        "Is Pygame Zero installed?"
    )
