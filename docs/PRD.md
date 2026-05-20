# CGP Refactor Completion Benchmark PRD

Build a public-task benchmark evaluation that tests Continuity-Governed Prompting on realistic codebase refactor, migration, dependency-update, and multi-file change tasks.

## Two-Day Ready-To-Run Criteria

- Task adapter can load selected public tasks into `tasks/*.jsonl`.
- Baseline and CGP prompts are generated from the same normalized task input.
- Runner can prepare stable artifact folders under `runs/raw/`.
- Scorers emit upstream result, touched files, evidence completeness, completion claim, scope drift, and false-green candidate fields.
- README explains the smoke path.

## One-Week Criteria

- 60 public CodeScaleBench tasks.
- 3 agents planned, minimum 2 if tool constraints require it.
- Baseline and CGP conditions for every included agent-task pair.
- Exclusion log for dropped tasks.
- Summary tables and 15 percent human-review sample.

## Frozen Benchmark Shape

- Task manifest: `tasks/selected_tasks.codescale-60.jsonl`
- Harbor task package: `tasks/harbor/codescalebench-60/`
- Run plan: `runs/run_plan.codescale-60.csv`
- Agents: `codex`, `claude-code`, `gemini-cli`
- Conditions: `baseline`, `cgp`
- Planned matrix: 60 tasks x 3 agents x 2 conditions x 1 replication = 360 runs

One-command execution:

```bash
python scripts/run_benchmark.py --preset full
```

## Claims Boundary

No claim of scope-drift reduction, task-success improvement, or false-green reduction may be made until the corresponding endpoint supports it on the selected public task subset.
