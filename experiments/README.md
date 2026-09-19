# experiments/

What was tried and rejected, with the numbers.

Under Hevner et al.'s guidelines, design science must show the **search
process** — not only the artefact that survived. This directory is that
record. Each subdirectory documents one decision: what the alternatives
were, what was measured, and why the rejected option was rejected.

| Directory | Decision | Rejected on |
|---|---|---|
| `darc_iterations/` | DARC v0 → v4 | v0 corpus lexicon: source data unavailable, substitutes noisy. v1 flat suffix rules: 6–10% false positives on real LLM output. v2→v3: Tier A/B asymmetry left rare spoken verbs untagged, which under-detected register mixing. |
| `coherence_selection/` | Entity overlap over LaBSE | LaBSE adjacent +0.059 discrimination, window-3 +0.076, entity-based +0.426. Unrelated sentences scored 0.4338 against 0.4932 for coherent text. |
| `model_selection/` | Three generation models | SinLlama: OOM across four load configurations. Llama-3.1-8B: 11.0 tokens per Sinhala word, degenerate output. Kimi K3: reasoning-only. Kimi K2.6: reasoning consumed the token budget. gemini-3.7-flash: HTTP 503. |
| `segmentation_pr/` | Paragraph-bounded spans | Adding U+0027 to the quote set fixes H07 but breaks H04 (0 → 40 empty spans) and H05 (0 → 63). One story repaired at the cost of two. |

Two claims were also withdrawn when the evidence changed, and both are kept
rather than deleted:

- **SinBERT register bias 1.01× → 2.20×.** The original test used a single
  story that narrated in literary register throughout, so there was no
  variance in the independent variable and no bias could have been detected
  either way.
- **The DARC ceiling is not circularity.** It was first read as the prompt
  instructing the property being measured. The prompt actually used was
  variant A2, which omits register instruction — so the ceiling is a
  property of the models, and becomes the study's primary finding.
