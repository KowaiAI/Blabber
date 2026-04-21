import threading
from typing import Callable

try:
    import pyatspi
    HAS_ATSPI = True
except ImportError:
    HAS_ATSPI = False

try:
    from pynput import mouse
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False


class FocusMonitor:
    """Watches for mouse clicks and AT-SPI focus events to detect text field selection."""

    def __init__(self, on_text_field_focused: Callable[[], None]):
        self._callback = on_text_field_focused
        self._mouse_listener = None
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

        if HAS_ATSPI and HAS_PYNPUT:
            self._start_mouse_listener()

    def stop(self) -> None:
        with self._lock:
            self._running = False

        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None

        if HAS_ATSPI and self._atspi_listener:
            try:
                pyatspi.Registry.deregisterEventListener(
                    self._on_atspi_event, "focus:"
                )
            except Exception:
                pass

    def _start_atspi(self) -> None:
        try:
            pyatspi.Registry.registerEventListener(
                self._on_atspi_event, "focus:"
            )
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

    def _start_mouse_listener(self) -> None:
        try:
            self._mouse_listener = mouse.Listener(on_click=self._on_click)
            self._mouse_listener.start()
        except Exception:
            pass

    def _on_click(self, x, y, button, pressed) -> None:
        if pressed and self._running:
            self._callback()
