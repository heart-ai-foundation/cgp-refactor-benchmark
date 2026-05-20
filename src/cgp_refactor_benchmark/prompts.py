"""Prompt rendering for baseline and CGP benchmark conditions."""

from __future__ import annotations

from pathlib import Path

from .schema import BenchmarkTask


def bullet(items: tuple[str, ...] | list[str], fallback: str = "Not provided.") -> str:
    if not items:
        return fallback
    return "\n".join(f"- `{item}`" for item in items)


def render_prompt(task: BenchmarkTask, condition: str, template_path: Path) -> str:
    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{task_id}": task.task_id,
        "{task_source}": task.task_source,
        "{task_type}": task.task_type,
        "{title}": task.title,
        "{repo}": task.repo,
        "{base_ref}": task.base_ref or "Not provided.",
        "{instruction}": task.instruction,
        "{setup_commands}": bullet(task.setup_commands),
        "{verification_commands}": bullet(task.verification_commands),
        "{expected_files}": bullet(task.expected_files),
        "{allowed_paths}": bullet(task.allowed_paths or task.expected_files),
        "{obligations}": bullet(task.obligations, "No machine-readable obligations provided."),
        "{condition}": condition,
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text

