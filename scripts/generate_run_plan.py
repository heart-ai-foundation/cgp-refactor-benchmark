#!/usr/bin/env python3
"""Generate a CGP Refactor Completion Benchmark run plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cgp_refactor_benchmark.tasks import generate_run_plan, load_tasks, write_run_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=Path("tasks/selected_tasks.example.jsonl"))
    parser.add_argument("--agents", nargs="+", default=["codex"])
    parser.add_argument("--replications", type=int, default=1)
    parser.add_argument("--out", type=Path, default=Path("runs/run_plan.csv"))
    parser.add_argument("--metadata-out", type=Path, default=Path("runs/run_plan_metadata.json"))
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    rows = generate_run_plan(tasks, args.agents, replications=args.replications)
    write_run_plan(args.out, rows)
    args.metadata_out.write_text(
        json.dumps(
            {
                "task_manifest": str(args.tasks),
                "agents": args.agents,
                "conditions": ["baseline", "cgp"],
                "replications": args.replications,
                "run_count": len(rows),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out} ({len(rows)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
