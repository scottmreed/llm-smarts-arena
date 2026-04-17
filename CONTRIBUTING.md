# Contributing

This repository treats the benchmark as a versioned measurement instrument, not just a prompt file. Any change that affects scoring, comparability, or public artifact hygiene needs to be classified before it lands.

## Direct Contact Rule

If you believe a prompt contains a chemical error, ambiguity, or unfair constraint, contact the maintainer directly instead of opening a corrective pull request with a proposed answer. That keeps benchmark integrity and review flow manageable.

## Public Artifact Policy

Tracked benchmark runs should expose only shareable artifacts:

- `summary.json`
- `grade_result.json` with earned/max only
- `run_meta.json`
- figures under `figures/`

Do not commit raw model traces, parsed submissions, usage dumps, struggle reports, or trusted local grading files. Those belong under ignored local paths only.

## Versioning Policy

The benchmark uses semantic versioning with a stable scored core set defined in `benchmark_manifest.py`.

- **Major (`X.0.0`)**: use for breaking benchmark changes.
  These include corrected rubric errors that change scores, removed or replaced core scored questions, or any rewrite that breaks graph comparability.
- **Minor (`1.X.0`)**: use for additive, non-breaking public benchmark changes.
  These include new unscored diagnostic items, new reporting outputs, or new public metadata while preserving comparison on the scored core.
- **Patch (`1.1.X`)**: use for non-scoring harness, docs, plotting, or packaging changes.

If a change would make old and new public runs no longer directly comparable on the same graph, it is a major version change.

## Core Set Rule

Prefer adding non-core items over changing existing scored core questions. Keep a stable core set so:

- old runs remain comparable on the shared core metric
- new public prompt items do not invalidate prior graphs
- figures can continue to report a core percentage even when the public prompt grows

## Adding A New Question

Use this template in your design note or pull request description.

```md
## Question Proposal

- Title:
- Question ID target:
- Benchmark version impact: major / minor / patch
- Public role: scored / diagnostic
- Core set impact: stays core / non-core addition / core replacement
- Question category:
- Why this matters for tokenizer-sensitive chemical strings:
- Prompt text:
- Public answer-key treatment:
- Trusted grading impact:
- Tests to add:
```

Checklist:

- add the prompt to `smiles_llm_benchmark_questions.md`
- update `benchmark_manifest.py`
- add or update public grading logic in `smiles_llm_grader_v1.py`
- add tests
- regenerate `answer_key.md` if the public key changes

## Adding A New Model

Use this template for a new runnable model entry.

```md
## Model Proposal

- Provider family:
- API model string:
- Display label:
- Expected public output folder:
- Notes about token budget or output formatting:
- Validation run planned:
```

Checklist:

- confirm output goes to `outputs/<family>/<model-slug>/<timestamp>/`
- confirm raw artifacts remain local-only
- confirm figure labels are readable
- add any logo handling needed in `compare_benchmark_results.py`

## Review Standard

When reviewing benchmark changes, prioritize:

1. public artifact hygiene
2. scoring correctness
3. fairness and ambiguity
4. backward compatibility
5. graph clarity

Do not merge a scoring-affecting change without explicitly stating whether it is major, minor, or patch.
