#!/usr/bin/env bash
# setup.sh — TTS Bash Setup (Linux)
# Adds speak / tts-monitor / tts-stop functions to ~/.bashrc
#
# Run once:  bash setup.sh
# Then:      source ~/.bashrc

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Check dependencies ────────────────────────────────────────────────────────
MISSING=()
command -v spd-say &>/dev/null    || MISSING+=("speech-dispatcher")
command -v xclip   &>/dev/null    || command -v xsel &>/dev/null || \
command -v wl-paste &>/dev/null   || MISSING+=("xclip (or xsel / wl-clipboard)")

if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "Missing dependencies: ${MISSING[*]}"
    echo "Install with: sudo apt install ${MISSING[*]}"
    echo ""
fi

# ── Check if already installed ───────────────────────────────────────────────
if grep -q "# ── TTS Functions (Linux)" ~/.bashrc 2>/dev/null; then
    echo "TTS functions already in ~/.bashrc — skipping."
    echo "To reinstall, remove the TTS Functions block from ~/.bashrc first."
    exit 0
fi

# ── Append functions to .bashrc ──────────────────────────────────────────────
cat >> ~/.bashrc <<BASHFUNCTIONS

# ── TTS Functions (Linux) ─────────────────────────────────────────────────────
_TTS_DIR="$SCRIPT_DIR"

# speak: read text aloud via Linux TTS
# Usage:
#   speak "some text"
#   echo "some text" | speak
#   cat file.txt | speak
speak() {
    if [ "\$#" -gt 0 ]; then
        echo "\$@" | bash "\$_TTS_DIR/speak-md.sh"
    else
        cat | bash "\$_TTS_DIR/speak-md.sh"
    fi
}

# tts-monitor: start clipboard monitor in background
tts-monitor() {
    bash "\$_TTS_DIR/monitor.sh" &
    _TTS_MONITOR_PID=\$!
    echo "TTS monitor started (PID: \$_TTS_MONITOR_PID)"
    echo "  Copy any text to hear it read aloud."
    echo "  Run tts-stop to stop."
}

# tts-stop: stop the clipboard monitor
tts-stop() {
    if [ -n "\$_TTS_MONITOR_PID" ]; then
        kill "\$_TTS_MONITOR_PID" 2>/dev/null && echo "TTS monitor stopped."
        _TTS_MONITOR_PID=""
    else
        echo "No TTS monitor running (or PID unknown)."
    fi
}
# ─────────────────────────────────────────────────────────────────────────────
BASHFUNCTIONS

echo ""
echo "TTS functions added to ~/.bashrc"
echo ""
echo "Run this to activate now:"
echo "   source ~/.bashrc"
echo ""
echo "Available commands:"
echo "   speak 'some text'      — speak text directly"
echo "   echo 'text' | speak    — pipe any output to speaker"
echo "   cat file.txt | speak   — read a file aloud"
echo "   tts-monitor            — start clipboard monitor (background)"
echo "   tts-stop               — stop clipboard monitor"
