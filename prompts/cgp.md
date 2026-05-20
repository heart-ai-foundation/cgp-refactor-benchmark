# CGP Benchmark Task

Run condition: `{condition}`
Task ID: `{task_id}`
Task source: `{task_source}`
Task type: `{task_type}`

## Bound Objective

{instruction}

## Repository

`{repo}`

Base ref: `{base_ref}`

## Allowed Scope

{allowed_paths}

## Non-Goals

- Do not make unrelated refactors.
- Do not change dependencies, formatting, or configuration unless required by the task.
- Do not use target solution data or hidden benchmark answers.

## Setup

{setup_commands}

## Verification Gate

{verification_commands}

## Refactor Obligations

{obligations}

## Evidence Requirement

Produce or preserve these artifacts in the run folder:

- `diff.patch`
- `verification.log` or `verification.json`
- `transcript.log`, `transcript.txt`, `transcript.json`, or `transcript.jsonl`
- `final_response.txt` or `closeout.md`

Your closeout must state what changed, what verification supports completion, and any limitations or unfinished work.

## Stop Condition

If task instructions, allowed scope, repository state, or verification requirements disagree, stop and report the conflict instead of guessing.
