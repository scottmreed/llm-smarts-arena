from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Callable


PRIVATE_ROOT_NAME = ".benchmark_private"
SECRET_MODULE_NAME = "secret_benchmark.py"


def extract_json_substring(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_json_loose(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        extracted = extract_json_substring(text)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            return None


def missing_ids(payload: dict[str, Any] | None, required_ids: list[str]) -> list[str]:
    if not isinstance(payload, dict):
        return list(required_ids)
    answers = payload.get("answers") or []
    present = {a.get("id") for a in answers if isinstance(a, dict)}
    return [q for q in required_ids if q not in present]


def build_single_turn_result(raw_text: str, required_ids: list[str]) -> dict[str, Any]:
    payload = parse_json_loose(raw_text)
    parse_ok = isinstance(payload, dict)
    final_payload = payload if parse_ok else {"answers": []}
    missing = missing_ids(payload if parse_ok else None, required_ids)
    return {
        "payload": final_payload,
        "parse_ok": parse_ok,
        "retry_used": False,
        "missing_ids_turn1": missing,
        "missing_ids_final": missing_ids(final_payload, required_ids),
    }


def sanitize_public_grade_result(grade: dict[str, Any]) -> dict[str, Any]:
    per_question = grade.get("per_question", {})
    return {
        "score": grade.get("score"),
        "max_points": grade.get("max_points"),
        "percent": grade.get("percent"),
        "per_question": {
            qid: {"earned": row.get("earned"), "max": row.get("max")}
            for qid, row in per_question.items()
            if isinstance(row, dict)
        },
    }


def load_secret_benchmark_module(root: Path):
    module_path = root / PRIVATE_ROOT_NAME / SECRET_MODULE_NAME
    if not module_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("secret_benchmark", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def private_root(root: Path) -> Path:
    return root / PRIVATE_ROOT_NAME


def private_run_directory(root: Path, family: str, model_slug: str, stamp: str) -> Path:
    return private_root(root) / "runs" / family / model_slug / stamp


def _write_payload(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
        return
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_run_artifacts(
    *,
    public_dir: Path,
    private_dir: Path,
    public_grade: dict[str, Any],
    summary: dict[str, Any],
    meta: dict[str, Any],
    struggle: dict[str, Any],
    private_payload: dict[str, Any],
    trusted_payload: dict[str, Any] | None,
) -> None:
    public_dir.mkdir(parents=True, exist_ok=True)
    _write_payload(public_dir / "summary.json", summary)
    _write_payload(public_dir / "grade_result.json", public_grade)
    _write_payload(public_dir / "run_meta.json", meta)

    if private_payload or trusted_payload or struggle:
        private_dir.mkdir(parents=True, exist_ok=True)

    if struggle:
        _write_payload(private_dir / "struggle_report.json", struggle)

    for filename, payload in private_payload.items():
        _write_payload(private_dir / filename, payload)

    if trusted_payload:
        for filename, payload in trusted_payload.items():
            _write_payload(private_dir / filename, payload)


def build_diagnostic_match_report(
    submitted_by_id: dict[str, Any],
    public_key: dict[str, Any],
    canon_or_none: Callable[[Any], str | None],
    canon_list_sorted: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for qid, entry in public_key.items():
        if entry.get("status") != "unscored diagnostic":
            continue
        answer = submitted_by_id.get(qid)
        reference = entry.get("public_reference_answer", {})
        payload_report = {
            "submitted": answer,
            "exact_match": False,
            "canonical_match": False,
        }
        if not isinstance(answer, dict):
            report[qid] = payload_report
            continue

        if "smiles" in reference:
            submitted_smiles = answer.get("smiles")
            reference_smiles = reference.get("smiles")
            payload_report["exact_match"] = submitted_smiles == reference_smiles
            payload_report["canonical_match"] = canon_or_none(submitted_smiles) == canon_or_none(reference_smiles)
        elif "smiles_list" in reference:
            submitted_list = answer.get("smiles_list")
            reference_list = reference.get("smiles_list")
            payload_report["exact_match"] = submitted_list == reference_list
            if isinstance(submitted_list, list) and isinstance(reference_list, list):
                payload_report["canonical_match"] = canon_list_sorted(submitted_list) == canon_list_sorted(reference_list)
        report[qid] = payload_report
    return report
