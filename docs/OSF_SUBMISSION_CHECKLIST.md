# OSF Submission Checklist

Use this checklist immediately before submitting the OSF preregistration.

## Frozen Repository State

- Tag: `prereg-v0.1`
- Preregistration draft: `docs/OSF_PREREGISTRATION_DRAFT.md`
- Scoring spec: `docs/SCORING_SPEC.md`
- Frozen task manifest: `tasks/selected_tasks.codescale-60.jsonl`
- Frozen run plan: `runs/run_plan.codescale-60.csv`
- One-command execution: `python scripts/run_benchmark.py --preset full`

## Confirmatory Boundary

- Smoke and pilot runs are infrastructure validation only.
- Confirmatory analysis begins only after OSF submission.
- Confirmatory run command is exactly:

```bash
python scripts/run_benchmark.py --preset full
```

## OSF Entry Content

Copy `docs/OSF_PREREGISTRATION_DRAFT.md` into the OSF preregistration form or attach it as the preregistration protocol.

Attach or link the repository state identified by tag `prereg-v0.1`.

## Final Checks

- `git status --short` is clean.
- `python -m pytest` passes.
- The smoke result remains excluded from confirmatory analysis.
- No target `solution/` directories are packaged into the benchmark task set.
