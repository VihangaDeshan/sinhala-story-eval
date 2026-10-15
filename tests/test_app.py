# -*- coding: utf-8 -*-
"""
tests/test_app.py — Flask test-client tests for the SSEF web application.

Tests:
  1. English text → HTTP 400 with the library's validation message
  2. First story (fluency=False) → HTTP 200, all numbers match evaluate()
  3. Rendered page contains none of the forbidden words
  4. Over-length input → HTTP 400
  5. Highlight word counts equal darc() nS / dL for story 0 and
     N04_Avurudu · deepseek
"""

import json
import os
import sys

import pytest

# Ensure the src package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sinhala_story_eval import evaluate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app.app import _login_failures, _signup_history
    _login_failures.clear()
    _signup_history.clear()
    yield
    _login_failures.clear()
    _signup_history.clear()


@pytest.fixture
def auth_file(tmp_path, monkeypatch):
    path = str(tmp_path / "ssef_auth.json")
    monkeypatch.setenv("SSEF_AUTH_FILE", path)
    from app.auth import add_user
    add_user(path, "testuser", "testpassword123")
    return path


@pytest.fixture
def anon_client(auth_file):
    from app.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client(auth_file):
    from app.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        c.post("/login", data={"username": "testuser", "password": "testpassword123"})
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_story_text():
    """Return the text of the first story in generated30_stories.json."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "stories", "generated30_stories.json"
    )
    with open(path, encoding="utf-8") as f:
        stories = json.load(f)
    assert len(stories) > 0, "generated30_stories.json is empty"
    return stories[0]["text"]


# ---------------------------------------------------------------------------
# Test 1 — English text → 400 with library's validation message
# ---------------------------------------------------------------------------

def test_english_text_rejected(client):
    """FR-01: English text must be rejected with the library's message."""
    english = "The quick brown fox jumps over the lazy dog."
    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": english, "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    data = resp.get_json()
    assert "error" in data
    # The library's message mentions "no Sinhala script" or "mixed-script"
    msg = data["error"].lower()
    assert "sinhala" in msg, f"Validation message does not mention Sinhala: {data['error']}"


# ---------------------------------------------------------------------------
# Test 2 — First story, fluency=False → 200, exact numbers
# ---------------------------------------------------------------------------

def test_first_story_matches_library(client):
    """Numbers returned by the API must equal evaluate(text, fluency=False)."""
    text = _first_story_text()
    expected = evaluate(text, fluency=False)

    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": text, "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data[:200]}"
    data = resp.get_json()

    # Check every scalar key returned by evaluate()
    scalar_keys = [
        "words", "darc", "darc_narrative", "darc_dialogue", "darc_balance",
        "dialogue_ratio", "dialogue_spans", "narrative_tokens", "dialogue_tokens",
        "coherence", "mtld", "ttr", "composite",
    ]
    for key in scalar_keys:
        assert key in data, f"Key '{key}' missing from API response"
        assert data[key] == expected[key], (
            f"Mismatch for '{key}': API={data[key]!r}, library={expected[key]!r}"
        )

    # pppl values should all be None (fluency=False)
    for pppl_key in ("pppl_overall", "pppl_narrative", "pppl_dialogue"):
        assert data.get(pppl_key) is None, (
            f"Expected {pppl_key}=None with fluency=False, got {data.get(pppl_key)!r}"
        )

    # z_scores dict
    assert "z_scores" in data
    for label, val in expected["z_scores"].items():
        assert data["z_scores"][label] == val, (
            f"z_scores['{label}'] mismatch: API={data['z_scores'][label]!r}, lib={val!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Rendered page has no forbidden words
# ---------------------------------------------------------------------------

import re as _re

# The build prompt mandates these exact footer and note strings verbatim.
# They legitimately contain the words "good", "bad", and "verdict", so we
# strip them before checking for unsanctioned quality-verdict language.
_MANDATORY_FIXED_STRINGS = [
    "ssef gives no good-or-bad verdict and does not measure plot, creativity or enjoyment.",
    "scores are shown against eight published sinhala stories.",
    "summary only. it did not predict readers' overall-quality ratings (r = +0.25). read the four dimensions.",
    "good-or-bad",
    "good-or-bad verdict",
    # howto.1 (required verbatim): 'not whether it is good or bad'
    "whether it is good or bad",
]

# Words that would constitute an unsanctioned quality verdict
FORBIDDEN = {"excellent", "poor", "stars"}
# "good", "bad", "verdict" appear in the required fixed text; test separately
FORBIDDEN_STANDALONE = {"good", "bad", "verdict"}


def test_no_quality_verdict_in_page(client):
    """The rendered page must not contain forbidden quality-verdict words.

    The footer contains 'good-or-bad verdict' because the build prompt
    requires it verbatim.  We strip the mandatory fixed strings from the
    HTML before testing, so those required occurrences don't trigger the
    assertion, but any additional, unsanctioned use would.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8").lower()

    # Plain forbidden words (never appear in required text)
    for word in FORBIDDEN:
        assert word not in html, (
            f"Forbidden word '{word}' found in rendered page HTML"
        )

    # For words that appear in required fixed strings, strip those strings
    # first and then verify no further occurrences remain.
    stripped = html
    for fixed in _MANDATORY_FIXED_STRINGS:
        stripped = stripped.replace(fixed, " ")

    for word in FORBIDDEN_STANDALONE:
        # Use word-boundary matching so "bad" doesn't match "badly" etc.
        found = _re.search(rf'\b{_re.escape(word)}\b', stripped)
        assert not found, (
            f"Forbidden word '{word}' found outside required fixed strings in page HTML"
        )


# ---------------------------------------------------------------------------
# Test 4 — Over-length input → 400
# ---------------------------------------------------------------------------

def test_overlength_input_rejected(client):
    """Input over 30,000 characters must be rejected with HTTP 400."""
    # Use valid Sinhala characters to avoid triggering the script check first
    long_text = "ක" * 30_001
    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": long_text, "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    data = resp.get_json()
    assert "error" in data
    assert "30,000" in data["error"] or "30000" in data["error"], (
        f"Error message does not mention character limit: {data['error']}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Highlight word counts equal darc() nS / dL
# ---------------------------------------------------------------------------

def _load_stories():
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "stories", "generated30_stories.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _evaluate_via_api(client, text):
    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": text, "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.data[:300]}"
    )
    return resp.get_json()


def _highlight_counts(api_data):
    """Return (n_spoken_in_narration, n_literary_in_dialogue) from API segments."""
    segs = api_data.get("segments") or []
    n_s = sum(1 for s in segs if s["type"] == "spoken_in_narration")
    n_l = sum(1 for s in segs if s["type"] == "literary_in_dialogue")
    return n_s, n_l


def test_highlight_counts_match_darc(client):
    """Highlighted word counts must equal darc()['nS'] and darc()['dL'] exactly.

    Tested on:
      - Story 0  (N01_CoastTrain · gemini)
      - N04_Avurudu · deepseek  (the one with the lowest darc_narrative sub-score)

    If counts differ, the highlighting function is inconsistent with the
    library's segmentation and this test will fail with a diagnostic message.
    The counts must NOT be adjusted to force a match; any discrepancy
    indicates a bug in _highlight_text().
    """
    from sinhala_story_eval.metrics.register import darc

    stories = _load_stories()

    # --- Story 0 ---
    s0 = stories[0]
    _, sub0 = darc(s0["text"])
    data0 = _evaluate_via_api(client, s0["text"])
    hl_nS_0, hl_dL_0 = _highlight_counts(data0)

    assert hl_nS_0 == sub0["nS"], (
        f"Story 0 ({s0['id']} · {s0['model']}): "
        f"spoken_in_narration word count {hl_nS_0} != darc nS {sub0['nS']}. "
        f"_highlight_text() is inconsistent with segment()."
    )
    assert hl_dL_0 == sub0["dL"], (
        f"Story 0 ({s0['id']} · {s0['model']}): "
        f"literary_in_dialogue word count {hl_dL_0} != darc dL {sub0['dL']}. "
        f"_highlight_text() is inconsistent with segment()."
    )

    # --- N04_Avurudu · deepseek ---
    # Story ids repeat across the three models; find by id AND model.
    deepseek_n04 = next(
        (s for s in stories if s["id"] == "N04_Avurudu" and s["model"] == "deepseek"),
        None,
    )
    assert deepseek_n04 is not None, (
        "N04_Avurudu · deepseek not found in generated30_stories.json"
    )
    _, sub23 = darc(deepseek_n04["text"])
    data23 = _evaluate_via_api(client, deepseek_n04["text"])
    hl_nS_23, hl_dL_23 = _highlight_counts(data23)

    assert hl_nS_23 == sub23["nS"], (
        f"N04_Avurudu · deepseek: "
        f"spoken_in_narration word count {hl_nS_23} != darc nS {sub23['nS']}. "
        f"_highlight_text() is inconsistent with segment()."
    )
    assert hl_dL_23 == sub23["dL"], (
        f"N04_Avurudu · deepseek: "
        f"literary_in_dialogue word count {hl_dL_23} != darc dL {sub23['dL']}. "
        f"_highlight_text() is inconsistent with segment()."
    )



# ---------------------------------------------------------------------------
# Test 6 — language files
# ---------------------------------------------------------------------------

import re as _re2
import shutil
import subprocess

_I18N_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "static", "i18n")


def _load_i18n(lang):
    with open(os.path.join(_I18N_DIR, lang + ".json"), encoding="utf-8") as f:
        return json.load(f)


def test_si_json_has_same_keys_as_en_json():
    en, si = _load_i18n("en"), _load_i18n("si")
    assert set(en) == set(si), (
        f"only in en: {sorted(set(en) - set(si))}; only in si: {sorted(set(si) - set(en))}"
    )


def test_placeholders_match_between_languages():
    """A filled Sinhala string must keep the same {n} {m} {k} {s} placeholders."""
    en, si = _load_i18n("en"), _load_i18n("si")
    for key, val in si.items():
        if val:
            assert sorted(_re2.findall(r"\{\w+\}", val)) == sorted(_re2.findall(r"\{\w+\}", en[key])), key


def test_english_strings_have_no_verdict_words():
    """The page text now comes from en.json; apply the same rule to it directly."""
    en = _load_i18n("en")
    text = " ".join(en.values()).lower()
    for word in FORBIDDEN:
        assert word not in text, word
    for fixed in _MANDATORY_FIXED_STRINGS:
        text = text.replace(fixed, " ")
    for word in FORBIDDEN_STANDALONE:
        assert not _re.search(rf"{word}", text), word


def test_howto_panel_is_open_and_above_cards(client):
    html = client.get("/").data.decode("utf-8")
    assert "<details class=\"howto\" open>" in html
    assert html.index("class=\"howto\"") < html.index("id=\"metrics-section\"")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_switching_language_changes_no_number(tmp_path):
    """Render the same result in English and Sinhala (view.js, run under Node)
    and compare every numeric token in the output."""
    text = _first_story_text()
    result = evaluate(text, fluency=False)
    result["_fluency_on"] = False
    result["segments"] = []
    # Also exercise the fluency-on branch with fixed figures.
    fluent = dict(result, pppl_overall=12.3456, pppl_narrative=10.1111,
                  pppl_dialogue=14.2222, _fluency_on=True)
    payload = tmp_path / "results.json"
    payload.write_text(json.dumps({"off": result, "on": fluent}), encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "js", "check_numbers.js")
    proc = subprocess.run(["node", script, str(payload)], capture_output=True,
                          text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# Test 7 — Input instructions and reference labels (Change A, B, C)
# ---------------------------------------------------------------------------

def test_input_instructions_rendered_in_english_page(client):
    """1. The rendered English page contains 'Input instructions' and the instr.1 text."""
    en = _load_i18n("en")
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Input instructions" in html
    assert en["instr.1"] in html


def test_si_json_keys_and_non_empty():
    """2. si.json and en.json have exactly the same keys, and no new key is empty in si.json."""
    en, si = _load_i18n("en"), _load_i18n("si")
    assert set(en) == set(si)
    new_keys = [
        "instr.title", "instr.1", "instr.2", "instr.3", "instr.4", "instr.5",
        "instr.6", "notice.length",
    ]
    for k in new_keys:
        assert k in si, f"Key {k} missing in si.json"
        assert si[k] and si[k].strip(), f"New key {k} is empty in si.json"


def test_tested_length_story_has_no_notice(client):
    """3. The first story in generated30_stories.json that lies inside 488–1,273 words:
    HTTP 200, all numbers unchanged from evaluate(text, fluency=False), and no length notice."""
    from app.app import TESTED_MIN_WORDS, TESTED_MAX_WORDS
    stories = _load_stories()
    target_story = None
    expected_eval = None
    for s in stories:
        ev = evaluate(s["text"], fluency=False)
        if TESTED_MIN_WORDS <= ev["words"] <= TESTED_MAX_WORDS:
            target_story = s
            expected_eval = ev
            break

    assert target_story is not None, "No story found within tested range"
    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": target_story["text"], "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()

    scalar_keys = [
        "words", "darc", "darc_narrative", "darc_dialogue", "darc_balance",
        "dialogue_ratio", "dialogue_spans", "narrative_tokens", "dialogue_tokens",
        "coherence", "mtld", "ttr", "composite",
    ]
    for key in scalar_keys:
        assert data[key] == expected_eval[key]
    assert data["z_scores"] == expected_eval["z_scores"]
    assert data.get("length_notice") is None


def test_short_sinhala_text_has_length_notice(client):
    """4. A short Sinhala text (take the first 3 sentences of that same story):
    HTTP 200, scores returned, and the length notice is present with the correct {n}."""
    from app.app import TESTED_MIN_WORDS, TESTED_MAX_WORDS
    stories = _load_stories()
    target_story = None
    for s in stories:
        ev = evaluate(s["text"], fluency=False)
        if TESTED_MIN_WORDS <= ev["words"] <= TESTED_MAX_WORDS:
            target_story = s
            break

    assert target_story is not None
    sents = [s.strip() for s in target_story["text"].replace("\n", " ").split(".") if s.strip()]
    short_text = ". ".join(sents[:3]) + "."

    resp = client.post(
        "/api/evaluate",
        data=json.dumps({"text": short_text, "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()

    assert "words" in data
    assert data["words"] < TESTED_MIN_WORDS
    assert "darc" in data
    assert "coherence" in data
    assert "mtld" in data

    assert data.get("length_notice") is not None
    expected_notice = f"This story has {data['words']} words. SSEF was tested on stories of 488 to 1,273 words, so scores for this length have not been tested."
    assert data["length_notice"] == expected_notice


def test_card_labels_say_8_story_average_not_published_average():
    """5. The card labels contain '8-story average' and no longer contain 'published average'."""
    en = _load_i18n("en")
    assert "8-story average" in en["dir.above"]
    assert "8-story average" in en["dir.below"]
    for key in ("ref.published", "dir.above", "dir.below"):
        assert "published average" not in en[key].lower()


# ---------------------------------------------------------------------------
# Section 7 — Authentication Tests (New Tests 1–14)
# ---------------------------------------------------------------------------

def test_auth_1_not_signed_in_redirect_and_401(anon_client):
    """1. Not signed in: GET / -> redirect to /login; POST /api/evaluate -> 401."""
    resp = anon_client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp = anon_client.post(
        "/api/evaluate",
        data=json.dumps({"text": _first_story_text(), "fluency": False}),
        content_type="application/json",
    )
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "login required"}


def test_auth_2_signup_valid_and_stored_hash(anon_client, auth_file):
    """2. Sign-up with a valid username and matching passwords -> signed in,
    redirected to /; the file now holds that user with a hash, not the password."""
    resp = anon_client.post(
        "/register",
        data={
            "username": "valid_user",
            "password": "valid_password123",
            "confirm": "valid_password123",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"

    # Signed in check
    main_resp = anon_client.get("/")
    assert main_resp.status_code == 200

    # The file now holds that user with a hash, not the password
    with open(auth_file, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    assert "valid_user" in auth_data["users"]
    stored_hash = auth_data["users"]["valid_user"]
    assert "valid_password123" not in stored_hash
    assert stored_hash.startswith("scrypt:") or stored_hash.startswith("pbkdf2:")


def test_auth_3_signup_taken_username(anon_client, auth_file):
    """3. Sign-up with a taken username (any letter case) -> register.taken; nothing changes."""
    en = _load_i18n("en")
    with open(auth_file, "r", encoding="utf-8") as f:
        orig = f.read()

    for variant in ["testuser", "TestUser", "TESTUSER"]:
        resp = anon_client.post(
            "/register",
            data={
                "username": variant,
                "password": "password999",
                "confirm": "password999",
            },
        )
        assert resp.status_code == 200
        assert en["register.taken"] in resp.data.decode("utf-8")

    with open(auth_file, "r", encoding="utf-8") as f:
        assert f.read() == orig


def test_auth_4_signup_validation_failures(anon_client, auth_file):
    """4. Sign-up with mismatching passwords, a 7-character password, and an
    invalid username (ab, has space, 31 characters) -> matching messages; nothing created."""
    en = _load_i18n("en")
    with open(auth_file, "r", encoding="utf-8") as f:
        orig = f.read()

    # Mismatching passwords
    resp = anon_client.post(
        "/register",
        data={"username": "mismatch_user", "password": "password123", "confirm": "different123"},
    )
    assert resp.status_code == 200
    assert en["register.mismatch"] in resp.data.decode("utf-8")

    # 7-character password
    resp = anon_client.post(
        "/register",
        data={"username": "short_pw_user", "password": "1234567", "confirm": "1234567"},
    )
    assert resp.status_code == 200
    assert en["register.short_password"] in resp.data.decode("utf-8")

    # Invalid usernames: ab, has space, 31 characters
    for bad_u in ["ab", "has space", "u" * 31]:
        resp = anon_client.post(
            "/register",
            data={"username": bad_u, "password": "password123", "confirm": "password123"},
        )
        assert resp.status_code == 200
        assert en["register.invalid_username"] in resp.data.decode("utf-8")

    # Nothing created
    with open(auth_file, "r", encoding="utf-8") as f:
        assert f.read() == orig


def test_auth_5_registration_disabled(monkeypatch, auth_file):
    """5. SSEF_REGISTRATION=off -> sign-up shows register.closed and creates nothing; sign-in works."""
    monkeypatch.setenv("SSEF_REGISTRATION", "off")
    from app.app import create_app
    en = _load_i18n("en")
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as c:
        # GET shows register.closed
        resp = c.get("/register")
        assert resp.status_code == 200
        assert en["register.closed"] in resp.data.decode("utf-8")

        # POST creates nothing and shows register.closed
        with open(auth_file, "r", encoding="utf-8") as f:
            orig = f.read()
        resp = c.post(
            "/register",
            data={"username": "closed_user", "password": "password123", "confirm": "password123"},
        )
        assert resp.status_code == 200
        assert en["register.closed"] in resp.data.decode("utf-8")
        with open(auth_file, "r", encoding="utf-8") as f:
            assert f.read() == orig

        # Sign-in still works
        login_resp = c.post(
            "/login",
            data={"username": "testuser", "password": "testpassword123"},
            follow_redirects=True,
        )
        assert login_resp.status_code == 200


def test_auth_6_wrong_password_correct_password_and_evaluate(anon_client):
    """6. Wrong password -> login.error; correct password -> /; then evaluating
    the first generated story (fluency off) gives exactly the numbers of evaluate(text, fluency=False)."""
    en = _load_i18n("en")

    # Wrong password
    resp = anon_client.post(
        "/login",
        data={"username": "testuser", "password": "wrong_password"},
    )
    assert resp.status_code == 200
    assert en["login.error"] in resp.data.decode("utf-8")

    # Correct password -> redirects to /
    resp = anon_client.post(
        "/login",
        data={"username": "testuser", "password": "testpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"

    # Evaluating the first generated story gives exactly evaluate(text, fluency=False)
    text = _first_story_text()
    expected = evaluate(text, fluency=False)

    api_resp = anon_client.post(
        "/api/evaluate",
        data=json.dumps({"text": text, "fluency": False}),
        content_type="application/json",
    )
    assert api_resp.status_code == 200
    data = api_resp.get_json()

    scalar_keys = [
        "words", "darc", "darc_narrative", "darc_dialogue", "darc_balance",
        "dialogue_ratio", "dialogue_spans", "narrative_tokens", "dialogue_tokens",
        "coherence", "mtld", "ttr", "composite",
    ]
    for key in scalar_keys:
        assert data[key] == expected[key]
    assert data["z_scores"] == expected["z_scores"]


def test_auth_7_logout(client):
    """7. POST /logout -> / redirects to /login again."""
    resp = client.get("/")
    assert resp.status_code == 200

    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_auth_8_login_lockout(anon_client):
    """8. Six wrong sign-in attempts from one client -> login.locked, and the
    correct password is refused until the lock expires."""
    import time
    from app.app import _login_failures
    en = _load_i18n("en")

    for _ in range(5):
        resp = anon_client.post(
            "/login",
            data={"username": "testuser", "password": "badpassword"},
        )
        assert resp.status_code == 200
        assert en["login.error"] in resp.data.decode("utf-8")

    # 6th wrong attempt gets login.locked
    resp = anon_client.post(
        "/login",
        data={"username": "testuser", "password": "badpassword"},
    )
    assert resp.status_code == 200
    assert en["login.locked"] in resp.data.decode("utf-8")

    # Correct password is also refused while locked
    resp = anon_client.post(
        "/login",
        data={"username": "testuser", "password": "testpassword123"},
    )
    assert resp.status_code == 200
    assert en["login.locked"] in resp.data.decode("utf-8")

    # Expire the lock
    ip = "127.0.0.1"
    if ip in _login_failures:
        _login_failures[ip]["locked_until"] = time.time() - 1

    # Now correct password succeeds
    resp = anon_client.post(
        "/login",
        data={"username": "testuser", "password": "testpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_auth_9_signup_limit(anon_client):
    """9. Six sign-ups from one client within an hour -> the sixth gets register.limit."""
    en = _load_i18n("en")
    for i in range(5):
        resp = anon_client.post(
            "/register",
            data={
                "username": f"limit_user_{i}",
                "password": "password123",
                "confirm": "password123",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        anon_client.post("/logout")

    # 6th attempt
    resp = anon_client.post(
        "/register",
        data={
            "username": "limit_user_5",
            "password": "password123",
            "confirm": "password123",
        },
    )
    assert resp.status_code == 200
    assert en["register.limit"] in resp.data.decode("utf-8")


def test_auth_10_login_disabled(monkeypatch, tmp_path):
    """10. SSEF_LOGIN=off -> / and /api/evaluate work without signing in."""
    monkeypatch.setenv("SSEF_LOGIN", "off")
    dummy_auth = str(tmp_path / "must_not_be_created.json")
    monkeypatch.setenv("SSEF_AUTH_FILE", dummy_auth)

    from app.app import create_app
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert not os.path.exists(dummy_auth)

        resp = c.post(
            "/api/evaluate",
            data=json.dumps({"text": _first_story_text(), "fluency": False}),
            content_type="application/json",
        )
        assert resp.status_code == 200


def test_auth_11_healthz_public(anon_client):
    """11. GET /healthz -> ok without signing in."""
    resp = anon_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data.decode("utf-8") == "ok"


def test_auth_12_safe_next_url(anon_client):
    """12. next=https://example.com and next=//example.com after sign-in do not leave the site."""
    # Absolute URL
    resp = anon_client.post(
        "/login?next=https://example.com",
        data={"username": "testuser", "password": "testpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"

    # Protocol-relative URL
    resp = anon_client.post(
        "/login?next=//example.com",
        data={"username": "testuser", "password": "testpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"

    # Valid relative next URL
    resp = anon_client.post(
        "/login?next=/some/local/path",
        data={"username": "testuser", "password": "testpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/some/local/path"


def test_auth_13_concurrent_create_user(tmp_path):
    """13. Two threads calling create_user with different names at the same
    time -> both users exist and the file is valid JSON."""
    from app.auth import create_user
    import threading

    auth_path = str(tmp_path / "concurrent_auth.json")

    def worker(uname):
        create_user(auth_path, uname, "threadpassword123")

    t1 = threading.Thread(target=worker, args=("thread_user_1",))
    t2 = threading.Thread(target=worker, args=("thread_user_2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    with open(auth_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "thread_user_1" in data["users"]
    assert "thread_user_2" in data["users"]


def test_auth_14_no_tracked_file_contains_werkzeug_hash():
    """14. No tracked file contains a werkzeug hash (scan tracked text files
    for scrypt: and pbkdf2:, excluding this test file itself)."""
    import subprocess
    proc = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    files = proc.stdout.strip().splitlines()

    for fpath in files:
        norm = os.path.normpath(fpath)
        if norm.endswith("test_app.py"):
            continue
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        assert "scrypt:" not in content, f"Tracked file {fpath} contains scrypt hash"
        assert "pbkdf2:" not in content, f"Tracked file {fpath} contains pbkdf2 hash"
