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
        self._transcribe_stop = threading.Event()
        self._listen_session_id = 0
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
            self._listen_session_id += 1
            session_id = self._listen_session_id
        threading.Thread(
            target=self._start_listening, args=(session_id,), daemon=True
        ).start()

    def _start_listening(self, session_id: int) -> None:
        if not self._stt.is_loaded:
            self._set_state(State.LOADING)
            self._stt.load()

        with self._state_lock:
            if session_id != self._listen_session_id:
                return
        self._set_state(State.READY)
        time.sleep(START_LISTENING_DELAY_SECONDS)
        with self._state_lock:
            if session_id != self._listen_session_id or self._state != State.READY:
                return

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
        with self._state_lock:
            if self._state != State.LISTENING:
                return
        self._set_state_with_fields(State.PAUSED, pause_since=time.time())

    def _cmd_stop(self) -> None:
        with self._state_lock:
            current = self._state
            self._listen_session_id += 1
            if current == State.OFF:
                return
        self._capture.stop()
        self._drain_transcribe_queue()
        self._set_state_with_fields(State.OFF, pause_since=0.0, last_speech_time=0.0)

    def _cmd_minimize(self) -> None:
        GLib.idle_add(self._do_minimize)

    def _do_minimize(self) -> bool:
        if self._widget:
            self._widget.hide()
            self._widget_visible = False
        return False

    def _on_focus(self) -> None:
        with self._state_lock:
            auto_start = self._cfg.get("auto_start_on_click", False)
            can_auto_start = self._state in (State.OFF, State.PAUSED, State.IDLE)
        if auto_start and can_auto_start:
            self._cmd_start()

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
            if self._transcribe_stop.is_set():
                continue
            try:
                text = self._stt.transcribe(audio_bytes)
                with self._state_lock:
                    current_state = self._state
                if (
                    text
                    and not self._transcribe_stop.is_set()
                    and current_state not in (State.OFF, State.IDLE)
                ):
                    display_server = self._cfg.get("display_server") or "auto"
                    type_text(text + " ", display_server=display_server)
            except Exception:
                logger.exception("Failed to transcribe speech chunk")

    def _handle_silence(self) -> None:
        pass

    def _set_state(self, state: str) -> None:
        self._set_state_with_fields(state)

    def _set_state_with_fields(
        self,
        state: str,
        pause_since: float | None = None,
        last_speech_time: float | None = None,
    ) -> None:
        with self._state_lock:
            self._state = state
            if pause_since is not None:
                self._pause_since = pause_since
            if last_speech_time is not None:
                self._last_speech_time = last_speech_time
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
            with self._state_lock:
                auto_pause_sec = self._cfg.get("auto_pause_seconds", 30)
                idle_sec = self._cfg.get("idle_timeout_seconds", 60)
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
        self._set_state_with_fields(State.PAUSED, pause_since=time.time())
        return False

    def _go_idle(self) -> bool:
        with self._state_lock:
            if self._state != State.PAUSED:
                return False
        self._set_state_with_fields(State.IDLE, pause_since=0.0)
        return False

    def _drain_transcribe_queue(self) -> None:
        while True:
            try:
                self._transcribe_queue.get_nowait()
            except queue.Empty:
                break

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
        with self._state_lock:
            self._listen_session_id += 1
        self._transcribe_stop.set()
        self._drain_transcribe_queue()
        try:
            self._transcribe_queue.put_nowait(TRANSCRIBE_WORKER_STOP)
        except queue.Full:
            logger.warning(
                "Transcribe queue was full during shutdown; drained and retrying"
            )
            self._drain_transcribe_queue()
            try:
                self._transcribe_queue.put_nowait(TRANSCRIBE_WORKER_STOP)
            except queue.Full:
                logger.error("Failed to enqueue transcribe stop sentinel")
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
