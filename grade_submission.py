#!/usr/bin/env python3
"""Grade a benchmark submission."""

import importlib.util
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python grade_submission.py <submission_path> [model_name]")
    sys.exit(1)

submission_path = Path(sys.argv[1])
model_name = sys.argv[2] if len(sys.argv) > 2 else "unknown"

_DIR = Path(__file__).resolve().parent
_GRADER = _DIR / "smiles_llm_grader_v1.py"

spec = importlib.util.spec_from_file_location("smiles_llm_grader_v1", _GRADER)
grader_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader_mod)

with open(submission_path) as f:
    submission = json.load(f)

result = grader_mod.grade(submission)

run_dir = submission_path.parent

# Write grade_result.json
with open(run_dir / "grade_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)

# Create summary
summary = {
    "score": result["score"],
    "max_points": result["max_points"],
    "percent": result["percent"],
    "retry_used": (run_dir / "model_response_turn2_raw.txt").exists(),
    "missing_ids_turn1": [],
    "missing_ids_final": [],
}

with open(run_dir / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)

# Create run_meta
meta = {
    "model": model_name,
    "timestamp_utc": run_dir.name,
    "summary": summary,
}

with open(run_dir / "run_meta.json", "w") as f:
    json.dump(meta, f, indent=2)

print(f"Graded {model_name}: {summary['score']:.2f} / {summary['max_points']:.0f} ({summary['percent']:.2f}%)")
