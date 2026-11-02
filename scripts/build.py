#!/usr/bin/env python3
"""Rebuild the generated files from posts.json and the edition pages.

Run from the repository root after any change to posts.json or posts/:
    python3 scripts/build.py
Writes feed.xml (RSS) and search.json (archive search). Never edit those by hand.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_feed  # noqa: E402
import build_search  # noqa: E402

ROOT = build_feed.ROOT
feed = build_feed.render()
(ROOT / "feed.xml").write_text(feed, encoding="utf-8")
search = build_search.render()
(ROOT / "search.json").write_text(search, encoding="utf-8")
print(f"feed.xml: {feed.count('<item>')} editions")
stories = search.count('"t":')
print(f"search.json: {stories} stories")
