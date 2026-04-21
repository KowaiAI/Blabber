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
        on_settings: Callable,
        x: int = 10,
        y: int = 10,
    ):
        super().__init__(type=Gtk.WindowType.POPUP)
        self._on_start = on_start
        self._on_pause = on_pause
        self._on_settings = on_settings
        self._drag_offset = (0, 0)
        self._last_plus_time = 0.0

        self._build_ui()
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
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
            padding: 2px 6px;
            color: #888;
        }
        #btn-plus {
            background: rgba(255,255,255,0.08);
            border: none;
            border-radius: 4px;
            color: #eee;
            font-size: 14px;
            font-weight: bold;
            min-width: 28px;
            min-height: 28px;
            padding: 0;
        }
        #btn-plus:hover { background: rgba(255,255,255,0.18); }
        #btn-plus.listening { color: #ff4d4d; }
        #btn-plus.paused { color: #ffaa00; }
        #btn-settings {
            background: transparent;
            border: none;
            color: #888;
            font-size: 12px;
            min-width: 24px;
            min-height: 28px;
            padding: 0 4px;
        }
        #btn-settings:hover { color: #ccc; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        self._status_dot = Gtk.Label(label="⚫")
        self._status_dot.set_name("status-dot")
        box.pack_start(self._status_dot, False, False, 0)

        self._btn_settings = Gtk.Button(label="⚙")
        self._btn_settings.set_name("btn-settings")
        self._btn_settings.set_relief(Gtk.ReliefStyle.NONE)
        self._btn_settings.connect("clicked", lambda _: self._on_settings())
        box.pack_start(self._btn_settings, False, False, 0)

        self._btn_plus = Gtk.Button(label="+")
        self._btn_plus.set_name("btn-plus")
        self._btn_plus.set_relief(Gtk.ReliefStyle.NONE)
        self._btn_plus.connect("clicked", self._handle_plus_click)
        box.pack_start(self._btn_plus, False, False, 0)

        self.add(box)

    def _handle_plus_click(self, _) -> None:
        import time
        now = time.time()
        if now - self._last_plus_time < 0.4:
            self._on_pause()
            self._last_plus_time = 0.0
        else:
            self._last_plus_time = now
            GLib.timeout_add(450, self._single_click_action)

    def _single_click_action(self) -> bool:
        import time
        if time.time() - self._last_plus_time >= 0.4:
            self._on_start()
        return False

    def set_state(self, state: str) -> None:
        """state: 'off' | 'listening' | 'paused' | 'idle'"""
        GLib.idle_add(self._apply_state, state)

    def _apply_state(self, state: str) -> bool:
        dots = {"off": "⚫", "listening": "🔴", "paused": "🟡", "idle": "🟠"}
        self._status_dot.set_text(dots.get(state, "⚫"))
        ctx = self._btn_plus.get_style_context()
        for cls in ("listening", "paused"):
            ctx.remove_class(cls)
        if state == "listening":
            ctx.add_class("listening")
        elif state == "paused":
            ctx.add_class("paused")
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
