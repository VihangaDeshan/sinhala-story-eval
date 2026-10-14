// Renders the result cards in English and in Sinhala with view.js and fails
// if any numeric token differs between the two. Usage: node check_numbers.js results.json
"use strict";
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..", "..", "app", "static");
const view = require(path.join(root, "view.js"));
const load = (p) => JSON.parse(fs.readFileSync(p, "utf-8"));
const en = load(path.join(root, "i18n", "en.json"));
const si = load(path.join(root, "i18n", "si.json"));
const results = process.argv[2] ? load(process.argv[2]) : {};

const ref = {
  pppl_overall: { mean: 20.5, sd: 3 }, coherence: { mean: 0.42, sd: 0.1 },
  mtld: { mean: 80.1, sd: 10 }, darc: { mean: 0.55, sd: 0.2 },
};
const translator = (dict) => (key, params) =>
  view.fill(dict[key] || en[key] || key, params || {});

const NUM = /[−+-]?\d+(?:[.,]\d+)*/g;
let failed = false;

// Static strings (r-values, n = 30, 30,000 ...): same numbers in every filled key.
for (const key of Object.keys(en)) {
  if (!si[key]) continue;
  const a = (en[key].match(NUM) || []).slice().sort().join(" "), b = (si[key].match(NUM) || []).slice().sort().join(" ");
  if (a !== b) { console.log("key " + key + ": en numbers [" + a + "] != si numbers [" + b + "]"); failed = true; }
}

for (const [name, result] of Object.entries(results)) {
  const out = {};
  for (const [lang, dict] of [["en", en], ["si", si]]) {
    const v = view.buildView(result, ref, result._fluency_on === true,
                             translator(dict), { n: 7, m: 3 });
    // Every card field, concatenated; tags stripped so style="width:…" is excluded.
    const flat = JSON.stringify(v).replace(/<[^>]*>/g, " ");
    out[lang] = flat.match(NUM) || [];
  }
  if (out.en.length === 0) { console.log(name + ": no numbers found - test is vacuous"); failed = true; }
  if (JSON.stringify(out.en) !== JSON.stringify(out.si)) {
    console.log(name + ": numbers differ\n  en: " + out.en.join(" ") + "\n  si: " + out.si.join(" "));
    failed = true;
  } else {
    console.log(name + ": " + out.en.length + " numeric tokens identical in en and si");
  }
}
process.exit(failed ? 1 : 0);
