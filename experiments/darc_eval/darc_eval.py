# -*- coding: utf-8 -*-
"""
DARC computational evaluation (RQ2) — controlled perturbation tests.

Run from the root of the sinhala-story-eval repo (the library must be importable):

    python darc_eval.py --stories data/stories/all38_stories.json

Writes darc_eval_results.csv and darc_eval_summary.txt next to this script.

TESTS
-----
T1  Narrative corruption (sensitivity).
    Real spoken-register narration sentences, taken from the human reference
    stories whose narration is spoken (H01, H03 by default), are inserted into
    the narration of each generated story at 0, 10, 25 and 50 % of its
    narration sentences. DARC must fall as the level rises.
    RQ2 criterion: Spearman rho(level, DARC) <= -0.8, and the four levels in
    the correct order for each story.
    The injected text is human-written, not produced by DARC's own rules, so
    the test is not circular.

T2  Dialogue invariance (the dialogue-aware claim).
    The same amount of extra spoken text is added as quoted DIALOGUE
    (paragraphs of the form "...") taken from other generated stories. Spoken
    dialogue is conventional, so DARC should NOT fall. A dialogue-blind
    baseline (spoken share of all register-marked tokens in the whole text)
    is computed on the same texts; it should fall. This is the test that
    separates DARC from the naive approach.

T3  Baseline comparison on T1: DARC vs the naive baseline.

T4  Neutral-word false positives: every word in lexicon.NEUTRAL must be
    unlabelled by classify_register.

Each perturbation is repeated over --seeds random draws.
"""
import argparse, json, math, random, re, statistics as st, sys, pathlib, csv

from sinhala_story_eval.segment import segment
from sinhala_story_eval.metrics.register import darc, classify_register
from sinhala_story_eval.tokenize import tok

PARA = re.compile(r'\n\s*\n')
SENT = re.compile(r'(?<=[.!?෴])\s+')
QUOTES = '"“”‘’„«»'
QP = re.compile(f'[{QUOTES}]([^{QUOTES}]*)[{QUOTES}]', re.DOTALL)


def darc_score(text):
    out = darc(text)
    if isinstance(out, tuple):
        out = out[0]
    if isinstance(out, dict):
        out = out.get('darc', out.get('score'))
    return float(out)


def baseline(text):
    """Dialogue-blind: 1 - spoken share of register-marked tokens, whole text."""
    L = S = 0
    for w in tok(text):
        c = classify_register(w)
        if c == 'L':
            L += 1
        elif c == 'S':
            S += 1
    return 1 - S / (L + S) if (L + S) else 1.0


def sentences(text):
    return [s.strip() for s in SENT.split(text) if len(tok(s)) >= 3]


def narration_sentences(text):
    nar, _ = segment(text)
    return sentences(nar)


def dialogue_lines(text):
    return [m.strip() for m in QP.findall(text) if len(tok(m)) >= 2]


def inject_narration(text, pool, frac, rng):
    """Insert spoken narration sentences into narration paragraphs (outside quotes)."""
    paras = PARA.split(text)
    n_nar = max(1, len(narration_sentences(text)))
    k = round(frac * n_nar)
    if k == 0:
        return text
    nar_idx = [i for i, p in enumerate(paras) if not QP.search(p) and tok(p)]
    if not nar_idx:
        nar_idx = list(range(len(paras)))
    for _ in range(k):
        i = rng.choice(nar_idx)
        paras[i] = paras[i].rstrip() + ' ' + rng.choice(pool)
    return '\n\n'.join(paras)


def inject_dialogue(text, pool, frac, rng):
    """Insert the same amount of spoken text as quoted dialogue paragraphs."""
    paras = PARA.split(text)
    n_nar = max(1, len(narration_sentences(text)))
    k = round(frac * n_nar)
    for _ in range(k):
        pos = rng.randrange(len(paras) + 1)
        paras.insert(pos, '"' + rng.choice(pool) + '"')
    return '\n\n'.join(paras)


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for t in range(i, j + 1):
                r[o[t]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float('nan')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stories', required=True)
    ap.add_argument('--spoken-sources', default='H01,H03',
                    help='human stories whose narration is spoken (source of T1 injections)')
    ap.add_argument('--levels', default='0,0.10,0.25,0.50')
    ap.add_argument('--seeds', type=int, default=5)
    a = ap.parse_args()
    levels = [float(x) for x in a.levels.split(',')]
    S = json.load(open(a.stories, encoding='utf-8'))
    gen = [s for s in S if s.get('corpus', 'generated') == 'generated' and s.get('model') != 'human' and s.get('text')]
    src_ids = set(a.spoken_sources.split(','))
    src = [s for s in S if s['id'] in src_ids and s.get('text')]
    if not src:
        sys.exit('No spoken-narration source texts found; check --spoken-sources and that human texts are in the JSON.')

    # T1 pool: spoken narration sentences from human stories, kept only if they carry spoken marking
    pool_nar = [x for s in src for x in narration_sentences(s['text'])
                if any(classify_register(w) == 'S' for w in tok(x))]
    pool_dia_all = [(s['id'], s['model'], x) for s in gen for x in dialogue_lines(s['text'])]
    print(f'{len(gen)} generated stories | narration injection pool {len(pool_nar)} sentences | dialogue pool {len(pool_dia_all)} lines')

    here = pathlib.Path(__file__).parent
    rows = []
    for s in gen:
        pool_dia = [x for (i, m, x) in pool_dia_all if (i, m) != (s['id'], s['model'])]
        for seed in range(a.seeds):
            for lv in levels:
                rng = random.Random(f"{s['id']}|{s['model']}|{seed}|{lv}")
                t1 = inject_narration(s['text'], pool_nar, lv, rng)
                rng = random.Random(f"D|{s['id']}|{s['model']}|{seed}|{lv}")
                t2 = inject_dialogue(s['text'], pool_dia, lv, rng)
                rows.append(dict(id=s['id'], model=s['model'], seed=seed, level=lv,
                                 T1_darc=darc_score(t1), T1_base=baseline(t1),
                                 T2_darc=darc_score(t2), T2_base=baseline(t2)))
    with open(here / 'darc_eval_results.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    out = []
    def P(*x): out.append(' '.join(str(v) for v in x)); print(*x)

    def mean_by_level(key):
        return {lv: st.mean(r[key] for r in rows if r['level'] == lv) for lv in levels}

    P('\n=== T1 narrative corruption (spoken narration injected) ===')
    for key in ('T1_darc', 'T1_base'):
        m = mean_by_level(key)
        P(f'  {key:8s} mean by level: ' + '  '.join(f'{lv:.0%}: {m[lv]:.4f}' for lv in levels))
    rho_d = spearman([r['level'] for r in rows], [r['T1_darc'] for r in rows])
    rho_b = spearman([r['level'] for r in rows], [r['T1_base'] for r in rows])
    P(f'  Spearman rho(level, DARC)     = {rho_d:+.3f}   (RQ2 target <= -0.80)')
    P(f'  Spearman rho(level, baseline) = {rho_b:+.3f}')
    # per-story ordering using the seed-averaged score
    ok = ok_ni = tot = 0; per_story_rho = []
    for key_s in {(r['id'], r['model']) for r in rows}:
        sc = [st.mean(r['T1_darc'] for r in rows if (r['id'], r['model']) == key_s and r['level'] == lv) for lv in levels]
        tot += 1; ok += all(sc[i] > sc[i + 1] for i in range(len(sc) - 1))
        ok_ni += all(sc[i] >= sc[i + 1] for i in range(len(sc) - 1)) and sc[0] > sc[-1]
        per_story_rho.append(spearman(levels, sc))
    P(f'  stories with all levels in strictly correct order: {ok}/{tot}')
    P(f'  stories never increasing and lower at the top level: {ok_ni}/{tot}')
    P(f'  per-story rho: median {st.median(per_story_rho):+.3f}, worst {max(per_story_rho):+.3f}')

    P('\n=== T2 dialogue invariance (same amount of spoken text added as quoted dialogue) ===')
    for key in ('T2_darc', 'T2_base'):
        m = mean_by_level(key)
        P(f'  {key:8s} mean by level: ' + '  '.join(f'{lv:.0%}: {m[lv]:.4f}' for lv in levels))
    md, mb = mean_by_level('T2_darc'), mean_by_level('T2_base')
    P(f'  change 0% -> {levels[-1]:.0%}:  DARC {md[levels[-1]] - md[levels[0]]:+.4f}   baseline {mb[levels[-1]] - mb[levels[0]]:+.4f}')
    P('  Expected: DARC roughly flat (dialogue-aware); baseline falls (dialogue-blind).')

    P('\n=== T4 neutral-word false positives ===')
    try:
        from sinhala_story_eval import lexicon
        neu = sorted(getattr(lexicon, 'NEUTRAL'))
        fp = [w for w in neu if classify_register(w) is not None]
        P(f'  {len(fp)}/{len(neu)} neutral words labelled' + (f': {fp}' if fp else ' (none)'))
    except Exception as e:
        P(f'  skipped ({e})')

    (here / 'darc_eval_summary.txt').write_text('\n'.join(out), encoding='utf-8')
    print('\nwrote darc_eval_results.csv and darc_eval_summary.txt')


if __name__ == '__main__':
    main()
