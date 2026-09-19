# -*- coding: utf-8 -*-
"""
Composite score — equal-weighted z-scores against a human reference.

THE SCALE PROBLEM
-----------------
The four dimensions are not commensurable. PPPL is unbounded (4–28), DARC
and coherence run 0–1, MTLD runs 166–648. They cannot be averaged raw, so a
reference distribution is needed to put them on a common footing.

    z_d = (x_d − reference_mean_d) / reference_SD_d
    composite = mean(z_Fluency, z_DARC, z_Coherence, z_MTLD)

Fluency is lower-is-better, so its z-score is sign-flipped.

WHY THE HUMAN CORPUS IS THE REFERENCE
-------------------------------------
Two alternatives, both rejected:

  - Normalising against the GENERATED corpus makes its own mean the origin.
    DARC 0.979 would become "average" when it is at ceiling. Circular.

  - Normalising against SYNTHETIC values is worse. Synthetic test text
    scored coherence 0.43 where real writing scores 0.08, and MTLD ~50
    where real writing scores 341.

The human corpus is published Sinhala fiction — the only distribution here
that represents the language as actually written.

CONSEQUENCE
-----------
The human mean composite is 0.000 by construction. That is the definition
of the origin, not a finding. Do not report it as one.

NEVER REPORT THE COMPOSITE ALONE
--------------------------------
Generated stories beat the human reference on register consistency and lose
to it on entity coherence by similar magnitudes, so equal weighting lets
them cancel:

    gemini    DARC +1.25   Coherence −1.23   sum +0.02
    deepseek  DARC +1.22   Coherence −1.71   sum −0.49
    gpt       DARC +1.24   Coherence −1.91   sum −0.67

A composite near zero means the dimensions DISAGREE, not that quality is
average. Reporting it alone conceals the most informative pattern in the
data. Always publish the per-dimension z-scores beside it.

LIMITATIONS TO STATE
--------------------
  - n = 8 for the reference, so the SDs are themselves uncertain.
  - Human fluency SD is 8.005 on a mean of 11.57 (CV 69%), because human
    fluency ranges 4.14–27.51. That wide denominator compresses fluency
    z-scores relative to the other three dimensions.
  - Equal weighting is a stated choice, not a derived optimum.
"""

import statistics

__all__ = ["DIMENSIONS", "reference_from", "z_scores", "composite",
           "HUMAN_REFERENCE"]

# (key, label, lower_is_better)
DIMENSIONS = [
    ("pppl_overall", "Fluency",   True),
    ("darc",         "DARC",      False),
    ("coherence",    "Coherence", False),
    ("mtld",         "MTLD",      False),
]

EQUAL_WEIGHTS = {"Fluency": 0.25, "DARC": 0.25,
                 "Coherence": 0.25, "MTLD": 0.25}

# Measured on the 8-story human reference corpus, segmenter v4.
# (mean, SD)
# Full precision deliberately: rounding these to 4 dp shifts composites in
# the third decimal, which would stop the package reproducing the figures
# reported in the dissertation.
HUMAN_REFERENCE = {
    "pppl_overall": (11.56875,  8.004967096389949),
    "darc":         (0.5734375, 0.3281087839530403),
    "coherence":    (0.08025,   0.029579529601205145),
    "mtld":         (340.7525,  162.4884800971617),
}


def reference_from(records):
    """Build a reference distribution from scored records.

    Use this rather than HUMAN_REFERENCE when working with a different or
    extended reference corpus.
    """
    if len(records) < 3:
        raise ValueError("A reference distribution needs at least 3 texts")
    ref = {}
    for key, _, _ in DIMENSIONS:
        v = [r[key] for r in records if r.get(key) is not None]
        if len(v) < 3:
            raise ValueError(f"Too few usable values for {key}")
        ref[key] = (statistics.mean(v), statistics.stdev(v))
    return ref


def _check_keys(record):
    """Require every dimension key to be stated explicitly.

    WHY THIS EXISTS
    ---------------
    Renormalisation over the present dimensions is a wanted feature: a story
    scored without a GPU still yields a composite over the other three. But
    it made an absent key indistinguishable from a mistyped one, so a record
    built with the key `fluency` instead of `pppl_overall` returned a
    plausible composite computed over three dimensions, with no error. On
    the project corpus that silently shifted every one of the 38 composites,
    by up to 0.17.

    The rule is therefore: omission must be deliberate. All four keys must
    appear; pass an explicit None for a dimension that was not measured.
    """
    missing = [key for key, _, _ in DIMENSIONS if key not in record]
    if missing:
        raise KeyError(
            "record is missing dimension key(s): " + ", ".join(missing) +
            ". Pass an explicit None for any dimension that was not "
            "measured, e.g. {'pppl_overall': None}, so that an omission "
            "cannot be confused with a typo. Expected keys: " +
            ", ".join(key for key, _, _ in DIMENSIONS) +
            ". To restore the old lenient behaviour, pass strict=False."
        )


def z_scores(record, reference=None, strict=True):
    """Per-dimension z-scores, fluency already sign-flipped.

    With `strict` (the default) every dimension key must be present in
    `record`; use an explicit None to mark a dimension as not measured.
    """
    if strict:
        _check_keys(record)
    ref = reference or HUMAN_REFERENCE
    out = {}
    for key, label, lower_better in DIMENSIONS:
        if record.get(key) is None:
            out[label] = None
            continue
        mean, sd = ref[key]
        val = (record[key] - mean) / sd if sd else 0.0
        out[label] = round(-val if lower_better else val, 4)
    return out


def composite(record, reference=None, weights=None, strict=True):
    """Weighted mean of the z-scores.

    Dimensions whose value is None are skipped and the remaining weights
    renormalised, so a record scored without fluency still yields a
    composite over the other three.

    With `strict` (the default) a dimension key that is absent altogether
    raises KeyError rather than being treated as unmeasured — see
    `_check_keys`. Pass strict=False for the older lenient behaviour.
    """
    z = z_scores(record, reference, strict=strict)
    w = weights or EQUAL_WEIGHTS
    present = {k: v for k, v in z.items() if v is not None}
    if not present:
        return None, z
    total_w = sum(w[k] for k in present)
    score = sum(w[k] * v for k, v in present.items()) / total_w
    return round(score, 4), z
