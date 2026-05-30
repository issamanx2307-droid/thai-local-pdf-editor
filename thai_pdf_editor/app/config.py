# -*- coding: utf-8 -*-
"""Path configuration for the local desktop app."""

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = DATA_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"
SIGNATURE_DIR = DATA_DIR / "signatures"
SETTINGS_DIR = DATA_DIR / "settings"
RECENT_FILES_PATH = SETTINGS_DIR / "recent_files.json"
LAYOUT_SETTINGS_PATH = SETTINGS_DIR / "layout.json"
FONT_DIR = ASSETS_DIR / "fonts"
IMPORTED_FONT_DIR = FONT_DIR / "imported"
ICON_DIR = ASSETS_DIR / "icons"
APP_LOG_PATH = LOG_DIR / "app.log"

REQUIRED_DIRS = (
    ASSETS_DIR,
    FONT_DIR,
    IMPORTED_FONT_DIR,
    ICON_DIR,
    DATA_DIR,
    BACKUP_DIR,
    LOG_DIR,
    TEMP_DIR,
    SIGNATURE_DIR,
    SETTINGS_DIR,
)
