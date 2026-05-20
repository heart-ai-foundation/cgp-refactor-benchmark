"""Best-effort CodeScaleBench adapter.

This normalizes task metadata only. It must not load target solution data into prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schema import BenchmarkTask


REFORM_KEYWORDS = ("refactor", "migration", "dependency", "multi-file", "multi_file")


def first(payload: dict[str, Any], names: list[str], default: Any = None) -> Any:
    for name in names:
        if payload.get(name):
            return payload[name]
    return default


def normalize_codescalebench_task(payload: dict[str, Any], source_path: str = "") -> BenchmarkTask:
    verification = first(payload, ["verification_commands", "test_commands", "tests", "commands"], []) or []
    expected_files = first(payload, ["expected_files", "files", "target_files", "affected_files"], []) or []
    if isinstance(verification, str):
        verification = [verification]
    if isinstance(expected_files, str):
        expected_files = [expected_files]
    return BenchmarkTask.from_mapping(
        {
            "task_id": str(first(payload, ["task_id", "id", "name", "instance_id"], Path(source_path).stem)),
            "task_source": "codescalebench",
            "task_type": str(first(payload, ["task_type", "type", "category", "kind"], "unknown")).lower(),
            "title": str(first(payload, ["title", "name"], Path(source_path).stem)),
            "instruction": str(first(payload, ["instruction", "prompt", "task", "description", "issue"], "")),
            "repo": str(first(payload, ["repo", "repository", "repo_url", "repository_url"], "")),
            "base_ref": first(payload, ["base_ref", "commit", "base_commit", "start_commit"]),
            "verification_commands": verification,
            "expected_files": expected_files,
            "allowed_paths": first(payload, ["allowed_paths", "scope"], expected_files) or [],
            "obligations": first(payload, ["obligations", "requirements"], []) or [],
            "metadata": {"source_path": source_path},
        }
    )


def load_candidate_tasks(root: Path, limit: int | None = None) -> list[BenchmarkTask]:
    candidates: list[BenchmarkTask] = []
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                task = normalize_codescalebench_task(record, str(path))
            except ValueError:
                continue
            haystack = " ".join([task.task_type, task.title, task.instruction]).lower()
            if any(keyword in haystack for keyword in REFORM_KEYWORDS):
                candidates.append(task)
                if limit and len(candidates) >= limit:
                    return candidates
    return candidates

