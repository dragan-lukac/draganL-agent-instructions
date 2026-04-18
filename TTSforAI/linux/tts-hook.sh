#!/usr/bin/env bash
# tts-hook.sh — Claude Code Stop hook (Linux)
# Reads the last assistant text message from the transcript and speaks it.
# Wire into ~/.claude/settings.json under hooks > Stop
#
# Example settings.json entry:
#   "hooks": {
#     "Stop": [
#       {
#         "matcher": "",
#         "hooks": [
#           {
#             "type": "command",
#             "command": "bash /path/to/tts/linux/tts-hook.sh"
#           }
#         ]
#       }
#     ]
#   }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEAK_MD="$SCRIPT_DIR/speak-md.sh"

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('transcript_path', ''))
except:
    pass
" 2>/dev/null)

[ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ] && exit 0

# Extract last assistant text message from transcript
TEXT=$(python3 -c "
import json, sys

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f if '\"type\":\"assistant\"' in l]

for line in reversed(lines):
    try:
        obj = json.loads(line)
        blocks = [b for b in obj.get('message', {}).get('content', []) if b.get('type') == 'text']
        if blocks:
            print(' '.join(b['text'] for b in blocks))
            break
    except:
        continue
" "$TRANSCRIPT_PATH" 2>/dev/null)

if [ -n "$TEXT" ]; then
    echo "$TEXT" | bash "$SPEAK_MD"
fi
