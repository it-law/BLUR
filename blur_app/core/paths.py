from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "BLUR"
APP_AUTHOR = "BLUR"


def _dirs() -> PlatformDirs:
    return PlatformDirs(APP_NAME, APP_AUTHOR)


def get_app_data_dir() -> Path:
    return Path(_dirs().user_data_dir)


def get_playbooks_dir() -> Path:
    return get_app_data_dir() / "playbooks"


def get_temp_dir() -> Path:
    return get_app_data_dir() / "temp"


def get_audit_db_path() -> Path:
    return get_app_data_dir() / "audit.db"


def get_hotfolder_config_path() -> Path:
    return get_app_data_dir() / "hotfolder.json"
