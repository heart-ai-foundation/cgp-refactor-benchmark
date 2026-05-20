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
from pathlib import Path


REF_TASK_ROOT = Path("benchmarks/csb/refactor")


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


def package_task(source_task_dir: Path, out_root: Path, org: str) -> dict:
    old_config = read_toml(source_task_dir / "task.toml")
    task_section = old_config.get("task", {})
    metadata = old_config.get("metadata", {})
    verification = old_config.get("verification", {})
    environment = old_config.get("environment", {})

    task_id = str(task_section.get("id") or metadata.get("name") or source_task_dir.name).lower()
    target_dir = out_root / task_id
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(
        source_task_dir,
        target_dir,
        ignore=shutil.ignore_patterns("*.bak", "__pycache__", ".pytest_cache"),
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
            "category": str(task_section.get("category", "")),
            "language": str(task_section.get("language", "")),
            "difficulty": str(task_section.get("difficulty", "")),
            "source_task_dir": str(source_task_dir),
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
        "task_type": "refactor",
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


def selected_source_dirs(source_root: Path, limit: int) -> list[Path]:
    task_dirs = sorted(path for path in source_root.iterdir() if (path / "task.toml").exists())
    return task_dirs[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codescale-root", type=Path, default=Path("/home/dylan/CodeScaleBench"))
    parser.add_argument("--out-root", type=Path, default=Path("tasks/harbor/codescalebench-refactor"))
    parser.add_argument("--manifest", type=Path, default=Path("tasks/selected_tasks.codescale-smoke.jsonl"))
    parser.add_argument("--org", default="heart-cgp")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    source_root = args.codescale_root / REF_TASK_ROOT
    if not source_root.exists():
        raise SystemExit(f"missing CodeScaleBench refactor root: {source_root}")

    args.out_root.mkdir(parents=True, exist_ok=True)
    rows = [
        package_task(source_dir, args.out_root, args.org)
        for source_dir in selected_source_dirs(source_root, args.limit)
    ]
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
