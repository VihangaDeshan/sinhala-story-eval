/* ─────────────────────────────────────────────────────────────────────
   SSEF — app.js
   All UI logic. No frameworks. No CDN dependencies.
   Interface strings live in static/i18n/{en,si}.json; number formatting and
   card markup live in view.js.
───────────────────────────────────────────────────────────────────── */

"use strict";

// ── Human reference values injected by Jinja ───────────────────────────
// window.HUMAN_REFERENCE = { pppl_overall: {mean, sd}, darc: {...}, ... }
// window.FLUENCY_AVAILABLE = true | false

// ── Language ───────────────────────────────────────────────────────────
const LANG_KEY = "ssef-lang";
const I18N = { en: {}, si: {} };
let _lang = "en";

// Missing or empty Sinhala strings fall back to English, then to the key.
function tr(key, params) {
  const s = (I18N[_lang] && I18N[_lang][key]) || I18N.en[key] || key;
  return SSEFView.fill(s, params || {});
}

function readSavedLang() {
  try {
    const v = localStorage.getItem(LANG_KEY);
    return v === "si" ? "si" : "en";
  } catch (e) { return "en"; }
}

function saveLang(l) {
  try { localStorage.setItem(LANG_KEY, l); } catch (e) { /* storage blocked */ }
}

async function loadI18n() {
  const get = (l) => fetch(`/static/i18n/${l}.json`)
    .then((r) => (r.ok ? r.json() : {}))
    .catch(() => ({}));
  const [en, si] = await Promise.all([get("en"), get("si")]);
  I18N.en = en;
  I18N.si = si;
}

function setLang(l) {
  _lang = l === "si" ? "si" : "en";
  saveLang(_lang);
  applyLang();
}

// ── Polling / result state ─────────────────────────────────────────────
let _pollInterval = null;
let _currentJobId = null;
let _storedText   = "";   // kept so the fluency path can call /api/highlight
let _pollSecs     = 0;
let _valState     = null; // what the validation line currently shows
let _last         = null; // last rendered {result, text}, re-rendered on language change
let _defaultOpt   = null;

// ── DOM refs ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function applyLang() {
  document.documentElement.lang = _lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    if (el.dataset.i18n === "login.signedin" && el.dataset.user) {
      el.textContent = tr("login.signedin", { u: el.dataset.user });
    } else {
      el.textContent = tr(el.dataset.i18n);
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", tr(el.dataset.i18nPlaceholder));
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", tr(el.dataset.i18nAria));
  });
  document.querySelectorAll(".lang-btn").forEach((b) => {
    const on = b.dataset.lang === _lang;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on ? "true" : "false");
  });

  if (_defaultOpt) _defaultOpt.textContent = tr("input.sample");
  setPollingText();
  renderValidation();
  if (_last) renderResults(_last.result, _last.text, false);
}

// ── Initialization ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Populate sample story dropdown
  const sel   = $("sample-select");
  const stories = window.STORIES || [];
  if (stories.length > 0 && sel) {
    // Build an index by the server-supplied `idx` so duplicate id+model
    // combinations (e.g. N04_Avurudu exists for gemini, gpt, deepseek) each
    // get a unique entry and load the correct text.
    const storyByIdx = {};
    stories.forEach((s) => { storyByIdx[s.idx] = s; });

    stories.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.idx;
      opt.textContent = `${s.id} · ${s.model}`;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      const idx = sel.value;
      if (idx !== "" && storyByIdx[idx]) {
        $("story-textarea").value = storyByIdx[idx].text;
      }
      sel.value = "";   // reset so same item can be reselected
    });
    // default option text
    const def = document.createElement("option");
    def.value = "";
    def.textContent = tr("input.sample");
    sel.insertBefore(def, sel.firstChild);
    sel.value = "";
    _defaultOpt = def;
  } else if (sel) {
    sel.parentElement.classList.add("hidden");
  }

  // Fluency checkbox
  const fluencyChk = $("fluency-checkbox");
  if (!window.FLUENCY_AVAILABLE) {
    fluencyChk.disabled = true;
    fluencyChk.parentElement.classList.add("disabled");
    $("fluency-unavailable-note").classList.remove("hidden");
  }

  // Non-Sinhala demo button (demo input is deliberately English)
  $("btn-non-sinhala").addEventListener("click", () => {
    $("story-textarea").value = "The quick brown fox jumps over the lazy dog.";
  });

  // Submit
  $("btn-submit").addEventListener("click", submitEvaluate);

  // Language toggle
  document.querySelectorAll(".lang-btn").forEach((b) => {
    b.addEventListener("click", () => setLang(b.dataset.lang));
  });

  // The page is server-rendered in English; load the string files and
  // switch to the saved language once they arrive.
  _lang = readSavedLang();
  loadI18n().then(applyLang);
});

// ── Submit handler ──────────────────────────────────────────────────────
// Server errors carry a `code` for the app's own messages; the library's
// validation messages have none and are shown exactly as returned.
function errorFrom(data) {
  if (data && data.code) showValidationKey("err." + data.code, null, false);
  else if (data && data.error) showValidationRaw(data.error, false);
  else showValidationKey("err.generic", null, false);
}

async function submitEvaluate() {
  const text        = $("story-textarea").value;
  const wantFluency = $("fluency-checkbox").checked;

  clearResults();

  if (!text.trim()) {
    showValidationKey("err.empty", null, false);
    return;
  }
  if (text.length > 30000) {
    showValidationKey("err.too_long", null, false);
    return;
  }

  $("btn-submit").disabled = true;
  _storedText = text;

  try {
    const resp = await fetch("/api/evaluate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ text, fluency: wantFluency }),
    });

    if (resp.status === 202) {
      // Background fluency job
      const data = await resp.json();
      _currentJobId = data.job_id;
      showPolling();
      startPolling();
      return;   // btn stays disabled while polling
    }

    const data = await resp.json();
    $("btn-submit").disabled = false;

    if (!resp.ok) {
      errorFrom(data);
      return;
    }

    renderResults(data, text, true);
  } catch (err) {
    $("btn-submit").disabled = false;
    showValidationKey("err.generic", null, false);
  }
}

// ── Polling ─────────────────────────────────────────────────────────────
function startPolling() {
  let elapsed = 0;
  _pollInterval = setInterval(async () => {
    elapsed += 2;
    try {
      const resp = await fetch(`/api/job/${_currentJobId}`);
      const data = await resp.json();
      updatePollingCounter(data.elapsed ?? elapsed);

      if (data.status === "done") {
        stopPolling();
        $("btn-submit").disabled = false;
        // fetch highlights
        const hlResp = await fetch("/api/highlight", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ text: _storedText }),
        });
        const hlData = await hlResp.json();
        const result = data.result;
        result.segments = hlData.segments || [];
        renderResults(result, _storedText, true);
      } else if (data.status === "error") {
        stopPolling();
        $("btn-submit").disabled = false;
        hidePolling();
        errorFrom(data);
      }
    } catch (err) {
      // network hiccup — keep polling
    }
  }, 2000);
}

function stopPolling() {
  if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
  hidePolling();
}

function showPolling() {
  _pollSecs = 0;
  setPollingText();
  $("polling-banner").classList.remove("hidden");
}

function hidePolling() {
  $("polling-banner").classList.add("hidden");
}

function updatePollingCounter(secs) {
  _pollSecs = secs;
  setPollingText();
}

function setPollingText() {
  $("polling-text").textContent = tr("msg.running", { s: _pollSecs });
}

// ── Render results ──────────────────────────────────────────────────────
function countSegments(segments) {
  let n = 0, m = 0;
  for (const seg of segments || []) {
    if (seg.type === "spoken_in_narration") n++;      // each entry is one token
    else if (seg.type === "literary_in_dialogue") m++;
  }
  return { n, m };
}

function setCard(id, c) {
  const card = $(id);
  card.querySelector(".metric-score").textContent = c.score;
  card.querySelector(".metric-ref").textContent = c.ref;
  card.querySelector(".metric-direction-wrap").innerHTML = c.dir;
  card.querySelector(".metric-sub").innerHTML = c.sub;
}

function renderResults(result, text, scroll) {
  _last = { result, text };
  const fluencyOn = result._fluency_on === true;
  const ref = window.HUMAN_REFERENCE || {};
  const view = SSEFView.buildView(result, ref, fluencyOn, tr, countSegments(result.segments));

  // 1. Validation line
  showValidationKey("msg.accepted", { n: result.words }, true);

  // Length notice
  const lengthNoticeEl = $("length-notice");
  if (lengthNoticeEl) {
    if (result.length_notice) {
      lengthNoticeEl.textContent = tr("notice.length", { n: result.words });
      lengthNoticeEl.classList.remove("hidden");
    } else {
      lengthNoticeEl.classList.add("hidden");
      lengthNoticeEl.textContent = "";
    }
  }

  // 2. Metric cards
  $("metrics-section").classList.remove("hidden");
  setCard("card-fluency", view.fluency);
  $("card-fluency").querySelector(".metric-off").classList.toggle("hidden", !view.fluency.off);
  setCard("card-coherence", view.coherence);
  setCard("card-lexical", view.lexical);
  setCard("card-register", view.register);

  // 3. Composite
  const comp = $("composite-section");
  comp.querySelector(".comp-label").textContent = view.composite.label;
  comp.querySelector(".comp-score").textContent = view.composite.score;
  comp.classList.remove("hidden");

  // 4. Story viewer
  renderStoryViewer(result, text, view.count);

  if (scroll) $("results-top").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Validation banner ───────────────────────────────────────────────────
function showValidationKey(key, params, ok) {
  _valState = { key, params, ok };
  renderValidation();
}

// Used only for library validation messages, which are shown as returned.
function showValidationRaw(text, ok) {
  _valState = { text, ok };
  renderValidation();
}

function renderValidation() {
  const el = $("validation-line");
  if (!_valState) return;
  const msg = _valState.text !== undefined ? _valState.text : tr(_valState.key, _valState.params);
  el.textContent = _valState.ok ? `✓  ${msg}` : `✗  ${msg}`;
  el.className   = `validation-line ${_valState.ok ? "ok" : "err"}`;
  el.classList.remove("hidden");
}

// ── Story viewer ─────────────────────────────────────────────────────────
function renderStoryViewer(result, text, countLine) {
  const wrap = $("story-section");
  wrap.classList.remove("hidden");

  const segments = result.segments;

  let html = "";
  if (segments && segments.length > 0) {
    let inDialogue = false;
    for (const seg of segments) {
      const isDia = (seg.type === "dialogue" || seg.type === "literary_in_dialogue");
      if (isDia && !inDialogue) {
        html += '<span class="hl-dia">';
        inDialogue = true;
      } else if (!isDia && inDialogue) {
        html += '</span>';
        inDialogue = false;
      }

      const escaped = escapeHTML(seg.text);
      if (seg.type === "spoken_in_narration") {
        html += `<span class="hl-spoken-nar">${escaped}</span>`;
      } else if (seg.type === "literary_in_dialogue") {
        html += `<span class="hl-lit-dia">${escaped}</span>`;
      } else {
        html += escaped;
      }
    }
    if (inDialogue) {
      html += '</span>';
    }
  } else {
    html = escapeHTML(text);
  }

  $("story-text-content").innerHTML = html;

  // these counts equal darc()['nS'] and darc()['dL'] respectively
  $("highlight-count").textContent = countLine;
}


// ── Utility ──────────────────────────────────────────────────────────────
function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clearResults() {
  _last = null;
  _valState = null;
  $("validation-line").classList.add("hidden");
  const lengthNoticeEl = $("length-notice");
  if (lengthNoticeEl) {
    lengthNoticeEl.classList.add("hidden");
    lengthNoticeEl.textContent = "";
  }
  $("metrics-section").classList.add("hidden");
  $("composite-section").classList.add("hidden");
  $("story-section").classList.add("hidden");
  $("polling-banner").classList.add("hidden");
  $("story-text-content").innerHTML = "";
  $("highlight-count").textContent = "";
  stopPolling();
}
