import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from typing import Callable
from blabber import config


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, on_model_changed: Callable[[str], None]):
        super().__init__(title="Blabber Settings", transient_for=parent, flags=0)
        self._on_model_changed = on_model_changed
        self._cfg = config.load()

        self.set_default_size(340, 260)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY,
        )

        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(14)
        box.set_margin_bottom(14)

        # Model size
        model_label = Gtk.Label(label="<b>Transcription Model</b>", use_markup=True)
        model_label.set_halign(Gtk.Align.START)
        box.add(model_label)

        model_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._model_combo = Gtk.ComboBoxText()
        options = [
            ("small",  "Small  (~466 MB) — Fast, good accuracy"),
            ("medium", "Medium (~1.5 GB) — Balanced"),
            ("large",  "Large  (~3 GB)   — Best accuracy, slower"),
        ]
        for key, label in options:
            self._model_combo.append(key, label)
        self._model_combo.set_active_id(self._cfg.get("model_size", "small"))
        model_box.pack_start(self._model_combo, True, True, 0)
        box.add(model_box)

        box.add(Gtk.Separator())

        # Auto-start on click
        auto_label = Gtk.Label(label="<b>Behaviour</b>", use_markup=True)
        auto_label.set_halign(Gtk.Align.START)
        box.add(auto_label)

        self._auto_start = Gtk.CheckButton(
            label="Auto-start listening when text field is clicked"
        )
        self._auto_start.set_active(self._cfg.get("auto_start_on_click", False))
        box.add(self._auto_start)

        box.add(Gtk.Separator())

        # Timeouts
        timeout_label = Gtk.Label(label="<b>Power Saving</b>", use_markup=True)
        timeout_label.set_halign(Gtk.Align.START)
        box.add(timeout_label)

        pause_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pause_box.add(Gtk.Label(label="Auto-pause after silence (seconds):"))
        self._pause_spin = Gtk.SpinButton.new_with_range(5, 300, 5)
        self._pause_spin.set_value(self._cfg.get("auto_pause_seconds", 30))
        pause_box.pack_end(self._pause_spin, False, False, 0)
        box.add(pause_box)

        idle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        idle_box.add(Gtk.Label(label="Idle after paused (seconds):"))
        self._idle_spin = Gtk.SpinButton.new_with_range(10, 600, 10)
        self._idle_spin.set_value(self._cfg.get("idle_timeout_seconds", 60))
        idle_box.pack_end(self._idle_spin, False, False, 0)
        box.add(idle_box)

        self.show_all()

    def run_and_save(self) -> None:
        response = self.run()
        if response == Gtk.ResponseType.APPLY:
            self._save()
        self.destroy()

    def _save(self) -> None:
        cfg = config.load()
        new_model = self._model_combo.get_active_id()
        if not new_model:
            new_model = "small"
        model_changed = new_model != cfg.get("model_size")

        cfg["model_size"] = new_model
        cfg["auto_start_on_click"] = self._auto_start.get_active()
        cfg["auto_pause_seconds"] = int(self._pause_spin.get_value())
        cfg["idle_timeout_seconds"] = int(self._idle_spin.get_value())
        config.save(cfg)

        if model_changed:
            self._on_model_changed(new_model)
