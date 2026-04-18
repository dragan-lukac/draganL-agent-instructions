#!/usr/bin/env bash
# speak-md.sh — Strip markdown formatting and speak via TTS (Linux)
# Usage:
#   echo "# Hello **world**" | bash speak-md.sh
#   cat response.md | bash speak-md.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEAK="$SCRIPT_DIR/speak.sh"

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

cat | strip_markdown | bash "$SPEAK"
