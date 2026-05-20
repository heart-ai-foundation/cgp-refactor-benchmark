# CGP Refactor Completion Benchmark

Ready-to-run base for evaluating Continuity-Governed Prompting (CGP) on public refactor, migration, and multi-file codebase-change tasks.

This repository is intentionally separate from the completed CGP Reliability and Auditability Benchmark. It tests a new question: whether CGP improves task success, evidence completeness, scope discipline, and refactor/migration completion on realistic public tasks.

## Status

Active scaffold. Do not treat any benchmark effect as established until the run plan, task source, scorers, and results are frozen and reported.

## Claims Boundary

Allowed before results:

- The prior CGP benchmark found reliability and auditability effects, but did not support scope-drift reduction because the registered drift endpoint hit a floor.
- This benchmark is designed to test public refactor/migration governance.

Not allowed before results:

- CGP reduces scope drift.
- CGP improves all coding-agent workflows.
- CGP makes agents more capable.

## Quick Smoke Path

```bash
python scripts/package_codescale_harbor.py --limit 3
python scripts/generate_run_plan.py
python scripts/prepare_run.py --run-id local-refactor-smoke-codex-baseline-r1
python scripts/prepare_run.py --run-id local-refactor-smoke-codex-cgp-r1
```

For Harbor execution against packaged CodeScaleBench tasks:

```bash
harbor run \
  --path tasks/harbor/codescalebench-refactor \
  --agent nop \
  --n-concurrent 1 \
  --n-tasks 1 \
  --jobs-dir runs/harbor-smoke \
  --yes
```

After a run directory has artifacts, score it:

```bash
python scripts/score_run.py runs/raw/local-refactor-smoke-codex-cgp-r1 --out runs/raw/local-refactor-smoke-codex-cgp-r1/score.json
```

For a JSONL score file:

```bash
python scripts/summarize.py --scores results/scores.jsonl
```

## Layout

- `tasks/selected_tasks.example.jsonl` - normalized example task manifest
- `prompts/` - baseline and CGP prompt templates
- `src/cgp_refactor_benchmark/` - adapter, prompt, scoring, and summary code
- `scripts/` - CLI entry points
- `runs/` - generated run plans and raw run artifacts
- `results/` - score JSONL and summary CSV outputs
- `docs/` - PRD, scoring spec, runbook, preregistration draft
