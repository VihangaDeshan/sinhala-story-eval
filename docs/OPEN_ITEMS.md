# Open items — writing side, not implementation

Recorded here so they are not lost. **None of these blocks the code, the
package, or the GitHub upload.** They are things to settle when Chapter 4
and Chapter 5 are being written, and they are parked deliberately rather
than kept in the working conversation.

Some of these may already have been resolved in earlier sessions. Check the
decision log before acting on any of them.

---

## 1. Correlation claim — check which coefficient was reported

`project.md` §5.2 states that no metric pair exceeds |r| = 0.50 across the
30 generated stories.

Recomputed with **Pearson** on `all38_v4_scores.csv`, 2026-09-19:

    pppl_overall x coherence   r = -0.5034
    pppl_overall x mtld        r = +0.4207
    coherence    x mtld        r = -0.3894
    darc         x mtld        r = +0.3542
    darc         x coherence   r = +0.0990
    pppl_overall x darc        r = +0.0106

One pair sits 0.0034 above the stated threshold. The substantive point — the
four dimensions are largely independent, and none is redundant — is
unaffected.

**To check:** whether the reported figure was Spearman rather than Pearson.
If Spearman, recompute and use that. If Pearson, the sentence needs
rewording to something like "the strongest association is fluency–coherence
at r = −0.50, at the threshold; the remaining five pairs fall well below
it."

Reproduce with `python pipeline/05_validate.py`.

## 2. "Dialogue quantity not instructed" — wording

Prompt variant A2 contains:

    - Include several exchanges of dialogue between the characters.

So dialogue **presence** was instructed. Its **proportion** was not, which
is what keeps the DARC Balance sub-score non-circular. The claim is sound;
the wording "dialogue quantity was not instructed" is looser than the prompt
supports, and the prompt will be in the appendix.

## 3. MODEL_IDS in `pipeline/prompts_v3.py` does not match the executed run

The module records `kimi` and leaves `chatgpt` as a gap, and does not
mention deepseek. The corpus was produced with gemini-3.5-flash,
deepseek-v4-pro and gpt-5.6-sol.

The file is left unedited on purpose — it is a dated record from
2026-08-19, and silently correcting it would erase the design trail. The
ids actually used are in `pipeline/01_generate.py` with a note. Reconcile
the two in the methodology rather than in the file.

## 4. A1-vs-A2 pilot data

`prompts_v3.STAGES` records a pilot of 2 topics x 3 models x 2 variants =
12 generations, which did not enter the corpus. If those generations still
exist they are the direct control for the spontaneous-adherence finding —
what the models did when register *was* instructed. They would belong in
`experiments/`.

## 5. Specification-level limitation

`prompts_v3.py` flags it itself: the topics specify weather, season and
sensory atmosphere, which pushes models toward descriptive narration and
depresses the DARC Balance sub-score for reasons unrelated to model
competence. Identical across models, so RQ4 is unaffected; absolute DARC
values are shifted, which matters for the composite. Normalisation to 25–40
words was specified but not applied.

Confirm this appears in the limitations section. It is an accepted
limitation, not an oversight.

## 6. `dia_spans` vs "dialogue lines"

Stage 05 reports a human mean `dia_spans` of 11.125; `project.md` §5 reports
human "Dialogue lines" as 12.5. Confirm whether these are the same measure
before quoting either.

---

## Verified on 2026-09-19 — no action needed

- **No English-preamble leak in the corpus.** All 38 texts scanned: none
  begins in Latin script, and every generated story begins in Sinhala. The
  only Latin runs are in-story code-switching (`bug`, `API` in the IT
  night-shift story; `Hmm` and an English phrase in two human stories). The
  risk flagged in `prompts_v3.strip_preamble` did not materialise.
- **Variant A2 omits the register instruction.** Diffed mechanically: A1 and
  A2 differ by exactly one line, the register instruction. Run
  `python pipeline/01_generate.py --dry-run` to see it.
- **The package reproduces the reported figures**: 90 tests pass; stage 02
  reproduces all 38 rows of the score table and stage 04 all 38 composites,
  with zero mismatches; stage 05 reproduces every discrimination ratio, the
  composite discrimination ratio and the variance ratio.
