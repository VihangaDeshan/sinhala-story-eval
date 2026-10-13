#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 02 — CPU metrics: DARC, entity coherence, MTLD, TTR.

No GPU, no network, no model. Runs the whole 38-story corpus in seconds, so
it can be re-run freely whenever the library changes. That is the point of
keeping fluency in a separate stage.

This script imports the library rather than reimplementing the metrics, so
the published package and the study cannot drift apart. If a metric changes,
this stage changes with it and the change shows up in the output table.

USAGE

    python pipeline/02_score_cpu.py
    python pipeline/02_score_cpu.py --generated-only
    python pipeline/02_score_cpu.py --out data/scores/rerun.csv

The human reference texts are third-party copyright and are not in the
repository (see data/README.md). Without them the stage scores the 30
generated stories and says so. `--generated-only` makes that explicit.

KEYING: `id` is the topic, not the story. Rows are keyed on (id, model).
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sinhala_story_eval import evaluate, __version__          # noqa: E402

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GENERATED = os.path.join(REPO, "data/stories/generated30_stories.json")
HUMAN = os.path.join(REPO, "data/stories/private/human8_stories.json")
DEFAULT_OUT = os.path.join(REPO, "data/scores/all38_v4_scores.csv")

COLUMNS = [
    "id", "model", "corpus", "words",
    "pppl_overall", "pppl_narrative", "pppl_dialogue",
    "darc", "darc_nar", "darc_dia", "darc_bal",
    "dia_ratio", "dia_spans", "nar_tokens", "dia_tokens",
    "coherence", "mtld", "ttr",
]


def load_corpus(generated_only=False):
    with open(GENERATED, encoding="utf-8") as f:
        stories = json.load(f)
    if generated_only:
        return stories, False
    if os.path.exists(HUMAN):
        with open(HUMAN, encoding="utf-8") as f:
            stories = stories + json.load(f)
        return stories, True
    return stories, False


def carry_forward_fluency(out_path):
    """Fluency is produced by stage 03 and is expensive. Re-running stage 02
    must not wipe it, so any existing PPPL values are read back and carried
    into the new table, keyed on (id, model)."""
    if not os.path.exists(out_path):
        return {}
    keep = {}
    with open(out_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            keep[(row["id"], row["model"])] = {
                k: row.get(k, "") for k in
                ("pppl_overall", "pppl_narrative", "pppl_dialogue")
            }
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-only", action="store_true")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    stories, have_human = load_corpus(args.generated_only)
    prior = carry_forward_fluency(args.out)

    keys = set()
    rows = []
    for s in stories:
        key = (s["id"], s["model"])
        if key in keys:
            raise ValueError(f"duplicate (id, model): {key}")
        keys.add(key)

        r = evaluate(s["text"], fluency=False, include_composite=False)
        carried = prior.get(key, {})
        rows.append({
            "id": s["id"], "model": s["model"], "corpus": s["corpus"],
            "words": r["words"],
            "pppl_overall": carried.get("pppl_overall", ""),
            "pppl_narrative": carried.get("pppl_narrative", ""),
            "pppl_dialogue": carried.get("pppl_dialogue", ""),
            "darc": r["darc"],
            "darc_nar": r["darc_narrative"],
            "darc_dia": r["darc_dialogue"],
            "darc_bal": r["darc_balance"],
            "dia_ratio": r["dialogue_ratio"],
            "dia_spans": r["dialogue_spans"],
            "nar_tokens": r["narrative_tokens"],
            "dia_tokens": r["dialogue_tokens"],
            "coherence": r["coherence"],
            "mtld": r["mtld"],
            "ttr": r["ttr"],
        })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    n_carried = sum(1 for r in rows if r["pppl_overall"] != "")
    print(f"library v{__version__}")
    print(f"scored {len(rows)} stories "
          f"({'30 generated + 8 human' if have_human else 'generated only'})")
    print(f"fluency values carried forward from stage 03: {n_carried}")
    print(f"wrote {args.out}")
    if not have_human:
        print("NOTE: human reference texts absent — the composite in stage 04 "
              "will fall back to the stored HUMAN_REFERENCE constants.")


if __name__ == "__main__":
    main()
