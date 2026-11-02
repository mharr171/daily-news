#!/usr/bin/env python3
"""Build search.json, the full-text search index used by archive.html.

Indexes every story in every edition listed in posts.json: headline, summary,
"Why it matters" line, topic, source line, and link. Recap and Coming up
sections are left out because they repeat stories already indexed.
Uses only the Python standard library.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_SECTIONS = {"week-in-review", "month-in-review", "coming-up", "news-quiz", "source-mix"}

SECTION = re.compile(r'<section class="topic"(?: id="([^"]*)")?>\s*<h2>(.*?)</h2>(.*?)</section>', re.S)
STORY = re.compile(r'<article class="story">(.*?)</article>', re.S)
HEAD = re.compile(r'<h3>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>', re.S)
PARA = re.compile(r'<p( class="[^"]*")?>(.*?)</p>', re.S)


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def stories_in(page):
    out = []
    for sid, name, body in SECTION.findall(page):
        if sid in SKIP_SECTIONS:
            continue
        topic = text(name)
        for story in STORY.findall(body):
            h = HEAD.search(story)
            if not h:
                continue
            item = {"t": text(h.group(2)), "u": h.group(1), "c": topic, "s": "", "w": "", "src": ""}
            for cls, p in PARA.findall(story):
                if 'class="why"' in cls:
                    item["w"] = re.sub(r"^Why it matters:\s*", "", text(p))
                elif 'class="source"' in cls:
                    item["src"] = text(p)
                elif not cls and not item["s"]:
                    item["s"] = text(p)
            out.append({k: v for k, v in item.items() if v})
    return out


def render(root=ROOT):
    """Return the search index as a JSON string."""
    data = json.loads((root / "posts.json").read_text(encoding="utf-8"))
    editions = data["editions"] if isinstance(data, dict) else data
    index = []
    for e in sorted((e for e in editions if e.get("date") and e.get("file")),
                    key=lambda e: e["date"], reverse=True):
        page = root / e["file"]
        if page.exists():
            index.append({"d": e["date"], "f": e["file"], "stories": stories_in(page.read_text(encoding="utf-8"))})
    return json.dumps({"editions": index}, ensure_ascii=False, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    out = render()
    (ROOT / "search.json").write_text(out, encoding="utf-8")
    n = sum(len(e["stories"]) for e in json.loads(out)["editions"])
    print(f"search.json: {n} stories")
