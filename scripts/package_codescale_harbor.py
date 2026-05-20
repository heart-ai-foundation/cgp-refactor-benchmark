#!/usr/bin/env python3
"""Package CodeScaleBench tasks for the installed Harbor task schema.

CodeScaleBench tasks already use the standard Harbor filesystem contract
(`instruction.md`, `environment/Dockerfile`, `tests/test.sh`) but their
`task.toml` files predate Harbor schema 1.2. This script copies selected tasks
and rewrites only the metadata file needed by the current Harbor CLI.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tomllib
from collections import defaultdict
from pathlib import Path


REF_TASK_ROOT = Path("benchmarks/csb/refactor")
BENCHMARK_ROOT = Path("benchmarks")

FULL_CATEGORY_ORDER = [
    # Primary preregistered task families.
    "migration-inventory",
    "cross_file_refactoring",
    "refactor",
    "enterprise_dep_refactor",
    # Additional PRD-covered multi-file codebase-change families needed to
    # reach the documented 50-60 task target.
    "cross_module_bug_fix",
    "bug_fix",
    "bug_investigation",
    "ccb_swebenchpro",
]


def size_to_mb(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip().upper()
    if text.endswith("G"):
        return int(float(text[:-1]) * 1024)
    if text.endswith("M"):
        return int(float(text[:-1]))
    return int(float(text))


def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [f"{key} = {toml_value(item)}" for key, item in value.items()]
        return "{ " + ", ".join(parts) + " }"
    return json.dumps("" if value is None else str(value))


def write_harbor_task_toml(path: Path, config: dict) -> None:
    lines: list[str] = []
    lines.append(f"schema_version = {toml_value(config['schema_version'])}")
    lines.append(f"artifacts = {toml_value(config['artifacts'])}")
    for section in ["task", "metadata", "verifier", "agent", "environment", "solution"]:
        lines.append("")
        lines.append(f"[{section}]")
        for key, value in config[section].items():
            if isinstance(value, dict):
                continue
            lines.append(f"{key} = {toml_value(value)}")
        for key, value in config[section].items():
            if isinstance(value, dict):
                lines.append("")
                lines.append(f"[{section}.{key}]")
                for subkey, subvalue in value.items():
                    lines.append(f"{subkey} = {toml_value(subvalue)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def task_category(config: dict) -> str:
    return str(config.get("task", {}).get("category", ""))


def task_id_from_config(config: dict, source_task_dir: Path) -> str:
    task_section = config.get("task", {})
    metadata = config.get("metadata", {})
    return str(task_section.get("id") or metadata.get("name") or source_task_dir.name).lower()


def task_type_for_category(category: str) -> str:
    if category == "migration-inventory":
        return "migration"
    if category in {"cross_file_refactoring", "refactor", "enterprise_dep_refactor"}:
        return "refactor"
    return "multi_file_change"


def package_task(source_task_dir: Path, out_root: Path, org: str, selection_rank: int) -> dict:
    old_config = read_toml(source_task_dir / "task.toml")
    task_section = old_config.get("task", {})
    metadata = old_config.get("metadata", {})
    verification = old_config.get("verification", {})
    environment = old_config.get("environment", {})

    task_id = task_id_from_config(old_config, source_task_dir)
    category = task_category(old_config)
    target_dir = out_root / task_id
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(
        source_task_dir,
        target_dir,
        ignore=shutil.ignore_patterns("*.bak", "__pycache__", ".pytest_cache", "solution"),
    )

    harbor_config = {
        "schema_version": "1.2",
        "artifacts": [],
        "task": {
            "name": f"{org}/{task_id}",
            "description": str(metadata.get("description") or task_id),
            "authors": [{"name": "CodeScaleBench"}],
            "keywords": ["codescalebench", "refactor", str(task_section.get("language", "")).lower()],
        },
        "metadata": {
            "codescalebench_task_id": str(task_section.get("id") or task_id),
            "origin_suite": str(metadata.get("origin_suite", "")),
            "repo": str(task_section.get("repo", "")),
            "category": category,
            "language": str(task_section.get("language", "")),
            "difficulty": str(task_section.get("difficulty", "")),
            "source_task_dir": str(source_task_dir),
            "selection_rank": selection_rank,
            "verification_command": str(verification.get("command", "bash /tests/test.sh")),
            "verification_reward_type": str(verification.get("reward_type", "")),
        },
        "verifier": {
            "timeout_sec": float(task_section.get("time_limit_sec") or 600),
            "env": {},
        },
        "agent": {
            "timeout_sec": float(task_section.get("time_limit_sec") or 600),
        },
        "environment": {
            "build_timeout_sec": float(environment.get("build_timeout_sec") or 600),
            "os": "linux",
            "cpus": int(environment.get("cpus") or 1),
            "memory_mb": size_to_mb(environment.get("memory") or environment.get("memory_mb"), 2048),
            "storage_mb": size_to_mb(environment.get("storage") or environment.get("storage_mb"), 10240),
            "gpus": 0,
            "allow_internet": True,
            "mcp_servers": [],
            "env": {},
        },
        "solution": {
            "env": {},
        },
    }
    write_harbor_task_toml(target_dir / "task.toml", harbor_config)

    instruction = (target_dir / "instruction.md").read_text(encoding="utf-8")
    return {
        "task_id": task_id,
        "task_source": "codescalebench",
        "task_type": task_type_for_category(category),
        "title": str(metadata.get("description") or task_id),
        "instruction": instruction,
        "repo": str(task_section.get("repo", "")),
        "base_ref": None,
        "setup_commands": [],
        "verification_commands": [str(verification.get("command", "bash /tests/test.sh"))],
        "expected_files": [],
        "allowed_paths": [],
        "obligations": [],
        "metadata": harbor_config["metadata"] | {
            "packaged_task_dir": str(target_dir),
            "harbor_task_name": f"{org}/{task_id}",
        },
    }


def selected_smoke_source_dirs(source_root: Path, limit: int) -> list[Path]:
    task_dirs = sorted(path for path in source_root.iterdir() if (path / "task.toml").exists())
    return task_dirs[:limit]


def selected_full_source_dirs(codescale_root: Path, limit: int) -> list[Path]:
    by_category: dict[str, list[Path]] = defaultdict(list)
    seen_ids: set[str] = set()
    for task_toml in sorted((codescale_root / BENCHMARK_ROOT).glob("*/*/task.toml")):
        source_dir = task_toml.parent
        config = read_toml(task_toml)
        category = task_category(config)
        if category not in FULL_CATEGORY_ORDER:
            continue
        task_id = task_id_from_config(config, source_dir)
        if task_id in seen_ids:
            continue
        seen_ids.add(task_id)
        by_category[category].append(source_dir)

    selected: list[Path] = []
    for category in FULL_CATEGORY_ORDER:
        selected.extend(sorted(by_category.get(category, [])))
        if len(selected) >= limit:
            return selected[:limit]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codescale-root", type=Path, default=Path("/home/dylan/CodeScaleBench"))
    parser.add_argument("--out-root", type=Path, default=Path("tasks/harbor/codescalebench-refactor"))
    parser.add_argument("--manifest", type=Path, default=Path("tasks/selected_tasks.codescale-smoke.jsonl"))
    parser.add_argument("--org", default="heart-cgp")
    parser.add_argument("--preset", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    source_root = args.codescale_root / REF_TASK_ROOT
    benchmark_root = args.codescale_root / BENCHMARK_ROOT
    if args.preset == "smoke" and not source_root.exists():
        raise SystemExit(f"missing CodeScaleBench refactor root: {source_root}")
    if args.preset == "full" and not benchmark_root.exists():
        raise SystemExit(f"missing CodeScaleBench benchmark root: {benchmark_root}")

    args.out_root.mkdir(parents=True, exist_ok=True)
    source_dirs = (
        selected_smoke_source_dirs(source_root, args.limit)
        if args.preset == "smoke"
        else selected_full_source_dirs(args.codescale_root, args.limit)
    )
    if len(source_dirs) < args.limit:
        raise SystemExit(f"only selected {len(source_dirs)} tasks, requested {args.limit}")
    rows = [package_task(source_dir, args.out_root, args.org, rank) for rank, source_dir in enumerate(source_dirs, 1)]
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"packaged {len(rows)} tasks into {args.out_root}")
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
