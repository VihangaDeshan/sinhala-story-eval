# -*- coding: utf-8 -*-
"""
Fluency — SinBERT pseudo-perplexity.

OPTIONAL DEPENDENCY. Needs torch and transformers, and a GPU for practical
speed. The other three metrics are pure Python.

    pip install sinhala-story-eval[fluency]

WHY PSEUDO-PERPLEXITY
---------------------
Standard perplexity is defined only for causal language models. SinBERT is
a bidirectional masked LM, so PPL is mathematically undefined for it.
Pseudo-perplexity via pseudo-log-likelihood (Salazar et al., 2020) resolves
this: mask each token in turn and record the model's log-probability for
the original.

CHUNKING IS MANDATORY
---------------------
SinBERT's limit is 512 tokens. A 654-word Sinhala story tokenised to
2,675 tokens, so naive truncation evaluates about 19% of it:

    truncated at 512 tokens    22.92
    chunked over full story     7.51
    deviation                  67.2%

Chunks are sentence-aware and a short tail is merged into the previous
chunk, because short chunks give unstable PPPL. They are combined by a
token-weighted average IN LOG SPACE — PPPL is an exponential quantity, so
an arithmetic mean would be wrong. (Verified: combining 4.0 and 16.0 at
equal weight yields 8.0, the geometric mean.)

REPORT NARRATIVE AND DIALOGUE SEPARATELY
----------------------------------------
Not optional. SinBERT was pre-trained on sin-cc-15M — CC-100, OSCAR and
Sinhala news — which is overwhelmingly formal written Sinhala. Measured
across the human reference corpus:

    literary narration   mean narrative PPPL  3.07
    spoken narration     mean narrative PPPL  6.74
    ratio                                     2.20x

A single overall PPPL therefore conflates fluency with narration style.
An earlier test reported no bias (1.01x), but it used a single story that
narrated in literary register throughout — no variance in the independent
variable, so no bias could have been detected either way. That figure is
withdrawn.
"""

import math
import re

from ..segment import segment

__all__ = ["fluency", "chunk_text", "load_model"]

SENT_SPLIT = r'(?<=[.!?\u0DF4])\s+'
DEFAULT_MODEL = "NLPC-UOM/SinBERT-large"

_model = None
_tokenizer = None
_loaded_name = None


def load_model(name=DEFAULT_MODEL, device=None):
    """Load and cache SinBERT. Repeated calls reuse the loaded model."""
    global _model, _tokenizer, _loaded_name
    if _model is not None and _loaded_name == name:
        return _tokenizer, _model
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForMaskedLM
    except ImportError as e:
        raise ImportError(
            "Fluency needs the optional extra:\n"
            "    pip install sinhala-story-eval[fluency]"
        ) from e
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    _tokenizer = AutoTokenizer.from_pretrained(name)
    _model = AutoModelForMaskedLM.from_pretrained(name).to(device)
    _model.eval()
    _loaded_name = name
    return _tokenizer, _model


def chunk_text(text, max_words=100, min_last=30):
    """Sentence-aware chunking. Never cuts mid-sentence; merges a tail
    shorter than `min_last` into the previous chunk."""
    parts = [p for p in re.split(SENT_SPLIT, text.strip()) if p.strip()]
    chunks, cur, n = [], [], 0
    for p in parts:
        w = len(p.split())
        if n + w > max_words and cur:
            chunks.append(" ".join(cur))
            cur, n = [p], w
        else:
            cur.append(p)
            n += w
    if cur:
        chunks.append(" ".join(cur))
    if len(chunks) > 1 and len(chunks[-1].split()) < min_last:
        chunks[-2] += " " + chunks[-1]
        chunks.pop()
    return chunks


def _pppl_chunk(text, tokenizer, model, batch_size=32, max_len=512):
    """PPPL for one chunk, batched. Returns (pppl, n_tokens)."""
    import torch
    enc = tokenizer(text, return_tensors="pt",
                    truncation=True, max_length=max_len)
    ids = enc["input_ids"].to(model.device)
    n = ids.shape[1]
    if n < 4:
        return None, 0
    positions = list(range(1, n - 1))      # skip [CLS] and [SEP]
    total_lp = 0.0
    with torch.no_grad():
        for start in range(0, len(positions), batch_size):
            batch = positions[start:start + batch_size]
            rep = ids.repeat(len(batch), 1)
            originals = []
            for r, pos in enumerate(batch):
                originals.append(rep[r, pos].item())
                rep[r, pos] = tokenizer.mask_token_id
            logits = model(rep).logits
            for r, pos in enumerate(batch):
                lp = torch.log_softmax(logits[r, pos], dim=-1)
                total_lp += lp[originals[r]].item()
            del rep, logits
    return math.exp(-total_lp / len(positions)), len(positions)


def _pppl_long(text, tokenizer, model, **kw):
    """Chunked PPPL, token-weighted in log space."""
    weighted, total = 0.0, 0
    for c in chunk_text(text):
        p, ntok = _pppl_chunk(c, tokenizer, model, **kw)
        if p is None or ntok == 0:
            continue
        weighted += math.log(p) * ntok
        total += ntok
    return round(math.exp(weighted / total), 2) if total else None


def fluency(text, model_name=DEFAULT_MODEL, batch_size=32, device=None):
    """SinBERT pseudo-perplexity. Lower is more fluent.

    Returns overall, narrative and dialogue figures. Report all three —
    see the module docstring on register bias.
    """
    tokenizer, model = load_model(model_name, device)
    nar, dia = segment(text)
    return {
        "pppl_overall": _pppl_long(text, tokenizer, model,
                                   batch_size=batch_size),
        "pppl_narrative": (_pppl_long(nar, tokenizer, model,
                                      batch_size=batch_size)
                           if nar.strip() else None),
        "pppl_dialogue": (_pppl_long(dia, tokenizer, model,
                                     batch_size=batch_size)
                          if dia.strip() else None),
    }
