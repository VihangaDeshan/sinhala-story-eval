# -*- coding: utf-8 -*-
"""
Narrative / dialogue segmentation — v4.

Every register measurement depends on this split being right, so a defect
here propagates into every DARC number. It was validated against manual
annotation on five stories (142 spans).

THE v4 RULE
-----------
A dialogue span may not cross a paragraph break.

In Sinhala prose a dialogue turn occupies its own paragraph. Constraining
spans to paragraphs means an unpaired quotation mark is contained within its
own paragraph instead of shifting every subsequent pairing in the story.

WHY IT WAS NEEDED
-----------------
H07 in the reference corpus opens a span with U+0022 and closes it with
U+0027 (a straight apostrophe). U+0027 was not in the quote set, so that
closing mark was invisible: twelve empty spans, six narration passages
captured as dialogue, precision 0.143.

REJECTED ALTERNATIVE
--------------------
Adding U+0027 to the quote set fixes H07 but breaks H04 (0 → 40 empty spans)
and H05 (0 → 63), which use apostrophes as ordinary punctuation. One story
repaired at the cost of two.

EFFECT
------
2 of 38 stories changed. All 30 generated stories were unaffected — their
quotation marks were already balanced.

KNOWN LIMIT (D21)
-----------------
Unquoted and em-dash dialogue are invisible here. The paragraph rule
contains pairing failures; it does not detect dialogue that was never
quoted. The generation prompt requires double quotation marks for this
reason.
"""

import re

# Eight glyph variants. LLM output is inconsistent about which it uses.
QUOTES = '"\u201c\u201d\u2018\u2019\u201e\u00ab\u00bb'
QP = f'[{QUOTES}]([^{QUOTES}]*)[{QUOTES}]'

_PARA_SPLIT = re.compile(r'\n\s*\n')


def segment(text):
    """Split into (narrative, dialogue).

    Identical to the naive whole-text scan for any text whose quotation
    marks are balanced.
    """
    dia_parts, nar_parts = [], []
    for para in _PARA_SPLIT.split(text):
        if not para or not para.strip():
            continue
        found = re.findall(QP, para, re.DOTALL)
        dia_parts += [x.strip() for x in found if x.strip()]
        nar_parts.append(re.sub(QP, ' ', para))
    narrative = re.sub(r'\s+', ' ', ' '.join(nar_parts)).strip()
    return narrative, ' '.join(dia_parts)


def dialogue_spans(text):
    """Every quoted span, paragraph-bounded. Used for dialogue-structure
    counts, which discriminate between models where DARC does not."""
    out = []
    for para in _PARA_SPLIT.split(text):
        if para and para.strip():
            out += re.findall(QP, para, re.DOTALL)
    return out
