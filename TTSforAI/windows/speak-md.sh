#!/usr/bin/env bash
# speak-md.sh — Strip markdown formatting and speak via TTS
# Usage:
#   echo "# Hello **world**" | bash speak-md.sh
#   cat response.md | bash speak-md.sh

SPEAK_PS1="C:/Users/Dragan.Lukac/Documents/01Projects/dragan-ai-tools/scripts/tts/speak.ps1"

strip_markdown() {
    sed \
        -e '/^```/,/^```/d' \
        -e 's/^#{1,6} *//' \
        -e 's/\*\*\([^*]*\)\*\*/\1/g' \
        -e 's/\*\([^*]*\)\*/\1/g' \
        -e 's/`[^`]*`//g' \
        -e 's/^\s*[-*+] *//' \
        -e 's/\[[^]]*\]([^)]*)//g' \
        -e 's/^> *//' \
        -e 's/|//g' \
        -e '/^[-=]\+$/d' \
        -e '/^[[:space:]]*$/d'
}

cat | strip_markdown | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SPEAK_PS1"
