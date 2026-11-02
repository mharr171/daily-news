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
EDITION_FILES = re.compile(r"^(posts\.json|feed\.xml|search\.json|calendar\.json|threads\.json|posts/\d{4}-\d{2}-\d{2}\.html)$")
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


CAL_CATEGORIES = {
    "Holidays", "Bank holidays", "Religious", "Cultural", "Patriotic & memorial", "Awareness",
    "Seasonal", "Seasons", "Time changes", "Sunlight", "Friday the 13th", "Moon & sky", "Space",
    "Government", "Financial", "Millbrae", "Community", "County arts",
    "Sports", "Sports calendar", "Entertainment",
}
CAL_TEAMS = {"49ers", "Warriors", "Giants", "Earthquakes", "Bay FC", "Hawaii", "San Francisco City FC", "Valkyries"}


def check_calendar():
    path = ROOT / "calendar.json"
    if not path.exists():
        return
    try:
        cal = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"calendar.json is not valid JSON: {e}")
        return
    events = cal.get("events")
    if not isinstance(events, list):
        fail("calendar.json must have an \"events\" list.")
        return
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cal.get("updated", ""))):
        fail("calendar.json: \"updated\" must be a YYYY-MM-DD date.")
    seen, prev = set(), ""
    for i, e in enumerate(events):
        where = f"calendar.json event {i + 1} ({e.get('title', '?')})"
        d = str(e.get("date", ""))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            fail(f"{where}: bad date {d!r}.")
            continue
        if e.get("end") and not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e["end"])) and e["end"] >= d):
            fail(f"{where}: end must be a date on or after the start.")
        for k in ("title", "category", "url"):
            if not e.get(k):
                fail(f"{where}: missing {k}.")
        if e.get("category") not in CAL_CATEGORIES:
            fail(f"{where}: category must be one of {sorted(CAL_CATEGORIES)}.")
        if e.get("category") == "Sports" and e.get("team") not in CAL_TEAMS:
            warn(f"{where}: unexpected team {e.get('team')!r}.")
        if d < prev:
            fail(f"{where}: events must be in date order.")
        prev = d
        key = (d, e.get("title"))
        if key in seen:
            fail(f"{where}: duplicate event on {d}.")
        seen.add(key)
        for k in ("title", "description", "location"):
            if '"' in str(e.get(k, "")):
                warn(f"{where}: straight double quote in {k}; use “ ”.")


def thread_ids():
    path = ROOT / "threads.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"threads.json is not valid JSON: {e}")
        return set()
    ids = set()
    for i, t in enumerate(data.get("threads") or []):
        where = f"threads.json thread {i + 1} ({t.get('id', '?')})"
        for k in ("id", "title", "status", "summary", "updated", "entries"):
            if not t.get(k):
                fail(f"{where}: missing {k}.")
        if t.get("status") not in ("Developing", "Resolved"):
            fail(f"{where}: status must be Developing or Resolved.")
        if t.get("id") in ids:
            fail(f"{where}: duplicate id.")
        ids.add(t.get("id"))
        dates = []
        for e in t.get("entries") or []:
            for k in ("date", "edition", "headline", "url"):
                if not e.get(k):
                    fail(f"{where}: an entry is missing {k}.")
            if e.get("edition") and not (ROOT / e["edition"]).exists():
                fail(f"{where}: entry points to {e['edition']}, which doesn’t exist.")
            dates.append(e.get("date", ""))
        if dates and t.get("updated") != max(dates):
            warn(f"{where}: updated should be its newest entry’s date, {max(dates)}.")
    return ids


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
EXTRA_SECTIONS = {"on-this-day", "week-in-review", "month-in-review", "coming-up", "news-quiz", "source-mix"}
KICKERS = {"top", "developing", "good", "feature"}
THREADS = set()


def d_of(p):
    return p.stem


def check_features(p, s):
    """Checks for the features editions have had since Nov 1, 2026."""
    for need in ('assets/edition.css', 'assets/edition.js', 'assets/reader.js', 'id="today-box"'):
        if need not in s:
            fail(f"{p.name}: missing {need} (copy the current templates/day.html).")
    brief = re.search(r'<section class="brief"[^>]*>(.*?)</section>', s, re.S)
    if not brief:
        fail(f"{p.name}: missing The day in 60 seconds.")
    else:
        k = brief.group(1).count("<li>")
        if not 3 <= k <= 4:
            warn(f"{p.name}: The day in 60 seconds has {k} items; the task asks for 3–4.")
    kinds = re.findall(r'<p class="kicker ([a-z]+)">', s)
    for k in kinds:
        if k not in KICKERS:
            fail(f"{p.name}: unknown kicker class {k!r}; use one of {sorted(KICKERS)}.")
    if kinds.count("top") > 3:
        warn(f"{p.name}: {kinds.count('top')} Top story labels; the task asks for at most 3.")
    if "good" not in kinds:
        warn(f"{p.name}: no Good news story.")
    for href in re.findall(r'<p class="previously">.*?</p>', s, re.S):
        for a in re.findall(r'href="([^"]+)"', href):
            if a.startswith("../tracker.html#"):
                if a.split("#", 1)[1] not in THREADS:
                    fail(f"{p.name}: Previously links to tracker thread {a.split('#', 1)[1]!r}, which isn’t in threads.json.")
                continue
            if a.startswith("http"):
                continue
            if not (ROOT / "posts" / a).exists():
                fail(f"{p.name}: Previously link to {a}, which doesn’t exist.")
    wd = __import__("datetime").date.fromisoformat(p.stem).weekday()
    if wd == 6:
        quiz = re.search(r'<section class="topic" id="news-quiz">(.*?)</section>', s, re.S)
        if not quiz:
            warn(f"{p.name}: Sunday edition has no news quiz.")
        elif quiz.group(1).count('<li class="qa">') != 5:
            warn(f"{p.name}: the news quiz should have 5 questions.")
        if 'id="source-mix"' not in s:
            warn(f"{p.name}: Sunday edition has no Source mix.")


def check_size(pages):
    """Warn when a new or changed edition has fewer topic stories than the minimum."""
    for p in pages:
        s = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
        n = sum(body.count('<article class="story">')
                for sid, body in re.findall(r'<section class="topic"(?: id="([^"]*)")?>(.*?)</section>', s, re.S)
                if sid not in EXTRA_SECTIONS)
        otd = re.search(r'<section class="topic" id="on-this-day">(.*?)</section>', s, re.S)
        if not otd:
            warn(f"{p.name} has no On this day section.")
        elif otd.group(1).count('<article class="story">') != 3:
            warn(f"{p.name}: On this day should have exactly 3 items.")
        if d_of(p) >= "2026-11-01":
            check_features(p, s)
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
    return re.findall(r'<article class="story">\s*(?:<p class="kicker[^"]*">.*?</p>\s*)?<h3><a href="(https?://[^"]+)"', s, re.S)


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
    check_calendar()
    THREADS.update(thread_ids())
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
