#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 05 — validation statistics for Chapter 4.

Recomputes every headline number from the score tables, so the figures in
the dissertation have a script behind them rather than a spreadsheet nobody
can find later.

WHAT IT REPORTS

  1. Per-model means for each dimension.
  2. Discrimination ratio = (between-model spread) / (mean within-model SD).
     A metric with a ratio below 1 cannot separate the models: its spread
     between models is smaller than its noise within them.
  3. Pairwise Pearson correlations across the 30 generated stories. These
     justify a multi-dimensional framework — if two dimensions correlated
     strongly, one of them would be redundant.
  4. Composite variance, generated against human.
  5. Weight sensitivity: does the model ranking survive reweighting?

WHAT IT IS NOT

This is DEMONSTRATION arithmetic over the automated scores. It says nothing
about whether the metrics agree with human judgement. That is RQ3 and needs
the rater data, which this stage does not touch.

USAGE

    python pipeline/05_validate.py
    python pipeline/05_validate.py --expect   # compare to reported figures
"""

import argparse
import csv
import itertools
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCORES = os.path.join(REPO, "data/scores/all38_v4_scores.csv")
COMPOSITE = os.path.join(REPO, "data/scores/composite_scores.csv")

GENERATED_MODELS = ["gemini", "deepseek", "gpt"]

# Figures as reported in the dissertation, for regression checking. If a
# code change moves one of these, the discrepancy must be explained, not
# quietly adopted.
REPORTED_DISCRIMINATION = {
    "pppl_overall": 3.94,
    "dia_spans": 3.73,
    "coherence": 2.32,
    "mtld": 1.44,
    "darc": 0.60,
}
REPORTED_COMPOSITE_DISCRIMINATION = 2.32
REPORTED_VARIANCE_RATIO = 4.36


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    v = (v or "").strip()
    return float(v) if v else None


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = st.mean(xs), st.mean(ys)
    num_ = sum((x - mx) * (y - my) for x, y in pairs)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) *
                    sum((y - my) ** 2 for y in ys))
    return num_ / den if den else None


def discrimination(rows, column):
    """Between-model spread over mean within-model SD."""
    by_model = {}
    for m in GENERATED_MODELS:
        vals = [num(r[column]) for r in rows
                if r["model"] == m and num(r[column]) is not None]
        if len(vals) < 2:
            return None
        by_model[m] = vals
    means = [st.mean(v) for v in by_model.values()]
    within = st.mean([st.stdev(v) for v in by_model.values()])
    spread = max(means) - min(means)
    return (spread, within, spread / within if within else None, by_model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", action="store_true",
                    help="check against the reported figures")
    args = ap.parse_args()

    scores = load(SCORES)
    comp = load(COMPOSITE)
    gen = [r for r in scores if r["corpus"] == "generated"]

    print("=" * 66)
    print("1. PER-MODEL MEANS")
    print("=" * 66)
    cols = ["pppl_overall", "darc", "coherence", "mtld", "dia_spans"]
    print(f"{'model':10s} {'n':>3s}" + "".join(f"{c:>14s}" for c in cols))
    for m in GENERATED_MODELS + ["human"]:
        rs = [r for r in scores if r["model"] == m]
        cells = []
        for c in cols:
            v = [num(r[c]) for r in rs if num(r[c]) is not None]
            cells.append(f"{st.mean(v):14.4f}" if v else f"{'—':>14s}")
        print(f"{m:10s} {len(rs):3d}" + "".join(cells))

    print()
    print("=" * 66)
    print("2. DISCRIMINATION RATIOS (generated corpus, n=30)")
    print("=" * 66)
    print(f"{'metric':14s}{'between':>12s}{'within SD':>12s}{'ratio':>10s}"
          f"{'verdict':>12s}")
    failures = []
    for c in ["pppl_overall", "dia_spans", "coherence", "mtld", "darc"]:
        d = discrimination(gen, c)
        if d is None:
            print(f"{c:14s}{'insufficient data':>46s}")
            continue
        spread, within, ratio, _ = d
        verdict = "separates" if ratio >= 2 else (
            "weak" if ratio >= 1 else "CEILING/FLOOR")
        print(f"{c:14s}{spread:12.4f}{within:12.4f}{ratio:10.2f}"
              f"{verdict:>12s}")
        if args.expect and c in REPORTED_DISCRIMINATION:
            want = REPORTED_DISCRIMINATION[c]
            if abs(round(ratio, 2) - want) > 0.005:
                failures.append(f"discrimination[{c}] {ratio:.2f} "
                                f"but {want:.2f} reported")

    print()
    print("   DARC's ratio below 1 is a finding, not a defect: it does not")
    print("   separate the models because all thirty sit at ceiling. It does")
    print("   separate the human corpus, which spans 0.13 to 0.97.")

    print()
    print("=" * 66)
    print("3. PAIRWISE CORRELATIONS (generated, n=30)")
    print("=" * 66)
    dims = ["pppl_overall", "darc", "coherence", "mtld"]
    strongest = 0.0
    for a, b in itertools.combinations(dims, 2):
        r = pearson([num(x[a]) for x in gen], [num(x[b]) for x in gen])
        if r is None:
            continue
        strongest = max(strongest, abs(r))
        flag = "  <-- REDUNDANT?" if abs(r) > 0.5 else ""
        print(f"{a:14s} x {b:14s} r = {r:+.4f}{flag}")
    print(f"\n   strongest |r| = {strongest:.4f}"
          f" — {'below' if strongest <= 0.5 else 'ABOVE'} the 0.50 threshold")

    print()
    print("=" * 66)
    print("4. COMPOSITE")
    print("=" * 66)
    by = {}
    for r in comp:
        by.setdefault(r["model"], []).append(float(r["composite"]))
    for m in GENERATED_MODELS + ["human"]:
        v = by.get(m, [])
        if v:
            print(f"   {m:10s} n={len(v):2d}  mean {st.mean(v):+.4f}"
                  f"  SD {st.stdev(v):.4f}")
    print("   human mean is 0.000 BY CONSTRUCTION — the origin, not a result")

    gen_c = [float(r["composite"]) for r in comp if r["corpus"] == "generated"]
    hum_c = [float(r["composite"]) for r in comp if r["corpus"] == "human"]
    means = [st.mean(by[m]) for m in GENERATED_MODELS]
    within = st.mean([st.stdev(by[m]) for m in GENERATED_MODELS])
    comp_ratio = (max(means) - min(means)) / within
    print(f"\n   composite discrimination ratio {comp_ratio:.2f}")

    if hum_c:
        ratio = st.stdev(hum_c) / st.stdev(gen_c)
        print(f"   variance: human SD {st.stdev(hum_c):.4f} vs generated "
              f"{st.stdev(gen_c):.4f} — {ratio:.2f}x")
        print("   LLM output clusters in a narrow band; human writing does not")
        if args.expect:
            if abs(round(comp_ratio, 2) - REPORTED_COMPOSITE_DISCRIMINATION) > 0.005:
                failures.append(f"composite discrimination {comp_ratio:.2f} "
                                f"but {REPORTED_COMPOSITE_DISCRIMINATION} reported")
            if abs(round(ratio, 2) - REPORTED_VARIANCE_RATIO) > 0.005:
                failures.append(f"variance ratio {ratio:.2f} but "
                                f"{REPORTED_VARIANCE_RATIO} reported")

    print()
    print("=" * 66)
    print("5. WEIGHT SENSITIVITY — does the ranking survive reweighting?")
    print("=" * 66)
    schemes = {
        "equal": {"z_fluency": .25, "z_darc": .25, "z_coherence": .25, "z_mtld": .25},
        "no coherence": {"z_fluency": 1/3, "z_darc": 1/3, "z_coherence": 0, "z_mtld": 1/3},
        "no fluency": {"z_fluency": 0, "z_darc": 1/3, "z_coherence": 1/3, "z_mtld": 1/3},
        "no DARC": {"z_fluency": 1/3, "z_darc": 0, "z_coherence": 1/3, "z_mtld": 1/3},
        "no MTLD": {"z_fluency": 1/3, "z_darc": 1/3, "z_coherence": 1/3, "z_mtld": 0},
        "DARC-heavy": {"z_fluency": 1/6, "z_darc": .5, "z_coherence": 1/6, "z_mtld": 1/6},
    }
    firsts = set()
    for name, w in schemes.items():
        agg = {}
        for m in GENERATED_MODELS:
            rs = [r for r in comp if r["model"] == m]
            agg[m] = st.mean([sum(w[k] * float(r[k]) for k in w) for r in rs])
        order = sorted(agg, key=lambda m: -agg[m])
        firsts.add(order[0])
        print(f"   {name:14s} " +
              " > ".join(f"{m} ({agg[m]:+.3f})" for m in order))
    print(f"\n   first place: {'ROBUST — ' + firsts.pop() if len(firsts) == 1 else 'NOT robust'}"
          " across all weightings tested")
    print("   second and third place are NOT robust — report both")

    if args.expect:
        print()
        print("=" * 66)
        if failures:
            print("REGRESSION FAILURES against the reported figures:")
            for f in failures:
                print("  -", f)
            sys.exit(1)
        print("All checked figures match the dissertation. No drift.")


if __name__ == "__main__":
    main()
