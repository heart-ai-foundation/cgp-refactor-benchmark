# CGP Refactor Completion Benchmark

Ready-to-run base for evaluating Continuity-Governed Prompting (CGP) on public refactor, migration, and multi-file codebase-change tasks.

This repository is intentionally separate from the completed CGP Reliability and Auditability Benchmark. It tests a new question: whether CGP improves task success, evidence completeness, scope discipline, and refactor/migration completion on realistic public tasks.

## Status

Preregistered benchmark. The public OSF registration is available at
https://osf.io/9dhkp/.

The preregistration freeze is tag `prereg-v0.1` at commit
`e65809a56959ca15d1e87bde5a017364fc55a13a`. Do not treat any benchmark
effect as established until confirmatory runs are completed and reported.

## Claims Boundary

Allowed before results:

- The prior CGP benchmark found reliability and auditability effects, but did not support scope-drift reduction because the registered drift endpoint hit a floor.
- This benchmark is designed to test public refactor/migration governance.

Not allowed before results:

- CGP reduces scope drift.
- CGP improves all coding-agent workflows.
- CGP makes agents more capable.

## One-Command Runs

```bash
python scripts/run_benchmark.py --preset smoke --agents codex --n-tasks 1
```

The documented 60-task benchmark matrix is also one command:

```bash
python scripts/run_benchmark.py --preset full
```

This packages CodeScaleBench tasks, renders baseline and CGP Harbor task
variants, writes the run plan, and runs Harbor for each agent-condition cell.
Use `--dry-run` to print the exact Harbor commands without launching agents:

```bash
python scripts/run_benchmark.py --preset full --dry-run
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
