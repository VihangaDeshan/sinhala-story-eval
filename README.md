# sinhala-story-eval

A quality evaluation framework for Sinhala short stories, built for a BSc (Hons) Computing dissertation under Design Science Research.

Four dimensions, of which the fourth is the contribution:

| Dimension | Method | Needs GPU |
|---|---|---|
| Fluency | SinBERT pseudo-perplexity, chunked and dialogue-aware | yes |
| Coherence | Entity overlap with Sinhala case stemming | no |
| Lexical diversity | MTLD, with TTR as a baseline | no |
| **Register consistency** | **DARC** | no |

**DARC** is a dialogue-aware measure of diglossic register consistency for Sinhala. It is built on documented verb morphology rather than on a corpus, so it has no data dependency that can break.

## Install

```bash
pip install sinhala-story-eval              # three CPU metrics, no dependencies
pip install sinhala-story-eval[fluency]     # adds SinBERT PPPL (torch, ~2 GB)
```

## Use

```python
from sinhala_story_eval import evaluate

result = evaluate(story_text)
# {'darc': 0.975, 'darc_narrative': 0.988, 'coherence': 0.0497,
#  'mtld': 353.81, 'composite': 0.0902, 'z_scores': {...}, ...}

result = evaluate(story_text, fluency=True)   # adds PPPL, ~90s on a T4
```

Individual metrics:

```python
from sinhala_story_eval import darc, coherence, mtld, segment

score, sub = darc(story_text)
narrative, dialogue = segment(story_text)
```

Dialogue must be in double quotation marks. The segmenter cannot see unquoted dialogue.

## What DARC measures

Sinhala is diglossic. Narrative prose conventionally uses the **literary** register for narration and the **spoken** register for dialogue. The two differ grammatically, not just lexically:

| Register | Sentence |
|---|---|
| Spoken | නිමල් කමලාට **ගැහුවා** |
| Literary | නිමල් කමලාට **ගැහුවේය** |

Same verb, same meaning — only the subject-agreement suffix differs. That is why the measure needs no corpus.

```
Narrative Register  (50%)   narration should be literary
Dialogue Register   (25%)   dialogue should be spoken
Register Balance    (25%)   dialogue 15–50% of tokens

DARC = 0.50·narrative + 0.25·dialogue + 0.25·balance
```

**A high score means the text follows the convention. It does not mean the text is good.**

## Validation

| Check | Result |
|---|---|
| Minimal pairs, common verbs | 40/40 |
| Minimal pairs, rare verbs | 20/20 |
| False positives on neutral words | 0/48 |
| Synthetic corruption gap | +0.183 |
| Segmentation precision/recall | 5 stories, 142 spans, manually annotated |
| Weight sensitivity | correct story first under all six weightings |

```bash
pytest          # 82 tests lock these in
```

## Findings

Measured on 30 LLM-generated stories and 8 published human-written stories.

**LLMs follow the Sinhala register convention more consistently than human authors do.** Register was never instructed in the prompt, yet all 30 generated stories narrated in the literary register and all 30 fell inside the expected dialogue-balance band. Five of eight published human stories narrate mainly in the spoken register — a recognised modern style.

**Human writing occupies both extremes; LLM output clusters.** Composite SD 0.686 for human stories against 0.157 for generated — a 4.36× ratio. Six of eight human stories sit in the top or bottom five of all 38.

**DARC cannot separate the three models on this corpus, and that is informative.** All 30 scored ≥ 0.90, so between-model spread (0.013) falls below within-model noise (0.021). On the human corpus DARC spreads across 0.13–0.97. The measure discriminates; a uniformly conventional corpus gives it nothing to discriminate.

**LaBSE does not measure Sinhala narrative coherence.** Ten unrelated sentences scored 0.4338 against 0.4932 for a coherent story — a discrimination of +0.059. Entity overlap achieves +0.426 on the same data. Reported as a negative finding.

## Repository layout

```
src/sinhala_story_eval/   the library
pipeline/                 numbered stage scripts for the study
experiments/              design-cycle evidence: what was tried and rejected
data/                     stories, scores, human evaluation
docs/                     decisions, methodology, sources
tests/
```

`experiments/` holds the rejected alternatives with their numbers — the LaBSE rejection, five rejected generation models, the DARC v0→v4 iterations, and the segmentation defect. Under Hevner's guidelines this record is part of the contribution, not an appendix to it.

## Limitations

- Unquoted and em-dash dialogue are invisible to the segmenter (D21).
- About 35% of tokens carry a register tag. This is by design — nouns, adjectives and many particles are register-neutral.
- The composite is normalised against 8 human stories, so those standard deviations are themselves uncertain.
- Human fluency SD is wide (CV 69%), which compresses fluency z-scores relative to the other three dimensions.
- The claim that Sinhala diglossia is realised primarily in verb morphology rests on published grammars and has not been verified against a native-speaker linguist.

## Citation

```bibtex
@software{sammandapperuma2026ssef,
  author = {Sammandapperuma, S.M.A.D.V.D.},
  title  = {sinhala-story-eval: A Quality Evaluation Framework for
            Sinhala Story Generation},
  year   = {2026},
  note   = {BSc (Hons) Computing, Coventry University / NIBM}
}
```

## References

- Ferguson, C. A. (1959). Diglossia. *Word*, 15(2), 325–340.
- Mawelle, I. (2023). A spectrum? Diglossia as seen in contemporary Sinhala novels. *Journal of Social Sciences and Humanities Review*, 8(3), 91–108. https://doi.org/10.4038/jsshr.v8i3.120
- Chandralal, D. (2010). *Sinhala*. John Benjamins.
- Zubair, C. (2010). Diglossia versus register: Discursive classifications of two Sinhala varieties. *Berkeley Linguistics Society*.
- McCarthy, P. M., & Jarvis, S. (2010). MTLD, vocd-D, and HD-D. *Behavior Research Methods*, 42(2), 381–392.
- Salazar, J. et al. (2020). Masked Language Model Scoring. *ACL 2020*.
- Dhananjaya, V. et al. (2022). BERTifying Sinhala. arXiv:2208.07864.

MIT licence.
