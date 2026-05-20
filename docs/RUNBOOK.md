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

## Harbor Packaging

The installed Harbor CLI expects task schema `1.2`. CodeScaleBench tasks already
provide the right task files, but their `task.toml` metadata is older. Package
selected tasks before Harbor execution:

```bash
python scripts/package_codescale_harbor.py --limit 3
```

This writes:

- `tasks/harbor/codescalebench-refactor/`
- `tasks/selected_tasks.codescale-smoke.jsonl`

Local Harbor execution requires real Docker Compose. On this Fedora machine,
Harbor was installed with `uv tool install harbor`, and the working runtime is
rootless Docker from Fedora packages (`moby-engine`, `docker-cli`,
`docker-compose`) with Docker context `rootless`.

Smoke command:

```bash
harbor run \
  --path /home/dylan/cgp-refactor-benchmark/tasks/harbor/codescalebench-refactor \
  --agent nop \
  --n-concurrent 1 \
  --n-tasks 1 \
  --jobs-dir /home/dylan/cgp-refactor-benchmark/runs/harbor-smoke \
  --yes
```

The Docker smoke run on 2026-05-20 completed with `Trials=1`,
`Exceptions=0`, and reward `0.0` for the NOP agent.

## Failure Classes

- `agent_failure`: agent crashed, timed out, or did not produce a patch.
- `infra_failure`: checkout, dependency, Docker, or verifier infrastructure failed.
- `task_failure`: agent produced a patch but task verifier/reward failed.
- `scoring_failure`: run completed but scorer crashed.

Preserve failed artifact folders.
