#!/usr/bin/env python3
"""
scrape_apple_notes.py — Scrape Apple Notes "Pasme" folder from iCloud and import to Notion

Usage:
    python3 scrape_apple_notes.py --root <notion_page_id>

Steps:
    1. Opens iCloud Notes in a browser window
    2. YOU log in manually (handles 2FA etc.)
    3. Script waits for you to be ready, then scrapes the Pasme folder
    4. Imports all notes into Notion under a new "Apple Notes - Pasme" page
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
load_env()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found in scripts/.env", file=sys.stderr)
    sys.exit(1)

import argparse
from notion_client import Client
from playwright.async_api import async_playwright

notion = Client(auth=NOTION_TOKEN)

# ── Notion helpers ────────────────────────────────────────────────────────────

def create_notion_page(parent_id: str, title: str, content: str) -> str:
    blocks = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        for i in range(0, len(line), 1900):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line[i:i+1900]}}]
                }
            })
        if len(blocks) >= 100:
            break

    result = notion.pages.create(
        parent={"page_id": parent_id},
        properties={"title": {"title": [{"text": {"content": title[:255]}}]}},
        children=blocks[:100]
    )
    time.sleep(0.4)
    return result["id"]

# ── Scraper ───────────────────────────────────────────────────────────────────

async def scrape_and_import(root_id: str):
    async with async_playwright() as p:
        # Launch visible browser so user can log in
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        print("\n🌐 Opening iCloud Notes...")
        await page.goto("https://www.icloud.com/notes/")

        ready_file = Path("/tmp/tts_notes_ready")
        ready_file.unlink(missing_ok=True)

        print("""
══════════════════════════════════════════
  ACTION REQUIRED

  A browser window has opened.
  Please:
    1. Log in to iCloud
    2. Navigate to the "Pasme" folder
       (click it in the left sidebar)
    3. Make sure the notes list is visible

  Then run this in a terminal to continue:
    touch /tmp/tts_notes_ready
══════════════════════════════════════════""")

        print("⏳ Waiting for /tmp/tts_notes_ready ...")
        while not ready_file.exists():
            await asyncio.sleep(1)
        print("✅ Ready signal received, scraping...")

        print("\n🔍 Waiting for notes to fully load...")

        # Wait for the spinner to disappear and notes to appear
        try:
            await page.wait_for_selector('ui-activity-indicator', state='hidden', timeout=30000)
            print("  ✓ Spinner gone")
        except:
            pass

        # Wait a bit more for JS to render
        await page.wait_for_timeout(4000)

        # Dump HTML for debugging
        html = await page.content()
        debug_path = Path("/tmp/icloud_notes_debug.html")
        debug_path.write_text(html)
        print(f"  📄 Page HTML saved to {debug_path}")

        # Get all note titles from the sidebar list
        note_items = await page.query_selector_all('[class*="note-list-item"], [class*="NoteListItem"], li[data-note-id]')

        if not note_items:
            note_items = await page.query_selector_all('li[role="option"], [class*="list-item"]')

        if not note_items:
            note_items = await page.query_selector_all('li')

        print(f"  Found {len(note_items)} note(s) in the list")

        notes_data = []

        for i, item in enumerate(note_items):
            try:
                # Click the note to open it
                await item.click()
                await page.wait_for_timeout(1500)

                # Get title
                title_el = await page.query_selector(
                    '[class*="note-title"], [class*="NoteTitle"], '
                    '.note-header h1, [contenteditable="true"] h1, '
                    '[class*="title-field"]'
                )
                title = await title_el.inner_text() if title_el else f"Note {i+1}"
                title = title.strip() or f"Note {i+1}"

                # Get body content
                body_el = await page.query_selector(
                    '[class*="note-content"], [class*="NoteContent"], '
                    '[class*="editor"], [contenteditable="true"]'
                )
                body = await body_el.inner_text() if body_el else ""
                body = body.strip()

                print(f"  📝 [{i+1}/{len(note_items)}] {title[:60]}")
                notes_data.append({"title": title, "content": body})

            except Exception as e:
                print(f"  ⚠ Could not read note {i+1}: {e}")
                continue

        await browser.close()

        if not notes_data:
            print("\n⚠ No notes were scraped. The iCloud Notes UI may have changed.")
            print("  Try the manual export option below.")
            return

        # ── Import to Notion Songs database ──────────────────────────────────
        SONGS_DB = "e2813f2c3e06427ca7d06afcee1b00eb"
        print(f"\n📤 Importing {len(notes_data)} notes to Songs database...")

        for note in notes_data:
            try:
                blocks = []
                for line in note["content"].splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    for i in range(0, len(line), 1900):
                        blocks.append({
                            "object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[i:i+1900]}}]}
                        })
                    if len(blocks) >= 100:
                        break

                notion.pages.create(
                    parent={"database_id": SONGS_DB},
                    icon={"type": "emoji", "emoji": "🎵"},
                    properties={
                        "Naslov": {"title": [{"text": {"content": note["title"][:255]}}]},
                    },
                    children=blocks[:100]
                )
                time.sleep(0.4)
                print(f"  ✓ Imported: {note['title'][:60]}")
            except Exception as e:
                print(f"  ✗ Failed to import '{note['title']}': {e}")

        # Save scraped data locally as backup
        backup_path = Path(__file__).parent / "pasme_notes_backup.json"
        backup_path.write_text(json.dumps(notes_data, ensure_ascii=False, indent=2))
        print(f"\n💾 Backup saved to: {backup_path}")
        print(f"\n✅ Done! {len(notes_data)} notes imported to Notion.")

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Apple Notes Pasme folder → Notion")
    parser.add_argument("--root", help="Notion page ID to import notes under")
    args = parser.parse_args()

    root_id = args.root or os.environ.get("NOTION_ROOT_PAGE_ID")
    if not root_id:
        print("Error: provide --root or set NOTION_ROOT_PAGE_ID in .env")
        sys.exit(1)

    asyncio.run(scrape_and_import(root_id))
