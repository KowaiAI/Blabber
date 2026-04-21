import os
import subprocess
import shutil


def _detect_display_server() -> str:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        return "wayland"
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"


def _inject_x11(text: str) -> None:
    subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
        check=False,
    )


def _inject_wayland(text: str) -> None:
    if shutil.which("ydotool"):
        subprocess.run(["ydotool", "type", "--", text], check=False)
    elif shutil.which("wtype"):
        subprocess.run(["wtype", "--", text], check=False)
    else:
        _inject_via_clipboard(text)


def _inject_via_clipboard(text: str) -> None:
    """Clipboard fallback: copy text then paste with Ctrl+V.

    Uses Wayland-native tools (wl-copy / wtype) when available, then falls
    back to the X11 equivalents (xclip / xdotool) for XWayland or X11 sessions.
    """
    try:
        if shutil.which("wl-copy") and shutil.which("wtype"):
            # Wayland-native path
            proc = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
            )
            proc.communicate(input=text.encode())
            subprocess.run(["wtype", "-M", "ctrl", "v", "-m", "ctrl"], check=False)
        else:
            # X11 / XWayland path
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            proc.communicate(input=text.encode())
            subprocess.run(["xdotool", "key", "ctrl+v"], check=False)
    except Exception:
        pass


def type_text(text: str, display_server: str = "auto") -> None:
    if not text:
        return
    if display_server == "auto":
        display_server = _detect_display_server()

    if display_server == "wayland":
        _inject_wayland(text)
    else:
        _inject_x11(text)
