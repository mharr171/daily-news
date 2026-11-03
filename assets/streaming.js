// Streaming Now: filters the saved catalog in data/streaming/ in the browser. No API calls, no key.
(function () {
  "use strict";
  var IMG = "https://image.tmdb.org/t/p/";
  var BATCH = 60;
  var $ = function (id) { return document.getElementById(id); };
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  var state = {
    kind: store.get("lfs-stream-kind", "movie"),
    free: store.get("lfs-stream-free", false),
    sort: store.get("lfs-stream-sort", "pop"),
    off: new Set(store.get("lfs-stream-off", [])),   // services turned off; new services default to on
    genre: 0, q: "", shown: 0, list: []
  };
  var providers = null, meta = null, featured = null, picks = null, svc = {}, data = {}, byId = {}, shardCache = {};

  function norm(s) { return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim(); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function json(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); }

  // ---------- services ----------
  function groupOf(s) { return providers.groups.filter(function (g) { return g.id === s.group; })[0]; }
  function isFree(key) { var s = svc[key]; return !!(s && groupOf(s).free); }
  function freeLabel(key) { var g = groupOf(svc[key]); return g.label || "Free"; }
  function enabled(key) { return svc[key] && !state.off.has(key); }
  function availableKeys() {
    var seen = {};
    ["movie", "tv"].forEach(function (k) { providers.services.forEach(function (s) { if (s.tmdb_ids && s.tmdb_ids[k] && s.tmdb_ids[k].length) seen[s.key] = 1; }); });
    return seen;
  }

  function buildSettings() {
    var wrap = $("service-list"); wrap.textContent = "";
    var avail = availableKeys();
    providers.groups.forEach(function (g) {
      var list = providers.services.filter(function (s) { return s.group === g.id; });
      var box = el("div", "svc-group"), h = el("h3", null, g.name), tools = el("span");
      var on = el("button", null, "All on"), off = el("button", null, "All off");
      on.type = off.type = "button";
      on.onclick = function () { list.forEach(function (s) { state.off.delete(s.key); }); saveOff(); buildSettings(); refresh(); };
      off.onclick = function () { list.forEach(function (s) { state.off.add(s.key); }); saveOff(); buildSettings(); refresh(); };
      tools.append(on, off); h.append(tools); box.append(h);
      var grid = el("div", "svc-list");
      list.forEach(function (s) {
        var lab = el("label"), cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = !state.off.has(s.key);
        cb.onchange = function () { if (cb.checked) state.off.delete(s.key); else state.off.add(s.key); saveOff(); refresh(); };
        lab.append(cb, document.createTextNode(" " + s.name));
        if (s.tmdb_ids && !avail[s.key]) lab.append(el("span", "na", " (not listed)"));
        grid.append(lab);
      });
      box.append(grid); wrap.append(box);
    });
  }
  function saveOff() { store.set("lfs-stream-off", Array.from(state.off)); }

  // ---------- data ----------
  function load(kind) {
    if (data[kind]) return Promise.resolve(data[kind]);
    return json("data/streaming/" + (kind === "movie" ? "movies" : "tv") + ".json").then(function (d) {
      byId[kind] = {};
      d.items.forEach(function (it) { it._n = norm(it.t); it._k = kind; byId[kind][it.i] = it; });
      data[kind] = d.items; return d.items;
    });
  }

  // ---------- browse ----------
  function matches(it) {
    var any = false, free = false;
    for (var i = 0; i < it.s.length; i++) { if (enabled(it.s[i])) { any = true; if (isFree(it.s[i])) free = true; } }
    if (!any) return false;
    if (state.free && !free) return false;
    if (state.genre && it.g.indexOf(state.genre) < 0) return false;
    if (state.q) { for (var t = 0; t < state.words.length; t++) { if (it._n.indexOf(state.words[t]) < 0) return false; } }
    return true;
  }
  function sorter() {
    if (state.sort === "rating") return function (a, b) { return b.r - a.r; };
    if (state.sort === "new") return function (a, b) { return b.y - a.y; };
    if (state.sort === "az") return function (a, b) { return a._n < b._n ? -1 : 1; };
    return null;
  }

  function refresh() {
    var kind = state.kind;
    if (!data[kind]) return;
    state.words = norm(state.q).split(" ").filter(Boolean);
    var base = data[kind].filter(function (it) { return enabledAny(it); });
    var s = sorter();
    state.list = data[kind].filter(matches);
    if (s) state.list.sort(s);
    renderGenres(base);
    $("grid").textContent = ""; state.shown = 0;
    var n = state.list.length;
    $("tally").innerHTML = "";
    var strong = el("strong", null, n.toLocaleString()); $("tally").append(strong, document.createTextNode((kind === "movie" ? " movies" : " TV shows") + " on your services" + (meta && meta.updated ? " · updated " + meta.updated : "")));
    $("notice").hidden = n > 0;
    if (!n) $("notice").textContent = state.off.size === providers.services.length ? "All services are off. Turn some on under My services." : "Nothing matches. Try another genre, a different search, or turn on more services.";
    more();
    renderFeatured();
  }
  function enabledAny(it) { for (var i = 0; i < it.s.length; i++) if (enabled(it.s[i])) return true; return false; }

  function renderGenres(base) {
    var names = (meta && meta.genres && meta.genres[state.kind]) || {};
    var count = {};
    base.forEach(function (it) { it.g.forEach(function (g) { count[g] = (count[g] || 0) + 1; }); });
    var box = $("genres"); box.textContent = "";
    function chip(id, label) {
      var b = el("button", null, label); b.type = "button"; b.setAttribute("aria-pressed", String(state.genre === id));
      b.onclick = function () { state.genre = id; refresh(); }; box.append(b);
    }
    chip(0, "All genres");
    Object.keys(count).filter(function (g) { return names[g]; }).sort(function (a, b) { return names[a] < names[b] ? -1 : 1; })
      .forEach(function (g) { chip(+g, names[g]); });
    if (state.genre && !count[state.genre]) state.genre = 0;
  }

  function more() {
    var end = Math.min(state.shown + BATCH, state.list.length), g = $("grid");
    for (var i = state.shown; i < end; i++) g.append(card(state.list[i]));
    state.shown = end;
  }

  function serviceLine(it) {
    var keys = it.s.filter(enabled);
    keys.sort(function (a, b) { return (isFree(b) ? 1 : 0) - (isFree(a) ? 1 : 0); });
    var names = keys.slice(0, 2).map(function (k) { return svc[k].name; }).join(", ");
    return names + (keys.length > 2 ? " +" + (keys.length - 2) : "");
  }
  function anyFree(it) { return it.s.some(function (k) { return enabled(k) && isFree(k); }); }

  function posterBox(it, size, srcset, sizes) {
    var box = el("div", "poster"), ph = el("div", "ph", it.t);
    box.append(ph);
    if (it.p) {
      var img = document.createElement("img");
      img.loading = "lazy"; img.decoding = "async"; img.alt = "Poster for " + it.t;
      img.src = IMG + size + "/" + it.p;
      if (srcset) { img.srcset = srcset.map(function (w) { return IMG + "w" + w + "/" + it.p + " " + w + "w"; }).join(", "); img.sizes = sizes; }
      img.onload = function () { img.classList.add("ok"); ph.hidden = true; };
      img.onerror = function () { img.remove(); };
      box.append(img);
    }
    return box;
  }

  function card(it, extra) {
    var b = el("button", "card"); b.type = "button";
    var p = posterBox(it, "w185", [185, 342], "(max-width: 40rem) 40vw, 170px");
    if (anyFree(it)) p.append(el("span", "badge", "Free"));
    b.append(p, el("span", "t", it.t + (it.y ? " (" + it.y + ")" : "")), el("span", "s", serviceLine(it)));
    if (extra) b.append(el("span", "x", extra));
    b.onclick = function () { openDetail(it); };
    return b;
  }


  // ---------- featured: new releases and this week's picks ----------
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function shortDate(d) { var p = (d || "").split("-"); return p.length === 3 ? MONTHS[+p[1] - 1] + " " + (+p[2]) : ""; }
  function usable(it) { return it && enabledAny(it) && (!state.free || anyFree(it)); }

  function renderFeatured() {
    var box = $("featured");
    if (!featured && !picks) { box.hidden = true; return; }
    if (state.q || state.genre) { box.hidden = true; return; }
    Promise.all([load("movie"), load("tv")]).then(function () {
      var kind = state.kind, shown = false;

      var pk = [];
      if (picks && picks.picks) {
        picks.picks.forEach(function (p) {
          var it = byId[p.k] && byId[p.k][p.i];
          if (usable(it)) pk.push([it, p.b || ""]);
        });
      }
      pk = pk.slice(0, 8);
      var sp = $("strip-picks"); sp.textContent = "";
      pk.forEach(function (x) { sp.append(card(x[0], x[1])); });
      $("row-picks").hidden = !pk.length;
      $("picks-note").textContent = picks && picks.week_of ? "Chosen by Claude for the week of " + shortDate(picks.week_of) + ", from titles on your services." : "";
      shown = shown || pk.length > 0;

      var nw = [];
      if (featured && featured.new && featured.new[kind]) {
        featured.new[kind].forEach(function (f) {
          var it = byId[kind][f.i];
          if (usable(it)) nw.push([it, f.d]);
        });
      }
      nw = nw.slice(0, 24);
      var sn = $("strip-new"); sn.textContent = "";
      nw.forEach(function (x) { sn.append(card(x[0], "Out " + shortDate(x[1]))); });
      $("new-h").textContent = kind === "movie" ? "New movies" : "New TV shows";
      $("row-new").hidden = !nw.length;
      shown = shown || nw.length > 0;

      box.hidden = !shown;
    });
  }

  // ---------- detail ----------
  function shard(kind, id) {
    var n = id % meta.shards, key = kind + "-" + n;
    if (!shardCache[key]) shardCache[key] = json("data/streaming/detail/" + key + ".json").catch(function () { return {}; });
    return shardCache[key];
  }
  function openDetail(it) {
    var kind = it._k || state.kind;
    $("detail-h").textContent = it.t;
    var g = (meta.genres[kind] || {}), names = it.g.map(function (x) { return g[x]; }).filter(Boolean).join(", ");
    $("detail-meta").textContent = [it.y || "", kind === "movie" ? "Movie" : "TV show", names, it.r ? "★ " + it.r.toFixed(1) + " / 10" : ""].filter(Boolean).join(" · ");
    var pbox = $("detail-poster"); pbox.textContent = ""; pbox.append(posterBox(it, "w500", [342, 500, 780], "(max-width: 36rem) 14rem, 15rem"));
    $("detail-overview").textContent = "";
    shard(kind, it.i).then(function (d) { if ($("detail-h").textContent === it.t) $("detail-overview").textContent = d[String(it.i)] || "No description available."; });
    var ul = $("detail-where"); ul.textContent = "";
    var keys = it.s.slice().sort(function (a, b) { return (enabled(b) ? 1 : 0) - (enabled(a) ? 1 : 0) || (isFree(b) ? 1 : 0) - (isFree(a) ? 1 : 0); });
    keys.forEach(function (k) {
      if (!svc[k]) return;
      var li = el("li"); li.append(el("strong", null, svc[k].name));
      li.append(isFree(k) ? el("span", "tag-free", freeLabel(k)) : el("span", "tag-paid", "Subscription"));
      if (!enabled(k)) li.append(el("span", "tag-paid", "(turned off in My services)"));
      ul.append(li);
    });
    $("detail-link").href = "https://www.themoviedb.org/" + kind + "/" + it.i + "/watch?locale=US";
    $("detail").showModal();
  }

  // ---------- wiring ----------
  function setKind(kind) {
    state.kind = kind; state.genre = 0; store.set("lfs-stream-kind", kind);
    ["movie", "tv"].forEach(function (k) { $("tab-" + k).setAttribute("aria-selected", String(k === kind)); });
    $("notice").hidden = false; $("notice").textContent = "Loading the catalog…";
    load(kind).then(refresh).catch(function () { $("notice").textContent = "The streaming catalog hasn’t been loaded yet. Check back after the next daily update."; $("tally").textContent = ""; });
  }

  function init() {
    $("tab-movie").onclick = function () { setKind("movie"); };
    $("tab-tv").onclick = function () { setKind("tv"); };
    var t; $("q").oninput = function () { clearTimeout(t); t = setTimeout(function () { state.q = $("q").value; refresh(); }, 120); };
    $("free-only").checked = state.free; $("free-only").onchange = function () { state.free = this.checked; store.set("lfs-stream-free", state.free); refresh(); };
    $("sort").value = state.sort; $("sort").onchange = function () { state.sort = this.value; store.set("lfs-stream-sort", state.sort); refresh(); };
    $("open-settings").onclick = function () { buildSettings(); $("settings").showModal(); };
    $("reset-services").onclick = function () { state.off.clear(); saveOff(); buildSettings(); refresh(); };
    ["settings", "detail"].forEach(function (id) { $(id).addEventListener("click", function (e) { if (e.target === this) this.close(); }); });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) { if (es[0].isIntersecting && state.shown < state.list.length) more(); }, { rootMargin: "800px" }).observe($("sentinel"));
    }
    Promise.all([json("data/streaming/providers.json"), json("data/streaming/meta.json")]).then(function (r) {
      providers = r[0]; meta = r[1];
      providers.services.forEach(function (s) { svc[s.key] = s; });
      json("data/streaming/featured.json").then(function (f) { featured = f; renderFeatured(); }).catch(function () {});
      json("data/streaming/picks.json").then(function (p) { picks = p; renderFeatured(); }).catch(function () {});
      setKind(state.kind);
    }).catch(function () {
      $("notice").textContent = "The streaming catalog hasn’t been loaded yet. Check back after the next daily update.";
    });
  }
  init();
})();
