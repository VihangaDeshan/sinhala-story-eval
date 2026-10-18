# coherence_selection

**Decision:** coherence is measured by entity overlap between adjacent
sentences, after Sinhala case stemming. LaBSE sentence embeddings were
implemented first and rejected. Dissertation Section 4.6.3.

## LaBSE against entity overlap

| Method | Coherent story | Unrelated sentences | Discrimination |
|---|---|---|---|
| LaBSE, adjacent sentences | 0.4932 | 0.4338 | +0.059 |
| LaBSE, window of 3 | 0.4873 | 0.4118 | +0.076 |
| Entity overlap | 0.4259 | 0.0000 | **+0.426** |

Ten unrelated sentences scored almost the same as a coherent story under
LaBSE. LaBSE is trained to align translation pairs, so it measures shared
meaning across languages, not whether a story holds together. This is
reported as a negative finding.

## Stemming

Sinhala case endings give one character several surface forms, so
unstemmed matching misses the same entity in neighbouring sentences.

| Tokens | Coherence |
|---|---|
| Raw | 0.1429 |
| Stemmed | 0.4286 (3.0×) |

MTLD does not stem; there the effect is only −4.9%.

## Validity control

Shuffling sentences is the wrong test for this measure, because entity
overlap measures continuity, not order. The control used is entity
continuity: same characters throughout 0.7222, partial continuity 0.1111,
new characters in every sentence 0.0000.

Real stories score around 0.08 (human reference mean 0.080). The higher
figures above come from short test texts that repeat names in nearly every
sentence.

The implementation and these figures are also recorded in
`src/sinhala_story_eval/metrics/coherence.py`.
