# -*- coding: utf-8 -*-
"""Coherence, lexical diversity and the composite."""

import pytest
from sinhala_story_eval import coherence, mtld, ttr, evaluate, composite


CONTINUOUS = """කමල් උදෑසන අවදි විය. කමල් තේ වතුයාය බලා ගියේය. එහිදී කමල් නදීෂාව දුටුවේය. නදීෂා මල් නෙළමින් සිටියාය. කමල් නදීෂා වෙත ළං විය. කමල් සහ නදීෂා කතා කළහ. නදීෂා කමල්ට කැමති විය. කමල් සහ නදීෂා නිතර හමු වූහ. කමල් නදීෂාට ආදරය කළේය. අවසානයේ කමල් සහ නදීෂා විවාහ වූහ."""

DISCONTINUOUS = """කමල් උදෑසන අවදි විය. සුනිල් තේ වතුයාය බලා ගියේය. එහිදී මාලනී රංජනීව දුටුවේය. ප්‍රියන්ත මල් නෙළමින් සිටියාය. චමිල් අනුෂා වෙත ළං විය. සමන් සහ කුමාරි කතා කළහ. දිනේෂ් ලක්මාලිට කැමති විය. නිමල් සහ සිතාරා නිතර හමු වූහ. රුවන් තිලකාට ආදරය කළේය. අවසානයේ ගාමිණී සහ පද්මා විවාහ වූහ."""


def test_coherence_tracks_entity_continuity():
    """The correct control for this metric. Shuffling is NOT — it raises
    the score, because entity overlap measures continuity, not order."""
    assert coherence(CONTINUOUS) > coherence(DISCONTINUOUS)


def test_coherence_needs_two_sentences():
    assert coherence("කමල් ගියේය.") is None


def test_mtld_tracks_vocabulary_richness():
    rich = ("කමල් උදෑසන අවදි විය. තරුණයා කුඹුරට ගමන් කළේය. අහසේ වලාකුළු "
            "පාවෙමින් තිබුණි. සුළඟ මෘදු ලෙස හමා ගියේය. පක්ෂීන් මධුර ගීත ගැයූහ.")
    poor = "කමල් ගියා. " * 10
    assert mtld(rich) > mtld(poor)


def test_mtld_needs_ten_tokens():
    assert mtld("කමල් ගියේය.") is None


def test_ttr_is_length_sensitive():
    """Why MTLD is primary and TTR only a baseline."""
    short = "කමල් උදෑසන අවදි විය."
    long = short * 10
    assert ttr(short) > ttr(long)


def test_evaluate_without_fluency():
    r = evaluate(CONTINUOUS)
    assert r["pppl_overall"] is None
    assert r["darc"] is not None
    assert r["composite"] is not None


def test_composite_renormalises_when_fluency_missing():
    """A record scored without fluency must still yield a composite over
    the remaining three dimensions."""
    r = evaluate(CONTINUOUS)
    score, z = composite(r)
    assert z["Fluency"] is None
    assert score is not None


def test_human_reference_is_the_origin():
    """Composite is defined against the human corpus, so a record at the
    human mean scores 0. This is the definition, not a finding."""
    from sinhala_story_eval import HUMAN_REFERENCE
    at_mean = {k: v[0] for k, v in HUMAN_REFERENCE.items()}
    score, _ = composite(at_mean)
    assert abs(score) < 1e-9
