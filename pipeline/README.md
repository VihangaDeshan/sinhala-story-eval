# pipeline/

Numbered stages. Each imports the library rather than reimplementing it, so
the study and the published package cannot drift apart.

| Stage | Runs | Needs GPU |
|---|---|---|
| `01_generate.py` | OpenRouter, three models, length gate 720–880 words | no |
| `02_score_cpu.py` | DARC, coherence, MTLD | no |
| `PPPL_All38.ipynb` (Colab) | SinBERT PPPL, all 38 stories, T4, 11 Sep 2026 (119.8 min); H02/H07 narrative and dialogue re-run after segmenter v4 in `PPPL_Patch_v4.ipynb` | **yes** |
| `04_composite.py` | z-scores against the human reference | no |
| `05_validate.py` | correlations, Krippendorff α, discrimination ratios | no |

Fluency is a separate stage because it is the only one needing a GPU, and
at roughly 90 seconds per story it dominates the runtime.

Stage 02 can be re-run freely. Stage 03 should not be, unless segmentation
changes — and then only for the stories whose segmentation actually
changed. `pppl_overall` never calls `segment()`, so it stays valid
regardless.
