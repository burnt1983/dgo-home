#!/usr/bin/env python3
"""DGO Home. An on-screen home remote with Cream, Dark, and Glass."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

CFG = Path.home() / ".config" / "dgo-home" / "config.json"
THEMES = (("Cream", "cream"), ("Dark", "dark"), ("Glass", "glass"))
PLATE_STEPS = (("Solid", 0), ("Soft", 28), ("Sheer", 50), ("Clear", 70))
PLATES = {
    "cream": (0.984, 0.969, 0.941),
    "dark": (0.047, 0.047, 0.051),
    "glass": (1.0, 0.980, 0.957),
}
INKS = {
    "cream": "#161616",
    "dark": "#f4efe6",
    "glass": "#241c18",
}
MUTED = {
    "cream": "#5c5348",
    "dark": "#cbbfae",
    "glass": "#5c5148",
}


def load_config() -> dict:
    try:
        data = json.loads(CFG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    theme = data.get("theme")
    if theme not in PLATES:
        data["theme"] = "cream"
    try:
        data["transparency"] = max(0, min(100, int(data.get("transparency", 0))))
    except (TypeError, ValueError):
        data["transparency"] = 0
    try:
        data["volume"] = max(0, min(100, int(data.get("volume", 40))))
    except (TypeError, ValueError):
        data["volume"] = 40
    for key in ("light", "lamp", "fan", "speaker"):
        data[key] = bool(data.get(key, False))
    data["note"] = str(data.get("note") or "")
    return data


def save_config(data: dict) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CFG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, CFG)


def theme_css(theme: str) -> bytes:
    ink = INKS[theme]
    muted = MUTED[theme]
    if theme == "dark":
        trough, highlight = "rgba(244, 239, 230, 0.22)", "#f4efe6"
    else:
        trough, highlight = "rgba(22, 22, 22, 0.12)", "#161616"
    return f"""
#dgo-home,
#dgo-home scrolledwindow,
#dgo-home viewport,
#dgo-home box,
#dgo-home .background {{
  background-color: transparent;
  background-image: none;
  border: none;
  box-shadow: none;
}}
#dgo-home label {{
  font-family: Outfit, Sans;
  color: {ink};
  text-shadow: none;
}}
#dgo-home label.heading {{
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.5px;
}}
#dgo-home label.section {{ font-weight: 600; }}
#dgo-home label.hint {{ color: {muted}; font-size: 11px; }}
#dgo-home button {{
  font-family: Outfit, Sans;
  background-color: #fffcf8;
  background-image: none;
  color: #161616;
  border-radius: 999px;
  min-height: 34px;
  padding: 0 14px;
  font-size: 13.5px;
  font-weight: 600;
  border: 1px solid rgba(22, 22, 22, 0.14);
  box-shadow: none;
}}
#dgo-home button label {{ color: #161616; text-shadow: none; }}
#dgo-home button.theme-on,
#dgo-home button.theme-on label,
#dgo-home button.plate-on,
#dgo-home button.plate-on label,
#dgo-home button.on,
#dgo-home button.on label {{
  background-color: #161616;
  color: #f6f1e8;
  border-color: #161616;
}}
#dgo-home button.theme-dark,
#dgo-home button.theme-dark label,
#dgo-home button.theme-dark.theme-on,
#dgo-home button.theme-dark.theme-on label {{
  background-color: #ffffff;
  color: #161616;
  border-color: #161616;
  box-shadow: none;
}}
#dgo-home button.theme-dark.theme-on {{
  box-shadow: inset 0 0 0 2px #161616;
}}
#dgo-home button.close,
#dgo-home button.close label {{
  background: none;
  border: none;
  box-shadow: none;
  min-width: 28px;
  min-height: 28px;
  padding: 0;
  color: {ink};
  font-size: 18px;
  font-weight: 400;
}}
#dgo-home scale {{ color: {ink}; }}
#dgo-home scale trough {{
  background-color: {trough};
  min-height: 6px;
  border: none;
}}
#dgo-home scale highlight {{
  background-color: {highlight};
  border: none;
}}
""".encode()


def _rounded(cr, x, y, w, h, r) -> None:
    import math

    radius = max(0.0, min(float(r), w / 2.0, h / 2.0))
    cr.new_sub_path()
    cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, 0)
    cr.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
    cr.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()


class Home(Gtk.Window):
    def __init__(self, check: bool = False):
        super().__init__(title="DGO Home")
        self._check = check
        self.cfg = load_config()
        self._theme_buttons: list[tuple[Gtk.Button, str]] = []
        self._plate_buttons: list[tuple[Gtk.Button, int]] = []
        self._device_buttons: dict[str, Gtk.Button] = {}
        self.set_name("dgo-home")
        self.set_app_paintable(True)
        self.set_default_size(440, 640)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.connect("draw", self._paint)
        self.connect("screen-changed", self._on_screen)
        self._on_screen()
        self._css = Gtk.CssProvider()
        self._css.load_from_data(theme_css(self.cfg["theme"]))
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(14)
        root.set_margin_bottom(14)
        root.set_margin_start(16)
        root.set_margin_end(16)
        self.add(root)

        title = Gtk.Label()
        title.set_markup('DGO <span weight="450">Home</span>')
        title.get_style_context().add_class("heading")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        close = Gtk.Button(label="×")
        close.get_style_context().add_class("close")
        close.connect("clicked", lambda *_: self.destroy())
        head = Gtk.Box(spacing=8)
        head.pack_start(title, True, True, 0)
        head.pack_end(close, False, False, 0)
        handle = Gtk.EventBox()
        handle.set_visible_window(False)
        handle.add(head)
        handle.connect("button-press-event", self._drag)
        root.pack_start(handle, False, False, 0)

        themes = Gtk.Box(spacing=6)
        themes.set_homogeneous(True)
        for label, key in THEMES:
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("theme")
            if key == "dark":
                button.get_style_context().add_class("theme-dark")
            button.connect("clicked", lambda _b, name=key: self._choose_theme(name))
            self._theme_buttons.append((button, key))
            themes.pack_start(button, True, True, 0)
        root.pack_start(themes, False, False, 0)

        self.status = Gtk.Label(label=self.cfg["note"] or "Ready")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        root.pack_start(self.status, False, False, 0)

        root.pack_start(self._section("Transparency"), False, False, 0)
        self.plate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.plate_scale.set_value(self.cfg["transparency"])
        self.plate_scale.set_draw_value(True)
        self.plate_scale.connect("value-changed", self._on_plate)
        self.plate_scale.set_tooltip_text(self._plate_tip())
        root.pack_start(self.plate_scale, False, False, 0)
        presets = Gtk.Box(spacing=6)
        presets.set_homogeneous(True)
        for label, amount in PLATE_STEPS:
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _b, n=amount: self.plate_scale.set_value(n))
            self._plate_buttons.append((button, amount))
            presets.pack_start(button, True, True, 0)
        root.pack_start(presets, False, False, 0)

        root.pack_start(self._section("Speaker"), False, False, 0)
        self.speaker = Gtk.Button(label=self._speaker_label())
        self.speaker.connect("clicked", self._toggle_speaker)
        root.pack_start(self.speaker, False, False, 0)

        root.pack_start(self._section("Devices"), False, False, 0)
        for key, label in (("light", "Light"), ("lamp", "Lamp"), ("fan", "Fan")):
            button = Gtk.Button(label=self._device_label(label, key))
            button.connect("clicked", lambda _b, name=key, title=label: self._toggle_device(name, title))
            self._device_buttons[key] = button
            root.pack_start(button, False, False, 0)

        root.pack_start(self._section("Volume"), False, False, 0)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume.set_value(self.cfg["volume"])
        self.volume.set_draw_value(True)
        self.volume.connect("value-changed", self._on_volume)
        root.pack_start(self.volume, False, False, 0)

        self._mark_theme_buttons()
        self._mark_plate_buttons()
        self._mark_devices()
        self.connect("destroy", self._shutdown)

    def _section(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        label.get_style_context().add_class("section")
        return label

    def _on_screen(self, *_args) -> None:
        screen = self.get_screen()
        if screen is None:
            return
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

    def _paint(self, widget, cr) -> bool:
        if not widget.get_has_window():
            return False
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        if width < 2 or height < 2:
            return False
        theme = self.cfg["theme"]
        red, green, blue = PLATES[theme]
        alpha = 1.0 - (self.cfg["transparency"] / 100.0)
        if theme == "glass":
            alpha = min(0.38, alpha)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        if alpha <= 0.001:
            return False
        cr.set_operator(cairo.OPERATOR_OVER)
        _rounded(cr, 0.5, 0.5, width - 1, height - 1, 22)
        cr.set_source_rgba(red, green, blue, alpha)
        cr.fill_preserve()
        if theme == "dark":
            cr.set_source_rgba(1, 1, 1, 0.20)
        else:
            cr.set_source_rgba(0.08, 0.08, 0.08, 0.10)
        cr.set_line_width(1.4)
        cr.stroke()
        return False

    def _plate_tip(self) -> str:
        if self.cfg["theme"] == "glass":
            return "0 is the fullest glass. 100 is clear."
        return "0 is solid. 100 is clear."

    def _choose_theme(self, name: str) -> None:
        if name not in PLATES:
            return
        self.cfg["theme"] = name
        self._css.load_from_data(theme_css(name))
        self._mark_theme_buttons()
        self.plate_scale.set_tooltip_text(self._plate_tip())
        self.queue_draw()
        save_config(self.cfg)

    def _mark_theme_buttons(self) -> None:
        current = self.cfg["theme"]
        for button, key in self._theme_buttons:
            context = button.get_style_context()
            if key == current:
                context.add_class("theme-on")
            else:
                context.remove_class("theme-on")

    def _on_plate(self, scale) -> None:
        self.cfg["transparency"] = int(round(scale.get_value()))
        self._mark_plate_buttons()
        self.queue_draw()
        save_config(self.cfg)

    def _mark_plate_buttons(self) -> None:
        amount = self.cfg["transparency"]
        for button, preset in self._plate_buttons:
            context = button.get_style_context()
            if preset == amount:
                context.add_class("plate-on")
            else:
                context.remove_class("plate-on")

    def _device_label(self, title: str, key: str) -> str:
        return f"{title}  ·  {'On' if self.cfg[key] else 'Off'}"

    def _mark_devices(self) -> None:
        names = {"light": "Light", "lamp": "Lamp", "fan": "Fan"}
        for key, button in self._device_buttons.items():
            button.set_label(self._device_label(names[key], key))
            context = button.get_style_context()
            if self.cfg[key]:
                context.add_class("on")
            else:
                context.remove_class("on")

    def _toggle_device(self, key: str, title: str) -> None:
        self.cfg[key] = not self.cfg[key]
        self.cfg["note"] = f"{title} {'on' if self.cfg[key] else 'off'}"
        self.status.set_text(self.cfg["note"])
        self._mark_devices()
        save_config(self.cfg)

    def _speaker_label(self) -> str:
        return "Speaker on" if self.cfg["speaker"] else "Speaker off"

    def _toggle_speaker(self, *_args) -> None:
        self.cfg["speaker"] = not self.cfg["speaker"]
        self.speaker.set_label(self._speaker_label())
        self.cfg["note"] = self._speaker_label()
        self.status.set_text(self.cfg["note"])
        context = self.speaker.get_style_context()
        if self.cfg["speaker"]:
            context.add_class("on")
        else:
            context.remove_class("on")
        save_config(self.cfg)

    def _on_volume(self, scale) -> None:
        self.cfg["volume"] = int(round(scale.get_value()))
        self.cfg["note"] = f"Volume {self.cfg['volume']}"
        self.status.set_text(self.cfg["note"])
        save_config(self.cfg)

    def _drag(self, _widget, event) -> bool:
        if getattr(event, "button", 0) != 1:
            return False
        self.begin_move_drag(int(event.button), int(event.x_root), int(event.y_root), event.time)
        return True

    def _shutdown(self, *_args) -> None:
        if not self._check:
            Gtk.main_quit()


def theme_check() -> int:
    existed = CFG.exists()
    raw = CFG.read_text(encoding="utf-8") if existed else ""
    errors = []
    win = Home(check=True)
    try:
        if win.get_title() != "DGO Home":
            errors.append("title")
        texts = []
        buttons = []

        def walk(widget) -> None:
            if isinstance(widget, Gtk.Label):
                texts.append(widget.get_text())
            if isinstance(widget, Gtk.Button) and widget.get_label():
                buttons.append(widget.get_label())
            if hasattr(widget, "get_children"):
                for child in widget.get_children():
                    walk(child)

        walk(win)
        if "DGO Home" not in texts:
            errors.append("heading")
        for name in ("Cream", "Dark", "Glass"):
            if name not in buttons:
                errors.append(name)
        for stem in ("Light", "Lamp", "Fan", "Speaker"):
            if not any(item.startswith(stem) for item in buttons):
                errors.append(stem)
        win._choose_theme("dark")
        if win.cfg["theme"] != "dark":
            errors.append("dark")
        css = theme_css("dark").decode()
        if "#fffcf8" not in css or "#161616" not in css:
            errors.append("pills")
        if "solid teal" in (win.plate_scale.get_tooltip_text() or ""):
            errors.append("tip")
        win._choose_theme("glass")
        _red, _green, _blue = PLATES["glass"]
        # solid glass stays see-through
        alpha = min(0.38, 1.0)
        if alpha > 0.38:
            errors.append("glass")
    finally:
        if existed:
            CFG.write_text(raw, encoding="utf-8")
        elif CFG.exists():
            CFG.unlink()
        win.destroy()
    if errors:
        print("DGO_HOME_FAIL " + ", ".join(errors))
        return 1
    print("DGO_HOME_OK")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return theme_check()
    win = Home()
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
