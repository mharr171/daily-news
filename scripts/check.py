#!/usr/bin/env python3
"""Pre-publish checks for Live Full Stack.

Run from the repository root before committing:
    python3 scripts/check.py                 # all checks, including story links in changed pages
    python3 scripts/check.py --no-links      # skip the link check (no network)
    python3 scripts/check.py --allow-site-changes   # when the reader asked for design changes

Exits with status 1 if any check fails. Warnings don't fail the run.
Uses only the Python standard library.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
import build_feed  # noqa: E402
import build_search  # noqa: E402

# Files a normal edition may change. Anything else needs --allow-site-changes.
EDITION_FILES = re.compile(r"^(posts\.json|feed\.xml|search\.json|posts/\d{4}-\d{2}-\d{2}\.html)$")
# Files that must never change.
NEVER = {"CNAME"}

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def changed_files():
    """Files changed compared with origin/main, including uncommitted and new files."""
    base = git("merge-base", "HEAD", "origin/main")
    out = set()
    if base:
        out |= set((git("diff", "--name-only", base.strip()) or "").split())
    out |= set((git("diff", "--name-only") or "").split())
    out |= set((git("ls-files", "--others", "--exclude-standard") or "").split())
    if base is None:
        warn("Couldn’t compare with origin/main, so the changed-files check was skipped.")
        return None
    return sorted(out)


def check_posts_json():
    try:
        data = json.loads((ROOT / "posts.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"posts.json is not valid JSON: {e}")
        return []
    eds = data.get("editions") if isinstance(data, dict) else None
    if not isinstance(eds, list):
        fail("posts.json must be an object with an \"editions\" list.")
        return []
    dates = []
    for i, e in enumerate(eds):
        where = f"posts.json entry {i + 1}"
        d = e.get("date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            fail(f"{where}: bad or missing date {d!r}.")
            continue
        where = f"posts.json {d}"
        dates.append(d)
        if e.get("file") != f"posts/{d}.html":
            fail(f"{where}: file should be posts/{d}.html, not {e.get('file')!r}.")
        elif not (ROOT / e["file"]).exists():
            fail(f"{where}: {e['file']} doesn’t exist.")
        if not e.get("summary"):
            fail(f"{where}: summary is empty.")
        heads = e.get("headlines") or []
        if not heads:
            fail(f"{where}: no headlines.")
        for h in heads:
            if not h.get("title") or not h.get("topic"):
                fail(f"{where}: every headline needs a title and a topic.")
                break
            if "&amp;" in h["topic"]:
                fail(f"{where}: topic {h['topic']!r} should use a plain & in JSON.")
        if not 4 <= len(heads) <= 5:
            warn(f"{where}: has {len(heads)} headlines (the task asks for 4–5).")
    if dates != sorted(dates, reverse=True):
        fail("posts.json editions aren’t in date order, newest first.")
    if len(dates) != len(set(dates)):
        fail("posts.json has more than one entry for the same date.")
    return dates


def check_pages(dates):
    listed = set(dates)
    for p in sorted((ROOT / "posts").glob("*.html")):
        s = p.read_text(encoding="utf-8")
        d = p.stem
        if "{{" in s:
            fail(f"{p.name}: leftover {{{{ placeholder.")
        m = re.search(r'<body data-date="([^"]*)"', s)
        if not m or m.group(1) != d:
            fail(f"{p.name}: body data-date should be {d}.")
        if d not in listed:
            warn(f"{p.name} isn’t listed in posts.json.")
        og = re.search(r'<meta property="og:description" content="([^"]*)">', s)
        if not og:
            fail(f"{p.name}: og:description tag is missing or broken (a straight \" in the summary?).")
        if re.search(r"<img\b", s, re.I):
            fail(f"{p.name}: contains an image; editions use no photos.")


def check_feed():
    try:
        expected = build_feed.render()
    except Exception as e:  # noqa: BLE001
        fail(f"Couldn’t build the feed: {e}")
        return
    path = ROOT / "feed.xml"
    if not path.exists() or path.read_text(encoding="utf-8") != expected:
        fail("feed.xml is out of date. Run: python3 scripts/build.py")
    try:
        expected = build_search.render()
    except Exception as e:  # noqa: BLE001
        fail(f"Couldn’t build the search index: {e}")
        return
    path = ROOT / "search.json"
    if not path.exists() or path.read_text(encoding="utf-8") != expected:
        fail("search.json is out of date. Run: python3 scripts/build.py")


MIN_STORIES = 8
EXTRA_SECTIONS = {"week-in-review", "month-in-review", "coming-up"}


def check_size(pages):
    """Warn when a new or changed edition has fewer topic stories than the minimum."""
    for p in pages:
        s = p.read_text(encoding="utf-8")
        n = sum(body.count('<article class="story">')
                for sid, body in re.findall(r'<section class="topic"(?: id="([^"]*)")?>(.*?)</section>', s, re.S)
                if sid not in EXTRA_SECTIONS)
        if n < MIN_STORIES:
            warn(f"{p.name} has {n} topic stories; the task asks for at least {MIN_STORIES}. "
                 "Add more if there’s strong news, and explain in the report if not.")


def check_changed(files, allow_site):
    if files is None:
        return
    for f in files:
        top = f.split("/")[0]
        if f in NEVER:
            fail(f"{f} changed. It must never be edited.")
        elif top == "tasks":
            fail(f"{f}: the repository must not have a tasks/ folder.")
        elif not EDITION_FILES.match(f) and not allow_site:
            fail(f"{f} changed, but an edition should only change posts.json, feed.xml and posts/ pages.")


def story_links(page):
    s = page.read_text(encoding="utf-8")
    return re.findall(r'<article class="story">\s*<h3><a href="(https?://[^"]+)"', s)


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; LiveFullStackLinkCheck/1.0)",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return url, r.status, None
    except urllib.error.HTTPError as e:
        return url, e.code, None
    except Exception as e:  # noqa: BLE001
        return url, None, str(e)


def check_links(pages):
    urls = sorted({u for p in pages for u in story_links(p)})
    if not urls:
        return
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, urls))
    for url, status, err in results:
        if status in (404, 410):
            fail(f"Broken link ({status}): {url}")
        elif status is None:
            warn(f"Couldn’t reach {url} ({err}). Check it by hand.")
        elif status >= 400:
            warn(f"{url} answered {status}; the site may block automated checks. Check it by hand.")
    print(f"Checked {len(urls)} story links.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-links", action="store_true", help="skip the story link check")
    ap.add_argument("--allow-site-changes", action="store_true",
                    help="allow changes outside posts.json, feed.xml and posts/")
    ap.add_argument("--links-for", nargs="*", metavar="YYYY-MM-DD",
                    help="check links in these editions instead of the changed ones")
    args = ap.parse_args()

    dates = check_posts_json()
    check_pages(dates)
    check_feed()
    files = changed_files()
    check_changed(files, args.allow_site_changes)

    changed_pages = [ROOT / f for f in (files or []) if re.fullmatch(r"posts/\d{4}-\d{2}-\d{2}\.html", f)]
    check_size([p for p in changed_pages if p.exists()])

    if not args.no_links:
        if args.links_for:
            pages = [ROOT / "posts" / f"{d}.html" for d in args.links_for]
        else:
            pages = [ROOT / f for f in (files or []) if re.fullmatch(r"posts/\d{4}-\d{2}-\d{2}\.html", f)]
        check_links([p for p in pages if p.exists()])

    for w in warns:
        print("WARN ", w)
    for f in fails:
        print("FAIL ", f)
    if fails:
        print(f"\n{len(fails)} check(s) failed. Don’t publish.")
        sys.exit(1)
    print("\nAll checks passed." + (f" {len(warns)} warning(s) to review." if warns else ""))


if __name__ == "__main__":
    main()
