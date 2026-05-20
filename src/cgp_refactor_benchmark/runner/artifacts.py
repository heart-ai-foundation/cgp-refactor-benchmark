"""Run artifact directory helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ..schema import BenchmarkTask, RunCell


def prepare_run_dir(root: Path, cell: RunCell, task: BenchmarkTask, prompt: str) -> Path:
    run_dir = root / cell.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "task.json").write_text(json.dumps(task.to_mapping(), indent=2) + "\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": cell.run_id,
                "task_id": cell.task_id,
                "task_source": task.task_source,
                "task_type": task.task_type,
                "agent": cell.agent,
                "condition": cell.condition,
                "replication": cell.replication,
                "status": "prepared",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    (run_dir / "evidence").mkdir(exist_ok=True)
    return run_dir

