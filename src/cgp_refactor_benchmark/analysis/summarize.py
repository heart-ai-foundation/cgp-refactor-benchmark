"""Summarize scored run JSONL into CSV."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


FIELDS = [
    "agent",
    "condition",
    "n",
    "upstream_success_rate",
    "mean_evidence_completeness",
    "scope_drift_any_rate",
    "mean_scope_drift_count",
    "false_green_candidate_rate",
    "mean_boundary_discipline",
]


def load_scores(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def bool_rate(rows: list[dict[str, Any]], field: str) -> float:
    return mean(1 if row.get(field) else 0 for row in rows)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("agent", ""), row.get("condition", ""))].append(row)
    out: list[dict[str, Any]] = []
    for (agent, condition), items in sorted(groups.items()):
        out.append(
            {
                "agent": agent,
                "condition": condition,
                "n": len(items),
                "upstream_success_rate": bool_rate(items, "upstream_success"),
                "mean_evidence_completeness": mean(float(item.get("evidence_completeness") or 0) for item in items),
                "scope_drift_any_rate": bool_rate(items, "scope_drift_any"),
                "mean_scope_drift_count": mean(float(item.get("scope_drift_count") or 0) for item in items),
                "false_green_candidate_rate": bool_rate(items, "false_green_candidate"),
                "mean_boundary_discipline": mean(float(item.get("boundary_discipline") or 0) for item in items),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

