// Live Full Stack service worker.
// Pages and data: network first, so readers always get the newest edition; cached copy only when offline.
// Fonts, icons, CSS and JS: cached copy first, refreshed in the background.
// Bump VERSION to clear old caches.
const VERSION = "v1";
const CACHE = "lfs-" + VERSION;
const PRECACHE = ["/", "/index.html", "/posts.json", "/assets/edition.css", "/assets/edition.js",
  "/assets/reader.js", "/assets/pwa.js", "/fonts/fonts.css", "/fonts/anton-latin-400-normal.woff2",
  "/fonts/old-standard-tt-latin-400-normal.woff2", "/fonts/old-standard-tt-latin-400-italic.woff2",
  "/fonts/old-standard-tt-latin-700-normal.woff2", "/favicon-32.png", "/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.allSettled(PRECACHE.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("lfs-") && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const isStatic = u => /\.(css|js|woff2?|png|ico|svg)$/.test(u.pathname) && !u.pathname.endsWith("/sw.js");

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (isStatic(url)) {
    e.respondWith(caches.open(CACHE).then(async c => {
      const hit = await c.match(req);
      const net = fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }
  e.respondWith(fetch(req).then(r => {
    if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
    return r;
  }).catch(() => caches.match(req).then(h => h || caches.match("/index.html"))));
});
