import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    HAS_INDICATOR = True
except (ValueError, ImportError):
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3
        HAS_INDICATOR = True
    except (ValueError, ImportError):
        HAS_INDICATOR = False

from gi.repository import Gtk
from typing import Callable


ICON_MAP = {
    "off":       "audio-input-microphone-muted-symbolic",
    "loading":   "audio-input-microphone-muted-symbolic",
    "ready":     "audio-input-microphone-symbolic",
    "listening": "audio-input-microphone-symbolic",
    "paused":    "audio-input-microphone-symbolic",
    "idle":      "audio-input-microphone-muted-symbolic",
}

LABEL_MAP = {
    "off":       "Blabber — Off",
    "loading":   "Blabber — Loading",
    "ready":     "Blabber — Ready",
    "listening": "Blabber — Listening",
    "paused":    "Blabber — Paused",
    "idle":      "Blabber — Idle",
}


class TrayIcon:
    def __init__(self, on_show_hide: Callable, on_quit: Callable):
        self._on_show_hide = on_show_hide
        self._on_quit = on_quit
        self._indicator = None
        self._state = "off"

        if HAS_INDICATOR:
            self._indicator = AppIndicator3.Indicator.new(
                "blabber",
                ICON_MAP["off"],
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self._indicator.set_menu(self._build_menu())

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        item_toggle = Gtk.MenuItem(label="Show / Hide (Shift+B)")
        item_toggle.connect("activate", lambda _: self._on_show_hide())
        menu.append(item_toggle)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Quit Blabber")
        item_quit.connect("activate", lambda _: self._on_quit())
        menu.append(item_quit)

        menu.show_all()
        return menu

    def set_state(self, state: str) -> None:
        self._state = state
        if self._indicator:
            self._indicator.set_icon_full(
                ICON_MAP.get(state, ICON_MAP["off"]),
                LABEL_MAP.get(state, "Blabber"),
            )
