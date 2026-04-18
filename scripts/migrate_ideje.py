#!/usr/bin/env python3
import os, requests
from pathlib import Path

def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
load_env()

TOKEN  = os.environ["NOTION_TOKEN"]
ROOT   = os.environ["NOTION_ROOT_PAGE_ID"]
OLD_DB = "346a338b6c5181e8bcf0cb4c48085fb0"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

ICONS = {
    "Ai Programski jezik":           "🤖",
    "Drustvena mreza":               "📱",
    "LLM":                           "🧠",
    "Mobile OS - BOS":               "📲",
    "Kafic":                         "☕",
    "Kuca na moru":                  "🏖️",
    "Lokalni linux server - exposed": "🖥️",
    "PrviSrpskiQAPodcast":           "🎙️",
    "Sava Savanovic - restoran":     "🍽️",
    "Sekure":                        "🛡️",
    "Video Igra":                    "🎮",
    "Zimnica - Siki":                "🫙",
}

DESCRIPTIONS = {
    "Drustvena mreza": "Drustvena mreza za deljenje memeova. Slicno ovo sto radimo na insta u porukama. Kreiras grupe ljudi koji zelis da vide prepisku, kao da imas svoj javni zid, ali je uvek za grupu ljudi. Imas pool memeova za nedelju dana, koje mozes da koristis u porukama i postovima na zidu. Memeovi se rotiraju na nedeljnom nivou. Finansiranje iz donacija, community.",
    "Sekure":    "Aplikacija za bezbednost sportova u prirodi.",
    "Video Igra": "Psihoterapija kroz narativ igre. Hocemo da pruzimo utehu usamljenim i napatenim dusama. Bavimo se raznim aspektima ljudske duse — depresija, manija, anksioznost. Mozda mozemo da ubacimo i druge stvari: religija, meditacija, horoskop, filozofija.",
    "Zimnica - Siki": "Pravimo dzem: coko sljiva, visnja, borovnica i mozda jabuka. Pravimo ajvar. Kvalitet pre svega, nema konzervansa. Potencijalni podrum kao magacin.",
}

DB_PROPS = {
    "Title":  {"title": {}},
    "Status": {
        "select": {"options": [
            {"name": "Raw",       "color": "gray"},
            {"name": "Exploring", "color": "yellow"},
            {"name": "Active",    "color": "green"},
            {"name": "Parked",    "color": "red"},
        ]}
    },
    "Author": {"rich_text": {}},
    "Date":   {"date": {}},
}

GROUPS = {
    "Brate ti si lud": {
        "icon": "🤪",
        "ideas": [
            "Ai Programski jezik",
            "Drustvena mreza",
            "LLM",
            "Mobile OS - BOS",
        ]
    },
    "Realne": {
        "icon": "🎯",
        "ideas": [
            "Kafic",
            "Kuca na moru",
            "Lokalni linux server - exposed",
            "PrviSrpskiQAPodcast",
            "Sava Savanovic - restoran",
            "Sekure",
            "Video Igra",
            "Zimnica - Siki",
        ]
    }
}

def api(method, path, data=None):
    r = requests.request(method, f"https://api.notion.com/v1{path}",
                         headers=HEADERS, json=data)
    return r.json()

# 1. Create the Ideje wrapper page in root
print("Creating Ideje wrapper page...")
page = api("POST", "/pages", {
    "parent": {"page_id": ROOT},
    "icon": {"type": "emoji", "emoji": "💡"},
    "properties": {
        "title": {"title": [{"text": {"content": "Ideje"}}]}
    }
})
ideje_page_id = page.get("id")
print(f"  {page.get('url', page.get('message'))}")

# 2. For each group: create inline database + populate with ideas
for group_name, group_data in GROUPS.items():
    print(f"\nCreating database: {group_name}...")
    db = api("POST", "/databases", {
        "parent":    {"page_id": ideje_page_id},
        "icon":      {"type": "emoji", "emoji": group_data["icon"]},
        "title":     [{"type": "text", "text": {"content": group_name}}],
        "properties": DB_PROPS,
        "is_inline": True,
    })
    db_id = db.get("id")
    if not db_id:
        print(f"  ERR: {db.get('message')}")
        continue
    print(f"  Created: {db.get('url')}")

    for title in group_data["ideas"]:
        icon  = ICONS.get(title, "💡")
        desc  = DESCRIPTIONS.get(title, "")
        body  = []
        if desc:
            body = [{"object": "block", "type": "paragraph",
                     "paragraph": {"rich_text": [{"text": {"content": desc}}]}}]

        r = api("POST", "/pages", {
            "parent":     {"database_id": db_id},
            "icon":       {"type": "emoji", "emoji": icon},
            "properties": {
                "Title":  {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": "Raw"}},
            },
            "children": body,
        })
        print(f"  {'OK' if r.get('id') else r.get('message')}: {icon} {title}")

print("\nDone!")
