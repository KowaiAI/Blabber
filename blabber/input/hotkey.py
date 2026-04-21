from typing import Callable
import threading

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False


class HotkeyListener:
    """Listens for Shift+B global hotkey to show/hide the widget."""

    def __init__(self, on_triggered: Callable[[], None]):
        self._callback = on_triggered
        self._listener = None
        self._current_keys: set = set()
        self._keys_lock = threading.Lock()

    def start(self) -> None:
        if not HAS_PYNPUT:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_press(self, key) -> None:
        with self._keys_lock:
            self._current_keys.add(key)
        self._check_hotkey()

    def _on_release(self, key) -> None:
        with self._keys_lock:
            self._current_keys.discard(key)

    def _check_hotkey(self) -> None:
        with self._keys_lock:
            keys_snapshot = set(self._current_keys)

        shift_pressed = any(
            k in keys_snapshot
            for k in (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l)
        )
        b_pressed = False
        for key in keys_snapshot:
            key_char = getattr(key, "char", None)
            if key_char and key_char.lower() == "b":
                b_pressed = True
                break

        if shift_pressed and b_pressed:
            with self._keys_lock:
                self._current_keys.clear()
            self._callback()
