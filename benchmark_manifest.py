from __future__ import annotations

from typing import Any


BENCHMARK_ID = "llm-smarts-arena"
BENCHMARK_NAME = "LLM SMILES/SMARTS Arena"
BENCHMARK_VERSION = "1.1.0"
CORE_QUESTION_SET = "core-v1"

SCORED_QUESTION_IDS = [f"Q{i}" for i in range(1, 25)]
DIAGNOSTIC_QUESTION_IDS = ["Q-C1", "Q-C2", "Q-C3", "Q-C5", "Q-C8", "Q-C10"]
PUBLIC_QUESTION_IDS = [
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Q-C1",
    "Q5",
    "Q6",
    "Q7",
    "Q8",
    "Q-C2",
    "Q9",
    "Q10",
    "Q11",
    "Q12",
    "Q-C3",
    "Q13",
    "Q14",
    "Q15",
    "Q16",
    "Q-C5",
    "Q17",
    "Q18",
    "Q19",
    "Q20",
    "Q-C8",
    "Q21",
    "Q22",
    "Q23",
    "Q24",
    "Q-C10",
]
QUESTION_IDS = PUBLIC_QUESTION_IDS[:]
CORE_QUESTION_IDS = SCORED_QUESTION_IDS[:]

QUESTION_CATEGORIES = {
    "Long Chains": ["Q1", "Q2", "Q3", "Q4"],
    "Ring Systems": ["Q5", "Q6", "Q7", "Q8", "Q9"],
    "Reactions": ["Q10", "Q11", "Q12"],
    "Polymers": ["Q13", "Q14"],
    "SMARTS": ["Q15", "Q16"],
    "SMILES Fix": ["Q17", "Q18", "Q19"],
    "Design": ["Q20"],
    "Constraints": ["Q21", "Q22", "Q23", "Q24"],
}

FAMILY_DISPLAY_NAMES = {
    "claude": "Anthropic",
    "openai": "OpenAI",
}


def benchmark_major(version: str = BENCHMARK_VERSION) -> int:
    return int(version.split(".", 1)[0])


def percent_for_questions(per_question: dict[str, Any], question_ids: list[str]) -> float:
    earned = 0.0
    maximum = 0.0
    for qid in question_ids:
        row = per_question.get(qid)
        if not isinstance(row, dict):
            continue
        earned += float(row.get("earned", 0.0))
        maximum += float(row.get("max", 0.0))
    return round((100.0 * earned / maximum) if maximum else 0.0, 2)
