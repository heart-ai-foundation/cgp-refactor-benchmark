# Scoring Specification

Primary endpoint: Harbor verifier reward for each trial. Treat reward as a
continuous score on the scale emitted by the public task verifier, typically
`0.0` to `1.0`.

Secondary binary success: task pass flag or `reward >= task pass threshold`,
where the verifier exposes a threshold.

Secondary endpoints:

- Evidence completeness, 0-5.
- Scope drift count and binary flag.
- False-green / incomplete-completion candidate flag.
- Refactor or migration obligation coverage.
- Boundary discipline, 0-3.
- Cost and time, exploratory.

## Failure Classes

- `infra_failure`: Docker, Harbor, checkout, task packaging, dependency setup,
  or verifier infrastructure failure.
- `agent_failure`: agent crash, authentication failure during a run, timeout,
  or failure to produce an output.
- `task_failure`: agent produced an output or patch, but the public verifier
  scored it as incomplete or incorrect.
- `scoring_failure`: Harbor completed but benchmark post-processing failed.

Confirmed infrastructure failures are reported separately and excluded from
task-performance estimates. Agent failures remain part of agent performance
unless caused by shared infrastructure.

## Evidence Completeness

One point each:

- Final diff or patch captured.
- Verification command output captured.
- Transcript or run log captured.
- Agent states what changed and what evidence supports completion.
- Limitations or unfinished work are explicitly stated when present.

## False-Green Candidate

`completion_claimed && verification_green && obligations_missing`

Human review adjudicates final false-green labels.

## Human Review Sample

Review 15% of completed trial artifacts, stratified by condition, agent, and
collapsed task type where feasible.
