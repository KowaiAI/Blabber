import threading
from typing import Callable

try:
    import pyatspi
    HAS_ATSPI = True
except ImportError:
    HAS_ATSPI = False


class FocusMonitor:
    """Watches AT-SPI focus events to detect when a text field is focused."""

    def __init__(self, on_text_field_focused: Callable[[], None]):
        self._callback = on_text_field_focused
        self._atspi_listener = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        if HAS_ATSPI:
            self._start_atspi()

    def stop(self) -> None:
        with self._lock:
            self._running = False

        if HAS_ATSPI and self._atspi_listener:
            try:
                pyatspi.Registry.deregisterEventListener(
                    self._on_atspi_event, "focus:"
                )
            except Exception:
                pass
            self._atspi_listener = None

    def _start_atspi(self) -> None:
        try:
            pyatspi.Registry.registerEventListener(
                self._on_atspi_event, "focus:"
            )
            self._atspi_listener = self._on_atspi_event
            t = threading.Thread(target=self._atspi_loop, daemon=True)
            t.start()
        except Exception:
            pass

    def _atspi_loop(self) -> None:
        try:
            pyatspi.Registry.start(gil=False)
        except Exception:
            pass

    def _on_atspi_event(self, event) -> None:
        if not self._running:
            return
        try:
            role = event.source.getRole()
            text_roles = {
                pyatspi.ROLE_TEXT,
                pyatspi.ROLE_ENTRY,
                pyatspi.ROLE_PASSWORD_TEXT,
                pyatspi.ROLE_EDITBAR,
                pyatspi.ROLE_TERMINAL,
            }
            if role in text_roles:
                self._callback()
        except Exception:
            pass
