#!/usr/bin/env python3
"""
migrate_to_notion.py — Migrate HUB content to Notion
Recreates the full HUB folder structure as Notion pages.

Usage:
    python3 migrate_to_notion.py --dry-run   # preview what will be created
    python3 migrate_to_notion.py             # run the migration

Requirements:
    pip install notion-client python-docx beautifulsoup4

Before running:
    1. Go to notion.so → your integration → share a root page with it
    2. Run: python3 notion.py list-databases  to find the root page ID
    3. Set ROOT_PAGE_ID below, or pass --root <page_id>
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from typing import Optional

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

from notion_client import Client
from docx import Document
from bs4 import BeautifulSoup

notion = Client(auth=NOTION_TOKEN)

HUB = Path("/home/dragan/HUB")

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_docx(path: Path) -> str:
    try:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"(Could not read file: {e})"

def read_html(path: Path) -> str:
    try:
        soup = BeautifulSoup(path.read_text(errors="ignore"), "html.parser")
        return soup.get_text(separator="\n").strip()
    except Exception as e:
        return f"(Could not read file: {e})"

def chunks(text: str, size: int = 1900):
    """Split text into chunks for Notion's 2000 char block limit."""
    for i in range(0, len(text), size):
        yield text[i:i+size]

def text_to_blocks(text: str) -> list:
    """Convert plain text into Notion paragraph blocks."""
    blocks = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for chunk in chunks(line):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })
    return blocks[:100]  # Notion allows max 100 blocks per request

def make_callout(text: str, emoji: str = "ℹ️") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def make_bookmark(url: str, caption: str = "") -> dict:
    return {
        "object": "block",
        "type": "bookmark",
        "bookmark": {"url": url}
    }

def make_heading(text: str, level: int = 2) -> dict:
    htype = f"heading_{level}"
    return {
        "object": "block",
        "type": htype,
        htype: {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }

def create_page(parent_id: str, title: str, children: list = None, emoji: str = None, dry_run: bool = False) -> Optional[str]:
    icon = {"type": "emoji", "emoji": emoji} if emoji else None
    if dry_run:
        print(f"  [DRY RUN] Would create page: '{title}' under {parent_id[:8]}...")
        return "dry-run-id"
    try:
        kwargs = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            },
        }
        if icon:
            kwargs["icon"] = icon
        if children:
            kwargs["children"] = children[:100]
        result = notion.pages.create(**kwargs)
        page_id = result["id"]
        print(f"  ✓ Created: '{title}'")
        time.sleep(0.4)  # rate limit
        return page_id
    except Exception as e:
        print(f"  ✗ Failed to create '{title}': {e}")
        return None

def append_blocks(page_id: str, blocks: list, dry_run: bool = False):
    if dry_run or not blocks:
        return
    try:
        for i in range(0, len(blocks), 100):
            notion.blocks.children.append(block_id=page_id, children=blocks[i:i+100])
            time.sleep(0.3)
    except Exception as e:
        print(f"    ✗ Could not append blocks: {e}")

# ── Migration sections ────────────────────────────────────────────────────────

def migrate_docx_folder(parent_id: str, folder: Path, dry_run: bool):
    """Create one Notion page per .docx/.html file in a folder."""
    files = sorted(folder.glob("**/*"))
    for f in files:
        if f.suffix.lower() == ".docx":
            content = read_docx(f)
            blocks = text_to_blocks(content)
            create_page(parent_id, f.stem, children=blocks, dry_run=dry_run)
        elif f.suffix.lower() == ".html":
            content = read_html(f)
            blocks = text_to_blocks(content)
            create_page(parent_id, f.stem, children=blocks, dry_run=dry_run)

def migrate_hub(root_id: str, dry_run: bool = False):
    print("\n══════════════════════════════════════")
    print("  HUB → Notion Migration")
    print(f"  Root page: {root_id}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("══════════════════════════════════════\n")

    # ── DaHab ────────────────────────────────────────────────────────────────
    print("📁 DaHab")
    dahab_id = create_page(root_id, "DaHab", emoji="🏠", dry_run=dry_run)
    if dahab_id:
        migrate_docx_folder(dahab_id, HUB / "DaHab", dry_run)

    # ── Ideje ─────────────────────────────────────────────────────────────────
    print("\n📁 Ideje")
    ideje_id = create_page(root_id, "Ideje", emoji="💡", dry_run=dry_run)
    if ideje_id:
        for subfolder in ["Brate, ti si lud", "Realne"]:
            path = HUB / "Ideje" / subfolder
            if path.exists():
                print(f"  📁 {subfolder}")
                sub_id = create_page(ideje_id, subfolder, dry_run=dry_run)
                if sub_id:
                    migrate_docx_folder(sub_id, path, dry_run)

    # ── Ljudi ─────────────────────────────────────────────────────────────────
    print("\n📁 Ljudi")
    ljudi_id = create_page(root_id, "Ljudi", emoji="👥", dry_run=dry_run)
    if ljudi_id:
        migrate_docx_folder(ljudi_id, HUB / "Ljudi", dry_run)

    # ── Dokumentacija ─────────────────────────────────────────────────────────
    print("\n📁 Dokumentacija")
    dok_id = create_page(root_id, "Dokumentacija", emoji="📄", dry_run=dry_run)
    if dok_id:
        muzika_path = HUB / "Dokumentacija" / "Muzika"
        if muzika_path.exists():
            print("  📁 Muzika")
            muz_id = create_page(dok_id, "Muzika", emoji="🎵", dry_run=dry_run)
            if muz_id:
                migrate_docx_folder(muz_id, muzika_path, dry_run)

    # ── Music projects ────────────────────────────────────────────────────────
    print("\n📁 Music")
    music_id = create_page(root_id, "Music", emoji="🎸", dry_run=dry_run)
    if music_id:
        # CAT_FAT
        print("  📁 CAT_FAT")
        catfat_blocks = [
            make_callout("YouTube channel — CAT_FAT music", "🎬"),
            make_bookmark("https://www.youtube.com/@CAT_FAT_music"),
            make_heading("Content", 2),
        ]
        catfat_id = create_page(music_id, "CAT_FAT", emoji="🎬", children=catfat_blocks, dry_run=dry_run)
        if catfat_id:
            migrate_docx_folder(catfat_id, HUB / "Projekti" / "CAT_FAT", dry_run)

        # SlobodaZaSve
        print("  📁 SlobodaZaSve")
        sloboda_blocks = [
            make_callout("YouTube channel — SlobodaZaSve", "🎬"),
            make_bookmark("https://www.youtube.com/@SloZaSe"),
            make_heading("Content", 2),
        ]
        sloboda_id = create_page(music_id, "SlobodaZaSve", emoji="🎬", children=sloboda_blocks, dry_run=dry_run)
        if sloboda_id:
            migrate_docx_folder(sloboda_id, HUB / "Projekti" / "SlobodaZaSve - youtube kanal", dry_run)

        # JammingSessions
        print("  📁 JammingSessions")
        jamming_blocks = [make_callout("Home jamming sessions — docs and recordings by date", "🎙️")]
        jamming_id = create_page(music_id, "JammingSessions", emoji="🎙️", children=jamming_blocks, dry_run=dry_run)
        if jamming_id:
            sessions_path = HUB / "Projekti" / "JammingSessions"
            # Top-level docs
            migrate_docx_folder(jamming_id, sessions_path, dry_run)
            # Session date subfolders
            for date_folder in sorted(sessions_path.iterdir()):
                if date_folder.is_dir():
                    print(f"    📅 {date_folder.name}")
                    session_id = create_page(jamming_id, date_folder.name, emoji="📅", dry_run=dry_run)
                    if session_id:
                        migrate_docx_folder(session_id, date_folder, dry_run)
                        # Note audio files
                        audio_files = list(date_folder.glob("*.mp3")) + list(date_folder.glob("*.wav"))
                        if audio_files and not dry_run:
                            audio_blocks = [make_heading("Audio Files", 2)]
                            for af in audio_files:
                                audio_blocks.append({
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": f"🎵 {af.name} (local file: {af})"}}]
                                    }
                                })
                            append_blocks(session_id, audio_blocks, dry_run)

    # ── Code Projects ─────────────────────────────────────────────────────────
    print("\n📁 Projekti (Code)")
    code_id = create_page(root_id, "Projekti", emoji="💻", dry_run=dry_run)
    if code_id:
        # circuitQ
        circuitq_blocks = [
            make_callout("Circuit simulation project", "⚡"),
            make_heading("GitHub", 2),
            make_bookmark("https://github.com/filip993/circuitQ"),
        ]
        create_page(code_id, "circuitQ", emoji="⚡", children=circuitq_blocks, dry_run=dry_run)

        # draganL-agent-instructions
        agent_blocks = [
            make_callout("Claude Code agent instructions, TTS setup, and scripts", "🤖"),
            make_heading("GitHub", 2),
            make_bookmark("https://github.com/dragan-lukac/draganL-agent-instructions"),
        ]
        create_page(code_id, "draganL-agent-instructions", emoji="🤖", children=agent_blocks, dry_run=dry_run)

        # TTS for AI
        tts_blocks = [
            make_callout("TTS (Text-to-Speech) scripts for Claude Code — part of draganL-agent-instructions", "🔊"),
            make_heading("GitHub", 2),
            make_bookmark("https://github.com/dragan-lukac/draganL-agent-instructions"),
        ]
        create_page(code_id, "TTS for AI", emoji="🔊", children=tts_blocks, dry_run=dry_run)

    print("\n✅ Migration complete!")
    print("\nNext step: run the Apple Notes scraper for the Pasme folder.")

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate HUB to Notion")
    parser.add_argument("--root", help="Root Notion page ID to create everything under")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating anything")
    args = parser.parse_args()

    root_id = args.root or os.environ.get("NOTION_ROOT_PAGE_ID")

    if not root_id:
        print("""
Error: No root page ID provided.

Steps:
  1. In Notion, create a page called "HUB" (or any name)
  2. Share it with your integration:
     Open the page → ... menu → Connections → select your integration
  3. Get the page ID from the URL:
     https://notion.so/Your-Page-Title-<PAGE_ID_HERE>
     (it's the last part after the last dash, 32 chars)
  4. Run:
     python3 migrate_to_notion.py --root <page_id>
     or add to scripts/.env:
     NOTION_ROOT_PAGE_ID=<page_id>
""")
        sys.exit(1)

    migrate_hub(root_id, dry_run=args.dry_run)
