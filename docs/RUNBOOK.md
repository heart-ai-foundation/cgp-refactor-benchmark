# Runbook

## Day 0

1. Confirm the task source.
2. Confirm installed agent CLIs.
3. Generate a smoke run plan.
4. Prepare one baseline and one CGP run.

## CodeScaleBench Inspection

Suggested first commands:

```bash
cd /home/dylan
git clone https://github.com/sourcegraph/CodeScaleBench.git
cd CodeScaleBench
find benchmarks -maxdepth 3 -type f | head -100
```

Do not load target solutions into prompts.

## Failure Classes

- `agent_failure`: agent crashed, timed out, or did not produce a patch.
- `infra_failure`: checkout, dependency, Docker, or verifier infrastructure failed.
- `task_failure`: agent produced a patch but task verifier/reward failed.
- `scoring_failure`: run completed but scorer crashed.

Preserve failed artifact folders.
