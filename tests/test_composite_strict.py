# -*- coding: utf-8 -*-
"""Strict dimension keys on the composite.

These tests exist because of a defect found on 2026-09-19 while regression
checking the package against the reported figures. `composite()` skipped any
dimension whose key was absent and renormalised the remaining weights, which
is wanted behaviour for a story scored without a GPU — but it made a
MISTYPED key indistinguishable from a deliberate omission.

A record built with the key `fluency` instead of `pppl_overall` returned a
plausible three-dimension composite with no error. Across the 38-story
corpus every composite was wrong, N01_CoastTrain/gemini by 0.165 (0.0905
against the reported 0.2555). Nothing in the output indicated a problem.

The rule now: omission must be explicit.
"""

import pytest
from sinhala_story_eval import composite, z_scores


# Values for N01_CoastTrain / gemini, which reproduces to 0.2555.
FULL = {
    "pppl_overall": 5.56,
    "darc": 0.975,
    "coherence": 0.0497,
    "mtld": 353.81,
}


def test_full_record_reproduces_reported_composite():
    score, _ = composite(FULL)
    assert score == 0.2555


def test_mistyped_dimension_key_raises():
    """The exact defect: `fluency` is not the key, `pppl_overall` is."""
    record = {"fluency": 5.56, "darc": 0.975,
              "coherence": 0.0497, "mtld": 353.81}
    with pytest.raises(KeyError):
        composite(record)


def test_error_names_the_missing_key():
    record = dict(FULL)
    del record["coherence"]
    with pytest.raises(KeyError) as exc:
        composite(record)
    assert "coherence" in str(exc.value)


def test_explicit_none_still_renormalises():
    """Deliberate omission is still supported — this is the CPU-only case."""
    record = dict(FULL, pppl_overall=None)
    score, z = composite(record)
    assert z["Fluency"] is None
    assert score is not None


def test_explicit_none_differs_from_full_record():
    """Guards against the renormalised value silently equalling the full
    one, which would make the two cases indistinguishable in a test."""
    full, _ = composite(FULL)
    partial, _ = composite(dict(FULL, pppl_overall=None))
    assert full != partial


def test_strict_false_restores_lenient_behaviour():
    record = {"darc": 0.975, "coherence": 0.0497, "mtld": 353.81}
    score, _ = composite(record, strict=False)
    assert score is not None


def test_z_scores_is_strict_too():
    with pytest.raises(KeyError):
        z_scores({"fluency": 5.56, "darc": 0.975,
                  "coherence": 0.0497, "mtld": 353.81})


def test_all_dimensions_none_returns_none():
    record = {k: None for k in FULL}
    score, z = composite(record)
    assert score is None
    assert all(v is None for v in z.values())
