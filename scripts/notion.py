#!/usr/bin/env python3
"""
notion.py — Notion API helper
Loads token from scripts/.env and provides easy functions to
list, read, create, and update Notion pages/databases.

Usage:
    python3 notion.py list-databases
    python3 notion.py list-pages <database_id>
    python3 notion.py get-page <page_id>
    python3 notion.py search "query"
"""

import os
import sys
import json
import argparse
from pathlib import Path

# ── Load token from .env ──────────────────────────────────────────────────────
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
    print("Error: NOTION_TOKEN not found. Check scripts/.env", file=sys.stderr)
    sys.exit(1)

# ── Notion client ─────────────────────────────────────────────────────────────
try:
    from notion_client import Client
except ImportError:
    print("Error: notion-client not installed. Run: pip install notion-client", file=sys.stderr)
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN)

# ── Helper functions ──────────────────────────────────────────────────────────

def list_databases():
    """List all databases the integration has access to."""
    results = notion.search(filter={"value": "data_source", "property": "object"})
    dbs = results.get("results", [])
    if not dbs:
        print("No databases found. Make sure you've shared pages with your integration.")
        return
    print(f"Found {len(dbs)} database(s):\n")
    for db in dbs:
        title = _get_title(db)
        print(f"  [{db['id']}]  {title}")

def list_pages(database_id: str):
    """List all pages in a database."""
    results = notion.databases.query(database_id=database_id)
    pages = results.get("results", [])
    if not pages:
        print("No pages found in this database.")
        return
    print(f"Found {len(pages)} page(s):\n")
    for page in pages:
        title = _get_title(page)
        print(f"  [{page['id']}]  {title}")

def get_page(page_id: str):
    """Get a page and print its block content."""
    page = notion.pages.retrieve(page_id=page_id)
    title = _get_title(page)
    print(f"Page: {title}\nID:   {page_id}\n")
    blocks = notion.blocks.children.list(block_id=page_id)
    for block in blocks.get("results", []):
        text = _extract_block_text(block)
        if text:
            print(text)

def search(query: str):
    """Search all pages and databases."""
    results = notion.search(query=query)
    items = results.get("results", [])
    if not items:
        print(f"No results for: {query}")
        return
    print(f"Found {len(items)} result(s) for '{query}':\n")
    for item in items:
        title = _get_title(item)
        print(f"  [{item['object']}]  [{item['id']}]  {title}")

def create_page(database_id: str, title: str, content: str = ""):
    """Create a new page in a database."""
    new_page = notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Name": {
                "title": [{"text": {"content": title}}]
            }
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": content}}]
                }
            }
        ] if content else []
    )
    print(f"Created page: {title}")
    print(f"ID: {new_page['id']}")
    return new_page["id"]

# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_title(obj: dict) -> str:
    try:
        props = obj.get("properties", {})
        for key in ("Name", "Title", "title"):
            if key in props:
                rich = props[key].get("title", [])
                return "".join(r["plain_text"] for r in rich) or "(untitled)"
        # database title
        title_arr = obj.get("title", [])
        if title_arr:
            return "".join(t.get("plain_text", "") for t in title_arr) or "(untitled)"
    except Exception:
        pass
    return "(untitled)"

def _extract_block_text(block: dict) -> str:
    btype = block.get("type", "")
    data = block.get(btype, {})
    rich = data.get("rich_text", [])
    text = "".join(r.get("plain_text", "") for r in rich)
    if btype.startswith("heading"):
        return f"\n## {text}"
    if btype == "bulleted_list_item":
        return f"  • {text}"
    if btype == "numbered_list_item":
        return f"  1. {text}"
    if btype == "code":
        return f"\n```\n{text}\n```"
    return text

# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notion API helper")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list-databases", help="List all accessible databases")

    p_pages = sub.add_parser("list-pages", help="List pages in a database")
    p_pages.add_argument("database_id")

    p_get = sub.add_parser("get-page", help="Get page content")
    p_get.add_argument("page_id")

    p_search = sub.add_parser("search", help="Search Notion")
    p_search.add_argument("query")

    p_create = sub.add_parser("create-page", help="Create a page in a database")
    p_create.add_argument("database_id")
    p_create.add_argument("title")
    p_create.add_argument("content", nargs="?", default="")

    args = parser.parse_args()

    if args.cmd == "list-databases":
        list_databases()
    elif args.cmd == "list-pages":
        list_pages(args.database_id)
    elif args.cmd == "get-page":
        get_page(args.page_id)
    elif args.cmd == "search":
        search(args.query)
    elif args.cmd == "create-page":
        create_page(args.database_id, args.title, args.content)
    else:
        parser.print_help()
