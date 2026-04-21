#!/usr/bin/env bash
set -eo pipefail

BLABBER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/blabber"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║        Blabber Installer         ║${NC}"
echo -e "${BOLD}${CYAN}║   Speech-to-Text for Linux       ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════╝${NC}"
echo ""

# ── System packages ──────────────────────────────────────────────
echo -e "${BOLD}[1/4] Installing system dependencies...${NC}"
sudo apt-get update -qq
sudo apt-get install -y --fix-missing \
    python3 \
    python3-pip \
    xdotool \
    portaudio19-dev \
    gir1.2-ayatanaappindicator3-0.1 \
    gir1.2-gtk-3.0 \
    python3-pyatspi \
    libgirepository1.0-dev \
    python3-dev \
    xclip 2>&1 | grep -E "(Setting up|already installed)" | sed 's/^/  /' || true

# ydotool is optional (Wayland injection falls back to wtype or clipboard if absent)
if apt-cache show ydotool &>/dev/null; then
    sudo apt-get install -y ydotool 2>&1 | grep -E "(Setting up|already installed)" | sed 's/^/  /' || true
fi

# Prefer python3.12 if available on this system
if command -v python3.12 &>/dev/null; then
    PYTHON=python3.12
else
    PYTHON=python3
fi

echo -e "${GREEN}  ✓ System packages ready (using ${PYTHON})${NC}"

# ── Python packages ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] Installing Python packages...${NC}"
"$PYTHON" -m pip install --break-system-packages --quiet \
    faster-whisper \
    sounddevice \
    webrtcvad-wheels \
    pynput
echo -e "${GREEN}  ✓ Python packages ready${NC}"

# ── Model selection ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/4] Choose your transcription model:${NC}"
echo ""
echo -e "  ${CYAN}1)${NC} Small  (~466 MB)  — Fast, good accuracy         ${GREEN}[recommended]${NC}"
echo -e "  ${CYAN}2)${NC} Medium (~1.5 GB)  — Balanced speed & accuracy"
echo -e "  ${CYAN}3)${NC} Large  (~3 GB)    — Best accuracy, slower"
echo ""
read -rp "  Enter choice [1-3] (default: 1): " model_choice

case "$model_choice" in
    2) MODEL_SIZE="medium" ;;
    3) MODEL_SIZE="large"  ;;
    *) MODEL_SIZE="small"  ;;
esac

echo -e "${GREEN}  ✓ Selected: ${BOLD}${MODEL_SIZE}${NC}"

# Save config
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/config.json" <<EOF
{
  "model_size": "${MODEL_SIZE}",
  "auto_start_on_click": false,
  "auto_pause_seconds": 30,
  "idle_timeout_seconds": 60,
  "hotkey": "<shift>+b",
  "widget_x": 10,
  "widget_y": 10,
  "display_server": "auto"
}
EOF

# ── Pre-download model ────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Downloading ${MODEL_SIZE} model (this may take a few minutes)...${NC}"

# Map user-chosen size to the actual faster-whisper model name (mirrors stt/engine.py)
case "$MODEL_SIZE" in
    medium) WHISPER_MODEL="medium"   ;;
    large)  WHISPER_MODEL="large-v3" ;;
    *)      WHISPER_MODEL="small"    ;;
esac

"$PYTHON" - <<PYEOF
from faster_whisper import WhisperModel
print("  Downloading ${WHISPER_MODEL}...")
WhisperModel("${WHISPER_MODEL}", device="cpu", compute_type="int8")
print("  Model ready.")
PYEOF
echo -e "${GREEN}  ✓ Model downloaded and cached${NC}"

# ── Desktop entry + launcher ──────────────────────────────────────
echo ""
echo -e "${BOLD}[4/4] Creating launcher...${NC}"

LAUNCHER="$HOME/.local/bin/blabber"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec ${PYTHON} "${BLABBER_DIR}/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

DESKTOP="$HOME/.local/share/applications/blabber.desktop"
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Name=Blabber
Comment=Speech-to-Text Dictation
Exec=${LAUNCHER}
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;Accessibility;
StartupNotify=false
EOF

echo -e "${GREEN}  ✓ Launcher created at ~/.local/bin/blabber${NC}"
echo -e "${GREEN}  ✓ Desktop entry created${NC}"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║     Blabber is ready to use!     ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════╝${NC}"
echo ""
echo -e "  Run:  ${CYAN}blabber${NC}"
echo -e "  Or:   ${CYAN}${PYTHON} ${BLABBER_DIR}/main.py${NC}"
echo ""
echo -e "  ${YELLOW}Hotkey:${NC}  Shift+B to show/hide the widget"
echo -e "  ${YELLOW}Start:${NC}   Press ▶ on the widget to begin listening"
echo -e "  ${YELLOW}Pause:${NC}   Press ⏸ — auto-pauses after 30 s silence"
echo -e "  ${YELLOW}Idle:${NC}    Widget goes idle after 60 s paused; press ▶ to resume"
echo ""
