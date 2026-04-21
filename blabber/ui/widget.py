import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
from typing import Callable


class BlabberWidget(Gtk.Window):
    """Floating control panel — top-left by default, draggable."""

    def __init__(
        self,
        on_start: Callable,
        on_pause: Callable,
        on_stop: Callable,
        on_minimize: Callable,
        on_settings: Callable,
        on_quit: Callable,
        x: int = 10,
        y: int = 10,
    ):
        # POPUP windows are unreliable on some compositors/desktop shells.
        # Use an undecorated TOPLEVEL window for better production behavior.
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._on_start = on_start
        self._on_pause = on_pause
        self._on_stop = on_stop
        self._on_minimize = on_minimize
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._drag_offset = (0, 0)

        self._build_ui()
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.stick()

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.move(x, y)
        self._apply_css()
        self.connect("button-press-event", self._on_button_press)
        self.connect("motion-notify-event", self._on_motion)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK
        )

    def _apply_css(self) -> None:
        css = b"""
        window {
            background-color: rgba(30, 30, 30, 0.92);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.15);
        }
        #status-dot {
            font-size: 11px;
            padding: 2px 3px 2px 6px;
            color: #888;
        }
        #status-label {
            font-size: 11px;
            padding: 2px 6px 2px 2px;
            color: #aaa;
            min-width: 58px;
        }
        #status-label.off      { color: #666; }
        #status-label.loading  { color: #999; }
        #status-label.ready    { color: #4fc3a1; }
        #status-label.listening { color: #ff4d4d; }
        #status-label.paused   { color: #ffaa00; }
        #status-label.idle     { color: #ff8c00; }
        .ctrl-btn {
            background: rgba(255,255,255,0.08);
            border: none;
            border-radius: 4px;
            color: #eee;
            font-size: 13px;
            min-width: 26px;
            min-height: 26px;
            padding: 0;
        }
        .ctrl-btn:hover { background: rgba(255,255,255,0.18); }
        .ctrl-btn:disabled { color: #3a3a3a; background: transparent; }
        #btn-minimize, #btn-settings {
            background: transparent;
            border: none;
            color: #888;
            font-size: 12px;
            min-width: 22px;
            min-height: 26px;
            padding: 0 3px;
        }
        #btn-minimize:hover, #btn-settings:hover { color: #ccc; }
        #btn-quit {
            background: transparent;
            border: none;
            color: #888;
            font-size: 12px;
            min-width: 22px;
            min-height: 26px;
            padding: 0 3px;
        }
        #btn-quit:hover { color: #ff6666; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(4)

        # ── Status row ────────────────────────────────────────────────
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        self._status_dot = Gtk.Label(label="⚫")
        self._status_dot.set_name("status-dot")
        status_box.pack_start(self._status_dot, False, False, 0)

        self._status_label = Gtk.Label(label="Off")
        self._status_label.set_name("status-label")
        self._status_label.set_halign(Gtk.Align.START)
        status_box.pack_start(self._status_label, True, True, 0)

        vbox.pack_start(status_box, False, False, 0)

        # ── Button row ────────────────────────────────────────────────
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        self._btn_start = Gtk.Button(label="▶")
        self._btn_start.set_name("btn-start")
        self._btn_start.get_style_context().add_class("ctrl-btn")
        self._btn_start.set_tooltip_text("Start")
        self._btn_start.connect("clicked", lambda _: self._on_start())
        btn_box.pack_start(self._btn_start, False, False, 0)

        self._btn_pause = Gtk.Button(label="⏸")
        self._btn_pause.set_name("btn-pause")
        self._btn_pause.get_style_context().add_class("ctrl-btn")
        self._btn_pause.set_tooltip_text("Pause")
        self._btn_pause.connect("clicked", lambda _: self._on_pause())
        btn_box.pack_start(self._btn_pause, False, False, 0)

        self._btn_stop = Gtk.Button(label="⏹")
        self._btn_stop.set_name("btn-stop")
        self._btn_stop.get_style_context().add_class("ctrl-btn")
        self._btn_stop.set_tooltip_text("Stop")
        self._btn_stop.connect("clicked", lambda _: self._on_stop())
        btn_box.pack_start(self._btn_stop, False, False, 0)

        self._btn_minimize = Gtk.Button(label="—")
        self._btn_minimize.set_name("btn-minimize")
        self._btn_minimize.set_tooltip_text("Minimize")
        self._btn_minimize.connect("clicked", lambda _: self._on_minimize())
        btn_box.pack_start(self._btn_minimize, False, False, 0)

        self._btn_settings = Gtk.Button(label="⚙")
        self._btn_settings.set_name("btn-settings")
        self._btn_settings.set_tooltip_text("Settings")
        self._btn_settings.connect("clicked", lambda _: self._on_settings())
        btn_box.pack_start(self._btn_settings, False, False, 0)

        self._btn_quit = Gtk.Button(label="✕")
        self._btn_quit.set_name("btn-quit")
        self._btn_quit.set_tooltip_text("Quit")
        self._btn_quit.connect("clicked", lambda _: self._on_quit())
        btn_box.pack_start(self._btn_quit, False, False, 0)

        vbox.pack_start(btn_box, False, False, 2)
        self.add(vbox)

    def set_state(self, state: str) -> None:
        """state: 'off' | 'loading' | 'ready' | 'listening' | 'paused' | 'idle'"""
        GLib.idle_add(self._apply_state, state)

    def _apply_state(self, state: str) -> bool:
        dots = {
            "off":       "⚫",
            "loading":   "⏳",
            "ready":     "🟢",
            "listening": "🔴",
            "paused":    "🟡",
            "idle":      "🟠",
        }
        labels = {
            "off":       "Off",
            "loading":   "Loading…",
            "ready":     "Ready",
            "listening": "Listening",
            "paused":    "Paused",
            "idle":      "Idle",
        }
        self._status_dot.set_text(dots.get(state, "⚫"))
        self._status_label.set_text(labels.get(state, state.capitalize()))

        ctx = self._status_label.get_style_context()
        for cls in ("off", "loading", "ready", "listening", "paused", "idle"):
            ctx.remove_class(cls)
        ctx.add_class(state)

        is_busy = state in ("loading", "ready")
        is_listening = state == "listening"
        is_stoppable = state in ("listening", "paused", "idle", "ready")

        self._btn_start.set_sensitive(not is_listening and not is_busy)
        self._btn_pause.set_sensitive(is_listening)
        self._btn_stop.set_sensitive(is_stoppable)
        return False

    def _on_button_press(self, widget, event) -> None:
        if event.button == 1:
            pos = self.get_position()
            self._drag_offset = (int(event.x_root) - pos[0], int(event.y_root) - pos[1])

    def _on_motion(self, widget, event) -> None:
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            nx = int(event.x_root) - self._drag_offset[0]
            ny = int(event.y_root) - self._drag_offset[1]
            self.move(nx, ny)

    def get_position_xy(self) -> tuple[int, int]:
        return self.get_position()
