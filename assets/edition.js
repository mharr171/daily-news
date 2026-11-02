/* Live Full Stack: shared behavior for editions from Nov 1, 2026 on.
   Adds reading time, a Listen button, the sticky topic bar shadow, the Today box
   (calendar, sun, air quality, earthquakes) and next-game cards in Sports.
   Everything here is optional: if a request fails, that part is simply left out. */
(function () {
  "use strict";
  const DATE = document.body.dataset.date;            // YYYY-MM-DD
  if (!/^\d{4}-\d{2}-\d{2}$/.test(DATE || "")) return;
  const LAT = 37.5985, LON = -122.3872;               // Millbrae
  const TZ = "America/Los_Angeles";
  const $ = s => document.querySelector(s);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const parse = d => { const [y, m, dd] = d.split("-").map(Number); return new Date(Date.UTC(y, m - 1, dd)); };
  const iso = dt => dt.toISOString().slice(0, 10);
  const addDays = (d, n) => iso(new Date(parse(d).getTime() + n * 86400000));
  const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const short = d => { const x = parse(d); return DOW[x.getUTCDay()] + ", " + MON[x.getUTCMonth()] + " " + x.getUTCDate(); };
  const fmtTime = dt => dt.toLocaleTimeString("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" });
  const head = document.querySelector(".edition-head");

  // ---------- Reading time and Listen ----------
  (function tools() {
    if (!head) return;
    const words = Array.from(document.querySelectorAll(".brief, .topic")).map(s => s.innerText || s.textContent)
      .concat(head.querySelector(".summary") ? [head.querySelector(".summary").textContent] : [])
      .join(" ").split(/\s+/).filter(Boolean).length;
    const mins = Math.max(1, Math.round(words / 230));
    const bar = el("p", "edition-tools");
    bar.append(el("span", null, mins + "-minute read"));
    if ("speechSynthesis" in window && "SpeechSynthesisUtterance" in window) {
      const play = el("button"); play.type = "button";
      const stop = el("button"); stop.type = "button"; stop.textContent = "Stop"; stop.hidden = true;
      const status = el("span", "listening"); status.setAttribute("aria-live", "polite");
      let state = "idle";
      const label = () => {
        play.innerHTML = state === "playing" ? "❚❚ Pause" : state === "paused" ? "▶ Resume" : "▶ Listen";
        play.setAttribute("aria-label", state === "playing" ? "Pause reading" : state === "paused" ? "Resume reading" : "Listen to this edition");
        stop.hidden = state === "idle";
        status.textContent = state === "playing" ? "Reading aloud…" : "";
      };
      function chunks() {
        const out = [document.querySelector(".edition-head h1").textContent, head.querySelector(".summary")?.textContent || ""];
        document.querySelectorAll(".brief li").forEach(li => out.push(li.textContent));
        document.querySelectorAll("section.topic").forEach(sec => {
          const h = sec.querySelector("h2"); if (h) out.push(h.textContent + ".");
          sec.querySelectorAll("article.story").forEach(st => {
            const t = st.querySelector("h3"); if (t) out.push(t.textContent + ".");
            const p = Array.from(st.querySelectorAll("p")).find(x => !x.className); if (p) out.push(p.textContent);
          });
        });
        return out.filter(s => s && s.trim());
      }
      function speakAll() {
        speechSynthesis.cancel();
        const list = chunks();
        list.forEach((text, i) => {
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "en-US"; u.rate = 1;
          if (i === list.length - 1) u.onend = () => { state = "idle"; label(); };
          speechSynthesis.speak(u);
        });
      }
      play.addEventListener("click", () => {
        if (state === "idle") { speakAll(); state = "playing"; }
        else if (state === "playing") { speechSynthesis.pause(); state = "paused"; }
        else { speechSynthesis.resume(); state = "playing"; }
        label();
      });
      stop.addEventListener("click", () => { speechSynthesis.cancel(); state = "idle"; label(); });
      window.addEventListener("pagehide", () => speechSynthesis.cancel());
      label();
      bar.append(play, stop, status);
    }
    const h1 = head.querySelector("h1");
    h1.after(bar);
  })();

  // ---------- Sticky topic bar shadow ----------
  (function sticky() {
    const nav = document.querySelector(".contents");
    if (!nav || !("IntersectionObserver" in window)) return;
    const mark = el("div"); mark.style.height = "1px"; nav.before(mark);
    new IntersectionObserver(([e]) => nav.classList.toggle("stuck", !e.isIntersecting)).observe(mark);
  })();

  // ---------- Sunrise and sunset (NOAA sunrise equation) ----------
  function sunTimes(d) {
    const rad = Math.PI / 180;
    const jd = parse(d).getTime() / 86400000 + 2440587.5 + 0.5;      // noon UTC
    const n = Math.ceil(jd - 2451545.0 + 0.0008);
    const js = n - LON / 360;
    const M = (357.5291 + 0.98560028 * js) % 360;
    const C = 1.9148 * Math.sin(M * rad) + 0.02 * Math.sin(2 * M * rad) + 0.0003 * Math.sin(3 * M * rad);
    const lam = (M + C + 180 + 102.9372) % 360;
    const jt = 2451545.0 + js + 0.0053 * Math.sin(M * rad) - 0.0069 * Math.sin(2 * lam * rad);
    const dec = Math.asin(Math.sin(lam * rad) * Math.sin(23.4397 * rad));
    const cosw = (Math.sin(-0.833 * rad) - Math.sin(LAT * rad) * Math.sin(dec)) / (Math.cos(LAT * rad) * Math.cos(dec));
    if (cosw < -1 || cosw > 1) return null;
    const w = Math.acos(cosw) / rad;
    const toDate = j => new Date((j - 2440587.5) * 86400000);
    return { rise: toDate(jt - w / 360), set: toDate(jt + w / 360), len: (2 * w / 360) * 24 };
  }

  const AQI = [[50, "Good"], [100, "Moderate"], [150, "Unhealthy for sensitive groups"], [200, "Unhealthy"], [300, "Very unhealthy"], [Infinity, "Hazardous"]];
  const aqiLabel = v => AQI.find(a => v <= a[0])[1];

  // ---------- Today box ----------
  const box = document.getElementById("today-box");
  const calPromise = fetch("../calendar.json", { cache: "no-store" }).then(r => r.ok ? r.json() : Promise.reject()).then(j => j.events || []).catch(() => []);

  if (box) {
    const alertLine = box.querySelector(".alert-line");
    box.replaceChildren();
    const h = el("h2", null, "Today in and around Millbrae");
    const calLink = el("a", null, "Full calendar ›"); calLink.href = "../calendar.html#" + DATE.slice(0, 7);
    h.append(calLink);
    box.append(h);
    if (alertLine) box.append(alertLine);
    const grid = el("div", "tb-grid"); box.append(grid);
    const colCal = el("div"), colSky = el("div"), colQuake = el("div");
    grid.append(colCal, colSky, colQuake);

    // Calendar
    colCal.append(el("h3", null, "On the calendar"));
    calPromise.then(evs => {
      const today = evs.filter(e => {
        const end = e.end || e.date;
        if (!(e.date <= DATE && end >= DATE)) return false;
        const span = (parse(end) - parse(e.date)) / 86400000 + 1;
        return span < 10;
      });
      if (!today.length) { colCal.append(el("p", "muted", "Nothing listed for today.")); return; }
      const ul = el("ul");
      today.slice(0, 8).forEach(e => {
        const li = el("li");
        if (e.time && !/^(All day|TBD|See website|)$/.test(e.time)) li.append(el("span", "t", e.time.split(/ [–-] /)[0]), " ");
        if (e.url) { const a = el("a", null, e.title); a.href = e.url; a.target = "_blank"; a.rel = "noopener"; li.append(a); }
        else li.append(e.title);
        li.append(" ", el("span", "k", "· " + (e.team ? "Game" : e.category)));
        ul.append(li);
      });
      colCal.append(ul);
      if (today.length > 8) colCal.append(el("p", "muted", "+" + (today.length - 8) + " more on the calendar"));
    });

    // Sun and air
    colSky.append(el("h3", null, "Sun and air"));
    const s = sunTimes(DATE);
    if (s) {
      const hrs = Math.floor(s.len), mins = Math.round((s.len - hrs) * 60);
      colSky.append(el("p", null, "Sunrise " + fmtTime(s.rise) + " · Sunset " + fmtTime(s.set)));
      colSky.append(el("p", "muted", hrs + " hr " + mins + " min of daylight"));
    }
    const aq = el("p", "muted", "Air quality: loading…"); colSky.append(aq);
    fetch("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=" + LAT + "&longitude=" + LON +
          "&hourly=us_aqi&timezone=" + encodeURIComponent(TZ) + "&start_date=" + DATE + "&end_date=" + DATE)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(j => {
        const v = (j.hourly && j.hourly.us_aqi || []).filter(x => x != null);
        if (!v.length) throw 0;
        const peak = Math.round(Math.max(...v));
        aq.className = "";
        aq.replaceChildren("Air quality: peak AQI " + peak + " ");
        aq.append(el("span", "k", "(" + aqiLabel(peak) + ")"));
        const a = el("a", null, "AirNow ›"); a.href = "https://www.airnow.gov/?city=Millbrae&state=CA&country=USA"; a.target = "_blank"; a.rel = "noopener";
        const p = el("p", "k"); p.append(a); colSky.append(p);
      })
      .catch(() => aq.remove());

    // Earthquakes, magnitude 3+, Bay Area, 24 hours ending about 6 AM on the edition's date
    colQuake.append(el("h3", null, "Bay Area earthquakes"));
    const qp = el("p", "muted", "Checking USGS…"); colQuake.append(qp);
    const usgs = el("p", "k"); const ua = el("a", null, "USGS map ›");
    ua.href = "https://earthquake.usgs.gov/earthquakes/map/"; ua.target = "_blank"; ua.rel = "noopener";
    usgs.append(ua); colQuake.append(usgs);

    const start = addDays(DATE, -1) + "T14:00:00Z", end = DATE + "T14:00:00Z";
    fetch("https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=3&orderby=magnitude" +
          "&minlatitude=36.8&maxlatitude=38.6&minlongitude=-123.3&maxlongitude=-121.2&starttime=" + start + "&endtime=" + end)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(j => {
        const f = j.features || [];
        if (!f.length) { qp.textContent = "None of magnitude 3 or more in the past 24 hours."; return; }
        qp.remove();
        const ul = el("ul");
        f.slice(0, 4).forEach(q => {
          const li = el("li");
          const a = el("a", null, "M" + q.properties.mag.toFixed(1) + " " + q.properties.place);
          a.href = q.properties.url; a.target = "_blank"; a.rel = "noopener";
          li.append(a, " ", el("span", "k", fmtTime(new Date(q.properties.time))));
          ul.append(li);
        });
        colQuake.insertBefore(ul, usgs);
      })
      .catch(() => { qp.textContent = "Earthquake data is unavailable right now."; });
  }

  // ---------- Next games, at the top of Sports ----------
  const sports = document.getElementById("sports");
  if (sports) {
    calPromise.then(evs => {
      const until = addDays(DATE, 10);
      const next = new Map();
      evs.filter(e => e.category === "Sports" && e.team && e.date >= DATE && e.date <= until && (e.date === DATE || !/Final:/.test(e.description || "")))
        .forEach(e => { if (!next.has(e.team)) next.set(e.team, e); });
      if (!next.size) return;
      const row = el("div", "next-games");
      row.append(el("span", null, "Next up:"));
      [...next.values()].sort((a, b) => a.date < b.date ? -1 : 1).forEach(e => {
        const a = el("a"); a.href = e.url || "../calendar.html"; a.target = "_blank"; a.rel = "noopener";
        const tv = /TV: ([^.]+)\./.exec(e.description || "");
        a.append(el("b", null, e.title.replace("Hawaii", "Hawai‘i")), " ",
                 el("i", null, (e.date === DATE ? "Today" : short(e.date)) + (e.time && e.time !== "TBD" ? ", " + e.time : "") + (tv ? " · " + tv[1] : "")));
        row.append(a);
      });
      const h2 = sports.querySelector("h2");
      h2.after(row);
    });
  }
})();
