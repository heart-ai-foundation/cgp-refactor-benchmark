# Runbook

## Day 0

1. Confirm the task source.
2. Confirm installed agent CLIs.
3. Run the one-command smoke path.
4. Run the one-command full benchmark path after OSF preregistration freeze.

## One-Command Execution

Smoke one task per baseline/CGP condition for one agent:

```bash
python scripts/run_benchmark.py --preset smoke --agents codex --n-tasks 1
```

Prepare the full 60-task benchmark package and run plan without launching
agents:

```bash
python scripts/run_benchmark.py --preset full --prepare-only
```

Print the full benchmark Harbor commands without launching agents:

```bash
python scripts/run_benchmark.py --preset full --dry-run
```

Run the documented full matrix:

```bash
python scripts/run_benchmark.py --preset full
```

The full default is 60 tasks x 3 agents x 2 conditions x 1 replication = 360
runs. It renders condition-specific Harbor task directories under
`tasks/harbor/codescalebench-60-conditions/` and writes results under
`runs/harbor/full/{condition}/{agent}/r1/`.

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
python scripts/package_codescale_harbor.py \
  --preset full \
  --limit 60 \
  --out-root tasks/harbor/codescalebench-60 \
  --manifest tasks/selected_tasks.codescale-60.jsonl
```

This writes:

- `tasks/harbor/codescalebench-refactor/`
- `tasks/selected_tasks.codescale-smoke.jsonl`
- `tasks/harbor/codescalebench-60/`
- `tasks/selected_tasks.codescale-60.jsonl`

The 60-task package follows the PRD/OSF task-source rule: CodeScaleBench
refactor and migration tasks first, then dependency-refactor and multi-file
codebase-change categories to reach the documented 50-60 task target. Current
deterministic composition:

- 25 `migration-inventory`
- 13 `cross_file_refactoring`
- 2 `refactor`
- 2 `enterprise_dep_refactor`
- 8 `cross_module_bug_fix`
- 4 `bug_fix`
- 3 `bug_investigation`
- 3 `ccb_swebenchpro`

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

Docker smoke runs on 2026-05-20 completed with `Trials=1`, `Exceptions=0`,
and reward `0.0` for the NOP agent on both the 3-task smoke package and the
60-task benchmark package.

## Failure Classes

- `agent_failure`: agent crashed, timed out, or did not produce a patch.
- `infra_failure`: checkout, dependency, Docker, or verifier infrastructure failed.
- `task_failure`: agent produced a patch but task verifier/reward failed.
- `scoring_failure`: run completed but scorer crashed.

Preserve failed artifact folders.
