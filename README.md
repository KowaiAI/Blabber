## Blabber Mouth 
# An Offline, Private Speech-to-Text application for Linux Ubuntu/Mint. Made becasuse speech to text apps for Linux are annoyingly sketchy. 
#

written with Python 
Floating GTK3 widget, top-left default, draggable, collapsible to tray
Shift+B to show/hide
faster-whisper (small/medium/large), fully offline
Text injected directly into whatever text field is focused
Tab follows focus, stays listening 
Auto-idle → auto-off to save memory/battery
Auto-start on click (settings toggle)
Zero data collection, zero network after install
MIT licensed, open source

__________________________________________________________________________________

Blabber/
├── main.py                        # entry point (python 3.12)
├── install.sh                     # interactive installer
├── requirements.txt
└── blabber/
    ├── config.py                  # persistent settings (~/.config/blabber/)
    ├── app.py                     # main controller, wires everything together
    ├── audio/capture.py           # mic capture + VAD (webrtcvad)
    ├── stt/engine.py              # faster-whisper, load/unload, transcribe
    ├── input/injector.py          # xdotool (X11) / ydotool (Wayland) text injection
    ├── input/focus_monitor.py     # AT-SPI + pynput — detects focused text fields
    ├── input/hotkey.py            # Shift+B global hotkey
    └── ui/
        ├── widget.py              # floating GTK3 control panel, draggable
        ├── tray.py                # AppIndicator3 tray icon (🔴🟡🟠⚫)
        └── settings_dialog.py    # model size, auto-start, timeout sliders

____________________________________________________________________________

To install and run on a real desktop:

bash install.sh   # picks model, downloads it, creates launcher
blabber           # run it

______________________________________________________________________________


# Listening States

State	Icon
Listening	🔴	+ pressed / auto-start
Paused	🟡	- pressed
Idle	🟠	Paused 5-10 min (configurable)
Off	⚫	Idle 20 min → unloads model, frees memory

Off state still wakes back up when user presses + again — just reloads the model.


# Input	Actions 

Shift + B	Show/hide widget
+	Start / resume listening
-	Pause 🟡

Hit Tab and app will stay listening and type text into the next field once you speak agian

Settings is the gear icon 


## How It Works

1. Blabber launches → runs in background → tray icon ⚫
2. Shift+B → widget appears, starts watching for clicks
3. User clicks any text box → Blabber registers it as the target 🟡
4. User presses + → starts listening 🔴
5. Speech → words typed live into that registered input
6. - → pause 🟡 | ++ → stop ⚫


What Blabber monitors passively (no audio):

    Mouse clicks → to detect when user selects a text input
    Text field focus → via AT-SPI (Linux accessibility API) to confirm it's actually a text input, not just any click

Architecture update:

Blabber/
├── main.py
├── ui/
│   ├── widget.py        # floating control panel (no text area)
│   └── tray.py          # AppIndicator3 — ⚫🟡🔴 status
├── stt/
│   └── whisper_engine.py / vosk_engine.py
├── audio/
│   └── capture.py
├── input/
│   ├── hotkey.py        # Shift+B via pynput
│   ├── focus_monitor.py # AT-SPI + pynput mouse — detects target text field
│   └── injector.py      # xdotool type into registered target
└── config.py












