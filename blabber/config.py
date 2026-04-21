import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "blabber"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "model_size": "small",
    "auto_start_on_click": False,
    "idle_timeout_seconds": 360,
    "off_timeout_seconds": 1200,
    "hotkey": "<shift>+b",
    "widget_x": 10,
    "widget_y": 10,
    "display_server": "auto",
}


def load() -> dict:
    if not CONFIG_FILE.exists():
        return dict(DEFAULTS)
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str):
    return load().get(key, DEFAULTS.get(key))


def set(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)
