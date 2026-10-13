# -*- coding: utf-8 -*-
"""
sinhala-story-eval — a quality evaluation framework for Sinhala stories.

Four dimensions, of which the fourth is novel:

    fluency      SinBERT pseudo-perplexity, chunked and dialogue-aware
    coherence    entity-based overlap with Sinhala case stemming
    lexical      MTLD, with TTR as a length-sensitive baseline
    register     DARC — Dialog-Aware Register Consistency

DARC is the contribution. It is the first automated measure of diglossic
register consistency for Sinhala, built on documented verb morphology
rather than on a corpus, so it has no data dependency that can break.

USAGE

    from sinhala_story_eval import evaluate
    result = evaluate(story_text)              # three CPU metrics
    result = evaluate(story_text, fluency=True)  # adds PPPL, needs GPU

    from sinhala_story_eval.metrics import darc
    score, sub = darc(story_text)

Fluency needs the optional extra:

    pip install sinhala-story-eval[fluency]

Project: SSEF, BSc (Hons) Computing, Coventry University / NIBM.
"""

__version__ = "0.4.1"

from .segment import segment, dialogue_spans, QUOTES
from .tokenize import tok, ncons
from .metrics import darc, classify_register, coherence, mtld, ttr
from .composite import composite, z_scores, reference_from, HUMAN_REFERENCE

__all__ = [
    "evaluate",
    "segment", "dialogue_spans", "QUOTES",
    "tok", "ncons",
    "darc", "classify_register", "coherence", "mtld", "ttr",
    "composite", "z_scores", "reference_from", "HUMAN_REFERENCE",
    "__version__",
]


def evaluate(text, fluency=False, include_composite=True,
             reference=None, model_name=None):
    """Score one Sinhala story on the SSEF dimensions.

    Parameters
    ----------
    text : str
        The story. Dialogue must be in double quotation marks — the
        segmenter cannot see unquoted dialogue (limitation D21).
    fluency : bool
        Include SinBERT PPPL. Needs the [fluency] extra and, in practice,
        a GPU: roughly 90 seconds per 800-word story on a T4.
    include_composite : bool
        Add the z-scores and composite, normalised against `reference`.
    reference : dict, optional
        Reference distribution. Defaults to the 8-story human corpus.

    Returns
    -------
    dict
        Per-dimension scores, DARC sub-scores, and optionally z-scores and
        the composite.

    Notes
    -----
    A high DARC score means the text observes the register convention. It
    does not mean the text is good. Report the sub-scores alongside it —
    the one that drops tells you which defect occurred.
    """
    nar, dia = segment(text)
    darc_score, darc_sub = darc(text)

    result = {
        "words": len(text.split()),
        "darc": darc_score,
        "darc_narrative": darc_sub["nar"],
        "darc_dialogue": darc_sub["dia"],
        "darc_balance": darc_sub["bal"],
        "dialogue_ratio": darc_sub["ratio"],
        "dialogue_spans": len(dialogue_spans(text)),
        "narrative_tokens": darc_sub["nar_tokens"],
        "dialogue_tokens": darc_sub["dia_tokens"],
        "coherence": coherence(text),
        "mtld": mtld(text),
        "ttr": ttr(text),
        "pppl_overall": None,
        "pppl_narrative": None,
        "pppl_dialogue": None,
    }

    if fluency:
        from .metrics.fluency import fluency as _fluency
        kw = {"model_name": model_name} if model_name else {}
        result.update(_fluency(text, **kw))

    if include_composite:
        score, z = composite(result, reference)
        result["composite"] = score
        result["z_scores"] = z

    return result


# --- FR-01: input validation -------------------------------------------------
# evaluate() rejects input that is not Unicode Sinhala before any metric runs,
# as FR-01 requires. The original function is unchanged underneath.
import functools as _fr01_functools
import inspect as _fr01_inspect

from .validate import validate_text, MIN_SINHALA_SHARE  # noqa: E402

_evaluate_unvalidated = evaluate
_fr01_first = next(iter(_fr01_inspect.signature(_evaluate_unvalidated).parameters))


@_fr01_functools.wraps(_evaluate_unvalidated)
def evaluate(*args, **kwargs):
    validate_text(args[0] if args else kwargs.get(_fr01_first))
    return _evaluate_unvalidated(*args, **kwargs)


if "__all__" in globals():
    __all__ = list(__all__) + ["validate_text"]
