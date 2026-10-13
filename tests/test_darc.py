# -*- coding: utf-8 -*-
"""DARC regression tests.

These lock in the validation figures reported in the dissertation. If a
rule change breaks one of them, that change needs a decision-log entry
before it ships.
"""

import pytest
from sinhala_story_eval import darc, classify_register, segment


# Documented literary/spoken minimal pairs. Same verb, same meaning; only
# the subject-agreement suffix differs.
MINIMAL_PAIRS = [
    ("ගැහුවේය", "ගැහුවා"),    # Weerasinghe et al. (2013)
    ("ගියේය", "ගියා"),
    ("කීවාය", "කිව්වා"),
    ("දුටුවේය", "දැක්කා"),
    ("සිටියාය", "හිටියා"),
    ("කළහ", "කළා"),
    ("වූහ", "වුනා"),
    ("කරති", "කරනවා"),
    ("තිබිණි", "තිබුනා"),
    ("පැමිණියේය", "ආවා"),
    ("බැලීය", "බැලුවා"),
    ("ලැබුණි", "ලැබුනා"),
    ("විය", "වුණා"),
    ("ඇසුවේය", "ඇහුවා"),
    ("දුන්නේය", "දුන්නා"),
    ("කළේය", "කළා"),
    ("ගැයූහ", "ගැයුවා"),
    ("කීවේය", "කිව්වා"),
    ("සිටියේය", "හිටියා"),
    ("දුටුවාය", "දැක්කා"),
]

# Verbs outside the common set. v2 missed the spoken side of these because
# literary endings sat in Tier A while spoken ones sat in Tier B — an
# asymmetry that made the measure UNDER-detect register mixing.
RARE_PAIRS = [
    ("නැළවීය", "නැළෙව්වා"),
    ("සැරසුණාය", "සැරසුනා"),
    ("කැළඹිණි", "කැළඹුනා"),
    ("පිපුණි", "පිපුනා"),
    ("නැගුණි", "නැගුනා"),
    ("සැඟවිණි", "හැංගුනා"),
    ("ඉල්ලීය", "ඉල්ලුවා"),
    ("තෙරපිණි", "තෙරපුනා"),
    ("නැටුවාය", "නැටුවා"),
    ("හැඬුවාය", "හැඬුවා"),
]

# Register-neutral. The v1 defect tagged several of these: nouns ending
# -ා as spoken verbs, adjectives ending -ති as literary ones.
NEUTRAL_WORDS = [
    "කමල්", "නදීෂා", "හදවත", "සිත", "දෑස", "උදෑසන", "ගම", "මල්",
    "අහස", "සුළඟ", "පොත", "ගෙදර", "වතුර", "නගරය", "පාර", "ගස",
    "මීදුම", "කන්ද", "හිරු", "සීතල", "නිවස", "පියා", "දරුවා",
    "තාත්තා", "අම්මා", "සති", "නැති", "බලා", "ගලා", "මංගල්‍යය",
    "ප්‍රේමය", "ආදරය", "සතුට", "දුක",
]


@pytest.mark.parametrize("literary,spoken", MINIMAL_PAIRS)
def test_minimal_pairs(literary, spoken):
    assert classify_register(literary) == "L", f"{literary} should be literary"
    assert classify_register(spoken) == "S", f"{spoken} should be spoken"


@pytest.mark.parametrize("literary,spoken", RARE_PAIRS)
def test_rare_verbs(literary, spoken):
    assert classify_register(literary) == "L", f"{literary} should be literary"
    assert classify_register(spoken) == "S", f"{spoken} should be spoken"


@pytest.mark.parametrize("word", NEUTRAL_WORDS)
def test_no_false_positives(word):
    assert classify_register(word) is None, \
        f"{word} is register-neutral but was tagged {classify_register(word)}"


def test_yi_ambiguity_resolved_by_stem():
    """-යි marks both the literary 3sg present and the spoken predicative.
    Stem type decides which."""
    assert classify_register("කරයි") == "L"      # verb stem
    assert classify_register("හොඳයි") == "S"     # adjective stem
    assert classify_register("කැමතියි") == "S"
    assert classify_register("ආදරෙයි") == "S"


GOOD = """කමල් උදෑසන අවදි විය. ඔහු තේ වතුයාය බලා පිටත් විය. එහිදී ඔහු නදීෂාව දුටුවේය.

"ආයුබෝවන්. ඔයා මෙහෙ අලුත්ද?" කමල් ඇසුවේය.

"ඔව්. මම ඊයෙ තමයි ආවෙ," ඇය කීවාය.

ඇගේ කටහඬ ඔහුගේ හදවතට කා වැදිණි. ඔවුහු නිතර හමු වූහ."""

SPOKEN_IN_NARRATION = """කමල් උදෑසන අවදි වුණා. එයා තේ වත්තට ගියා. එහෙදි එයා නදීෂාව දැක්කා.

"ආයුබෝවන්. ඔයා මෙහෙ අලුත්ද?" කමල් ඇහුවා.

"ඔව්. මම ඊයෙ තමයි ආවෙ," එයා කිව්වා.

එයාගෙ කටහඬ එයාගෙ හිතට වැදුනා."""

LITERARY_IN_DIALOGUE = """කමල් උදෑසන අවදි විය. ඔහු තේ වතුයාය බලා පිටත් විය. එහිදී ඔහු නදීෂාව දුටුවේය.

"ආයුබෝවන්. ඔබ මෙහි නවකයෙක් වේද?" කමල් ඇසුවේය.

"එසේය. මම ඊයේ පැමිණියෙමි," ඇය කීවාය.

ඇගේ කටහඬ ඔහුගේ හදවතට කා වැදිණි."""


def test_corruption_is_detected():
    """Three texts with identical content differing only in verb forms,
    so any score difference is attributable to register alone."""
    good, _ = darc(GOOD)
    nar_bad, _ = darc(SPOKEN_IN_NARRATION)
    dia_bad, _ = darc(LITERARY_IN_DIALOGUE)
    assert good > nar_bad
    assert good > dia_bad


def test_subscore_identifies_the_defect():
    """The sub-score that drops says WHICH defect occurred — diagnostic
    information a single figure cannot carry."""
    _, good = darc(GOOD)
    _, nar_bad = darc(SPOKEN_IN_NARRATION)
    _, dia_bad = darc(LITERARY_IN_DIALOGUE)
    assert nar_bad["nar"] < good["nar"]      # narration defect shows there
    assert dia_bad["dia"] < good["dia"]      # dialogue defect shows there


def test_weight_sensitivity():
    """The correct story must rank first under every weighting tried."""
    grids = [(0.50, 0.25, 0.25), (0.40, 0.30, 0.30), (0.60, 0.20, 0.20),
             (0.34, 0.33, 0.33), (0.45, 0.30, 0.25), (0.55, 0.25, 0.20)]
    for wn, wd, wb in grids:
        g, _ = darc(GOOD, wn, wd, wb)
        a, _ = darc(SPOKEN_IN_NARRATION, wn, wd, wb)
        b, _ = darc(LITERARY_IN_DIALOGUE, wn, wd, wb)
        assert g > a and g > b, f"failed at weights {wn}/{wd}/{wb}"


def test_handles_edge_cases_without_crashing():
    for text in ["", "   ", "Hello world.", "කමල්",
                 "කමල් ගමට පැමිණියේය.",          # no dialogue
                 '"ආයුබෝවන්."',                   # dialogue only
                 'ඔහු කීවේය. "මම යනවා']:          # unclosed quote
        score, sub = darc(text)
        assert 0.0 <= score <= 1.0
