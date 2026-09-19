# -*- coding: utf-8 -*-
"""The four SSEF quality dimensions.

Fluency is imported lazily: it needs torch and transformers, which the
other three do not.
"""

from .register import darc, classify_register
from .coherence import coherence
from .lexical import mtld, ttr

__all__ = ["darc", "classify_register", "coherence", "mtld", "ttr", "fluency"]


def fluency(*args, **kwargs):
    """SinBERT pseudo-perplexity. Requires the [fluency] extra."""
    from .fluency import fluency as _fluency
    return _fluency(*args, **kwargs)
