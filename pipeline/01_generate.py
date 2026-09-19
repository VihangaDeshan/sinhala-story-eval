#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 01 — corpus generation.

This stage does NOT restate the prompt. It imports `prompts_v3.py`, which is
the actual module used on 2026-08-19, copied into the repository byte for
byte. A prompt paraphrased into a second file is a prompt that can drift out
of step with the one the corpus was generated from, and the project has
already been bitten once by reading the wrong prompt variant (DEC-045).

GENERATION IS NOT BIT-REPRODUCIBLE
----------------------------------
The seed was removed (DEC-033) because a fixed seed made every retry return
an identical story, so a topic that missed the length gate on attempt 1 was
stuck outside it for all four attempts. Re-running this stage will therefore
produce DIFFERENT stories. That is expected and is why the corpus ships as
data rather than as a script to be re-run.

What is reproducible is the *provenance*: this stage records the prompt
text, its SHA-256, the model id, the access date, the parameters, the gate,
every attempt and its word count, and the provider's generation id. Those
records are what an examiner can check.

USAGE

    python pipeline/01_generate.py --dry-run     # build prompts, no API calls
    python pipeline/01_generate.py --model gemini --variant A2

--dry-run needs no key and no network: it builds all ten prompts, prints
their SHA-256 digests, and stops. Use it to confirm that the prompt in the
repository is the prompt that produced the corpus.

ENVIRONMENT
    OPENROUTER_API_KEY   required for a real run

WARNING ON MODEL IDS
--------------------
`prompts_v3.MODEL_IDS` records the plan as of 2026-08-19 and does NOT match
the corpus that was actually produced: it names kimi and leaves chatgpt as a
gap, and it does not mention deepseek at all. The executed run used
gemini-3.5-flash, deepseek-v4-pro and gpt-5.6-sol. The mismatch is left in
place rather than edited, because prompts_v3.py is a dated record. The ids
actually used are listed below and must be reconciled before publication.
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import prompts_v3 as P                                        # noqa: E402

REPO = os.path.join(HERE, "..")
RAW_DIR = os.path.join(REPO, "data/raw")
LOG_PATH = os.path.join(REPO, "data/raw/attempt_log.csv")

# The ids of the executed run. See the warning above.
RUN_MODEL_IDS = {
    "gemini":   "google/gemini-3.5-flash",
    "deepseek": "deepseek/deepseek-v4-pro",
    "gpt":      "openai/gpt-5.6-sol",
}

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_all(variant):
    return {tid: P.build_prompt(tid, variant) for tid in P.TOPICS}


def dry_run(variant):
    prompts = build_all(variant)
    print(f"variant {variant} · {len(prompts)} topics · "
          f"gate {P.LENGTH_GATE} · {P.MAX_ATTEMPTS} attempts")
    print(f"params: {P.GEN_PARAMS}")
    print()
    for tid, text in prompts.items():
        print(f"{tid:18s} {sha256(text)}  {len(text.split())} words")
    print()
    sample = prompts["N12_ITNightShift"]
    print("--- N12_ITNightShift / " + variant + " ---")
    print(sample)
    print()
    a1 = P.build_prompt("N12_ITNightShift", "A1")
    a2 = P.build_prompt("N12_ITNightShift", "A2")
    only_a1 = [ln for ln in a1.splitlines() if ln not in a2.splitlines()]
    print("lines present in A1 but not in A2:")
    for ln in only_a1:
        print("   " + ln)
    print()
    print("A2 is the variant used for the corpus. The register instruction")
    print("appears only in A1, so register was not instructed — this is the")
    print("condition the spontaneous-adherence finding depends on.")


def call_openrouter(model_id, prompt, params):
    """One independent call. No conversation history: an attempt is never
    told that a previous attempt missed the gate, because that would be a
    different prompt and the three models would no longer have received
    identical input."""
    import urllib.request

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Use --dry-run to "
                         "inspect prompts without calling the API.")
    body = {"model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params["temperature"],
            "max_tokens": params["max_tokens"]}
    if params.get("seed") is not None:
        body["seed"] = params["seed"]
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        payload = json.loads(r.read().decode("utf-8"))
    choice = payload["choices"][0]
    return (choice["message"].get("content") or "",
            {"generation_id": payload.get("id"),
             "finish_reason": choice.get("finish_reason")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="A2", choices=["A1", "A2"])
    ap.add_argument("--model", choices=sorted(RUN_MODEL_IDS))
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="override; Gemini needs ~30000 because its thinking "
                         "tokens count against the output ceiling")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        dry_run(args.variant)
        return
    if not args.model:
        raise SystemExit("--model is required for a real run")

    params = dict(P.GEN_PARAMS)
    if args.max_tokens:
        params["max_tokens"] = args.max_tokens
    model_id = RUN_MODEL_IDS[args.model]
    accessed = dt.date.today().isoformat()

    os.makedirs(RAW_DIR, exist_ok=True)
    log = []
    produced = 0

    for tid in P.TOPICS:
        prompt = P.build_prompt(tid, args.variant)
        digest = sha256(prompt)
        accepted_text = None
        for attempt in range(1, P.MAX_ATTEMPTS + 1):
            text, meta = call_openrouter(model_id, prompt, params)
            text = P.strip_preamble(text)
            ok, wc, reason = P.accept(text)
            raw_name = f"{tid}__{args.model}__{args.variant}__a{attempt}.txt"
            with open(os.path.join(RAW_DIR, raw_name), "w",
                      encoding="utf-8") as f:
                f.write(text)
            log.append({
                "topic_id": tid, "model": args.model, "model_id": model_id,
                "variant": args.variant, "prompt_sha256": digest,
                "attempt": attempt, "word_count": wc, "accepted": ok,
                "reason": reason or "", "raw_file": raw_name,
                "temperature": params["temperature"],
                "max_tokens": params["max_tokens"],
                "seed": params.get("seed"),
                "gate_low": P.LENGTH_GATE[0], "gate_high": P.LENGTH_GATE[1],
                "generation_id": meta.get("generation_id"),
                "finish_reason": meta.get("finish_reason"),
                "accessed": accessed,
            })
            if meta.get("finish_reason") in ("length", "MAX_TOKENS"):
                print(f"  {tid} attempt {attempt}: TRUNCATED by the token "
                      f"ceiling — raise --max-tokens; this attempt is not "
                      f"comparable to the others")
            print(f"  {tid} attempt {attempt}: {wc} words, "
                  f"{'accepted' if ok else reason}")
            if ok:
                accepted_text = text
                break
        if accepted_text is None:
            print(f"  {tid}: NOT PRODUCED after {P.MAX_ATTEMPTS} attempts — "
                  f"this is a finding about the model, not an error")
        else:
            produced += 1

    new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        if new:
            w.writeheader()
        w.writerows(log)

    print(f"\n{produced}/{len(P.TOPICS)} accepted for {args.model}")
    print(f"attempt log appended to {LOG_PATH}")
    print("Rejections are data: they answer whether the model complied with "
          "the length instruction. Publish the log with the dataset.")
    print("Inspect the first and last line of every accepted raw file — "
          "strip_preamble trims blank lines only and cannot remove English "
          "planning prose.")


if __name__ == "__main__":
    main()
