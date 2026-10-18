# sinhala-story-eval

A quality evaluation framework for Sinhala short stories, built for a BSc (Hons) Computing dissertation (NIBM / Coventry University) under Design Science Research.

**Live web application:** https://generationkatha.online (sign-up required)

The framework measures four dimensions of a story. The fourth is the contribution of this work:

| Dimension | Method | Needs GPU |
|---|---|---|
| Fluency | SinBERT pseudo-perplexity, chunked and dialogue-aware | yes |
| Coherence | Entity overlap with Sinhala case stemming | no |
| Lexical diversity | MTLD, with TTR as a baseline | no |
| **Register consistency** | **DARC** | no |

**DARC** (Dialogue-Aware Register Consistency) is a dialogue-aware measure of literary and spoken Sinhala. It is rule-based: its rules come from Sinhala verb morphology, not from a training corpus.

## Install

The package is installed from GitHub (it is not on PyPI):

```bash
pip install "git+https://github.com/VihangaDeshan/sinhala-story-eval.git"              # three CPU metrics, no extra dependencies
pip install "sinhala-story-eval[fluency] @ git+https://github.com/VihangaDeshan/sinhala-story-eval.git"   # adds SinBERT PPPL (torch, ~2 GB)
```

To work on the code or run the tests, clone it instead:

```bash
git clone https://github.com/VihangaDeshan/sinhala-story-eval.git
cd sinhala-story-eval
pip install -e .
pytest
```

## Use

```python
from sinhala_story_eval import evaluate

result = evaluate(story_text)                 # three CPU dimensions + composite
result = evaluate(story_text, fluency=True)   # adds PPPL, about 90 s per 800-word story on a T4
```

Individual metrics:

```python
from sinhala_story_eval import darc, coherence, mtld, segment

score, sub = darc(story_text)
narrative, dialogue = segment(story_text)
```

Dialogue must be in double quotation marks. The segmenter cannot see unquoted dialogue.

Input that is not Sinhala script (fewer than 95% Sinhala letters) is rejected before any metric runs.

## What DARC measures

Sinhala is diglossic. Sinhala fiction conventionally narrates in the **literary** register and writes dialogue in the **spoken** register. The two differ in the verb ending:

| Register | Sentence |
|---|---|
| Spoken | ළමයා පොත **කියෙව්වා** |
| Literary | ළමයා පොත **කියෙව්වේය** |

Same verb, same meaning; only the verb ending differs. That is why the measure needs no corpus.

```
Narrative register  (50%)   narration should be literary
Dialogue register   (25%)   dialogue should be spoken
Register balance    (25%)   dialogue 15–50% of tokens

DARC = 0.50·narrative + 0.25·dialogue + 0.25·balance
```

A high score means the story follows this convention. **It is not an overall rating of the story.** Spoken narration can be a deliberate modern style.

## Validation

| Check | Result |
|---|---|
| Controlled perturbation (T1): spoken narration inserted at 0/10/25/50%, 30 stories × 5 seeds | Spearman ρ = −0.931 (dialogue-blind baseline −0.723); 30/30 stories ordered correctly |
| Dialogue invariance (T2): same text added as quoted dialogue | DARC −0.0098 vs baseline −0.1982 |
| Register-neutral words wrongly labelled (T4) | 0/58 |
| Segmentation, 5 stories, 142 manually annotated spans | Generated stories 1.00; H01 precision ≈ 0.95; H07 1.00 after segmenter v4 |
| Expert review by a native-speaker Sinhala educator | All 30 suffix rules judged correct |
| Agreement with five native-speaker raters (n = 30) | Fluency r = −0.71, MTLD r = +0.51, coherence r = +0.47 |

```bash
pytest          # 129 tests (100 library + 29 web interface)
```

## Findings

Measured on 30 LLM-generated stories and 8 published human-written stories.

- **LLMs followed the literary-narration convention without being told to.** Register was never instructed in the prompt, yet all 30 generated stories narrated in the literary register. Five of eight published human stories narrate mainly in the spoken register, a recognised modern style.
- **Human writing spreads widely; LLM output clusters.** Composite SD is 0.686 for human stories against 0.157 for generated stories, a 4.36× ratio.
- **DARC cannot separate the three models on this corpus.** All 30 generated stories sit near the ceiling. On the human stories DARC spreads across 0.13–0.97.
- **The composite is a summary, not an overall rating.** It did not predict the raters' overall-quality item (r = +0.25). Read the four dimensions.
- **LaBSE does not measure Sinhala narrative coherence.** Unrelated sentences scored 0.4338 against 0.4932 for a coherent story (+0.059). Entity overlap achieves +0.426 on the same data. This is reported as a negative finding.

## Repository layout

```
src/sinhala_story_eval/   the library
app/                      the web application (Flask); adds no measurement of its own
pipeline/                 numbered stage scripts for the study
experiments/              design-cycle evidence: what was tried and rejected
data/                     generated stories and scores
docs/                     design system of the web application
deploy/                   systemd and nginx configuration
tests/
```

`experiments/` holds the design-cycle record with its numbers: the DARC perturbation evaluation, the LaBSE rejection, five rejected generation models, the DARC V0→V4 iterations and the segmentation defect.

## Limitations

- Unquoted and em-dash dialogue are invisible to the segmenter.
- A literary verb whose particle ය is written as a separate word is read as spoken (17 of 41 flags in the generated corpus, 2 of 558 in the human stories). DARC was left unchanged; this is reported as a limitation.
- Some proper nouns can be flagged when their ending resembles a verb ending.
- The rule set was reviewed by one native-speaker educator.
- Word-level accuracy on naturally generated text was not measured against a human annotator.
- The composite is normalised against 8 human stories, so its standard deviations are themselves uncertain.

## Citation

```bibtex
@software{sammandapperuma2026ssef,
  author = {Sammandapperuma, S.M.A.D.V.D.},
  title  = {sinhala-story-eval: Automated Quality Evaluation of LLM-Generated
            Sinhala Love Stories with a Dialogue-Aware Measure of Literary
            and Spoken Sinhala},
  year   = {2026},
  note   = {BSc (Hons) Computing, Coventry University / NIBM}
}
```

## References

- Ferguson, C. A. (1959). Diglossia. *Word*, 15(2), 325–340.
- Mawelle, I. (2023). A spectrum? Diglossia as seen in contemporary Sinhala novels. *Journal of Social Sciences and Humanities Review*, 8(3), 91–108. https://doi.org/10.4038/jsshr.v8i3.120
- Zubair, C. (2010). Diglossia versus register: Discursive classifications of two Sinhala varieties. *Proceedings of the Annual Meeting of the Berkeley Linguistics Society*, 36, 499–514. https://doi.org/10.3765/bls.v36i1.3933
- McCarthy, P. M., & Jarvis, S. (2010). MTLD, vocd-D, and HD-D. *Behavior Research Methods*, 42(2), 381–392.
- Salazar, J., et al. (2020). Masked language model scoring. *ACL 2020*, 2699–2712.
- Dhananjaya, V., Demotte, P., Ranathunga, S., & Jayasena, S. (2022). BERTifying Sinhala: A comprehensive analysis of pre-trained language models for Sinhala text classification. *Proceedings of LREC 2022*, 7377–7385. https://aclanthology.org/2022.lrec-1.803/

MIT licence.
