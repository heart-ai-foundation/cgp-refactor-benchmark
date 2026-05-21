#!/usr/bin/env python3
"""One-command orchestration for the CGP refactor benchmark."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cgp_refactor_benchmark.prompts import render_prompt
from cgp_refactor_benchmark.tasks import generate_run_plan, load_tasks, write_run_plan


DEFAULT_AGENTS = ["codex", "claude-code", "gemini-cli"]
DEFAULT_CONDITIONS = ["baseline", "cgp"]
DEFAULT_AGENT_MODELS = {
    "codex": "openai/gpt-5-codex",
    "claude-code": "anthropic/claude-sonnet-4-5-20250929",
    "gemini-cli": "google/gemini-2.5-pro",
}


def run_command(command: list[str], dry_run: bool) -> None:
    printable = " ".join(command)
    if dry_run:
        print(f"DRY RUN: {printable}")
        return
    print(f"RUN: {printable}", flush=True)
    subprocess.run(command, check=True)


def parse_agent_models(values: list[str]) -> dict[str, str]:
    models = dict(DEFAULT_AGENT_MODELS)
    for value in values:
        if "=" not in value:
            raise SystemExit(
                f"invalid --agent-model {value!r}; expected format agent=model"
            )
        agent, model = value.split("=", 1)
        agent = agent.strip()
        model = model.strip()
        if not agent or not model:
            raise SystemExit(
                f"invalid --agent-model {value!r}; expected format agent=model"
            )
        models[agent] = model
    return models


def ensure_docker(dry_run: bool) -> None:
    if dry_run:
        print("DRY RUN: docker info || systemctl --user start docker.service")
        return
    probe = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0:
        return
    print("Docker daemon is not running; starting user docker.service.", flush=True)
    subprocess.run(["systemctl", "--user", "start", "docker.service"], check=True)
    subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def package_tasks(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        "scripts/package_codescale_harbor.py",
        "--preset",
        args.preset,
        "--limit",
        str(args.limit),
        "--codescale-root",
        str(args.codescale_root),
        "--out-root",
        str(args.base_task_root),
        "--manifest",
        str(args.manifest),
    ]
    run_command(command, args.dry_run)


def write_condition_tasks(args: argparse.Namespace) -> dict[str, str]:
    tasks = load_tasks(args.manifest)
    condition_roots: dict[str, str] = {}
    for condition in args.conditions:
        template_path = args.prompt_dir / f"{condition}.md"
        if not template_path.exists():
            raise SystemExit(f"missing prompt template: {template_path}")

        condition_root = args.condition_root / condition
        condition_roots[condition] = str(condition_root)
        if args.dry_run:
            print(f"DRY RUN: render {len(tasks)} {condition} tasks into {condition_root}")
            continue

        if condition_root.exists():
            shutil.rmtree(condition_root)
        condition_root.mkdir(parents=True, exist_ok=True)

        for task in tasks:
            source_dir = args.base_task_root / task.task_id
            target_dir = condition_root / task.task_id
            if not source_dir.exists():
                raise SystemExit(f"missing packaged task dir: {source_dir}")
            shutil.copytree(source_dir, target_dir)
            rendered = render_prompt(task, condition, template_path)
            (target_dir / "instruction.md").write_text(rendered, encoding="utf-8")
    return condition_roots


def write_plan(args: argparse.Namespace, condition_roots: dict[str, str]) -> None:
    tasks = load_tasks(args.manifest)
    rows = generate_run_plan(
        tasks,
        args.agents,
        conditions=args.conditions,
        replications=args.replications,
    )
    if args.dry_run:
        print(f"DRY RUN: write {len(rows)} run-plan rows to {args.run_plan}")
    else:
        write_run_plan(args.run_plan, rows)
        args.run_plan_metadata.parent.mkdir(parents=True, exist_ok=True)
        args.run_plan_metadata.write_text(
            json.dumps(
                {
                    "task_manifest": str(args.manifest),
                    "base_task_root": str(args.base_task_root),
                    "condition_roots": condition_roots,
                    "agents": args.agents,
                    "conditions": args.conditions,
                    "replications": args.replications,
                    "run_count": len(rows),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"run_count={len(rows)}")


def harbor_runs(args: argparse.Namespace, condition_roots: dict[str, str]) -> None:
    if args.prepare_only:
        return
    ensure_docker(args.dry_run)

    for replication in range(1, args.replications + 1):
        for condition in args.conditions:
            for agent in args.agents:
                jobs_dir = args.jobs_dir / args.preset / condition / agent / f"r{replication}"
                command = [
                    "harbor",
                    "run",
                    "--path",
                    condition_roots[condition],
                    "--agent",
                    agent,
                    "--model",
                    args.agent_models[agent],
                    "--n-concurrent",
                    str(args.n_concurrent),
                    "--jobs-dir",
                    str(jobs_dir),
                    "--job-name",
                    f"{args.preset}-{condition}-{agent}-r{replication}",
                    "--yes",
                ]
                if args.n_tasks is not None:
                    command.extend(["--n-tasks", str(args.n_tasks)])
                run_command(command, args.dry_run)


def default_paths(preset: str) -> dict[str, Path]:
    if preset == "smoke":
        name = "codescalebench-refactor"
        manifest = Path("tasks/selected_tasks.codescale-smoke.jsonl")
        run_plan = Path("runs/run_plan.codescale-smoke.csv")
    else:
        name = "codescalebench-60"
        manifest = Path("tasks/selected_tasks.codescale-60.jsonl")
        run_plan = Path("runs/run_plan.codescale-60.csv")
    return {
        "base_task_root": Path("tasks/harbor") / name,
        "condition_root": Path("tasks/harbor") / f"{name}-conditions",
        "manifest": manifest,
        "run_plan": run_plan,
        "run_plan_metadata": run_plan.with_suffix(".metadata.json"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package, condition, plan, and run the CGP benchmark from one command."
    )
    parser.add_argument("--preset", choices=["smoke", "full"], default="full")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--codescale-root", type=Path, default=Path("/home/dylan/CodeScaleBench")
    )
    parser.add_argument("--agents", nargs="+", default=DEFAULT_AGENTS)
    parser.add_argument(
        "--agent-model",
        action="append",
        default=[],
        metavar="AGENT=MODEL",
        help=(
            "Override the Harbor model for an agent. Repeatable. "
            "Defaults: "
            + ", ".join(
                f"{agent}={model}" for agent, model in DEFAULT_AGENT_MODELS.items()
            )
        ),
    )
    parser.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITIONS)
    parser.add_argument("--replications", type=int, default=1)
    parser.add_argument("--n-concurrent", type=int, default=1)
    parser.add_argument("--n-tasks", type=int, default=None)
    parser.add_argument("--jobs-dir", type=Path, default=Path("runs/harbor"))
    parser.add_argument("--prompt-dir", type=Path, default=Path("prompts"))
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-task-root", type=Path)
    parser.add_argument("--condition-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--run-plan", type=Path)
    parser.add_argument("--run-plan-metadata", type=Path)
    args = parser.parse_args()
    args.agent_models = parse_agent_models(args.agent_model)

    missing_models = [agent for agent in args.agents if agent not in args.agent_models]
    if missing_models:
        raise SystemExit(
            "missing Harbor model for agent(s): "
            + ", ".join(missing_models)
            + ". Add overrides like --agent-model agent=model."
        )

    defaults = default_paths(args.preset)
    args.limit = args.limit if args.limit is not None else (3 if args.preset == "smoke" else 60)
    for key, value in defaults.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    return args


def main() -> int:
    args = parse_args()
    if not args.skip_package:
        package_tasks(args)
    condition_roots = write_condition_tasks(args)
    write_plan(args, condition_roots)
    harbor_runs(args, condition_roots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
