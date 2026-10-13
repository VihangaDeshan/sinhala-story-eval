# -*- coding: utf-8 -*-
"""
Split-"ය" diagnostic for DARC narration scoring. Read-only: changes nothing in src/.

Finding under test: a narration verb such as "දුටුවා" is classified 'S', but
when followed by the literary agreement particle "ය" written as a separate
word ("දුටුවා ය") the form is literary.

For every story the narration is obtained exactly as darc() does
(segment() + tok()), every token is classified with classify_register(), and
each 'S' token whose NEXT narration token is exactly "ය" is counted as
split_ya. nar_adj = (nL + split_ya) / (nL + nS).

Human stories: only ids and counts are printed, never text.

Run from the repo root:
    python experiments/darc_eval/split_ya_diagnostic.py
"""
import io, json, pathlib, re, statistics as st, sys

from sinhala_story_eval.segment import segment
from sinhala_story_eval.tokenize import tok
from sinhala_story_eval.metrics.register import darc, classify_register

ROOT = pathlib.Path(__file__).resolve().parents[2]
GEN = ROOT / "data/stories/generated30_stories.json"
HUM = ROOT / "data/stories/private/human8_stories.json"
OUT = pathlib.Path(__file__).with_name("split_ya_diagnostic_2026-10-13.txt")

YA = "ය"
SHOW_WORDS = {("N04_Avurudu", "deepseek"), ("N01_CoastTrain", "gemini")}


def analyse(story):
    nar, _ = segment(story["text"])
    toks = tok(nar)
    tags = [classify_register(w) for w in toks]
    nL, nS = tags.count("L"), tags.count("S")
    split = [i for i, t in enumerate(tags)
             if t == "S" and i + 1 < len(toks) and toks[i + 1] == YA]
    # Sanity: tok() drops punctuation, so "X. ය" would also count. Check how
    # many split_ya pairs are separated by whitespace only in the raw narration.
    adj_pairs = 0
    if split:
        pairs = {toks[i] for i in split}
        for w in pairs:
            adj_pairs += len(re.findall(r"(?<![඀-෿‍])" + re.escape(w)
                                        + r"\s+" + YA + r"(?![඀-෿‍])", nar))
    _, sub = darc(story["text"])
    assert sub["nL"] == nL and sub["nS"] == nS, story["id"]
    n = nL + nS
    nar_adj = (nL + len(split)) / n if n else 0.5
    ya_tags = {}
    for i, w in enumerate(toks):
        if w == YA:
            ya_tags[tags[i]] = ya_tags.get(tags[i], 0) + 1
    return dict(id=story["id"], model=story.get("model"), corpus=story.get("corpus"),
                nar=sub["nar"], nL=nL, nS=nS, split_ya=len(split), ws_adjacent=adj_pairs,
                nar_adj=round(nar_adj, 3), ya_tokens=ya_tags,
                words=[toks[i] for i in split])


def main():
    buf = io.StringIO()
    p = lambda *a: print(*a, file=buf)

    p("SPLIT-ය DIAGNOSTIC — 2026-10-13")
    p("=" * 78)
    p("Formula check (src/sinhala_story_eval/metrics/register.py:130):")
    p("    s_nar = nL / (nL + nS) if (nL + nS) else 0.5   -> CONFIRMED")
    p()
    tag, rule = classify_register(YA, debug=True)
    p(f'Standalone "{YA}" token: classify_register -> {tag!r}  (rule: {rule})')
    p()

    gen = json.loads(GEN.read_text(encoding="utf-8"))
    hum = json.loads(HUM.read_text(encoding="utf-8"))
    rg = [analyse(s) for s in gen]
    rh = [analyse(s) for s in hum]

    hdr = f"{'id':<22}{'model/corpus':<14}{'nar':>7}{'nL':>6}{'nS':>6}{'split_ya':>10}{'ws_adj':>8}{'nar_adj':>9}  ya-token tags"
    for title, rows in (("GENERATED (30)", rg), ("HUMAN (8)", rh)):
        p(title)
        p("-" * len(hdr))
        p(hdr)
        for r in rows:
            mc = r["model"] if r["corpus"] == "generated" else (r["corpus"] or r["model"])
            p(f"{r['id']:<22}{str(mc):<14}{r['nar']:>7.3f}{r['nL']:>6}{r['nS']:>6}"
              f"{r['split_ya']:>10}{r['ws_adjacent']:>8}{r['nar_adj']:>9.3f}  {r['ya_tokens'] or '-'}")
        p()

    p("ws_adj = split_ya pairs separated only by whitespace in the raw narration")
    p("(tok() drops punctuation, so a pair split by '.' would still count as split_ya).")
    p()

    p("SPLIT_YA WORDS (generated only)")
    p("-" * 78)
    for r in rg:
        if (r["id"], r["model"]) in SHOW_WORDS:
            p(f"{r['id']} · {r['model']}: {len(r['words'])}")
            for w in r["words"]:
                p(f"    {w} {YA}")
    p()

    p("TOTALS")
    p("-" * 78)
    for title, rows in (("generated", rg), ("human", rh)):
        sS = sum(r["nS"] for r in rows)
        sY = sum(r["split_ya"] for r in rows)
        pct = 100 * sY / sS if sS else 0.0
        p(f"{title:<10} sum nS={sS:<5} sum split_ya={sY:<5} split_ya/nS={pct:5.1f}%  "
          f"mean nar={st.mean(r['nar'] for r in rows):.3f}  "
          f"mean nar_adj={st.mean(r['nar_adj'] for r in rows):.3f}")
    p()
    p("Human stories: nar < 0.5 before / after adjustment")
    for r in rh:
        b, a = r["nar"] < 0.5, r["nar_adj"] < 0.5
        flip = "  <- flips" if b != a else ""
        p(f"    {r['id']:<22} before={str(b):<6} after={str(a):<6}{flip}")

    text = buf.getvalue()
    OUT.write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
