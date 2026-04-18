#!/usr/bin/env bash
# speak.sh — Linux TTS Reader using Piper
# Reads text from stdin or arguments and speaks it aloud.
#
# Usage:
#   speak "hello world"
#   echo "hello world" | speak.sh
#   cat file.txt | speak.sh

PIPER=~/.local/bin/piper
VOICE=~/HUB/Projekti/draganL-agent-instructions/TTSforAI/piper/voices/en_US-ryan-high.onnx

if [ "$#" -gt 0 ]; then
    TEXT="$*"
else
    TEXT=$(cat)
fi

[ -z "$TEXT" ] && exit 0

echo "$TEXT" | "$PIPER" --model "$VOICE" --output-raw | aplay -r 22050 -f S16_LE -t raw -q
