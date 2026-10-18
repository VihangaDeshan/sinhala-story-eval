# darc_iterations

**Decision:** the DARC rule set in `src/sinhala_story_eval/lexicon.py`.
It reached its released form through five versions. Each change answered a
measured failure. Dissertation Section 4.6.1 and Table 4.4.

## Before V0: rejected alternative

A corpus-derived register lexicon (log-odds ratio over a labelled corpus)
was considered first and rejected: no annotated Sinhala register corpus was
available, and the substitutes were noisy. Rules from verb morphology were
used instead.

## Versions

| Version | Change | Reason |
|---|---|---|
| V0 | Single suffix list, no stem guard | First implementation |
| V1 | Base-consonant length guard replaces character length | Sinhala vowel signs are combining marks, so a character count overstates word length and missed short verbs |
| V2 | Endings split into Tier A (verb-only) and Tier B (also on nouns and adjectives) | False positives of 6–10% on real model output |
| V3 | Verb-root guard (129 roots) on Tier B; -යි resolved by stem type; rare verb forms added | The remaining false positives were nouns passing a Tier B ending |
| V4 | Segmentation only: a dialogue span may not cross a paragraph break | See `../segmentation_pr/` |

The rule lists did not change between V3 and V4.

## Development numbers

On items written by the researcher: 40/40 minimal-pair classifications,
20/20 less frequent verbs, no false positives in 48 negative cases. These
are development data. They show that the rules work at all; they are not
evaluation results. The evaluation is in `../darc_eval/`.

## Expert review

A native Sinhala-speaking educator reviewed the full rule set on
3 October 2026 and judged all 30 suffix rules correct, with one qualifying
note: spoken narration is not itself an error, so DARC measures adherence
to the literary-narration convention (dissertation Appendix E.8).
