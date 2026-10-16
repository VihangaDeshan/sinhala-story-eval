/* ─────────────────────────────────────────────────────────────────────
   SSEF — theme.js
   Light / dark theme. Loaded in <head> so the saved theme is applied before
   the page paints. With no saved choice the page follows the system setting.
   The choice is kept in this browser only (localStorage), like the language.
───────────────────────────────────────────────────────────────────── */
(function () {
  "use strict";
  var KEY = "ssef-theme";
  var root = document.documentElement;

  try {
    var saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) { /* storage blocked */ }

  function isDark() {
    var t = root.getAttribute("data-theme");
    if (t) return t === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var sync = function () { btn.setAttribute("aria-pressed", isDark() ? "true" : "false"); };
    sync();
    btn.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem(KEY, next); } catch (e) { /* storage blocked */ }
      sync();
    });
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) mq.addEventListener("change", sync);
    }
  });
})();
