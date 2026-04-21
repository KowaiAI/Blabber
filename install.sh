#!/usr/bin/env bash
set -e

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
    python3.12 \
    xdotool \
    ydotool \
    portaudio19-dev \
    gir1.2-ayatanaappindicator3-0.1 \
    gir1.2-gtk-3.0 \
    python3-pyatspi \
    libgirepository1.0-dev \
    python3-dev \
    xclip 2>&1 | grep -E "(Setting up|already)" | sed 's/^/  /'
echo -e "${GREEN}  ✓ System packages ready${NC}"

# ── Python packages ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] Installing Python packages...${NC}"
python3.12 -m pip install --break-system-packages --quiet \
    faster-whisper \
    sounddevice \
    pyaudio \
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
  "idle_timeout_seconds": 360,
  "off_timeout_seconds": 1200,
  "hotkey": "<shift>+b",
  "widget_x": 10,
  "widget_y": 10,
  "display_server": "auto"
}
EOF

# ── Pre-download model ────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Downloading ${MODEL_SIZE} model (this may take a few minutes)...${NC}"
python3.12 - <<PYEOF
from faster_whisper import WhisperModel
sizes = {"small": "small", "medium": "medium", "large": "large-v3"}
print(f"  Downloading {sizes['${MODEL_SIZE}']}...")
m = WhisperModel(sizes["${MODEL_SIZE}"], device="cpu", compute_type="int8")
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
exec python3.12 "${BLABBER_DIR}/main.py" "\$@"
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
echo -e "  Or:   ${CYAN}python3.12 ${BLABBER_DIR}/main.py${NC}"
echo ""
echo -e "  ${YELLOW}Hotkey:${NC} Shift+B to show/hide the widget"
echo -e "  ${YELLOW}Start:${NC}  Click a text field, then press +"
echo ""
