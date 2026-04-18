# Dragan's Agent Instructions

## Who you are working with
- Name: Dragan Lukač
- Based in: Ubuntu Linux (ThinkPad T450s)
- Works across: Claude Code CLI, Notion, HUB local folder, GitHub

## Session summaries

**At the start of every session:**
1. Check `sessions/` for the most recent session file
2. Briefly summarize what was left pending from that session
3. Inform Dragan of any unfinished tasks

**At the end of every session (or when asked):**
1. Create a new session file: `sessions/YYYY-MM-DD.md`
2. Include:
   - What was done
   - Scripts or files created/modified
   - Pending items for next session

## Key paths
| What | Path |
|---|---|
| HUB (local) | `/home/dragan/HUB/` |
| Scripts | `/home/dragan/HUB/Projekti/draganL-agent-instructions/scripts/` |
| Session logs | `/home/dragan/HUB/Projekti/draganL-agent-instructions/sessions/` |
| TTS scripts | `/home/dragan/HUB/Projekti/draganL-agent-instructions/TTSforAI/linux/` |
| Notion root page | `341a338b6c51809b8fe1d17ede7e28dc` |

## Rules
- Always create scripts in `scripts/`
- Never hardcode secrets — use `scripts/.env`
- Session files go in `sessions/YYYY-MM-DD.md`
- Keep responses concise — Dragan often uses voice input
