# -*- coding: utf-8 -*-
"""
DARC — Dialog-Aware Register Consistency.

The novel contribution of this framework: an automated measure of
diglossic register consistency for Sinhala narrative text.

WHAT IT MEASURES
----------------
Sinhala is diglossic. Narrative prose conventionally uses the LITERARY
register for narration and the SPOKEN register for character dialogue.
DARC quantifies how consistently a text observes that separation.

    Narrative Register  (50%)  nL / (nL + nS)   narration should be literary
    Dialogue Register   (25%)  dS / (dL + dS)   dialogue should be spoken
    Register Balance    (25%)  1.0 if dialogue is 15–50% of tokens

    DARC = 0.50·narrative + 0.25·dialogue + 0.25·balance      range 0–1

WEIGHTS
-------
50/25/25 is a stated design choice, not a derived optimum. A six-point
sensitivity grid found the correct story ranks first under every weighting
tested.

VALIDATION
----------
    minimal pairs, common verbs    40/40  = 100%
    minimal pairs, rare verbs      20/20  = 100%
    false positives                 0/48  =   0%
    synthetic corruption gap             +0.183
    segmentation precision/recall  5 stories, 142 spans, manually annotated

COVERAGE IS ~35% BY DESIGN
--------------------------
Nouns, adjectives and many particles are register-neutral. DARC measures
the ratio AMONG register-marked tokens, not among all tokens. This is not a
gap in the rule set.

INTERPRETING A HIGH SCORE
-------------------------
A near-ceiling DARC score means the text observes the convention. It does
NOT mean the text is good. On the project corpus all 30 generated stories
scored ≥ 0.90 without register having been instructed, so DARC could not
discriminate between models there — while on the human reference corpus it
spread across 0.13–0.97. The measure discriminates; a corpus that is
uniformly conventional gives it nothing to discriminate.
"""

from ..tokenize import tok, ncons
from ..segment import segment
from ..lexicon import (
    LIT_SUF_A, SPO_SUF_A, LIT_SUF_B, SPO_SUF_B,
    LIT_EXACT, SPO_EXACT, LIT_FUNC, SPO_FUNC,
    VERB_ROOTS, NEUTRAL,
)

__all__ = ["classify_register", "has_verb_root", "darc"]


def has_verb_root(stem):
    """True if `stem` begins with a known verb root, allowing up to two
    extra characters of morphology."""
    if stem in VERB_ROOTS:
        return True
    for r in VERB_ROOTS:
        if stem.startswith(r) and 0 <= len(stem) - len(r) <= 2:
            return True
    return False


def classify_register(w, debug=False):
    """Return 'L' (literary), 'S' (spoken) or None (register-neutral).

    Order matters. Exact-form and function-word lookups run before the
    suffix rules so that irregular forms are not mis-parsed by them.
    """
    def out(tag, rule):
        return (tag, rule) if debug else tag

    if w in NEUTRAL:
        return out(None, "NEUTRAL")
    if w in LIT_EXACT:
        return out("L", "LIT_EXACT")
    if w in SPO_EXACT:
        return out("S", "SPO_EXACT")
    if w in LIT_FUNC:
        return out("L", "LIT_FUNC")
    if w in SPO_FUNC:
        return out("S", "SPO_FUNC")

    # Tier A — verb-only endings, no stem check needed.
    # Longest first, so -නවා is not consumed by -වා.
    for s in sorted(SPO_SUF_A, key=len, reverse=True):
        if w.endswith(s) and ncons(w[:-len(s)]) >= 1:
            return out("S", f"A:{s}")
    for s in sorted(LIT_SUF_A, key=len, reverse=True):
        if w.endswith(s) and ncons(w[:-len(s)]) >= 1:
            return out("L", f"A:{s}")

    # Tier B — ambiguous endings, require a recognised verb stem.
    for s in sorted(SPO_SUF_B, key=len, reverse=True):
        if w.endswith(s):
            st = w[:-len(s)]
            if ncons(st) >= 1 and has_verb_root(st):
                return out("S", f"B:{s}")
    for s in sorted(LIT_SUF_B, key=len, reverse=True):
        if w.endswith(s):
            st = w[:-len(s)]
            if ncons(st) >= 1 and has_verb_root(st):
                return out("L", f"B:{s}")

    return out(None, "none")


def darc(text, w_nar=0.50, w_dia=0.25, w_bal=0.25,
         bal_lo=0.15, bal_hi=0.50, verbose=False):
    """Dialog-Aware Register Consistency.

    Returns (score, sub_scores). Sub-scores are diagnostic: the one that
    drops identifies WHICH defect occurred, which a single figure cannot.
    """
    nar, dia = segment(text)
    nt = [classify_register(w) for w in tok(nar)]
    dt = [classify_register(w) for w in tok(dia)]
    nL, nS = nt.count("L"), nt.count("S")
    dL, dS = dt.count("L"), dt.count("S")

    # 1. narration should be literary
    s_nar = nL / (nL + nS) if (nL + nS) else 0.5

    # 2. dialogue should be spoken
    if not dia.strip():
        s_dia = 0.30          # no dialogue at all is itself a defect
    elif (dL + dS) == 0:
        s_dia = 0.50          # dialogue present but register-neutral
    else:
        s_dia = dS / (dL + dS)

    # 3. both registers present in a workable ratio
    ntk, dtk = len(tok(nar)), len(tok(dia))
    tot = ntk + dtk
    if tot == 0:
        s_bal = 0.0
    else:
        r = dtk / tot
        if bal_lo <= r <= bal_hi:
            s_bal = 1.0
        elif r < bal_lo:
            s_bal = r / bal_lo
        else:
            s_bal = max(0.0, 1 - (r - bal_hi) / (1 - bal_hi))

    score = w_nar * s_nar + w_dia * s_dia + w_bal * s_bal
    sub = {"nar": round(s_nar, 3), "dia": round(s_dia, 3),
           "bal": round(s_bal, 3),
           "nL": nL, "nS": nS, "dL": dL, "dS": dS,
           "ratio": round(dtk / tot, 3) if tot else 0,
           "nar_tokens": ntk, "dia_tokens": dtk}

    if verbose:
        print(f"    narrative: L={nL} S={nS} -> {s_nar:.3f}  (x{w_nar})")
        print(f"    dialogue : L={dL} S={dS} -> {s_dia:.3f}  (x{w_dia})")
        print(f"    balance  : {sub['ratio']:.1%} dialogue -> {s_bal:.3f}  (x{w_bal})")

    return round(score, 4), sub
