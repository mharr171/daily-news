#!/usr/bin/env python3
"""Refresh the Streaming Now data from the TMDB API.

Run from the repository root:   python3 scripts/update_streaming.py

Needs a TMDB API key. It is read from the TMDB_API_KEY environment variable, or from
secrets/tmdb.env (a line like TMDB_API_KEY=...). The key is never printed or written to the data files.

Writes (only if everything succeeded):
  data/streaming/providers.json      services, with the TMDB provider ids found for each
  data/streaming/movies.json         compact list of movies, most popular first
  data/streaming/tv.json             compact list of TV shows, most popular first
  data/streaming/meta.json           update date, genres, counts, services TMDB doesn't list
  data/streaming/detail/*.json       overviews, in small shards loaded when a title is opened

Only TMDB image paths are stored, never images.

Options:  --pages N   pages of 20 titles per service and type (default 50, so up to 1,000)
          --dry-run   fetch and report, but don't write files
"""
import argparse, json, os, re, sys, time, datetime, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "streaming")
BASE = os.environ.get("TMDB_BASE_URL", "https://api.themoviedb.org/3")
SHARDS = 20
MONETIZATION = "flatrate|free|ads"


def load_key():
    key = os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        path = os.environ.get("TMDB_ENV_FILE") or os.path.join(ROOT, "secrets", "tmdb.env")
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                m = re.match(r"\s*TMDB_API_KEY\s*=\s*(.+?)\s*$", line)
                if m:
                    key = m.group(1).strip("\"'")
    if not key or key.startswith("paste_your"):
        sys.exit("No TMDB API key found. Put it in secrets/tmdb.env as TMDB_API_KEY=... (see secrets.example/tmdb.env).")
    return key


KEY = None


def redact(text):
    return text.replace(KEY, "***") if KEY else text


def api(path, **params):
    """GET one TMDB endpoint with retries. Returns parsed JSON. Never leaks the key in errors."""
    headers = {"Accept": "application/json", "User-Agent": "livefullstack-streaming-update"}
    if len(KEY) > 40:                      # a v4 read access token
        headers["Authorization"] = "Bearer " + KEY
    else:                                  # a v3 api key
        params["api_key"] = KEY
    url = BASE + path + "?" + urllib.parse.urlencode(params, safe="|")
    last = ""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 401:
                sys.exit("TMDB rejected the API key (401). Check secrets/tmdb.env.")
            if e.code == 404:
                return {}
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "2")) + 1)
                continue
        except Exception as e:             # network trouble
            last = redact(type(e).__name__ + ": " + str(e))
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TMDB request failed for {path} ({last})")


def norm(name):
    s = name.lower().replace("+", " plus ").replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def year_of(date):
    return int(date[:4]) if date and date[:4].isdigit() else 0


def main():
    global KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    KEY = load_key()

    prov = json.load(open(os.path.join(DATA, "providers.json"), encoding="utf-8"))
    services = prov["services"]
    country = prov.get("country", "US")

    # 1. Find each service's TMDB provider ids, separately for movies and TV.
    ids = {"movie": {}, "tv": {}}
    for kind in ("movie", "tv"):
        listing = api(f"/watch/providers/{kind}", watch_region=country).get("results", [])
        by_name = {}
        for p in listing:
            by_name.setdefault(norm(p["provider_name"]), []).append(p["provider_id"])
        for s in services:
            found = []
            for alias in s["aliases"]:
                found += by_name.get(norm(alias), [])
            ids[kind][s["key"]] = sorted(set(found))
        s_missing = [s["name"] for s in services if not ids[kind][s["key"]]]
        print(f"{kind}: matched {len(services) - len(s_missing)} of {len(services)} services")
        if s_missing:
            print("  not listed by TMDB for", kind + ":", ", ".join(s_missing))
        # Help fix aliases: show provider names that look similar to unmatched services.
        for s in services:
            if not ids[kind][s["key"]]:
                word = norm(s["name"]).split()[0]
                near = sorted({p["provider_name"] for p in listing if word in norm(p["provider_name"])})
                if near:
                    print(f"    {s['name']}: maybe one of {near}")
    for s in services:
        s["tmdb_ids"] = {k: ids[k][s["key"]] for k in ("movie", "tv")}

    # 2. Genre names.
    genres = {}
    for kind in ("movie", "tv"):
        genres[kind] = {str(g["id"]): g["name"] for g in api(f"/genre/{kind}/list", language="en-US").get("genres", [])}

    # 3. Titles per service. One discover query per service and type, most popular first.
    def pull(job):
        kind, s = job
        pid = ids[kind][s["key"]]
        out = []
        if not pid:
            return kind, s["key"], out
        for page in range(1, args.pages + 1):
            r = api(f"/discover/{kind}", watch_region=country, with_watch_providers="|".join(map(str, pid)),
                    with_watch_monetization_types=MONETIZATION, sort_by="popularity.desc",
                    include_adult="false", language="en-US", page=page)
            out += r.get("results", [])
            if page >= r.get("total_pages", 0):
                break
        return kind, s["key"], out

    jobs = [(k, s) for k in ("movie", "tv") for s in services]
    items = {"movie": {}, "tv": {}}
    counts = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for kind, key, results in pool.map(pull, jobs):
            counts[f"{kind}:{key}"] = len(results)
            for r in results:
                rec = items[kind].setdefault(r["id"], {
                    "i": r["id"],
                    "t": r.get("title") or r.get("name") or "",
                    "y": year_of(r.get("release_date") or r.get("first_air_date")),
                    "g": r.get("genre_ids", []),
                    "r": round(r.get("vote_average") or 0, 1),
                    "n": r.get("vote_count") or 0,
                    "p": (r.get("poster_path") or "").lstrip("/") or None,
                    "pop": r.get("popularity") or 0,
                    "o": (r.get("overview") or "").strip(),
                    "s": [],
                })
                if key not in rec["s"]:
                    rec["s"].append(key)
            print(f"  {kind:5} {key:12} {len(results):5} titles")

    # 4. Safety check: don't replace good data with a broken pull.
    total_new = sum(len(v) for v in items.values())
    old_meta = os.path.join(DATA, "meta.json")
    if os.path.exists(old_meta):
        old = json.load(open(old_meta, encoding="utf-8")).get("counts", {})
        old_total = old.get("movie", 0) + old.get("tv", 0)
        if old_total and total_new < old_total * 0.6:
            sys.exit(f"Only {total_new} titles came back, versus {old_total} last time. Not writing anything.")
    if total_new == 0:
        sys.exit("No titles came back. Not writing anything.")

    # 5. Write the files.
    if args.dry_run:
        print(f"Dry run: {len(items['movie'])} movies and {len(items['tv'])} TV shows. Nothing written.")
        return
    os.makedirs(os.path.join(DATA, "detail"), exist_ok=True)
    for f in os.listdir(os.path.join(DATA, "detail")):
        if f.endswith(".json"):
            os.remove(os.path.join(DATA, "detail", f))
    for kind, fname in (("movie", "movies.json"), ("tv", "tv.json")):
        ordered = sorted(items[kind].values(), key=lambda x: -x["pop"])
        shards = {}
        compact = []
        for rec in ordered:
            shards.setdefault(rec["i"] % SHARDS, {})[str(rec["i"])] = rec["o"][:600]
            compact.append({k: rec[k] for k in ("i", "t", "y", "g", "r", "p", "s")})
        write(os.path.join(DATA, fname), {"items": compact})
        for n, body in shards.items():
            write(os.path.join(DATA, "detail", f"{kind}-{n}.json"), body)
    missing = sorted({s["key"] for s in services if not any(ids[k][s["key"]] for k in ids)})
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).strftime("%Y-%m-%d")
    write(os.path.join(DATA, "meta.json"), {
        "updated": today, "country": country, "shards": SHARDS, "genres": genres,
        "counts": {"movie": len(items["movie"]), "tv": len(items["tv"])},
        "per_service": counts, "not_found": missing})
    write(os.path.join(DATA, "providers.json"), prov, pretty=True)
    print(f"Done: {len(items['movie'])} movies and {len(items['tv'])} TV shows. Services TMDB doesn't list at all: {missing or 'none'}")


def write(path, obj, pretty=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


if __name__ == "__main__":
    main()
