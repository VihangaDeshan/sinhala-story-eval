# -*- coding: utf-8 -*-
"""FR-01: the framework accepts Unicode Sinhala and rejects everything else.

Ten tests. The last one runs the check over every corpus story found under
data/, so the rule is shown never to reject a real story.
"""
import glob
import json
import os

import pytest

from sinhala_story_eval import evaluate, validate_text

SINHALA = "කමල් උදේම ගමට ගියේය. ඔහු ගෙදර ආවේ හවස් වෙලාවේය. "


def test_pure_sinhala_is_accepted():
    assert validate_text(SINHALA) is None


def test_sinhala_with_digits_punctuation_and_quotes_is_accepted():
    text = '"මම හෙට එනවා," ඔහු 2026 දී කීවේය! ඇය "හරි" කියා සිනාසුණාය.'
    assert validate_text(text) is None


def test_one_latin_loanword_in_a_sinhala_passage_is_accepted():
    assert validate_text(SINHALA * 6 + "ඔහු WiFi එක සොයා ගත්තේය.") is None


def test_english_is_rejected():
    with pytest.raises(ValueError, match="no Sinhala"):
        validate_text("He went to the village early and came home at dusk.")


def test_romanised_sinhala_is_rejected():
    with pytest.raises(ValueError, match="no Sinhala"):
        validate_text("mama heta enawa, oya enawada? eyaa gedara giyaa.")


def test_mixed_script_is_rejected():
    with pytest.raises(ValueError, match="mixed-script"):
        validate_text(SINHALA + "He went to the village and came home at dusk.")


def test_empty_and_whitespace_are_rejected():
    for blank in ("", "   ", "\n\n\t"):
        with pytest.raises(ValueError, match="empty"):
            validate_text(blank)


def test_non_string_input_is_rejected():
    for bad in (None, 42, b"bytes", ["list"]):
        with pytest.raises(TypeError):
            validate_text(bad)


def test_evaluate_rejects_before_any_metric_runs():
    with pytest.raises(ValueError):
        evaluate("He went to the village early and came home at dusk.")


def _corpus_texts():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    texts = []
    for path in glob.glob(os.path.join(root, "data", "**", "*.json"), recursive=True):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            texts += [(path, d.get("id"), d["text"]) for d in data
                      if isinstance(d, dict) and isinstance(d.get("text"), str)]
    return texts


def test_every_corpus_story_is_accepted():
    texts = _corpus_texts()
    if not texts:
        pytest.skip("no corpus story files found under data/")
    rejected = []
    for path, sid, text in texts:
        try:
            validate_text(text)
        except (ValueError, TypeError) as e:
            rejected.append((os.path.basename(path), sid, str(e)))
    assert not rejected, rejected
