#!/usr/bin/env bash
set -eo pipefail

BLABBER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/blabber"

# Parse flags
NO_PROMPT=false
for arg in "$@"; do
    [[ "$arg" == "--no-prompt" ]] && NO_PROMPT=true
done

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

# ─────────────────────────────────────────────────────────────────────────────
# Helper: returns 0 if the apt/deb package is fully installed, 1 otherwise.
# Uses dpkg -s and checks for the exact "install ok installed" status line so
# that packages in a half-installed or config-files-only state are not treated
# as present.
# ─────────────────────────────────────────────────────────────────────────────
apt_installed() {
    dpkg -s "$1" 2>/dev/null | grep -q "^Status: install ok installed"
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: install an apt package only when it is not already present.
# Prints "✓ already present" or "↓ installing" with the package name.
# Exits the whole installer with a clear message if the install fails.
# Note: apt-get update must have been run before calling this.
# ─────────────────────────────────────────────────────────────────────────────
ensure_apt() {
    local pkg="$1"
    if apt_installed "$pkg"; then
        echo -e "    ${GREEN}✓${NC} already present: ${pkg}"
    else
        echo -e "    ${YELLOW}↓${NC} installing: ${pkg} ..."
        if ! sudo apt-get install -y --fix-missing "$pkg" -qq >/dev/null 2>&1; then
            echo -e "    ${RED}✗ failed to install ${pkg}${NC}" >&2
            echo -e "    ${RED}  Please install it manually and re-run the installer.${NC}" >&2
            exit 1
        fi
        echo -e "    ${GREEN}✓${NC} installed: ${pkg}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: returns 0 if pip already knows about the package, 1 otherwise.
# $1 = pip distribution name (e.g. "faster-whisper", "webrtcvad-wheels").
# PYTHON must be set before calling this.
# ─────────────────────────────────────────────────────────────────────────────
pip_installed() {
    "$PYTHON" -m pip show "$1" &>/dev/null
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: install a Python package via pip only when it is not already present.
# $1 = pip install name  (e.g. "faster-whisper")
# $2 = pip show name     (optional; defaults to $1; use when they differ, e.g.
#                          install "webrtcvad-wheels" but show "webrtcvad-wheels")
# PYTHON must be set before calling this.
# ─────────────────────────────────────────────────────────────────────────────
ensure_pip() {
    local pkg="$1"
    local show_name="${2:-$1}"
    if pip_installed "$show_name"; then
        echo -e "    ${GREEN}✓${NC} already present: ${pkg}"
    else
        echo -e "    ${YELLOW}↓${NC} installing: ${pkg} ..."
        if ! "$PYTHON" -m pip install --break-system-packages --quiet "$pkg"; then
            echo -e "    ${RED}✗ failed to install ${pkg}${NC}" >&2
            echo -e "    ${RED}  Please install it manually and re-run the installer.${NC}" >&2
            exit 1
        fi
        echo -e "    ${GREEN}✓${NC} installed: ${pkg}"
    fi
}

# ── Step 1: System packages ───────────────────────────────────────────────────
echo -e "${BOLD}[1/4] Checking system dependencies...${NC}"

REQUIRED_APT=(
    python3
    python3-pip
    python3-dev
    portaudio19-dev
    libgirepository1.0-dev
    gir1.2-gtk-3.0
    gir1.2-ayatanaappindicator3-0.1
    python3-pyatspi
    xdotool
    xclip
)

# Scan for missing packages first so we only call apt-get update when needed.
MISSING_APT=()
for pkg in "${REQUIRED_APT[@]}"; do
    if ! apt_installed "$pkg"; then
        MISSING_APT+=("$pkg")
    fi
done

if [[ ${#MISSING_APT[@]} -gt 0 ]]; then
    echo -e "  ${YELLOW}${#MISSING_APT[@]} package(s) to install — fetching package lists...${NC}"
    sudo apt-get update -qq
else
    echo -e "  All required apt packages already present — skipping apt-get update."
fi

for pkg in "${REQUIRED_APT[@]}"; do
    ensure_apt "$pkg"
done

# ── Wayland text-injection tools (optional but recommended on Wayland) ────────
echo ""
echo -e "  ${BOLD}Wayland injection tools (optional):${NC}"
WAYLAND_INSTALLED=false

# Prefer ydotool (best Wayland support)
if apt_installed ydotool; then
    echo -e "    ${GREEN}✓${NC} already present: ydotool"
    WAYLAND_INSTALLED=true
elif apt-cache show ydotool &>/dev/null; then
    echo -e "    ${YELLOW}↓${NC} installing: ydotool ..."
    if sudo apt-get install -y ydotool -qq >/dev/null 2>&1; then
        echo -e "    ${GREEN}✓${NC} installed: ydotool"
        WAYLAND_INSTALLED=true
    else
        echo -e "    ${YELLOW}⚠${NC}  ydotool install failed — will try wtype instead"
    fi
else
    echo -e "    ${YELLOW}⚠${NC}  ydotool not in apt repos — will try wtype instead"
fi

# Fall back to wtype + wl-clipboard if ydotool was not obtained
if [[ "$WAYLAND_INSTALLED" == "false" ]]; then
    for pkg in wtype wl-clipboard; do
        if apt_installed "$pkg"; then
            echo -e "    ${GREEN}✓${NC} already present: ${pkg}"
        elif apt-cache show "$pkg" &>/dev/null; then
            echo -e "    ${YELLOW}↓${NC} installing: ${pkg} ..."
            if sudo apt-get install -y "$pkg" -qq >/dev/null 2>&1; then
                echo -e "    ${GREEN}✓${NC} installed: ${pkg}"
            else
                echo -e "    ${YELLOW}⚠${NC}  could not install ${pkg} — skipping"
            fi
        else
            echo -e "    ${YELLOW}⚠${NC}  ${pkg} not in apt repos — skipping"
        fi
    done
fi

# ── Detect Python interpreter ─────────────────────────────────────────────────
if command -v python3.12 &>/dev/null; then
    PYTHON=python3.12
else
    PYTHON=python3
fi

echo ""
echo -e "${GREEN}  ✓ System packages ready (using ${PYTHON})${NC}"

# ── Step 2: Python packages ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] Checking Python dependencies...${NC}"

# faster-whisper: distribution name matches pip show name
ensure_pip "faster-whisper"
# sounddevice: distribution name matches pip show name
ensure_pip "sounddevice"
# webrtcvad-wheels: the distribution is "webrtcvad-wheels"; pip show uses the same name
ensure_pip "webrtcvad-wheels"
# pynput: distribution name matches pip show name
ensure_pip "pynput"
# numpy: required by stt/engine.py; often already present but install if missing
ensure_pip "numpy"

echo -e "${GREEN}  ✓ Python packages ready${NC}"

# ── Step 3: Model selection ───────────────────────────────────────────────────
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

# ── Hugging Face token (optional — speeds up downloads, avoids rate limits) ───
if [[ -z "${HF_TOKEN:-}" && -z "${HUGGINGFACE_HUB_TOKEN:-}" ]]; then
    if [[ "$NO_PROMPT" == "true" || "${CI:-}" == "1" || ! -t 0 ]]; then
        echo -e "  ${YELLOW}⚠${NC}  No Hugging Face token set — downloading unauthenticated (may be slower)"
    else
        echo ""
        echo -e "  ${BOLD}Hugging Face token (optional)${NC}"
        echo -e "  A token speeds up downloads and avoids rate limits."
        echo -e "  Create one at ${CYAN}https://huggingface.co/settings/tokens${NC} (read-only scope is enough)."
        echo -e "  Press Enter to skip and download without a token."
        echo ""
        read -rsp "  Paste token (hidden): " HF_INPUT
        echo ""
        if [[ -n "$HF_INPUT" ]]; then
            export HF_TOKEN="$HF_INPUT"
            export HUGGINGFACE_HUB_TOKEN="$HF_INPUT"
            echo -e "  ${GREEN}✓${NC} Token set — authenticated download"
        else
            echo -e "  ${YELLOW}⚠${NC}  No token entered — downloading unauthenticated"
        fi
    fi
else
    echo -e "  ${GREEN}✓${NC} Hugging Face token already set in environment"
fi

# Pre-download the selected model
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

# ── Step 4: Desktop entry + launcher ─────────────────────────────────────────
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
