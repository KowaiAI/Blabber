import logging
import queue
import threading
import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from blabber import config
from blabber.audio.capture import AudioCapture
from blabber.stt.engine import STTEngine
from blabber.input.injector import type_text
from blabber.input.focus_monitor import FocusMonitor
from blabber.input.hotkey import HotkeyListener
from blabber.ui.widget import BlabberWidget
from blabber.ui.tray import TrayIcon
from blabber.ui.settings_dialog import SettingsDialog

TRANSCRIBE_THREAD_SHUTDOWN_TIMEOUT_SECONDS = 2
TRANSCRIBE_QUEUE_MAX_SIZE = 16
TRANSCRIBE_WORKER_STOP = object()
START_LISTENING_DELAY_SECONDS = 1.5
logger = logging.getLogger(__name__)


class State:
    OFF = "off"
    LOADING = "loading"
    READY = "ready"
    LISTENING = "listening"
    PAUSED = "paused"
    IDLE = "idle"


class BlabberApp:
    def __init__(self):
        self._cfg = config.load()
        self._state = State.OFF
        self._state_lock = threading.Lock()

        self._stt = STTEngine(model_size=self._cfg.get("model_size", "small"))
        self._capture = AudioCapture(
            on_speech_chunk=self._on_speech_chunk,
            on_silence=self._handle_silence,
        )
        self._focus_monitor = FocusMonitor(on_text_field_focused=self._on_focus)
        self._hotkey = HotkeyListener(on_triggered=self._toggle_widget)

        self._widget: BlabberWidget | None = None
        self._tray: TrayIcon | None = None

        self._pause_since: float = 0.0
        self._last_speech_time: float = 0.0
        self._timeout_thread: threading.Thread | None = None
        self._transcribe_thread: threading.Thread | None = None
        self._transcribe_queue: queue.Queue = queue.Queue(maxsize=TRANSCRIBE_QUEUE_MAX_SIZE)
        self._widget_visible = False

    def run(self) -> None:
        self._widget = BlabberWidget(
            on_start=self._cmd_start,
            on_pause=self._cmd_pause,
            on_stop=self._cmd_stop,
            on_minimize=self._cmd_minimize,
            on_settings=self._open_settings,
            on_quit=self._quit,
            x=self._cfg.get("widget_x", 10),
            y=self._cfg.get("widget_y", 10),
        )
        self._tray = TrayIcon(
            on_show_hide=self._toggle_widget,
            on_quit=self._quit,
        )

        self._focus_monitor.start()
        self._hotkey.start()
        self._start_timeout_watcher()
        self._start_transcribe_worker()

        self._widget.show_all()
        self._widget_visible = True
        self._set_state(State.OFF)

        Gtk.main()

    def _toggle_widget(self) -> None:
        GLib.idle_add(self._do_toggle_widget)

    def _do_toggle_widget(self) -> bool:
        if self._widget_visible:
            self._widget.hide()
            self._widget_visible = False
        else:
            self._widget.show_all()
            self._widget_visible = True
        return False

    def _cmd_start(self) -> None:
        with self._state_lock:
            if self._state in (State.LISTENING, State.LOADING, State.READY):
                return
        threading.Thread(target=self._start_listening, daemon=True).start()

    def _start_listening(self) -> None:
        if not self._stt.is_loaded:
            self._set_state(State.LOADING)
            self._stt.load()

        self._set_state(State.READY)
        time.sleep(START_LISTENING_DELAY_SECONDS)

        self._capture.start()
        with self._state_lock:
            self._last_speech_time = time.time()
            self._pause_since = 0.0
        self._set_state(State.LISTENING)

    def _cmd_pause(self) -> None:
        with self._state_lock:
            if self._state != State.LISTENING:
                return
        self._capture.stop()
        self._pause_since = time.time()
        self._set_state(State.PAUSED)

    def _cmd_stop(self) -> None:
        with self._state_lock:
            current = self._state
        if current not in (State.OFF, State.LOADING):
            self._capture.stop()
            self._pause_since = 0.0
            self._last_speech_time = 0.0
            self._set_state(State.OFF)

    def _cmd_minimize(self) -> None:
        GLib.idle_add(self._do_minimize)

    def _do_minimize(self) -> bool:
        if self._widget:
            self._widget.hide()
            self._widget_visible = False
        return False

    def _on_focus(self) -> None:
        cfg = config.load()
        if cfg.get("auto_start_on_click", False):
            with self._state_lock:
                if self._state in (State.OFF, State.PAUSED, State.IDLE):
                    threading.Thread(target=self._start_listening, daemon=True).start()

    def _on_speech_chunk(self, audio_bytes: bytes) -> None:
        with self._state_lock:
            self._last_speech_time = time.time()
        try:
            self._transcribe_queue.put_nowait(audio_bytes)
        except queue.Full:
            logger.warning("Dropping speech chunk because transcription queue is full")

    def _start_transcribe_worker(self) -> None:
        if self._transcribe_thread and self._transcribe_thread.is_alive():
            return
        self._transcribe_thread = threading.Thread(
            target=self._transcribe_loop, daemon=True
        )
        self._transcribe_thread.start()

    def _transcribe_loop(self) -> None:
        while True:
            audio_bytes = self._transcribe_queue.get()
            if audio_bytes is TRANSCRIBE_WORKER_STOP:
                break
            try:
                text = self._stt.transcribe(audio_bytes)
                if text:
                    display_server = config.get("display_server") or "auto"
                    type_text(text + " ", display_server=display_server)
            except Exception:
                logger.exception("Failed to transcribe speech chunk")

    def _handle_silence(self) -> None:
        pass

    def _set_state(self, state: str) -> None:
        with self._state_lock:
            self._state = state
        if self._widget:
            self._widget.set_state(state)
        if self._tray:
            self._tray.set_state(state)

    def _start_timeout_watcher(self) -> None:
        self._timeout_thread = threading.Thread(
            target=self._timeout_loop, daemon=True
        )
        self._timeout_thread.start()

    def _timeout_loop(self) -> None:
        while True:
            time.sleep(5)
            cfg = config.load()
            auto_pause_sec = cfg.get("auto_pause_seconds", 30)
            idle_sec = cfg.get("idle_timeout_seconds", 60)

            with self._state_lock:
                state = self._state
                last_speech = self._last_speech_time
                paused_since = self._pause_since

            if state == State.LISTENING and last_speech > 0:
                if time.time() - last_speech >= auto_pause_sec:
                    GLib.idle_add(self._auto_pause)

            elif state == State.PAUSED and paused_since > 0:
                if time.time() - paused_since >= idle_sec:
                    GLib.idle_add(self._go_idle)

    def _auto_pause(self) -> bool:
        with self._state_lock:
            if self._state != State.LISTENING:
                return False
        self._capture.stop()
        self._pause_since = time.time()
        self._set_state(State.PAUSED)
        return False

    def _go_idle(self) -> bool:
        with self._state_lock:
            if self._state != State.PAUSED:
                return False
        self._pause_since = 0.0
        self._set_state(State.IDLE)
        return False

    def _open_settings(self) -> None:
        GLib.idle_add(self._do_open_settings)

    def _do_open_settings(self) -> bool:
        dlg = SettingsDialog(
            parent=self._widget,
            on_model_changed=self._on_model_changed,
        )
        dlg.run_and_save()
        self._cfg = config.load()
        return False

    def _on_model_changed(self, new_size: str) -> None:
        was_listening = False
        with self._state_lock:
            was_listening = self._state == State.LISTENING

        if was_listening:
            self._capture.stop()
        self._stt.unload()
        self._stt = STTEngine(model_size=new_size)
        self._set_state(State.OFF)

    def _save_position(self) -> None:
        if self._widget:
            x, y = self._widget.get_position_xy()
            config.set_value("widget_x", x)
            config.set_value("widget_y", y)

    def _quit(self) -> None:
        self._save_position()
        self._capture.stop()
        self._transcribe_queue.put(TRANSCRIBE_WORKER_STOP)
        if self._transcribe_thread:
            self._transcribe_thread.join(
                timeout=TRANSCRIBE_THREAD_SHUTDOWN_TIMEOUT_SECONDS
            )
            if self._transcribe_thread.is_alive():
                logger.warning("Transcribe worker thread did not stop before timeout")
            self._transcribe_thread = None
        self._focus_monitor.stop()
        self._hotkey.stop()
        GLib.idle_add(Gtk.main_quit)
