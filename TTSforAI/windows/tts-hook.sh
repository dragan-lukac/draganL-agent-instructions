#!/usr/bin/env bash
# tts-hook.sh — Claude Code Stop hook (no jq required — uses PowerShell)
# Reads the last assistant text message from the transcript and speaks it via TTS.
# Wired into ~/.claude/settings.json under hooks > Stop

SPEAK_MD="C:/Users/Dragan.Lukac/Documents/01Projects/dragan-ai-tools/scripts/tts/speak-md.sh"

INPUT=$(cat)

TEXT=$(echo "$INPUT" | powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
  \$json = (\$input | Out-String) | ConvertFrom-Json
  \$transcriptPath = \$json.transcript_path
  if (-not \$transcriptPath -or -not (Test-Path \$transcriptPath)) { exit 0 }
  \$lines = @(Get-Content \$transcriptPath | Where-Object { \$_ -match '\"type\":\"assistant\"' })
  for (\$i = \$lines.Count - 1; \$i -ge 0; \$i--) {
    \$obj = \$lines[\$i] | ConvertFrom-Json
    \$textBlocks = @(\$obj.message.content | Where-Object { \$_.type -eq 'text' })
    if (\$textBlocks.Count -gt 0) {
      (\$textBlocks | ForEach-Object { \$_.text }) -join ' '
      break
    }
  }
" 2>/dev/null)

if [ -n "$TEXT" ]; then
  echo "$TEXT" | bash "$SPEAK_MD"
fi
