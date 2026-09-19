# -*- coding: utf-8 -*-
"""
Entity-based coherence.

WHY NOT LaBSE
-------------
The proposal specified mean LaBSE cosine similarity between adjacent
sentences — standard practice in NLG evaluation. It was tested and
rejected on evidence:

    method               coherent   unrelated   discrimination
    LaBSE adjacent         0.4932      0.4338        +0.059
    LaBSE window-3         0.4873      0.4118        +0.076
    entity-based           0.4259      0.0000        +0.426

Ten completely unrelated sentences scored 0.4338 under LaBSE — almost
identical to a genuinely coherent story. Individual pairs ranked backwards:
a related pair scored 0.256 while an unrelated pair scored 0.490.

Cause: LaBSE is trained to align translation pairs across languages. It
correctly gives 0.989 to the same sentence in two registers, which is a
different task from judging whether a story holds together.

Reported as a negative finding — a widely used coherence proxy does not
transfer to Sinhala narrative text.

STEMMING IS NOT OPTIONAL
------------------------
Sinhala is agglutinative: කමල් / කමල්ගේ / කමල්ට are one entity in three
surface forms. Counting them separately gives adjacent sentences zero
overlap even when both name the protagonist.

    raw tokens   0.1429
    stemmed      0.4286      3.0x

MTLD deliberately does NOT stem (effect there is only −4.9%). Entity
matching needs a word to match itself; diversity counting does not.

SHUFFLING IS THE WRONG VALIDITY TEST
------------------------------------
Shuffling sentences RAISES this score (−5% to −11.5%), because it spreads a
clustered entity evenly across pairs. Entity overlap measures CONTINUITY,
not ORDER. The correct control is entity continuity:

    same characters throughout      0.7222
    partial continuity              0.1111
    new characters every sentence   0.0000

OPERATING RANGE
---------------
Real writing scores ~0.08, not ~0.43. The higher figure came from synthetic
test text that repeated character names in nearly every sentence. Calibrate
against real values.
"""

import re
from collections import Counter

from ..tokenize import tok
from ..segment import QUOTES

__all__ = ["coherence", "split_sentences"]

# Case and possessive suffixes, longest first
CASE_SUFFIXES = ['ගෙන්', 'ගේ', 'ෙන්', 'ෙහි', 'වත්', 'මත්', 'ලා',
                 'ට', 'ව', 'ේ', 'ය', 'ක්', 'කු', 'න්']

# Very frequent forms that would otherwise dominate the entity set
STOPWORDS = {'විය', 'වූ', 'කර', 'කළ', 'ගිය', 'ඇති', 'තිබ', 'සිට', 'දෙ', 'එක',
             'මම', 'ඔයා', 'ඇය', 'ඔහු', 'මේ', 'ඒක', 'දැන්', 'නෑ', 'ඔව්', 'තම',
             'සහ', 'අතර', 'පසු', 'නිතර', 'තවත', 'හැම', 'දින'}

SENT_SPLIT = r'(?<=[.!?\u0DF4])\s+'


def _stem(w):
    for s in sorted(CASE_SUFFIXES, key=len, reverse=True):
        if w.endswith(s) and len(w) - len(s) >= 3:
            return w[:-len(s)]
    return w


def split_sentences(text, min_words=2):
    """Sentence split that protects quoted spans.

    Splitting naively on terminal punctuation tears dialogue apart:
    "ආයුබෝවන්. ඔයා මෙහෙ අලුත්ද?" becomes two fragments, and the first is
    then dropped by the minimum-length filter.
    """
    protected = []

    def _protect(m):
        protected.append(m.group(0))
        return f"\x00{len(protected)-1}\x00"

    qp_full = f'[{QUOTES}][^{QUOTES}]*[{QUOTES}]'
    tmp = re.sub(qp_full, _protect, text)
    out = []
    for p in re.split(SENT_SPLIT, tmp.strip()):
        for i, orig in enumerate(protected):
            p = p.replace(f"\x00{i}\x00", orig)
        p = p.strip()
        if len(p.split()) >= min_words:
            out.append(p)
    return out


def coherence(text, min_freq=2, min_len=3):
    """Mean Jaccard overlap of recurring entities between adjacent sentences.

    Returns None if the text has fewer than two usable sentences.
    """
    sents = split_sentences(text)
    if len(sents) < 2:
        return None
    freq = Counter(_stem(w) for w in tok(text))
    entities = {w for w, c in freq.items()
                if c >= min_freq and len(w) >= min_len and w not in STOPWORDS}
    per_sent = [set(_stem(w) for w in tok(s)) & entities for s in sents]
    overlaps = []
    for i in range(len(sents) - 1):
        a, b = per_sent[i], per_sent[i + 1]
        union = a | b
        overlaps.append(len(a & b) / len(union) if union else 0.0)
    return round(sum(overlaps) / len(overlaps), 4)
