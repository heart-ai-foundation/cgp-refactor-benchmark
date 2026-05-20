# OSF Preregistration Draft

Study title: Continuity-Governed Prompting on Public Refactor and Migration Benchmark Tasks.

Research question: Does CGP, operationalized as an external workflow scaffold, improve agent performance, evidence completeness, and scope discipline on public refactor and migration benchmark tasks compared with ordinary baseline prompting?

Design: within-task, between-condition benchmark evaluation.

Conditions:

- Baseline: ordinary task prompt with repository access and verification instructions.
- CGP: same task prompt plus bound objective, explicit scope, non-goals, evidence requirement, verification gate, stop condition, and closeout requirement.

Primary task source: CodeScaleBench refactor and migration tasks.

Fallbacks:

- SWE-Refactor.
- SWE-bench Lite or Verified subset.

Primary dependent variable: public benchmark task success or upstream reward.

Secondary variables: evidence completeness, scope drift, false-green / incomplete-completion event flag, affected-surface coverage, verification success, patch size, wall-clock time, token/cost estimate where available.
