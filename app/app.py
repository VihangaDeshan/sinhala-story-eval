# -*- coding: utf-8 -*-
"""
SSEF Web Application — app.py

Factory: create_app()
Endpoints:
    GET  /           Serve the single-page UI
    POST /api/evaluate  Evaluate text (fluency=false only via this route)
    GET  /api/job/<id>  Poll a background fluency job
    GET  /healthz    Returns "ok"
"""

import json
import logging
import os
import sys
import threading
import time
import traceback
import uuid

# Ensure the library is importable whether or not it is pip-installed.
# When running `python app/app.py` from the repo root the src/ tree is
# not automatically on sys.path unless `pip install -e .` was used.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.normpath(os.path.join(_HERE, "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from flask import Flask, jsonify, render_template, request


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Story data — loaded once at startup
# ---------------------------------------------------------------------------
# Range of the 38 stories SSEF was tested on (human reference 488–1,273 words; generated 720–880).
TESTED_MIN_WORDS = 488
TESTED_MAX_WORDS = 1273

_STORIES = []
_STORIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "stories", "generated30_stories.json"
)


# ---------------------------------------------------------------------------
# Interface strings — English is rendered server-side from the same file the
# browser loads, so there is one source for the English text.
# ---------------------------------------------------------------------------
_EN_PATH = os.path.join(_HERE, "static", "i18n", "en.json")
with open(_EN_PATH, encoding="utf-8") as _f:
    _EN = json.load(_f)


def _load_stories():
    global _STORIES
    path = os.path.normpath(_STORIES_PATH)
    if not os.path.exists(path):
        logger.warning("generated30_stories.json not found at %s", path)
        return
    with open(path, encoding="utf-8") as f:
        _STORIES = json.load(f)
    logger.info("Loaded %d sample stories", len(_STORIES))


# ---------------------------------------------------------------------------
# Fluency availability check
# ---------------------------------------------------------------------------
def _fluency_available():
    """Return True if fluency can run on this server."""
    if os.environ.get("SSEF_ALLOW_CPU_FLUENCY", "").strip() == "1":
        return True
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Background job registry (one fluency job at a time)
# ---------------------------------------------------------------------------
_jobs: dict = {}           # id -> {"status": ..., "result": ..., "error": ..., "start": ...}
_job_lock = threading.Lock()
_fluency_lock = threading.Lock()   # at most one fluency job running


def _run_fluency_job(job_id: str, text: str):
    """Execute in a background thread."""
    from sinhala_story_eval import evaluate, validate_text
    try:
        result = evaluate(text, fluency=True)
        # make composite label
        result["_fluency_on"] = True
        words = result.get("words", 0)
        if words < TESTED_MIN_WORDS or words > TESTED_MAX_WORDS:
            result["length_notice"] = _EN["notice.length"].replace("{n}", str(words))
        else:
            result["length_notice"] = None
        with _job_lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
    except Exception as exc:
        logger.error("Fluency job %s failed:\n%s", job_id, traceback.format_exc())
        with _job_lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
    finally:
        _fluency_lock.release()


# ---------------------------------------------------------------------------
# Highlight helpers (display only — no metric reimplementation)
# ---------------------------------------------------------------------------

# Pre-compile the Sinhala token regex once (same pattern as tokenize.tok).
import re as _re
_TOKEN_RE = _re.compile(r'[\u0D80-\u0DFF\u200d]+')


def _highlight_text(text: str):
    """
    Return a list of fine-grained segments:
      {"type": "narration" | "dialogue" |
               "spoken_in_narration" | "literary_in_dialogue",
       "text": str}

    The highlighted-word counts satisfy exactly:
        #(spoken_in_narration words) == darc(text)[1]['nS']
        #(literary_in_dialogue words) == darc(text)[1]['dL']

    Method
    ------
    segment() is the authoritative split — it applies the v4 paragraph rule
    so darc() and this function see identical narrative/dialogue partitions.
    We walk the original text paragraph by paragraph (mirroring the v4 rule),
    locate dialogue spans inside each paragraph with the same QP regex, then
    emit individual Sinhala tokens classified with classify_register().
    Non-token characters (punctuation, spaces, Latin) are emitted verbatim.
    """
    from sinhala_story_eval.segment import QUOTES, _PARA_SPLIT
    from sinhala_story_eval.metrics.register import classify_register

    _QP_FULL = _re.compile(
        f'[{QUOTES}]([^{QUOTES}]*)[{QUOTES}]', _re.DOTALL
    )

    segs = []

    # Split preserving paragraph separators so the original text reconstructs.
    para_texts = _PARA_SPLIT.split(text)
    separators = _PARA_SPLIT.findall(text)

    for para_idx, para in enumerate(para_texts):
        # Re-insert the paragraph separator that preceded this paragraph.
        if para_idx > 0:
            sep = separators[para_idx - 1] if para_idx - 1 < len(separators) else '\n\n'
            segs.append({'type': 'narration', 'text': sep})

        if not para or not para.strip():
            if para:
                segs.append({'type': 'narration', 'text': para})
            continue

        # Within this paragraph: find all dialogue spans (v4: bounded by paragraph).
        last = 0
        for m in _QP_FULL.finditer(para):
            start, end = m.start(), m.end()

            # Narration text before this dialogue span — word-level highlight.
            if start > last:
                _emit_narration_words(para[last:start], classify_register, segs)

            # Opening quote character (kept in 'dialogue' styling).
            segs.append({'type': 'dialogue', 'text': para[start:start + 1]})
            # Inner dialogue text — word-level highlight.
            _emit_dialogue_words(m.group(1), classify_register, segs)
            # Closing quote character.
            segs.append({'type': 'dialogue', 'text': para[end - 1:end]})

            last = end

        # Remaining narration after the last dialogue span in this paragraph.
        if last < len(para):
            _emit_narration_words(para[last:], classify_register, segs)

    return segs


def _emit_narration_words(text, classify_register, segs):
    """Append fine-grained segments for a narration region.

    Each Sinhala token is emitted as 'spoken_in_narration' if
    classify_register(w) == 'S', otherwise as 'narration'.
    Non-token characters are emitted as plain 'narration'.
    """
    pos = 0
    for m in _TOKEN_RE.finditer(text):
        if m.start() > pos:
            segs.append({'type': 'narration', 'text': text[pos:m.start()]})
        w = m.group(0)
        t = 'spoken_in_narration' if classify_register(w) == 'S' else 'narration'
        segs.append({'type': t, 'text': w})
        pos = m.end()
    if pos < len(text):
        segs.append({'type': 'narration', 'text': text[pos:]})


def _emit_dialogue_words(text, classify_register, segs):
    """Append fine-grained segments for a dialogue region (without quotes).

    Each Sinhala token is emitted as 'literary_in_dialogue' if
    classify_register(w) == 'L', otherwise as 'dialogue'.
    Non-token characters are emitted as plain 'dialogue'.
    """
    pos = 0
    for m in _TOKEN_RE.finditer(text):
        if m.start() > pos:
            segs.append({'type': 'dialogue', 'text': text[pos:m.start()]})
        w = m.group(0)
        t = 'literary_in_dialogue' if classify_register(w) == 'L' else 'dialogue'
        segs.append({'type': t, 'text': w})
        pos = m.end()
    if pos < len(text):
        segs.append({'type': 'dialogue', 'text': text[pos:]})


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    _load_stories()

    @app.context_processor
    def _inject_t():
        return {"t": lambda key: _EN[key]}

    # ------------------------------------------------------------------ GET /
    @app.route("/")
    def index():
        # Include the list index so the dropdown has a unique key even when
        # the same id (e.g. N04_Avurudu) appears for multiple models.
        stories_json = json.dumps(
            [{"idx": i, "id": s["id"], "model": s.get("model", ""), "text": s["text"]}
             for i, s in enumerate(_STORIES)],
            ensure_ascii=False,
        )
        fluency_ok = _fluency_available()
        from sinhala_story_eval import __version__
        ref = _get_reference()
        return render_template(
            "index.html",
            stories_json=stories_json,
            fluency_available=fluency_ok,
            lib_version=__version__,
            human_reference=ref,
        )

    # -------------------------------------------------------- GET /healthz
    @app.route("/healthz")
    def healthz():
        return "ok", 200

    # --------------------------------------------------- POST /api/evaluate
    @app.route("/api/evaluate", methods=["POST"])
    def api_evaluate():
        from sinhala_story_eval import evaluate, validate_text

        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        want_fluency = bool(data.get("fluency", False))

        # Hard length limit
        if len(text) > 30_000:
            return jsonify({"error": "Input exceeds 30,000 characters.",
                            "code": "too_long"}), 400

        # Validate
        try:
            validate_text(text)
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400

        # Fluency path: background job
        if want_fluency:
            if not _fluency_available():
                return jsonify({
                    "error": "Fluency is not available on this server (it needs a GPU).",
                    "code": "fluency_unavailable",
                }), 400

            acquired = _fluency_lock.acquire(blocking=False)
            if not acquired:
                return jsonify({
                    "error": "Server busy with another fluency job, try again shortly.",
                    "code": "busy",
                }), 503

            job_id = str(uuid.uuid4())
            with _job_lock:
                _jobs[job_id] = {
                    "status": "running",
                    "result": None,
                    "error": None,
                    "start": time.time(),
                }
            t = threading.Thread(target=_run_fluency_job, args=(job_id, text), daemon=True)
            t.start()
            return jsonify({"job_id": job_id}), 202

        # Synchronous (no fluency)
        try:
            result = evaluate(text, fluency=False)
            result["_fluency_on"] = False
            # Attach highlight segments
            result["segments"] = _highlight_text(text)
            words = result.get("words", 0)
            if words < TESTED_MIN_WORDS or words > TESTED_MAX_WORDS:
                result["length_notice"] = _EN["notice.length"].replace("{n}", str(words))
            else:
                result["length_notice"] = None
            return jsonify(result), 200
        except Exception as exc:
            logger.error("evaluate() failed:\n%s", traceback.format_exc())
            return jsonify({"error": "Evaluation failed: " + str(exc)}), 500

    # ------------------------------------------------- GET /api/job/<id>
    @app.route("/api/job/<job_id>")
    def api_job(job_id):
        with _job_lock:
            job = _jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Job not found"}), 404

        if job["status"] == "running":
            elapsed = round(time.time() - job["start"], 1)
            return jsonify({"status": "running", "elapsed": elapsed}), 200
        elif job["status"] == "done":
            result = job["result"]
            # Attach highlights
            try:
                # We need the original text — re-evaluate is wasteful but
                # the job result doesn't store the text. For display we use
                # the text stored in result["words"] — but we need the actual text.
                # Work-around: we cannot re-create segments without the text.
                # Return result without segments; the JS will use stored text.
                result["segments"] = None  # Signal: JS should call highlight endpoint or use stored text
            except Exception:
                pass
            return jsonify({"status": "done", "result": result}), 200
        else:
            return jsonify({"status": "error", "error": job.get("error", "Unknown error")}), 200

    # -------------------------------- POST /api/highlight (for fluency path)
    @app.route("/api/highlight", methods=["POST"])
    def api_highlight():
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        try:
            segments = _highlight_text(text)
            return jsonify({"segments": segments}), 200
        except Exception as exc:
            logger.error("Highlight failed:\n%s", traceback.format_exc())
            return jsonify({"error": str(exc)}), 500

    return app


def _get_reference():
    from sinhala_story_eval.composite import HUMAN_REFERENCE
    return {
        k: {"mean": v[0], "sd": v[1]}
        for k, v in HUMAN_REFERENCE.items()
    }


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False, host="127.0.0.1", port=5000)
