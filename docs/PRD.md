# CGP Refactor Completion Benchmark PRD

Build a public-task benchmark evaluation that tests Continuity-Governed Prompting on realistic codebase refactor, migration, dependency-update, and multi-file change tasks.

## Two-Day Ready-To-Run Criteria

- Task adapter can load selected public tasks into `tasks/*.jsonl`.
- Baseline and CGP prompts are generated from the same normalized task input.
- Runner can prepare stable artifact folders under `runs/raw/`.
- Scorers emit upstream result, touched files, evidence completeness, completion claim, scope drift, and false-green candidate fields.
- README explains the smoke path.

## One-Week Criteria

- 50-60 public tasks if feasible, or a documented smaller set.
- 3 agents if feasible, minimum 2 if tool constraints require it.
- Baseline and CGP conditions for every included agent-task pair.
- Exclusion log for dropped tasks.
- Summary tables and 10-20 percent human-review sample.

## Claims Boundary

No claim of scope-drift reduction, task-success improvement, or false-green reduction may be made until the corresponding endpoint supports it on the selected public task subset.
