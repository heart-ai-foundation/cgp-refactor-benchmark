"""Task manifest loading and deterministic run-plan generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .schema import BenchmarkTask, RunCell


RUN_PLAN_FIELDS = [
    "run_order",
    "run_id",
    "task_id",
    "task_source",
    "task_type",
    "agent",
    "condition",
    "replication",
]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
    return rows


def load_tasks(path: Path) -> list[BenchmarkTask]:
    tasks = [BenchmarkTask.from_mapping(row) for row in load_jsonl(path)]
    task_ids = [task.task_id for task in tasks]
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("task manifest contains duplicate task_id values")
    return tasks


def select_task_window(
    tasks: list[BenchmarkTask],
    task_start: int = 1,
    task_count: int | None = None,
) -> list[BenchmarkTask]:
    """Return a deterministic 1-based task window from a manifest."""
    if task_start < 1:
        raise ValueError("task_start must be >= 1")
    if task_count is not None and task_count < 1:
        raise ValueError("task_count must be >= 1")
    start_index = task_start - 1
    if start_index >= len(tasks):
        raise ValueError(
            f"task_start {task_start} is beyond manifest size {len(tasks)}"
        )
    end_index = None if task_count is None else start_index + task_count
    return tasks[start_index:end_index]


def generate_run_plan(
    tasks: list[BenchmarkTask],
    agents: list[str],
    conditions: list[str] | None = None,
    replications: int = 1,
) -> list[dict[str, str | int]]:
    conditions = conditions or ["baseline", "cgp"]
    rows: list[dict[str, str | int]] = []
    run_order = 1
    for task in tasks:
        for agent in agents:
            for replication in range(1, replications + 1):
                for condition in conditions:
                    cell = RunCell.build(task.task_id, agent, condition, replication)
                    rows.append(
                        {
                            "run_order": run_order,
                            "run_id": cell.run_id,
                            "task_id": task.task_id,
                            "task_source": task.task_source,
                            "task_type": task.task_type,
                            "agent": agent,
                            "condition": condition,
                            "replication": replication,
                        }
                    )
                    run_order += 1
    return rows


def write_run_plan(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_PLAN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
