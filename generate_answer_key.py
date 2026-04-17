#!/usr/bin/env python3
"""Build the public human-readable benchmark key."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from benchmark_manifest import BENCHMARK_VERSION, DIAGNOSTIC_QUESTION_IDS, QUESTION_CATEGORIES

_DIR = Path(__file__).resolve().parent
_GRADER = _DIR / "smiles_llm_grader_v1.py"
_OUT_MD = _DIR / "answer_key.md"


def _load_grader():
    spec = importlib.util.spec_from_file_location("smiles_llm_grader_v1", _GRADER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _json_block(data: object) -> list[str]:
    return ["```json", json.dumps(data, indent=2, sort_keys=True), "```", ""]


def render_answer_key_text(public_key: dict[str, object]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Answer Key")
    add("")
    add(f"Generated for benchmark version `{BENCHMARK_VERSION}`.")
    add("")
    add("Trusted scoring material is withheld from the public repository.")
    add("The public key only documents answer shapes plus unscored diagnostic reference entries.")
    add("")

    for category, qids in QUESTION_CATEGORIES.items():
        add(f"## {category}")
        add("")
        for qid in qids:
            add(f"### {qid}")
            add("")
            lines.extend(_json_block(public_key[qid]))

    add("## Diagnostic")
    add("")
    for qid in DIAGNOSTIC_QUESTION_IDS:
        add(f"### {qid}")
        add("")
        lines.extend(_json_block(public_key[qid]))

    return "\n".join(lines)


def main() -> None:
    grader = _load_grader()
    text = render_answer_key_text(grader.compute_public_answer_key())
    _OUT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {_OUT_MD}")


if __name__ == "__main__":
    main()
