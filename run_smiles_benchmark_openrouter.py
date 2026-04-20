#!/usr/bin/env python3
"""Run the benchmark against any OpenRouter model with no tools.

Uses the OpenAI SDK pointed at https://openrouter.ai/api/v1 — any model
available on OpenRouter can be tested by passing its full model ID, e.g.:
  google/gemma-4-31b-it:free
  meta-llama/llama-3.3-70b-instruct:free
  mistralai/mistral-7b-instruct:free

Design goals:
- **No tool use.** Raw chemical reasoning ability only.
- **Generous max_tokens** to guarantee room for the full answer list.
- **Single-turn auditability.** No retry on malformed output; failure is recorded.
- **Full response trace** written for audit.

Requirements: OPENROUTER_API_KEY, openai, RDKit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark_manifest import (
    BENCHMARK_ID,
    BENCHMARK_VERSION,
    CORE_QUESTION_IDS,
    CORE_QUESTION_SET,
    DIAGNOSTIC_QUESTION_IDS,
    PUBLIC_QUESTION_IDS,
    QUESTION_IDS,
    SCORED_QUESTION_IDS,
    percent_for_questions,
)
from benchmark_paths import run_directory
from benchmark_runner_utils import (
    build_diagnostic_match_report,
    build_single_turn_result,
    load_secret_benchmark_module,
    private_run_directory,
    sanitize_public_grade_result,
    write_run_artifacts,
)


def _load_dotenv():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key not in os.environ:
                        os.environ[key] = value


_load_dotenv()

_DIR = Path(__file__).resolve().parent
_QUESTIONS = _DIR / "smiles_llm_benchmark_questions.md"
_GRADER = _DIR / "smiles_llm_grader_v1.py"
_OUTPUT_DIR = _DIR / "outputs"

_DEFAULT_MODEL = "google/gemma-4-31b-it:free"
_FAMILY = "openrouter"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_TOKENS = 16000
_REQUIRED_IDS = PUBLIC_QUESTION_IDS[:]

_Q_TOPICS = {
    "Q1": "long mixed-heteroatom chain: heavy / total atoms w/ H / rotatable bonds",
    "Q2": "polystyrene heptamer: heavy / aromatic rings / rotatable bonds",
    "Q3": "polyol-amine: heavy / HBD / HBA (Lipinski)",
    "Q4": "SMARTS match count (10-carbon chain on undecane)",
    "Q5": "fully aromatic polycyclic: rings / heavy / formula",
    "Q6": "ketal-protected cyclohexanone: ring count / reagent / FG name",
    "Q7": "cubane: heavy / ring count / unique carbons",
    "Q8": "aza-triptycene-like: heavy / aromatic rings / ring count",
    "Q9": "biphenyl-allene: heavy / sp carbons / ketone tautomer SMILES",
    "Q10": "hydrogenation SMIRKS product",
    "Q11": "Fischer esterification SMIRKS products",
    "Q12": "amination SMIRKS products",
    "Q13": "monomer from PMMA-like backbone",
    "Q14": "monomer from poly(4-vinylpyridine) oligomer + aromatic ring count",
    "Q15": "SMARTS matches on diaryl carbonate",
    "Q16": "SMARTS matches for quaternary sp3 carbons",
    "Q17": "SMILES with space: fix and canonicalize",
    "Q18": "SMILES with tab: fix and canonicalize",
    "Q19": "SMILES with newline: fix and canonicalize",
    "Q20": "design a 50-heavy-atom 6-ring constrained molecule",
    "Q21": "constraint: 34-heavy 7-ring 5x6+2x5 N3O1S1",
    "Q22": "constraint: 34-heavy 7-ring 5x6+2x5 N4O1S1 HBA6 HBD0 rot3",
    "Q23": "constraint: 28-heavy 6-ring 4x6+2x5 N4O1 HBA5 HBD0 rot2",
    "Q24": "constraint: 25-heavy 5-ring 4x6+1x5 N2O1 HBA3 HBD0 rot2",
}


def _load_grader():
    spec = importlib.util.spec_from_file_location("smiles_llm_grader_v1", _GRADER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _text_response(response) -> str:
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        return message.content or ""
    return ""


def _dump_response_trace(response) -> list[dict]:
    trace = []
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        entry = {
            "index": 0,
            "type": "content",
            "role": getattr(message, "role", "assistant"),
        }
        if hasattr(message, "content"):
            entry["content"] = message.content
        trace.append(entry)
    return trace


def _usage_dict(response) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
    }


def _build_struggle_report(grade: dict, submitted_by_id: dict) -> dict:
    per_q = grade.get("per_question", {})
    losses = []
    full = []
    for qid, row in per_q.items():
        earned = float(row.get("earned", 0))
        mx = float(row.get("max", 0))
        if earned + 1e-9 < mx:
            losses.append(
                {
                    "id": qid,
                    "topic": _Q_TOPICS.get(qid, ""),
                    "points_lost": round(mx - earned, 3),
                    "earned": earned,
                    "max": mx,
                    "detail": row.get("detail"),
                    "model_answer": submitted_by_id.get(qid),
                }
            )
        else:
            full.append(qid)
    losses.sort(key=lambda x: (-x["points_lost"], x["id"]))
    return {
        "losses_ranked": losses,
        "questions_full_credit": sorted(full),
        "questions_with_any_loss": sorted(x["id"] for x in losses),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=_DEFAULT_MODEL, help="OpenRouter model ID (e.g. google/gemma-4-31b-it:free)")
    parser.add_argument("--max-tokens", type=int, default=_MAX_TOKENS, help="Max output tokens")
    return parser.parse_args()


def main() -> None:
    if not _QUESTIONS.is_file():
        raise SystemExit(f"Missing questions file: {_QUESTIONS}")
    if not _GRADER.is_file():
        raise SystemExit(f"Missing grader: {_GRADER}")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set")

    try:
        from openai import OpenAI
    except ImportError as e:
        raise SystemExit("Install openai: pip install openai") from e

    args = _parse_args()
    model_name = args.model
    max_tokens = args.max_tokens
    prompt = _QUESTIONS.read_text(encoding="utf-8")

    client = OpenAI(
        base_url=_OPENROUTER_BASE_URL,
        api_key=api_key,
    )

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_directory(_OUTPUT_DIR, _FAMILY, model_name, stamp)
    run_dir.mkdir(parents=True, exist_ok=True)
    private_run_dir = private_run_directory(_DIR, _FAMILY, run_dir.parent.name, stamp)

    meta = {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_major": int(BENCHMARK_VERSION.split(".", 1)[0]),
        "core_question_set": CORE_QUESTION_SET,
        "core_question_ids": CORE_QUESTION_IDS,
        "scored_question_ids": SCORED_QUESTION_IDS,
        "diagnostic_question_ids": DIAGNOSTIC_QUESTION_IDS,
        "public_question_ids": PUBLIC_QUESTION_IDS,
        "model": model_name,
        "family": _FAMILY,
        "thinking": None,
        "tools": None,
        "max_tokens": max_tokens,
        "questions_file": str(_QUESTIONS.relative_to(_DIR)),
        "grader_file": str(_GRADER.relative_to(_DIR)),
        "timestamp_utc": stamp,
        "required_ids": _REQUIRED_IDS,
    }

    print(f"Running benchmark with model: {model_name} (via OpenRouter)")
    print("Sending request...")

    response = client.chat.completions.create(
        model=model_name,
        max_completion_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    raw1 = _text_response(response)
    trace1 = _dump_response_trace(response)
    usage1 = _usage_dict(response)

    single_turn = build_single_turn_result(raw1, _REQUIRED_IDS)
    final_payload = single_turn["payload"]
    missing = single_turn["missing_ids_turn1"]
    retry_used = single_turn["retry_used"]
    if missing:
        print(f"Turn 1 submission incomplete or invalid. Missing IDs: {missing}")
    else:
        print("All IDs present after turn 1")

    grader = _load_grader()
    grade = grader.grade(final_payload if isinstance(final_payload, dict) else {"answers": []})
    public_grade = sanitize_public_grade_result(grade)

    submitted_by_id = {}
    if isinstance(final_payload, dict):
        for a in final_payload.get("answers", []) or []:
            if isinstance(a, dict) and "id" in a:
                submitted_by_id[a["id"]] = a.get("answer")

    summary = {
        "score": grade.get("score"),
        "max_points": grade.get("max_points"),
        "percent": grade.get("percent"),
        "core_percent": percent_for_questions(grade.get("per_question", {}), CORE_QUESTION_IDS),
        "parse_ok": single_turn["parse_ok"],
        "retry_used": retry_used,
        "missing_ids_turn1": missing,
        "missing_ids_final": single_turn["missing_ids_final"],
    }

    meta["summary"] = summary

    struggle = _build_struggle_report(grade, submitted_by_id)
    struggle["summary"] = summary
    private_payload = {
        "model_response_turn1_raw.txt": raw1,
        "model_response_turn1_trace.json": trace1,
        "model_submission_final.json": final_payload if final_payload else {"answers": []},
        "usage_turn1.json": usage1,
    }
    trusted_payload = None
    secret_module = load_secret_benchmark_module(_DIR)
    if secret_module is not None and hasattr(secret_module, "grade_submission"):
        trusted_grade = secret_module.grade_submission(
            final_payload if isinstance(final_payload, dict) else {"answers": []}
        )
        diagnostic_report = build_diagnostic_match_report(
            submitted_by_id,
            grader.compute_public_answer_key(),
            grader.canon_or_none,
            grader.canon_list_sorted,
        )
        trusted_payload = {
            "trusted_grade_result.json": trusted_grade,
            "diagnostic_report.json": diagnostic_report,
        }

    write_run_artifacts(
        public_dir=run_dir,
        private_dir=private_run_dir,
        public_grade=public_grade,
        summary=summary,
        meta=meta,
        struggle=struggle,
        private_payload=private_payload,
        trusted_payload=trusted_payload,
    )

    print("\n" + "=" * 50)
    print(f"Benchmark complete!")
    print(f"Score: {summary['score']} / {summary['max_points']} ({summary['percent']}%)")
    print(f"Output directory: {run_dir}")
    print("=" * 50)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
