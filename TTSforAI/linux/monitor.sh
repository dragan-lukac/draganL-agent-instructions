#!/usr/bin/env bash
# monitor.sh — Clipboard TTS Monitor (Linux)
# Watches the clipboard and automatically reads new text aloud.
# Requires: xclip, xdotool, piper (via speak-md.sh)
#
# Keyboard shortcuts (register in Ubuntu Settings > Keyboard > Custom Shortcuts):
#
#   Stop speech now:
#     Command: bash /home/dragan/HUB/Projekti/draganL-agent-instructions/TTSforAI/linux/stop.sh
#     Suggested key: Ctrl+Alt+S
#
#   Read selected/highlighted text:
#     Command: bash /home/dragan/HUB/Projekti/draganL-agent-instructions/TTSforAI/linux/read-selection.sh
#     Suggested key: Ctrl+Alt+R
#
# Usage:
#   bash monitor.sh          # runs in foreground, Ctrl+C to exit
#   bash monitor.sh &        # run in background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEAK="$SCRIPT_DIR/speak-md.sh"
PID_FILE="/tmp/tts-monitor-speak.pid"

# ── Detect clipboard tool ─────────────────────────────────────────────────────
get_clipboard() {
    if [ -n "$WAYLAND_DISPLAY" ] && command -v wl-paste &>/dev/null; then
        wl-paste --no-newline 2>/dev/null
    elif command -v xclip &>/dev/null; then
        xclip -selection clipboard -o 2>/dev/null
    elif command -v xsel &>/dev/null; then
        xsel --clipboard --output 2>/dev/null
    else
        echo ""
    fi
}

# ── Check dependencies ────────────────────────────────────────────────────────
if [ -z "$WAYLAND_DISPLAY" ] && ! command -v xclip &>/dev/null && ! command -v xsel &>/dev/null; then
    echo "Error: no clipboard tool found. Install: sudo apt install xclip" >&2
    exit 1
fi

echo "═══════════════════════════════════════"
echo "  Clipboard TTS Monitor — Running"
echo "  Copy any text to hear it read aloud"
echo ""
echo "  Shortcuts (set in Ubuntu keyboard settings):"
echo "    Ctrl+Alt+S — Stop speech"
echo "    Ctrl+Alt+R — Read selected text"
echo ""
echo "  Press Ctrl+C to exit"
echo "═══════════════════════════════════════"
echo ""

LAST_TEXT=$(get_clipboard)
SPEAK_PID=""

stop_speech() {
    if [ -n "$SPEAK_PID" ] && kill -0 "$SPEAK_PID" 2>/dev/null; then
        # Kill the whole process group to stop piper + aplay
        kill -- -"$SPEAK_PID" 2>/dev/null
        kill "$SPEAK_PID" 2>/dev/null
        SPEAK_PID=""
    fi
    # Also kill any stray piper/aplay processes
    pkill -f "piper" 2>/dev/null
    pkill -f "aplay" 2>/dev/null
    rm -f "$PID_FILE"
}

cleanup() {
    stop_speech
    echo ""
    echo "TTS monitor stopped."
    exit 0
}
trap cleanup INT TERM

POLL_MS=500

while true; do
    CURRENT=$(get_clipboard)

    if [ -n "$CURRENT" ] && [ "$CURRENT" != "$LAST_TEXT" ]; then
        LAST_TEXT="$CURRENT"
        PREVIEW="${CURRENT:0:70}"
        [ "${#CURRENT}" -gt 70 ] && PREVIEW="${PREVIEW}..."
        echo "[$(date '+%H:%M:%S')] $PREVIEW"

        stop_speech
        setsid bash "$SPEAK" "$CURRENT" &
        SPEAK_PID=$!
        echo "$SPEAK_PID" > "$PID_FILE"
    fi

    sleep "$(echo "scale=3; $POLL_MS/1000" | bc)"
done
