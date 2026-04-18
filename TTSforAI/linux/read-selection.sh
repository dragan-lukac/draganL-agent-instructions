#!/usr/bin/env bash
# read-selection.sh — Read currently highlighted/selected text aloud
# Bind this to a keyboard shortcut (e.g. Ctrl+Alt+R) in Ubuntu Settings
#
# Requires: xdotool, xclip
# Install: sudo apt install xdotool xclip

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEAK="$SCRIPT_DIR/speak-md.sh"
PID_FILE="/tmp/tts-monitor-speak.pid"

# Stop any currently playing speech first
if [ -f "$PID_FILE" ]; then
    SPEAK_PID=$(cat "$PID_FILE")
    if [ -n "$SPEAK_PID" ] && kill -0 "$SPEAK_PID" 2>/dev/null; then
        kill -- -"$SPEAK_PID" 2>/dev/null
        kill "$SPEAK_PID" 2>/dev/null
    fi
    rm -f "$PID_FILE"
fi
pkill -f "piper" 2>/dev/null
pkill -f "aplay" 2>/dev/null

# Small delay to ensure selection is still held after shortcut fires
sleep 0.3

# Get the currently selected (highlighted) text via X primary selection
SELECTED=$(xclip -selection primary -o 2>/dev/null)

if [ -z "$SELECTED" ]; then
    # Fallback: try xdotool to grab selection
    SELECTED=$(xdotool getactivewindow getselection 2>/dev/null)
fi

if [ -z "$SELECTED" ]; then
    echo "No text selected." >&2
    exit 1
fi

echo "Reading selection: ${SELECTED:0:70}..."
setsid bash -c "echo \"\$1\" | bash \"$SPEAK\"" _ "$SELECTED" &
SPEAK_PID=$!
echo "$SPEAK_PID" > "$PID_FILE"
