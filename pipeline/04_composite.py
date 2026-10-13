#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 04 — composite score.

Equal-weighted z-scores against the 8-story human reference distribution,
with fluency sign-flipped because lower perplexity is better.

THE REFERENCE
-------------
By default the reference is recomputed from the human rows of the input
table, so that a change upstream propagates rather than being silently
overridden by a stale constant. If those rows are absent — the human texts
are third-party copyright and may not be present (see data/README.md) — the
stage falls back to `HUMAN_REFERENCE`, the stored full-precision constants,
and says which it used. The two agree to full precision on the shipped
table; the stage asserts that rather than assuming it.

WHAT THE OUTPUT DOES NOT MEAN
-----------------------------
The human mean composite is 0.000 by construction. It is the origin, not a
result. And a composite near zero means the dimensions disagree, not that
quality is average — generated stories beat the reference on DARC and lose
on coherence, and equal weighting lets those cancel. The per-dimension
z-scores are therefore written into the same table and must be reported
beside the composite, never after it.

USAGE

    python pipeline/04_composite.py
    python pipeline/04_composite.py --in data/scores/rerun.csv

KEYING: rows are keyed on (id, model). `id` alone is the topic.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sinhala_story_eval import (composite, reference_from,   # noqa: E402
                                HUMAN_REFERENCE, __version__)
from sinhala_story_eval.composite import DIMENSIONS          # noqa: E402

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DEFAULT_IN = os.path.join(REPO, "data/scores/all38_v4_scores.csv")
DEFAULT_OUT = os.path.join(REPO, "data/scores/composite_scores.csv")

COLUMNS = ["id", "model", "corpus", "words", "pppl_overall", "darc",
           "coherence", "mtld", "z_fluency", "z_darc", "z_coherence",
           "z_mtld", "composite"]


def num(value):
    """CSV cell to float, or None for an empty cell. An empty cell means
    'not measured' and must stay distinguishable from zero."""
    value = (value or "").strip()
    return float(value) if value else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--force-stored-reference", action="store_true",
                    help="use HUMAN_REFERENCE even if human rows are present")
    args = ap.parse_args()

    with open(args.inp, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    records = {}
    for r in rows:
        key = (r["id"], r["model"])
        if key in records:
            raise ValueError(f"duplicate (id, model): {key}")
        records[key] = {k: num(r.get(k)) for k, _, _ in DIMENSIONS}
        records[key]["_row"] = r

    human = [records[k] for k in records if records[k]["_row"]["corpus"] == "human"]

    if human and not args.force_stored_reference:
        reference = reference_from(human)
        source = f"recomputed from {len(human)} human rows"
        drift = {k: (abs(reference[k][0] - HUMAN_REFERENCE[k][0]),
                     abs(reference[k][1] - HUMAN_REFERENCE[k][1]))
                 for k in HUMAN_REFERENCE}
        worst = max(max(d) for d in drift.values())
        if worst > 1e-9:
            print("WARNING: recomputed reference differs from the stored "
                  "HUMAN_REFERENCE constants. The published figures were "
                  "computed with the stored values.")
            for k, (dm, ds) in drift.items():
                if max(dm, ds) > 1e-9:
                    print(f"  {k}: mean drift {dm:.6g}, SD drift {ds:.6g}")
        else:
            print("reference matches the stored HUMAN_REFERENCE to full "
                  "precision")
    else:
        reference = HUMAN_REFERENCE
        source = ("stored HUMAN_REFERENCE constants "
                  "(human rows absent)" if not human else
                  "stored HUMAN_REFERENCE constants (forced)")

    out_rows = []
    for key, rec in records.items():
        row = rec["_row"]
        score, z = composite({k: rec[k] for k, _, _ in DIMENSIONS},
                             reference=reference)
        out_rows.append({
            "id": row["id"], "model": row["model"], "corpus": row["corpus"],
            "words": row["words"],
            "pppl_overall": row["pppl_overall"], "darc": row["darc"],
            "coherence": row["coherence"], "mtld": row["mtld"],
            "z_fluency": z["Fluency"], "z_darc": z["DARC"],
            "z_coherence": z["Coherence"], "z_mtld": z["MTLD"],
            "composite": score,
        })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    print(f"library v{__version__}")
    print(f"reference: {source}")
    print(f"wrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
