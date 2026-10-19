# -*- coding: utf-8 -*-
"""
build_colab_notebook.py: builds SSEF_Colab_Standalone.ipynb from THIS repository.

The notebook contains a verbatim copy of the library (src/sinhala_story_eval), the web app (app/)
and the 30 generated sample stories, so it runs on Colab with no GitHub access and no token.
Because the code is copied, not rewritten, the notebook produces exactly the repository's numbers.
The copyrighted human stories (data/stories/private/) are NOT included.

Run from the repository root:
    python build_colab_notebook.py
Then upload SSEF_Colab_Standalone.ipynb to Colab (File -> Upload notebook).
"""
import base64
import json
import pathlib

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SSEF_Colab_Standalone.ipynb"
BASE = "/content/ssef"
SKIP_PARTS = {"__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {".py", ".html", ".css", ".js", ".json", ".txt"}


def collect(folder, suffixes=None):
    folder = ROOT / folder
    if not folder.is_dir():
        raise SystemExit(f"Missing folder: {folder}. Run this from the repository root.")
    out = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or SKIP_PARTS & set(p.parts) or p.suffix in SKIP_SUFFIXES:
            continue
        if ".egg-info" in str(p):
            continue
        if suffixes and p.suffix not in suffixes:
            continue
        out.append(p)
    return out


files = (collect("src/sinhala_story_eval")
         + collect("app", {".py", ".html", ".css", ".js", ".json"})
         + collect("app/static/fonts")   # web fonts (.woff2, binary) and their licences
         + [ROOT / "data/stories/generated30_stories.json"])
if any("private" in p.parts for p in files):
    raise SystemExit("Refusing to include data/stories/private/.")
if any("instance" in p.parts or ("auth" in p.name and p.suffix == ".json") for p in files):
    raise SystemExit("Refusing to include instance/ or an account file.")
for p in files:
    if not p.exists():
        raise SystemExit(f"Missing file: {p}")


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}


def code(s, raw=False):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": (s if raw else s.strip("\n")).splitlines(True)}


rel = [p.relative_to(ROOT).as_posix() for p in files]
dirs = sorted({str(pathlib.PurePosixPath(BASE, r).parent) for r in rel})

cells = [md(f"""
# SSEF: standalone Colab backup

Everything is inside this notebook: the library, the web app and the 30 sample stories, copied
verbatim from the repository. There is no GitHub access and no token.

1. **Runtime → Change runtime type → T4 GPU** (needed for fluency only).
2. **Runtime → Run all.**
3. Click the link printed by the "Open the app" cell.

When finished: **Runtime → Disconnect and delete runtime.**
Files: {len(files)} copied from the repository.
"""),
         md("## 1. Files (verbatim copies; collapse this section)"),
         code("import os\nfor d in " + json.dumps(dirs) + ":\n    os.makedirs(d, exist_ok=True)\nprint('folders ready')")]

for p, r in zip(files, rel):
    if p.suffix in TEXT_SUFFIXES:
        text = p.read_text(encoding="utf-8")
        cells.append(code(f"%%writefile {BASE}/{r}\n" + text, raw=True))
    else:
        # Binary file (fonts): embedded as base64 and written back as bytes
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        cells.append(code(f"import base64, pathlib\n"
                          f"pathlib.Path({BASE + '/' + r!r}).write_bytes(base64.b64decode({b64!r}))\n"
                          f"print('wrote {r}')", raw=True))

cells += [
    md("## 2. Run"),
    code(f"""
# Setup: no installs are needed on Colab (torch, transformers and flask are preinstalled)
import os, sys, getpass, importlib.util, subprocess
os.chdir("{BASE}")
sys.path[:0] = ["{BASE}/src", "{BASE}"]
if importlib.util.find_spec("flask") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "flask"], check=True)
HF_TOKEN = getpass.getpass("HF_TOKEN (optional, press Enter to skip): ").strip()
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN
import torch, sinhala_story_eval
print("library", getattr(sinhala_story_eval, "__version__", "?"), "| GPU:", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("*** NO GPU. Fluency will be unavailable. Fix: Runtime -> Change runtime type -> T4 GPU -> Save,"
          " then Runtime -> Run all again. ***")
"""),
    code("""
# Self-test: the copied library must reproduce the dissertation's numbers for N01_CoastTrain (gemini)
import json, time
from sinhala_story_eval import evaluate
stories = json.load(open("data/stories/generated30_stories.json", encoding="utf-8"))
s = next(x for x in stories if x["id"] == "N01_CoastTrain" and x["model"] == "gemini")
r = evaluate(s["text"], fluency=False)
expected = {"words": (744, 0), "darc": (0.975, 0.0005), "coherence": (0.0497, 0.00005),
            "mtld": (353.81, 0.005), "ttr": (0.611, 0.0005)}
bad = {k: r[k] for k, (v, tol) in expected.items() if abs(r[k] - v) > tol}
print("SELF-TEST", "PASSED: numbers match the dissertation" if not bad else f"FAILED: {bad}")
"""),
    code("""
# Load SinBERT once (short warm-up), so the first real story does not wait for the download
if torch.cuda.is_available():
    t0 = time.time()
    evaluate(stories[0]["text"][:600], fluency=True)
    print(f"SinBERT ready ({time.time() - t0:.0f} s)")
else:
    print("No GPU: fluency is unavailable; the other three metrics work.")
"""),
    code("""
# Open the app (same interface as the AWS server)
import threading
from werkzeug.serving import make_server
from app.app import create_app
try:
    srv.shutdown()
except NameError:
    pass
srv = make_server("127.0.0.1", 5000, create_app(), threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
from google.colab.output import eval_js
print("Open the app:", eval_js("google.colab.kernel.proxyPort(5000)"))
"""),
    code("""
# Or show the app inside the notebook
from google.colab import output
output.serve_kernel_port_as_iframe(5000, height=1100)
"""),
    md("## 3. Fallback without the web page (same numbers, as cards)"),
    code("""
# Use this cell only if the web page does not open. "Run all" runs it with FLUENCY = False,
# so it does not compete with the app for the GPU. Set FLUENCY = True and run it by hand if needed.
IDX     = 0      # sample number (see the list printed below), or
TEXT    = ""     # paste your own story here; it is used instead of IDX
FLUENCY = False

from IPython.display import HTML, display
from sinhala_story_eval.composite import HUMAN_REFERENCE
for i, x in enumerate(stories):
    print(i, x["id"], "·", x["model"])

def ref_mean(key):
    v = HUMAN_REFERENCE[key]
    if isinstance(v, dict):
        return v.get("mean", next(iter(v.values())))
    return v[0] if isinstance(v, (list, tuple)) else v

NOTES = {
    "pppl": "Agrees with native-speaker ratings (r = −0.71, n = 30).",
    "coherence": "Moderate agreement with native-speaker ratings (r = +0.47, n = 30).",
    "mtld": "Agrees with native-speaker ratings (r = +0.51, n = 30).",
    "darc": "Validated on controlled register errors (ρ = −0.931) and by a native-speaker reviewer. "
            "Matched readers' narration judgement on all 30 stories.",
}

def card(title, value, key, lower_better=False, extra=""):
    if value is None:
        body = "<div style='font-size:28px'>—</div><div>Not computed (fluency off)</div>"
    else:
        m = ref_mean(key)
        side = "Above" if value > m else "Below"
        body = (f"<div style='font-size:28px'>{value:.4g}</div>"
                f"<div>Average of 8 published Sinhala stories (human-written): {m:.4g} · "
                f"{side} the 8-story average</div>"
                f"<div>{'Lower' if lower_better else 'Higher'} is better</div>{extra}")
    return ("<div style='border:1px solid #ccc;border-radius:8px;padding:12px;margin:6px;flex:1;min-width:230px'>"
            f"<b>{title}</b>{body}<div style='color:#666;font-size:12px;margin-top:6px'>{NOTES[key]}</div></div>")

text = TEXT.strip() or stories[IDX]["text"]
try:
    t0 = time.time()
    r = evaluate(text, fluency=FLUENCY and torch.cuda.is_available())
except (ValueError, TypeError) as e:
    display(HTML(f"<b style='color:#b00'>Rejected by input validation (FR-01):</b> {e}"))
else:
    fl = r.get("pppl_overall")
    fl_extra = (f"<div>Narration {r['pppl_narrative']:.4g} · Dialogue {r['pppl_dialogue']:.4g}</div>"
                if fl is not None and r.get("pppl_narrative") is not None else "")
    darc_extra = (f"<div>Narrative {r['darc_narrative']:.3f} · Dialogue {r['darc_dialogue']:.3f} · "
                  f"Balance {r['darc_balance']:.3f} · Dialogue ratio {100 * r['dialogue_ratio']:.1f}%</div>")
    dims = 4 if fl is not None else 3
    n = r["words"]
    length_note = ("" if 488 <= n <= 1273 else
                   f"<div style='color:#666;font-size:13px'>This story has {n} words. SSEF was tested on "
                   "stories of 488 to 1,273 words, so scores for this length have not been tested.</div>")
    display(HTML(
        f"<div>✓ Sinhala text accepted · {n} words · {time.time() - t0:.1f} s</div>" + length_note +
        "<div style='display:flex;flex-wrap:wrap'>"
        + card("Fluency · PPPL", fl, "pppl", lower_better=True, extra=fl_extra)
        + card("Coherence · entity overlap", r["coherence"], "coherence")
        + card("Lexical diversity · MTLD", r["mtld"], "mtld", extra=f"<div>TTR {r['ttr']:.4f}</div>")
        + card("Register consistency · DARC", r["darc"], "darc", extra=darc_extra)
        + "</div>"
        f"<div style='font-size:13px;margin:6px'>Composite ({dims} dimensions): <b>{r['composite']:.4f}</b>. "
        "Summary only. It did not predict readers' overall-quality ratings (r = +0.25).</div>"
        "<div style='color:#666;font-size:12px;margin:6px'>SSEF gives no good-or-bad verdict. "
        "Scores are shown against eight published Sinhala stories.</div>"))
"""),
    code("""
# Finish: stop the app, then Runtime → Disconnect and delete runtime
try:
    srv.shutdown(); print("App stopped.")
except NameError:
    print("App was not started.")
"""),
]

nb = {"cells": cells,
      "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
                   "kernelspec": {"display_name": "Python 3", "name": "python3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Wrote {OUT.name}: {len(files)} files embedded")
for r in rel:
    print("  ", r)
