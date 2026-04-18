#!/usr/bin/env bash
# setup.sh — TTS Bash Setup
# Adds speak / tts-monitor / tts-stop functions to ~/.bashrc
#
# Run once:  bash setup.sh
# Then:      source ~/.bashrc

TTS_DIR="C:/Users/Dragan.Lukac/Documents/01Projects/dragan-ai-tools/scripts/tts"

# ── Check if already installed ───────────────────────────────────────────────
if grep -q "# ── TTS Functions" ~/.bashrc 2>/dev/null; then
    echo "⚠️  TTS functions already in ~/.bashrc — skipping."
    echo "   To reinstall, remove the TTS Functions block from ~/.bashrc first."
    exit 0
fi

# ── Append functions to .bashrc ──────────────────────────────────────────────
cat >> ~/.bashrc <<BASHFUNCTIONS

# ── TTS Functions ─────────────────────────────────────────────────────────────
_TTS_DIR="C:/Users/Dragan.Lukac/Documents/01Projects/dragan-ai-tools/scripts/tts"

# speak: read text aloud via Windows TTS
# Usage:
#   speak "some text"
#   echo "some text" | speak
#   cat file.txt | speak
speak() {
    local script="\$_TTS_DIR/speak.ps1"
    if [ "\$#" -gt 0 ]; then
        echo "\$@" | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\$script"
    else
        cat | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\$script"
    fi
}

# tts-monitor: start clipboard monitor in background
# Automatically reads aloud whatever you copy to clipboard
tts-monitor() {
    local script="\$_TTS_DIR/monitor.ps1"
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "\$script" &
    _TTS_MONITOR_PID=\$!
    echo "🎤 TTS monitor started (PID: \$_TTS_MONITOR_PID)"
    echo "   Copy any text to hear it read aloud."
    echo "   Run tts-stop to stop."
}

# tts-stop: stop the clipboard monitor
tts-stop() {
    if [ -n "\$_TTS_MONITOR_PID" ]; then
        kill "\$_TTS_MONITOR_PID" 2>/dev/null && echo "🛑 TTS monitor stopped."
        _TTS_MONITOR_PID=""
    else
        echo "No TTS monitor running (or PID unknown)."
    fi
}
# ─────────────────────────────────────────────────────────────────────────────
BASHFUNCTIONS

echo ""
echo "✅ TTS functions added to ~/.bashrc"
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
