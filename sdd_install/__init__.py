"""Shared core of the SDD installer and uninstaller (stdlib only, Python >= 3.9).

`install.py` / `uninstall.py` at the repo root are the entrypoints; `install.sh`,
`install.ps1`, `uninstall.sh` and `uninstall.ps1` are thin shims that find a Python
interpreter and run them.
"""

MIN_PYTHON = (3, 9)
