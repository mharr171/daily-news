#!/usr/bin/env python3
"""Build feed.xml (RSS 2.0) from posts.json.

Run from the repository root after posts.json changes:
    python3 scripts/build_feed.py
Uses only the Python standard library.
"""
import json
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

SITE = "https://www.livefullstack.com"
TITLE = "Live Full Stack"
DESCRIPTION = "A daily roundup of the news: local and world news, sports, culture, and science and tech."
TZ = ZoneInfo("America/Los_Angeles")
MAX_ITEMS = 30

root = Path(__file__).resolve().parent.parent
data = json.loads((root / "posts.json").read_text(encoding="utf-8"))
editions = data["editions"] if isinstance(data, dict) else data
editions = sorted((e for e in editions if e.get("date") and e.get("file")),
                  key=lambda e: e["date"], reverse=True)[:MAX_ITEMS]


def pub_date(day):
    # Editions are published in the morning, Pacific time.
    return format_datetime(datetime.fromisoformat(day + "T07:00:00").replace(tzinfo=TZ))


def long_date(day):
    d = datetime.fromisoformat(day)
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")


items = []
for e in editions:
    url = f"{SITE}/{e['file']}"
    heads = e.get("headlines") or []
    title = f"{long_date(e['date'])}: {heads[0]['title']}" if heads else long_date(e["date"])
    body = f"<p>{escape(e.get('summary', ''))}</p>"
    if heads:
        body += "<ul>" + "".join(
            f"<li>{escape(h['title'])} <em>({escape(h.get('topic', ''))})</em></li>" for h in heads
        ) + "</ul>"
    body += f'<p><a href="{url}">Read the full edition</a></p>'
    items.append(
        "  <item>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{url}</link>\n"
        f'    <guid isPermaLink="true">{url}</guid>\n'
        f"    <pubDate>{pub_date(e['date'])}</pubDate>\n"
        f"    <description>{escape(body)}</description>\n"
        "  </item>"
    )

last = pub_date(editions[0]["date"]) if editions else format_datetime(datetime.now(TZ))
feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{TITLE}</title>
  <link>{SITE}/</link>
  <description>{escape(DESCRIPTION)}</description>
  <language>en-us</language>
  <lastBuildDate>{last}</lastBuildDate>
  <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
  <image>
    <url>{SITE}/icon-512.png</url>
    <title>{TITLE}</title>
    <link>{SITE}/</link>
  </image>
{chr(10).join(items)}
</channel>
</rss>
"""
(root / "feed.xml").write_text(feed, encoding="utf-8")
print(f"feed.xml: {len(items)} editions")
