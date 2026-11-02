/* Live Full Stack: reading options (text size and light/dark theme), shared by every page.
   Load it in <head> without defer so the saved choice applies before the page paints.
   Choices are saved in this browser only. */
(function () {
  var root = document.documentElement;
  var KEY_T = "lfs-theme", KEY_S = "lfs-text";
  var SIZES = [0.9, 1, 1.12, 1.25, 1.4];
  function get(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // Colors for a forced theme. Covers the variables every page uses; screen only, so print stays black on white.
  var LIGHT = "--paper:#E9E6DD;--ink:#222120;--muted:#5E5A52;--rule:#222120;--soft-rule:#B9B3A6;--spot:#A8231B;" +
    "--band:#A8231B;--on-band:#F6EFE6;--card:#F4F2EC;--c-obs:#A8231B;--c-local:#2F6B3A;--c-civic:#8A5A00;" +
    "--c-sports:#1F4E8C;--c-dates:#1F6E6E;--c-sky:#6A3D8F;color-scheme:light;";
  var DARK = "--paper:#1B1A18;--ink:#E7E2D6;--muted:#A59F92;--rule:#E7E2D6;--soft-rule:#4A463F;--spot:#E2675C;" +
    "--band:#8E2019;--on-band:#F6EFE6;--card:#26241F;--c-obs:#E2675C;--c-local:#7DBE86;--c-civic:#D9A441;" +
    "--c-sports:#82A9E0;--c-dates:#6CC4C4;--c-sky:#B795D6;color-scheme:dark;";
  var css = "@media screen{:root[data-theme=light]{" + LIGHT + "}:root[data-theme=dark]{" + DARK + "}" +
    ":root[data-text]{font-size:calc(100% * var(--text-scale,1))}" +
    ":root[data-text] body{font-size:calc(18px * var(--text-scale,1))}}" +
    ".rd-btn{position:fixed;right:max(1rem,env(safe-area-inset-right));bottom:max(1rem,env(safe-area-inset-bottom));z-index:50;" +
    "font:700 1rem/1 var(--serif,Georgia,serif);width:2.6rem;height:2.6rem;border-radius:50%;border:2px solid var(--ink);" +
    "background:var(--paper);color:var(--ink);cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.18)}" +
    ".rd-btn:hover{background:var(--ink);color:var(--paper)}" +
    ".rd-panel{position:fixed;right:max(1rem,env(safe-area-inset-right));bottom:calc(max(1rem,env(safe-area-inset-bottom)) + 3.1rem);" +
    "z-index:50;background:var(--paper);color:var(--ink);border:1px solid var(--ink);box-shadow:0 8px 24px rgba(0,0,0,.2);" +
    "padding:.75rem .9rem;font:15px/1.4 var(--serif,Georgia,serif);width:15.5rem}" +
    ".rd-panel p{margin:0 0 .35rem;font-style:italic;color:var(--muted);font-size:13px}" +
    ".rd-row{display:flex;gap:.3rem;margin-bottom:.7rem}.rd-row:last-child{margin-bottom:0}" +
    ".rd-row button{flex:1;font:inherit;font-size:14px;background:transparent;color:var(--ink);border:1px solid var(--soft-rule,#999);" +
    "padding:.25rem .3rem;cursor:pointer;border-radius:0}" +
    ".rd-row button[aria-pressed=true]{background:var(--ink);color:var(--paper);border-color:var(--ink)}" +
    ".rd-btn:focus-visible,.rd-row button:focus-visible{outline:2px solid var(--spot);outline-offset:2px}" +
    "@media print{.rd-btn,.rd-panel{display:none!important}}";
  var style = document.createElement("style");
  style.textContent = css;
  (document.head || root).appendChild(style);

  function applyTheme(t) {
    if (t === "light" || t === "dark") root.setAttribute("data-theme", t); else root.removeAttribute("data-theme");
  }
  function applySize(i) {
    i = Math.max(0, Math.min(SIZES.length - 1, i));
    if (SIZES[i] === 1) { root.removeAttribute("data-text"); root.style.removeProperty("--text-scale"); }
    else { root.setAttribute("data-text", ""); root.style.setProperty("--text-scale", SIZES[i]); }
    return i;
  }
  var theme = get(KEY_T, "auto");
  var size = SIZES.indexOf(parseFloat(get(KEY_S, "1")));
  if (size < 0) size = 1;
  applyTheme(theme);
  applySize(size);

  function build() {
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "rd-btn"; btn.textContent = "Aa";
    btn.setAttribute("aria-label", "Reading options: text size and theme");
    btn.setAttribute("aria-expanded", "false");
    var panel = document.createElement("div");
    panel.className = "rd-panel"; panel.hidden = true; panel.id = "rd-panel";
    panel.setAttribute("role", "dialog"); panel.setAttribute("aria-label", "Reading options");
    btn.setAttribute("aria-controls", "rd-panel");
    panel.innerHTML =
      '<p>Text size</p><div class="rd-row" id="rd-size">' +
      '<button type="button" data-d="-1" aria-label="Smaller text">A−</button>' +
      '<button type="button" data-d="0" aria-label="Default text size">A</button>' +
      '<button type="button" data-d="1" aria-label="Larger text">A+</button></div>' +
      '<p>Theme</p><div class="rd-row" id="rd-theme">' +
      '<button type="button" data-t="auto">Auto</button><button type="button" data-t="light">Light</button>' +
      '<button type="button" data-t="dark">Dark</button></div>';
    function sync() {
      panel.querySelectorAll("#rd-theme button").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.t === theme ? "true" : "false"); });
      panel.querySelector('[data-d="0"]').setAttribute("aria-pressed", SIZES[size] === 1 ? "true" : "false");
      panel.querySelector('[data-d="-1"]').disabled = size === 0;
      panel.querySelector('[data-d="1"]').disabled = size === SIZES.length - 1;
    }
    panel.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      if (b.dataset.t) { theme = b.dataset.t; applyTheme(theme); set(KEY_T, theme); }
      if (b.dataset.d) { var d = +b.dataset.d; size = applySize(d === 0 ? 1 : size + d); set(KEY_S, String(SIZES[size])); }
      sync();
    });
    function toggle(open) {
      panel.hidden = !open; btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) { sync(); var f = panel.querySelector("button:not(:disabled)"); if (f) f.focus(); }
    }
    btn.addEventListener("click", function () { toggle(panel.hidden); });
    document.addEventListener("click", function (e) { if (!panel.hidden && !panel.contains(e.target) && e.target !== btn) toggle(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) { toggle(false); btn.focus(); } });
    document.body.appendChild(panel);
    document.body.appendChild(btn);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
})();
