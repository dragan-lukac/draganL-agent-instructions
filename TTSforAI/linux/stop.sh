#!/usr/bin/env bash
# stop.sh — Stop any currently running TTS speech immediately
# Bind this to a keyboard shortcut (e.g. Ctrl+Alt+S) in Ubuntu Settings

PID_FILE="/tmp/tts-monitor-speak.pid"

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
