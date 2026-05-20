# OSF Preregistration Draft

Study title: Continuity-Governed Prompting on Public Refactor and Migration Benchmark Tasks.

Repository checkpoint for preregistration: commit `066f440` or later preregistration-final commit that only updates documentation.

## Research Question

Does Continuity-Governed Prompting (CGP), operationalized as an external workflow scaffold, improve agent performance, evidence completeness, and scope discipline on public refactor, migration, dependency-refactor, and multi-file codebase-change tasks compared with ordinary baseline prompting?

## Design

Within-task, between-condition benchmark evaluation. Each included task is evaluated under both prompting conditions for each included agent.

Conditions:

- Baseline: ordinary task prompt with repository access and verification instructions.
- CGP: same task prompt plus bound objective, explicit scope, non-goals, evidence requirement, verification gate, stop condition, and closeout requirement.

The executable benchmark command is:

```bash
python scripts/run_benchmark.py --preset full
```

This command packages tasks, renders condition-specific Harbor task directories, writes the run plan, starts/uses Docker, and runs Harbor for every agent-condition cell.

## Task Set

Primary task source: CodeScaleBench.

Frozen manifest:

- `tasks/selected_tasks.codescale-60.jsonl`
- `tasks/harbor/codescalebench-60/`
- condition-rendered generated directories: `tasks/harbor/codescalebench-60-conditions/{baseline,cgp}/`

Task count: 60.

Task composition:

- 25 `migration-inventory`
- 13 `cross_file_refactoring`
- 2 `refactor`
- 2 `enterprise_dep_refactor`
- 8 `cross_module_bug_fix`
- 4 `bug_fix`
- 3 `bug_investigation`
- 3 `ccb_swebenchpro`

Collapsed task-type composition:

- 25 migration tasks
- 17 refactor or dependency-refactor tasks
- 18 multi-file codebase-change tasks

Selection rule: include CodeScaleBench migration and refactor/dependency-refactor tasks first, then include multi-file codebase-change categories to reach the documented 60-task target. Excluded tasks, if any are dropped after preregistration because of infrastructure failure or corrupted task packaging, will be recorded in `tasks/exclusions.jsonl` with task ID, source, reason, and inspection date.

Target solution files are not included in packaged benchmark tasks. The packager excludes `solution/` directories.

## Agents

Planned agents:

- `codex`
- `claude-code`
- `gemini-cli`

The planned full matrix is:

- 60 tasks
- 3 agents
- 2 conditions
- 1 replication

Total planned runs: 360.

Run plan:

- `runs/run_plan.codescale-60.csv`
- `runs/run_plan.codescale-60.metadata.json`

If one planned agent cannot run because of authentication, CLI, or Harbor adapter failure, the minimum acceptable confirmatory run is two agents. Any dropped agent will be documented before results are interpreted.

## Primary Endpoint

Primary dependent variable: Harbor verifier reward for each trial.

The primary analysis treats reward as a continuous score on the scale emitted by the task verifier, typically `0.0` to `1.0`.

If a task emits an explicit pass threshold or binary pass flag, binary success will be analyzed as a secondary endpoint.

## Secondary Endpoints

Secondary variables:

- Evidence completeness, scored 0-5.
- Scope drift count and binary scope-drift flag.
- False-green or incomplete-completion candidate flag.
- Refactor or migration obligation coverage, where machine-readable obligations are available.
- Boundary discipline, scored 0-3.
- Verification success or binary pass flag, where available.
- Patch size and touched-file count.
- Wall-clock time.
- Token or cost estimate, where available from agent logs.

## Failure Handling

Failures are classified before analysis:

- `infra_failure`: Docker, Harbor, checkout, task packaging, dependency setup, or verifier infrastructure failure.
- `agent_failure`: agent crash, authentication failure during a run, timeout, or failure to produce an output.
- `task_failure`: agent produced an output or patch, but the public verifier scored it as incomplete or incorrect.
- `scoring_failure`: Harbor completed but benchmark post-processing failed.

Primary analysis excludes confirmed `infra_failure` cells from task-performance estimates and reports their count separately. Agent failures remain part of agent performance unless caused by a shared infrastructure fault.

Smoke and pilot runs are infrastructure validation only and are not part of the confirmatory analysis.

## Human Review

Human review will sample 15% of completed trial artifacts, stratified by condition, agent, and collapsed task type where feasible. Human review adjudicates:

- false-green candidate status
- incomplete-completion events
- obvious scope-drift disagreements
- evidence completeness ambiguities

Human review does not override the primary Harbor verifier reward unless a trial is reclassified as an infrastructure or scoring failure.

## Analysis Plan

Primary comparison: compare CGP vs baseline reward within task and agent. The preferred summary is paired condition differences aggregated by task-agent cell, with confidence intervals over task-agent cells. Results will also be reported stratified by agent and collapsed task type.

Secondary analyses compare CGP vs baseline on evidence completeness, scope drift, false-green candidates, boundary discipline, and verification success. These analyses are interpreted as supportive and exploratory unless explicitly labeled confirmatory in a final preregistration.

No claim of scope-drift reduction, task-success improvement, or false-green reduction will be made unless the corresponding endpoint supports it on the frozen public task subset.

## Fallbacks

Fallback task sources, only if CodeScaleBench execution becomes infeasible before confirmatory runs:

- SWE-Refactor.
- SWE-bench Lite or Verified subset.

Use of a fallback source requires a new frozen manifest and an updated preregistration note before confirmatory analysis.
