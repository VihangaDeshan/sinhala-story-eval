# -*- coding: utf-8 -*-
"""Sinhala tokenisation helpers."""

import re

# Sinhala block U+0D80–U+0DFF, plus ZWJ which joins conjunct consonants
_TOKEN = re.compile(r'[\u0D80-\u0DFF\u200d]+')

# Base consonants only — used as a morphological length guard. Sinhala vowel
# signs are combining marks, so len() in codepoints overstates word length.
_CONS = re.compile(r'[\u0D9A-\u0DC6]')


def tok(text):
    """Sinhala-script tokens. Latin text, digits and punctuation are dropped."""
    return _TOKEN.findall(text)


def ncons(word):
    """Base-consonant count — a stand-in for syllable weight."""
    return len(_CONS.findall(word))
