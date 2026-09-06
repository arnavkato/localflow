"""Load config.yaml from next to the script (or the .exe when frozen).
ponytail: plain dict, no schema class — YAGNI."""
import sys
from pathlib import Path

import yaml


def _base_dir():
    # frozen (PyInstaller): exe folder; from source: this file's folder
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def load(path=None):
    p = Path(path) if path else _base_dir() / "config.yaml"
    if not p.exists():
        sys.exit(f"config not found: {p.resolve()} (put config.yaml next to the app)")
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
