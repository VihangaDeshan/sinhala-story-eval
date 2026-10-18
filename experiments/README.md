# experiments/

What was tried, what was kept and what was rejected, with the numbers.

Under Hevner et al.'s guidelines, design science must show the **search
process**, not only the artefact that survived. This directory is that
record. Each subdirectory documents one decision: what the alternatives
were, what was measured, and why the rejected option was rejected.

| Directory | Decision | Evidence |
|---|---|---|
| `darc_eval/` | DARC construct accuracy (dissertation Section 5.6.1) | T1 ρ = −0.931 (baseline −0.723), 30/30 stories ordered; T2 DARC −0.0098 vs baseline −0.1982; T4 0/58. Includes the split-ය diagnostic. Script and all 600 results are in the folder. |
| `darc_iterations/` | DARC V0 → V4 (dissertation Table 4.4) | A corpus-derived lexicon was rejected before V0 because its source data were unavailable. V2 split the endings into two tiers after 6–10% false positives on real output. V3 added the verb-root guard. V4 changed segmentation only. |
| `coherence_selection/` | Entity overlap over LaBSE | LaBSE adjacent +0.059, window-3 +0.076, entity overlap +0.426. Unrelated sentences scored 0.4338 against 0.4932 for coherent text. |
| `model_selection/` | Three generation models | SinLlama: out of memory across four load configurations. Llama-3.1-8B: 11.0 tokens per Sinhala word, degenerate output. Kimi K3: reasoning only. Kimi K2.6: reasoning consumed the token budget. gemini-3.7-flash: HTTP 503. |
| `segmentation_pr/` | Paragraph-bounded spans (segmenter V4) | Adding U+0027 to the quote set fixes H07 but breaks H04 (0 → 40 empty spans) and H05 (0 → 63 spans, 62 empty). Paragraph-bounded spans fix H07 and change no generated story. |

Only `darc_eval/` holds runnable code and result files. The other four
folders hold a written summary of the decision; the working files for those
decisions are not in this repository.

Two claims were also withdrawn when the evidence changed. Both are kept
rather than deleted:

- **SinBERT register bias 1.01× → 2.20×.** The original test used a single
  story that narrated in literary register throughout, so there was no
  variance in the independent variable and no bias could have been detected
  either way.
- **The DARC ceiling is not circularity.** It was first read as the prompt
  instructing the property being measured. The prompt actually used was
  variant A2, which omits register instruction. The ceiling is therefore a
  property of the models, and it became the study's primary finding.
