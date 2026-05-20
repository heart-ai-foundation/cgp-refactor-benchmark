"""Shared schemas for benchmark tasks and run cells."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    task_source: str
    task_type: str
    title: str
    instruction: str
    repo: str
    base_ref: str | None = None
    setup_commands: tuple[str, ...] = ()
    verification_commands: tuple[str, ...] = ()
    expected_files: tuple[str, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    obligations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "BenchmarkTask":
        required = ["task_id", "task_source", "task_type", "title", "instruction", "repo"]
        missing = [name for name in required if not payload.get(name)]
        if missing:
            raise ValueError(f"task is missing required fields: {', '.join(missing)}")
        return cls(
            task_id=str(payload["task_id"]),
            task_source=str(payload["task_source"]),
            task_type=str(payload["task_type"]),
            title=str(payload["title"]),
            instruction=str(payload["instruction"]),
            repo=str(payload["repo"]),
            base_ref=str(payload["base_ref"]) if payload.get("base_ref") else None,
            setup_commands=tuple(str(item) for item in payload.get("setup_commands", [])),
            verification_commands=tuple(str(item) for item in payload.get("verification_commands", [])),
            expected_files=tuple(str(item) for item in payload.get("expected_files", [])),
            allowed_paths=tuple(str(item) for item in payload.get("allowed_paths", [])),
            obligations=tuple(str(item) for item in payload.get("obligations", [])),
            metadata=dict(payload.get("metadata", {})),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_source": self.task_source,
            "task_type": self.task_type,
            "title": self.title,
            "instruction": self.instruction,
            "repo": self.repo,
            "base_ref": self.base_ref,
            "setup_commands": list(self.setup_commands),
            "verification_commands": list(self.verification_commands),
            "expected_files": list(self.expected_files),
            "allowed_paths": list(self.allowed_paths),
            "obligations": list(self.obligations),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RunCell:
    run_id: str
    task_id: str
    agent: str
    condition: str
    replication: int = 1

    @classmethod
    def build(cls, task_id: str, agent: str, condition: str, replication: int = 1) -> "RunCell":
        return cls(f"{task_id}-{agent}-{condition}-r{replication}", task_id, agent, condition, replication)

