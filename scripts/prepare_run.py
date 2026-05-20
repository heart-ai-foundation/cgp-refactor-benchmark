#!/usr/bin/env python3
"""Prepare one benchmark run directory."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cgp_refactor_benchmark.prompts import render_prompt
from cgp_refactor_benchmark.runner.artifacts import prepare_run_dir
from cgp_refactor_benchmark.schema import RunCell
from cgp_refactor_benchmark.tasks import load_tasks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--tasks", type=Path, default=Path("tasks/selected_tasks.example.jsonl"))
    parser.add_argument("--run-plan", type=Path, default=Path("runs/run_plan.csv"))
    parser.add_argument("--out-root", type=Path, default=Path("runs/raw"))
    args = parser.parse_args()

    tasks = {task.task_id: task for task in load_tasks(args.tasks)}
    with args.run_plan.open(newline="", encoding="utf-8") as handle:
        rows = {row["run_id"]: row for row in csv.DictReader(handle)}
    if args.run_id not in rows:
        raise SystemExit(f"unknown run_id: {args.run_id}")

    row = rows[args.run_id]
    task = tasks[row["task_id"]]
    template = Path("prompts/cgp.md" if row["condition"] == "cgp" else "prompts/baseline.md")
    prompt = render_prompt(task, row["condition"], template)
    cell = RunCell(row["run_id"], row["task_id"], row["agent"], row["condition"], int(row["replication"]))
    run_dir = prepare_run_dir(args.out_root, cell, task, prompt)
    print(f"prepared {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
