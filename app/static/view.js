/* ─────────────────────────────────────────────────────────────────────
   SSEF — view.js
   Pure functions: result object + translator -> strings. No DOM access, so
   the same code runs in the browser and under Node (tests/js/check_numbers.js).
   Every number is formatted here from the result and never from a language
   file; the translator only supplies the surrounding words.
───────────────────────────────────────────────────────────────────── */
(function (root) {
  "use strict";

  function fmt(v, dp) {
    if (dp === undefined) dp = 4;
    if (v == null) return "—";
    return Number(v).toFixed(dp);
  }

  // Replace {name} placeholders; unknown placeholders are left as written.
  function fill(tpl, params) {
    return String(tpl).replace(/\{(\w+)\}/g, function (m, k) {
      return params && Object.prototype.hasOwnProperty.call(params, k) ? params[k] : m;
    });
  }

  function directionHTML(score, refMean, t) {
    const above = score > refMean;
    const label = above ? t("dir.above") : t("dir.below");
    const cls   = above ? "direction-above" : "direction-below";
    return `<span class="metric-direction ${cls}">${label}</span>`;
  }

  function simpleCard(score, dp, refMean, t) {
    return {
      score: score != null ? fmt(score, dp) : "—",
      ref:   refMean != null && score != null ? `${t("ref.published")} ${refMean.toFixed(dp)}` : "",
      dir:   refMean != null && score != null ? directionHTML(score, refMean, t) : "",
    };
  }

  // "TTR (baseline, length-sensitive)" -> label "TTR", note "(baseline, ...)".
  function splitTTR(s) {
    const i = s.indexOf("(");
    return i < 0 ? [s, ""] : [s.slice(0, i).trim(), s.slice(i)];
  }

  function buildView(result, ref, fluencyOn, t, counts) {
    ref = ref || {};
    const v = {};

    v.validation = t("msg.accepted", { n: result.words });

    // Fluency
    if (!fluencyOn || result.pppl_overall == null) {
      v.fluency = { off: true, score: "—", ref: "", dir: "", sub: "" };
    } else {
      const refMean = ref.pppl_overall ? ref.pppl_overall.mean : null;
      let sub = `<div class="metric-better">${t("dir.lower_better")}</div>`;
      if (result.pppl_narrative != null || result.pppl_dialogue != null) {
        sub += `<div class="metric-sub-row"><span>${t("sub.pppl_narration")}</span><span>${fmt(result.pppl_narrative, 2)}</span></div>`;
        sub += `<div class="metric-sub-row"><span>${t("sub.pppl_dialogue")}</span><span>${fmt(result.pppl_dialogue, 2)}</span></div>`;
      }
      const c = refMean != null
        ? { score: fmt(result.pppl_overall, 2),
            ref: `${t("ref.published")} ${refMean.toFixed(2)}`,
            dir: directionHTML(result.pppl_overall, refMean, t) }
        : { score: fmt(result.pppl_overall, 2), ref: "", dir: "" };
      v.fluency = Object.assign({ off: false, sub: sub }, c);
    }

    // Coherence
    v.coherence = Object.assign(
      simpleCard(result.coherence, 4, ref.coherence ? ref.coherence.mean : null, t),
      { sub: `<div class="metric-better">${t("dir.higher_better")}</div>` });

    // Lexical diversity
    const ttr = splitTTR(t("ttr.label"));
    v.lexical = Object.assign(
      simpleCard(result.mtld, 1, ref.mtld ? ref.mtld.mean : null, t),
      { sub: `
    <div class="metric-better">${t("dir.higher_better")}</div>
    <div class="metric-sub-row"><span>${ttr[0]} <span class="ttr-note">${ttr[1]}</span></span><span>${fmt(result.ttr, 4)}</span></div>
  ` });

    // Register
    const rc = simpleCard(result.darc, 4, ref.darc ? ref.darc.mean : null, t);
    if (rc.ref) {
      rc.dir = `<span class="metric-direction direction-note">${t("register.direction")}</span>`;
    }
    const dRatio = result.dialogue_ratio != null ? (result.dialogue_ratio * 100).toFixed(1) + "%" : "—";
    const bar = (x) => `<div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:${(x || 0) * 100}%"></div></div>`;
    v.register = Object.assign(rc, { sub: `
    <div class="metric-sub-row"><span>${t("sub.narrative")}</span><span>${fmt(result.darc_narrative, 3)}</span></div>
    ${bar(result.darc_narrative)}
    <div class="metric-sub-row"><span>${t("sub.dialogue")}</span><span>${fmt(result.darc_dialogue, 3)}</span></div>
    ${bar(result.darc_dialogue)}
    <div class="metric-sub-row"><span>${t("sub.balance")}</span><span>${fmt(result.darc_balance, 3)}</span></div>
    ${bar(result.darc_balance)}
    <div class="metric-sub-row"><span>${t("sub.ratio")}</span><span>${dRatio}</span></div>
  ` });

    // Composite
    v.composite = {
      label: fluencyOn ? t("comp.label4") : t("comp.label3"),
      score: result.composite != null ? fmt(result.composite, 4) : "—",
    };

    // Highlight count line (counts come from the segments, not the language)
    const c = counts || { n: 0, m: 0 };
    v.count = t("count.line", { n: c.n, m: c.m, k: c.n + c.m });

    return v;
  }

  const api = { fmt: fmt, fill: fill, buildView: buildView };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SSEFView = api;
})(typeof window !== "undefined" ? window : globalThis);
