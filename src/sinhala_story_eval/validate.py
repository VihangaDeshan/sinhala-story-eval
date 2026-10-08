# -*- coding: utf-8 -*-
"""Input validation for FR-01.

FR-01 requires the framework to accept Unicode Sinhala and to reject
romanised or mixed-script input with a reason, rather than scoring it.
Every metric in this package assumes Sinhala script: DARC reads Sinhala verb
endings, coherence stems Sinhala case markers, and SinBERT was trained on
Sinhala text. Scoring English or romanised Sinhala would return numbers that
look valid and mean nothing.

The rule: among the letters in the text, at least MIN_SINHALA_SHARE must be
Sinhala-script characters (U+0D80 to U+0DFF). Digits, punctuation, quotation
marks, whitespace and the zero-width joiner used in Sinhala conjuncts are not
letters and are ignored. The threshold leaves room for the occasional English
loanword written in Latin script inside an otherwise Sinhala story.
"""

SINHALA_START = 0x0D80
SINHALA_END = 0x0DFF
MIN_SINHALA_SHARE = 0.95


def sinhala_share(text):
    """Return (share, sinhala_count, other_letter_count) for text."""
    sinhala = other = 0
    for ch in text:
        if SINHALA_START <= ord(ch) <= SINHALA_END:
            sinhala += 1
        elif ch.isalpha():
            other += 1
    total = sinhala + other
    return (sinhala / total if total else 0.0), sinhala, other


def validate_text(text):
    """Raise if text is not Unicode Sinhala; return None if it is.

    TypeError  -- text is not a str
    ValueError -- text is empty, has no Sinhala, or is mixed-script/romanised
    """
    if not isinstance(text, str):
        raise TypeError(
            f"Story text must be a str, got {type(text).__name__}."
        )
    if not text.strip():
        raise ValueError("Story text is empty.")
    share, sinhala, other = sinhala_share(text)
    if sinhala == 0:
        raise ValueError(
            "Input contains no Sinhala script. The framework scores Unicode "
            "Sinhala only; romanised Sinhala and other languages are rejected."
        )
    if share < MIN_SINHALA_SHARE:
        raise ValueError(
            f"Input is mixed-script: {share:.1%} of its letters are Sinhala, "
            f"below the required {MIN_SINHALA_SHARE:.0%}. The framework scores "
            "Unicode Sinhala only."
        )
    return None
