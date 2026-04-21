# Blabber

**Offline, private speech-to-text dictation for Linux.**

Blabber listens to your microphone and types what you say directly into whatever text field is focused — browser, terminal, text editor, anything. No cloud, no account, no data ever leaves your machine.

---

## Features

- 🎙️ Real-time speech-to-text using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper models, fully offline)
- ⌨️ Types transcribed text into any focused input field (X11 and Wayland)
- 🪟 Compact floating GTK3 widget — draggable, always-on-top, minimises to tray
- 🔑 Global hotkey `Shift+B` to show/hide the widget from anywhere
- 💤 Auto-pause after silence, auto-idle after paused — frees memory when not in use
- ⚙️ Settings dialog: choose model size, configure timeouts, toggle auto-start
- 🔒 Zero network activity after install — completely private

---

## Requirements

### System packages

Run this once before anything else:

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-dev \
    portaudio19-dev \
    libgirepository1.0-dev \
    gir1.2-gtk-3.0 \
    gir1.2-ayatanaappindicator3-0.1 \
    python3-pyatspi \
    xdotool xclip
```

**Wayland users** — also install one of the following for best text injection:

```bash
sudo apt-get install -y ydotool      # recommended for Wayland
# or
sudo apt-get install -y wtype wl-clipboard
```

> `ydotool` may not be in the standard repos on all distros. If the install fails, `wtype` + `wl-clipboard` are a good alternative. If neither is available, Blabber falls back to clipboard paste automatically.

### Python packages

```bash
pip install -r requirements.txt
```

On Ubuntu 23.04+ or any system with an externally-managed Python environment:

```bash
pip install --break-system-packages -r requirements.txt
```

---

## Installation

The interactive installer handles everything in one step (system packages, Python packages, model download, launcher, desktop entry):

```bash
git clone https://github.com/KowaiAI/Blabber.git
cd Blabber
bash install.sh
```

The installer will ask you to choose a Whisper model:

| Choice | Model  | Size     | Speed       | Accuracy  |
|--------|--------|----------|-------------|-----------|
| 1      | Small  | ~466 MB  | Fast        | Good ✅ recommended |
| 2      | Medium | ~1.5 GB  | Moderate    | Better    |
| 3      | Large  | ~3 GB    | Slow        | Best      |

The model is downloaded once and cached. After install, run:

```bash
blabber
```

Or directly:

```bash
python3 main.py
```

---

## Usage

### Controls

| Action | What it does |
|--------|--------------|
| `Shift+B` | Show / hide the Blabber widget |
| **▶** (Start) | Load model (if needed) and begin listening |
| **⏸** (Pause) | Stop listening, keep model loaded |
| **⏹** (Stop)  | Stop listening and unload model |
| **—** (Minimise) | Hide widget to tray |
| **⚙** (Settings) | Open settings dialog |
| **✕** (Quit) | Exit Blabber |

### States

| Icon | State      | Meaning |
|------|------------|---------|
| ⚫   | Off        | Model not loaded |
| ⏳   | Loading    | Downloading / loading the Whisper model |
| 🟢   | Ready      | Model loaded, about to start capture |
| 🔴   | Listening  | Actively transcribing speech |
| 🟡   | Paused     | Capture stopped, model still in memory |
| 🟠   | Idle       | Paused too long — model unloaded to free memory |

### Auto-power-saving

- **Auto-pause** — if no speech is detected for N seconds (default: 30 s), Blabber pauses automatically
- **Auto-idle** — if paused for N seconds (default: 60 s), Blabber goes idle and unloads the model to free RAM
- Press **▶** at any time to resume from any state

---

## Settings

Open the ⚙ settings dialog to configure:

| Setting | Description |
|---------|-------------|
| Transcription model | Switch between Small / Medium / Large |
| Auto-start on text field click | Start listening when a text field is focused (via AT-SPI) |
| Auto-pause after silence | Seconds of silence before auto-pause (5–300 s) |
| Idle after paused | Seconds paused before going idle and freeing memory (10–600 s) |

Config is saved to `~/.config/blabber/config.json`.

---

## How It Works

1. **Audio capture** — `sounddevice` streams mic audio at 16 kHz in 30 ms frames
2. **Voice activity detection** — `webrtcvad` detects speech frames; silence after speech triggers a transcription job
3. **Transcription** — `faster-whisper` runs the Whisper model on CPU (int8 quantised) in a background thread
4. **Text injection** — transcribed text is typed into the focused window via `xdotool` (X11) or `ydotool`/`wtype` (Wayland); clipboard fallback if neither is available
5. **Focus detection** — AT-SPI accessibility events detect when text fields are focused (used for auto-start feature)

---

## Project Structure

```
Blabber/
├── main.py                        # Entry point
├── install.sh                     # Interactive installer
├── requirements.txt               # Python dependencies
└── blabber/
    ├── config.py                  # Persistent settings (~/.config/blabber/)
    ├── app.py                     # Main controller — wires everything together
    ├── audio/
    │   └── capture.py             # Mic capture + VAD (webrtcvad)
    ├── stt/
    │   └── engine.py              # faster-whisper: load / unload / transcribe
    ├── input/
    │   ├── injector.py            # xdotool (X11) / ydotool / wtype (Wayland)
    │   ├── focus_monitor.py       # AT-SPI focus events
    │   └── hotkey.py              # Shift+B global hotkey (pynput)
    └── ui/
        ├── widget.py              # Floating GTK3 control panel
        ├── tray.py                # AppIndicator3 tray icon
        └── settings_dialog.py    # Settings dialog
```

---

## License

MIT — see [LICENSE](LICENSE)













