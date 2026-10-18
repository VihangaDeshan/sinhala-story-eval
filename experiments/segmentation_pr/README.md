# segmentation_pr

**Decision:** segmenter V4. A dialogue span may not cross a paragraph
break. Dissertation Section 5.6.1 and Appendix E.9.

## Validation sample

Manual annotation of 142 detected dialogue spans in five stories.

| Story | Source | Spans | Precision | Recall |
|---|---|---|---|---|
| N03_GalleFort | Gemini | 18 | 1.00 | 1.00 |
| N10_Mirissa | GPT | 40 | 1.00 | 1.00 |
| N07_Rajarata | DeepSeek | 28 | 1.00 | 1.00 |
| H01 | Human | 35 | ≈ 0.95 | not recorded |
| H07, segmenter V3 | Human | 21 | 0.143 (3 of 21) | not recorded |
| H07, segmenter V4 | Human | 21 | 1.00 (21 of 21) | not recorded |

H01's errors were quoted text that is not speech, such as a text message.
H07 was included on purpose as a hard case, because it has an odd number of
quotation marks (43).

## Root cause in H07

One speech turn opens with U+0022 and closes with U+0027, the straight
apostrophe, which was not a recognised quotation mark. Every later pairing
shifted by one position, and narration of up to 132 words was captured as
dialogue.

## Candidate fixes

| Fix | Effect | Decision |
|---|---|---|
| Add U+0027 to the quotation marks | H07 repaired, but H04 went from 0 to 40 spans (all empty) and H05 from 0 to 63 (62 empty), because both use the apostrophe as ordinary punctuation | Rejected |
| A span may not cross a paragraph break | An unpaired mark stays inside its own paragraph | Adopted as V4 |

## Effect of V4 on the 38-story corpus

Empty spans 13 → 0. H07 DARC 0.1833 → 0.9718; H02 0.5133 → 0.5632. Only 2
of 38 stories changed, and none of the 30 generated stories. Dialogue that is
not in quotation marks remains invisible to the segmenter.
