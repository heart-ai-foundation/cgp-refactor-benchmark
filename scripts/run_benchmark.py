#!/usr/bin/env python3
"""One-command orchestration for the CGP refactor benchmark."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cgp_refactor_benchmark.prompts import render_prompt
from cgp_refactor_benchmark.tasks import (
    generate_run_plan,
    load_tasks,
    select_task_window,
    write_run_plan,
)


DEFAULT_AGENTS = ["codex", "claude-code", "gemini-cli"]
DEFAULT_CONDITIONS = ["baseline", "cgp"]
DEFAULT_AGENT_MODELS = {
    "codex": "openai/gpt-5.5",
    "claude-code": "anthropic/claude-sonnet-4-5-20250929",
    "gemini-cli": "google/gemini-2.5-pro",
    "gemini-openrouter": "openrouter/google/gemini-2.5-pro",
}
DEFAULT_AGENT_IMPORT_PATHS = {
    "claude-code": "harbor_oauth_agents:ClaudeCodeOAuth",
    "gemini-cli": "harbor_oauth_agents:GeminiCliOAuth",
}
HARBOR_AGENT_BY_LABEL = {
    "gemini-openrouter": "opencode",
}

AUTH_ENV_BY_AGENT = {
    "codex": ["CODEX_AUTH_JSON_PATH", "CODEX_FORCE_AUTH_JSON", "OPENAI_API_KEY"],
    "claude-code": [
        "CLAUDE_CODE_CREDENTIALS_PATH",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "AWS_BEARER_TOKEN_BEDROCK",
    ],
    "gemini-cli": [
        "GEMINI_OAUTH_CREDS_PATH",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_GENAI_USE_GCA",
    ],
    "gemini-openrouter": ["OPENROUTER_API_KEY"],
}


def run_command(
    command: list[str],
    dry_run: bool,
    monitor_job_dir: Path | None = None,
    monitor_label: str | None = None,
) -> None:
    printable = " ".join(command)
    if dry_run:
        print(f"DRY RUN: {printable}")
        return
    print(f"RUN: {printable}", flush=True)
    if monitor_job_dir is None:
        subprocess.run(command, check=True)
        return

    process = subprocess.Popen(command)
    seen_trials = set(existing_trial_results(monitor_job_dir))
    while process.poll() is None:
        announce_new_trial_results(monitor_job_dir, seen_trials, monitor_label)
        time.sleep(5)
    announce_new_trial_results(monitor_job_dir, seen_trials, monitor_label)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)


def existing_trial_results(job_dir: Path) -> list[Path]:
    if not job_dir.exists():
        return []
    return sorted(
        path.parent
        for path in job_dir.glob("*/result.json")
        if path.parent.name != job_dir.name
    )


def _trial_exception_type(trial_dir: Path) -> str:
    exception_path = trial_dir / "exception.txt"
    if not exception_path.exists():
        return "unknown"
    lines = exception_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("Traceback", "File ", "^")):
            continue
        if ": " in stripped:
            error_type = stripped.split(":", 1)[0].rsplit(".", 1)[-1]
            if "Error" in error_type or "Exception" in error_type:
                return error_type
        return stripped[:80]
    return "unknown"


def _trial_reward(trial_dir: Path) -> str:
    result_path = trial_dir / "result.json"
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    verifier = data.get("verifier_result") or {}
    rewards = verifier.get("rewards") or {}
    if "reward" in rewards:
        return str(rewards["reward"])
    if rewards:
        return json.dumps(rewards, sort_keys=True)
    return "unknown"


def announce_new_trial_results(
    job_dir: Path,
    seen_trials: set[Path],
    label: str | None,
) -> None:
    for trial_dir in existing_trial_results(job_dir):
        if trial_dir in seen_trials:
            continue
        seen_trials.add(trial_dir)
        prefix = f"[{label}] " if label else ""
        if (trial_dir / "exception.txt").exists():
            print(
                f"{prefix}TRIAL ERROR {trial_dir.name}: {_trial_exception_type(trial_dir)}",
                flush=True,
            )
        else:
            print(
                f"{prefix}TRIAL COMPLETE {trial_dir.name}: reward={_trial_reward(trial_dir)}",
                flush=True,
            )


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


def _has_nonempty_env(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def configure_codex_auth_from_host() -> None:
    if any(_has_nonempty_env(name) for name in AUTH_ENV_BY_AGENT["codex"]):
        return
    auth_path = Path.home() / ".codex" / "auth.json"
    if auth_path.exists():
        os.environ["CODEX_AUTH_JSON_PATH"] = str(auth_path)
        print(f"Using Codex auth from {auth_path}", flush=True)


def configure_oauth_file_env(agent: str, env_name: str, default_path: Path) -> None:
    if _has_nonempty_env(env_name):
        return
    if default_path.exists():
        os.environ[env_name] = str(default_path)
        print(f"Using {agent} OAuth credentials from {default_path}", flush=True)


def validate_agent_auth(args: argparse.Namespace) -> None:
    if args.dry_run or args.prepare_only or args.skip_auth_check:
        return
    if "codex" in args.agents:
        configure_codex_auth_from_host()
    if "claude-code" in args.agents:
        configure_oauth_file_env(
            "Claude Code",
            "CLAUDE_CODE_CREDENTIALS_PATH",
            Path.home() / ".claude" / ".credentials.json",
        )
    if "gemini-cli" in args.agents:
        configure_oauth_file_env(
            "Gemini CLI",
            "GEMINI_OAUTH_CREDS_PATH",
            Path.home() / ".gemini" / "oauth_creds.json",
        )
    missing = []
    for agent in args.agents:
        env_names = AUTH_ENV_BY_AGENT.get(agent)
        if not env_names:
            continue
        if not any(_has_nonempty_env(name) for name in env_names):
            missing.append(f"{agent} ({', '.join(env_names)})")
    if missing:
        raise SystemExit(
            "missing credentials for Harbor agent(s): "
            + "; ".join(missing)
            + ". Export the needed auth before running, or use --skip-auth-check."
        )


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
    tasks = selected_tasks(args)
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
    tasks = selected_tasks(args)
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
                    "task_start": args.task_start,
                    "task_count": args.task_count,
                    "batch_name": args.batch_name,
                    "confirm_each_task": args.confirm_each_task,
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
    if args.confirm_each_task:
        harbor_runs_with_confirmation(args, condition_roots)
        return

    for replication in range(1, args.replications + 1):
        for condition in args.conditions:
            for agent in args.agents:
                command, job_dir = build_harbor_command(
                    args,
                    condition_roots[condition],
                    condition,
                    agent,
                    replication,
                )
                run_command(
                    command,
                    args.dry_run,
                    monitor_job_dir=job_dir,
                    monitor_label=f"{condition}/{agent}/r{replication}",
                )


def harbor_runs_with_confirmation(
    args: argparse.Namespace,
    condition_roots: dict[str, str],
) -> None:
    tasks = selected_tasks(args)
    for task in tasks:
        for replication in range(1, args.replications + 1):
            for condition in args.conditions:
                task_root = prepare_single_task_root(
                    args,
                    Path(condition_roots[condition]),
                    condition,
                    task.task_id,
                )
                for agent in args.agents:
                    command, job_dir = build_harbor_command(
                        args,
                        str(task_root),
                        condition,
                        agent,
                        replication,
                        task_id=task.task_id,
                    )
                    try:
                        run_command(
                            command,
                            args.dry_run,
                            monitor_job_dir=job_dir,
                            monitor_label=(
                                f"{condition}/{agent}/r{replication}/{task.task_id}"
                            ),
                        )
                    except subprocess.CalledProcessError as exc:
                        print(
                            f"[{condition}/{agent}/r{replication}/{task.task_id}] "
                            f"HARBOR COMMAND ERROR exit={exc.returncode}",
                            flush=True,
                        )
                        if not confirm_continue(args):
                            return
                        continue
                    if not confirm_continue(args):
                        return


def prepare_single_task_root(
    args: argparse.Namespace,
    condition_root: Path,
    condition: str,
    task_id: str,
) -> Path:
    single_root = args.condition_root / "per-task" / condition / task_id
    if args.dry_run:
        print(f"DRY RUN: render one-task Harbor root {single_root}")
        return single_root

    source_dir = condition_root / task_id
    if not source_dir.exists():
        raise SystemExit(f"missing rendered task dir: {source_dir}")
    if single_root.exists():
        shutil.rmtree(single_root)
    single_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, single_root / task_id)
    return single_root


def build_harbor_command(
    args: argparse.Namespace,
    path: str,
    condition: str,
    agent: str,
    replication: int,
    task_id: str | None = None,
) -> tuple[list[str], Path]:
    jobs_root = args.jobs_dir / args.preset
    if args.batch_name:
        jobs_root = jobs_root / args.batch_name
    if task_id:
        jobs_root = jobs_root / "per-task" / task_id
    jobs_dir = jobs_root / condition / agent / f"r{replication}"

    job_name_parts = [args.preset, condition, agent, f"r{replication}"]
    if args.batch_name:
        job_name_parts.append(args.batch_name)
    if task_id:
        job_name_parts.append(task_id)
    job_name = "-".join(job_name_parts)
    job_dir = jobs_dir / job_name

    command = [
        "harbor",
        "run",
        "--path",
        path,
        "--model",
        args.agent_models[agent],
        "--n-concurrent",
        str(args.n_concurrent),
        "--jobs-dir",
        str(jobs_dir),
        "--job-name",
        job_name,
        "--yes",
    ]
    harbor_agent = HARBOR_AGENT_BY_LABEL.get(agent, agent)
    import_path = DEFAULT_AGENT_IMPORT_PATHS.get(agent)
    if import_path:
        command.extend(["--agent-import-path", import_path])
    else:
        command.extend(["--agent", harbor_agent])
    if args.n_tasks is not None:
        command.extend(["--n-tasks", str(args.n_tasks)])
    return command, job_dir


def confirm_continue(args: argparse.Namespace) -> bool:
    if args.dry_run:
        print("DRY RUN: prompt Continue to next task? [y/N]")
        return True
    answer = input("Continue to next task? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def selected_tasks(args: argparse.Namespace):
    return select_task_window(
        load_tasks(args.manifest),
        task_start=args.task_start,
        task_count=args.task_count,
    )


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
    parser.add_argument(
        "--task-start",
        type=int,
        default=1,
        help="1-based manifest position for the first task to render and run.",
    )
    parser.add_argument(
        "--task-count",
        type=int,
        default=None,
        help="Number of manifest tasks to render and run from --task-start.",
    )
    parser.add_argument(
        "--batch-name",
        default=None,
        help="Optional label for sliced task runs; defaults to tasks-START-END.",
    )
    parser.add_argument(
        "--confirm-each-task",
        action="store_true",
        help="Run one Harbor task at a time and ask before continuing.",
    )
    parser.add_argument("--jobs-dir", type=Path, default=Path("runs/harbor"))
    parser.add_argument("--prompt-dir", type=Path, default=Path("prompts"))
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--auth-check-only", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    parser.add_argument("--skip-auth-check", action="store_true")
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
    if args.confirm_each_task and args.n_concurrent != 1:
        raise SystemExit("--confirm-each-task requires --n-concurrent 1")
    if args.confirm_each_task and args.n_tasks is not None:
        raise SystemExit("--confirm-each-task cannot be combined with --n-tasks")

    defaults = default_paths(args.preset)
    args.limit = args.limit if args.limit is not None else (3 if args.preset == "smoke" else 60)
    for key, value in defaults.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    configure_batch_paths(args)
    return args


def configure_batch_paths(args: argparse.Namespace) -> None:
    if args.task_start < 1:
        raise SystemExit("--task-start must be >= 1")
    if args.task_count is not None and args.task_count < 1:
        raise SystemExit("--task-count must be >= 1")
    if args.task_start == 1 and args.task_count is None:
        return

    end = args.limit if args.task_count is None else args.task_start + args.task_count - 1
    if end > args.limit:
        end = args.limit
    if args.batch_name is None:
        args.batch_name = f"tasks-{args.task_start:03d}-{end:03d}"
    args.condition_root = args.condition_root / args.batch_name
    args.run_plan = args.run_plan.with_name(
        f"{args.run_plan.stem}.{args.batch_name}{args.run_plan.suffix}"
    )
    args.run_plan_metadata = args.run_plan.with_suffix(".metadata.json")


def main() -> int:
    args = parse_args()
    validate_agent_auth(args)
    if args.auth_check_only:
        print("auth_check=ok")
        return 0
    if not args.skip_package:
        package_tasks(args)
    condition_roots = write_condition_tasks(args)
    write_plan(args, condition_roots)
    harbor_runs(args, condition_roots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
