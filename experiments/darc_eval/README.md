# DARC perturbation evaluation (RQ2)

This folder holds the evidence for Chapter 5, Section 5.6.1.

| File | What it is |
|---|---|
| `darc_eval.py` | The evaluation script. Tests T1, T2 and T4. |
| `darc_eval_results.csv` | All 600 perturbed texts: 30 stories x 4 levels x 5 seeds, with DARC and baseline scores for T1 and T2. |
| `darc_eval_summary.txt` | The summary figures reported in Table 5.4 and Figure 5.1. |

**T1 — sensitivity.** Spoken-register narration sentences from two published human stories (H01, H03) are inserted into the narration of each generated story at 0, 10, 25 and 50 per cent of its narration sentences. DARC should fall as the level rises.

**T2 — dialogue invariance.** The same amount of spoken text is added as quoted dialogue instead. Spoken dialogue is conventional, so DARC should not fall. A dialogue-blind baseline is scored on the same texts and does fall.

**T4 — false positives.** Every register-neutral word in the lexicon must be left unlabelled.

## Reproduce

The random draws are seeded from the story id, model, seed and level, so a re-run gives identical numbers.

```
python experiments/darc_eval/darc_eval.py --stories <all 38 stories JSON> --spoken-sources H01,H03 --seeds 5
```

The human story texts are third-party copyright and are not in this repository; the JSON must be supplied locally.
