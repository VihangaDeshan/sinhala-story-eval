# -*- coding: utf-8 -*-
"""T1 follow-up analyses (24 Oct 2026), run from the repository root:

    python experiments/darc_eval/t1_extra.py --stories data/stories/all38_stories.json

1. T1 sub-score breakdown: the published T1 (classifier-filtered pool) with the
   narrative, dialogue and balance sub-scores recorded per text.
2. Filter-free T1: the same design, but the injection pool is ALL narration
   sentences of H01 and H03, with no DARC-based selection.

The human story texts are not distributed; only the scores are written.
"""
import argparse, csv, json, pathlib, random, statistics as st, sys
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import darc_eval as E
from sinhala_story_eval.metrics.register import darc, classify_register
from sinhala_story_eval.tokenize import tok

LEVELS = [0.0, 0.10, 0.25, 0.50]

def run(gen, pool, seeds=5, subs=False):
    rows = []
    for s in gen:
        for seed in range(seeds):
            for lv in LEVELS:
                rng = random.Random(f"{s['id']}|{s['model']}|{seed}|{lv}")
                t = E.inject_narration(s['text'], pool, lv, rng)
                sc, sub = darc(t)
                r = dict(id=s['id'], model=s['model'], seed=seed, level=lv,
                         darc=round(sc, 4), baseline=round(E.baseline(t), 4))
                if subs:
                    r.update(nar=sub['nar'], dia=sub['dia'], bal=sub['bal'])
                rows.append(r)
    return rows

def summary(name, rows, out):
    out.append(f'== {name}')
    for lv in LEVELS:
        R = [r for r in rows if r['level'] == lv]
        line = f"  {lv:.0%}: DARC {st.mean(r['darc'] for r in R):.4f}  baseline {st.mean(r['baseline'] for r in R):.4f}"
        if 'nar' in R[0]:
            line += '  N {:.3f}  D {:.3f}  B {:.3f}'.format(*(st.mean(r[k] for r in R) for k in ('nar', 'dia', 'bal')))
        out.append(line)
    u = [r for r in rows if not (r['level'] == 0 and r['seed'] > 0)]
    out.append(f"  rho(level, DARC) all {E.spearman([r['level'] for r in rows], [r['darc'] for r in rows]):+.3f}"
               f"  unique {E.spearman([r['level'] for r in u], [r['darc'] for r in u]):+.3f} (n={len(u)})"
               f"  baseline {E.spearman([r['level'] for r in rows], [r['baseline'] for r in rows]):+.3f}")
    ok = 0
    for key in {(r['id'], r['model']) for r in rows}:
        m = [st.mean(r['darc'] for r in rows if (r['id'], r['model']) == key and r['level'] == lv) for lv in LEVELS]
        ok += all(m[i] > m[i + 1] for i in range(3))
    out.append(f'  stories ordered correctly: {ok}/30')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stories', required=True); a = ap.parse_args()
    S = json.load(open(a.stories, encoding='utf-8'))
    gen = [s for s in S if s.get('corpus', 'generated') == 'generated' and s.get('model') != 'human' and s.get('text')]
    src = [s for s in S if s['id'] in ('H01', 'H03')]
    pool_all = [x for s in src for x in E.narration_sentences(s['text'])]
    pool_f = [x for x in pool_all if any(classify_register(w) == 'S' for w in tok(x))]
    out = [f'pool: filtered {len(pool_f)} sentences, unfiltered {len(pool_all)} sentences']
    r1 = run(gen, pool_f, subs=True); summary('T1 published (filtered pool) with sub-scores', r1, out)
    r2 = run(gen, pool_all); summary('T1 filter-free (all narration sentences of H01 and H03)', r2, out)
    for name, rows in (('t1_subscores_results.csv', r1), ('t1_filterfree_results.csv', r2)):
        with open(HERE / name, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (HERE / 't1_extra_summary.txt').write_text('\n'.join(out) + '\n', encoding='utf-8'); print('\n'.join(out))

if __name__ == '__main__':
    main()
