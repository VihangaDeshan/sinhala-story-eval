# -*- coding: utf-8 -*-
"""Segmentation tests, including the v4 paragraph rule."""

from sinhala_story_eval import segment, dialogue_spans


def test_basic_split():
    text = 'කමල් ගියේය.\n\n"මම එනවා," ඔහු කීවේය.\n\nඇය සිටියාය.'
    nar, dia = segment(text)
    assert "මම එනවා" in dia
    assert "කමල් ගියේය" in nar
    assert "මම එනවා" not in nar


def test_quote_glyph_variants():
    """LLM output is inconsistent about which quote characters it uses."""
    for open_q, close_q in [('"', '"'), ('\u201c', '\u201d'),
                            ('\u2018', '\u2019'), ('\u00ab', '\u00bb')]:
        text = f'කමල් කීවේය.\n\n{open_q}මම යනවා{close_q} ඔහු කීවේය.'
        _, dia = segment(text)
        assert "මම යනවා" in dia, f"failed for {open_q}...{close_q}"


def test_unpaired_quote_is_contained_to_its_paragraph():
    """The v4 rule. An unpaired mark must not swallow later narration.

    H07 in the reference corpus opened with U+0022 and closed with U+0027,
    which was not in the quote set: twelve empty spans and six narration
    passages captured as dialogue, precision 0.143.
    """
    text = (
        'පළමු ඡේදය නිරූපණයකි. මෙය narration වේ.\n\n'
        '"නොවැසූ උද්ධෘතයක්\n\n'
        'දෙවන ඡේදය ද narration වේ. මෙය dialogue නොවේ.\n\n'
        'තෙවන ඡේදය ද narration වේ.'
    )
    nar, dia = segment(text)
    assert "දෙවන ඡේදය" in nar, "narration leaked into dialogue"
    assert "තෙවන ඡේදය" in nar


def test_no_empty_spans():
    """Adjacent quote marks produced zero-word spans under the old scan."""
    text = 'කමල් කීවේය.\n\n"" "මම යනවා," ඔහු කීවේය.'
    spans = dialogue_spans(text)
    assert all(s.strip() for s in spans if s), "empty span returned"


def test_no_dialogue():
    text = "කමල් ගමට පැමිණියේය. ඔහු සතුටු විය."
    nar, dia = segment(text)
    assert dia == ""
    assert "කමල්" in nar
