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
from cgp_refactor_benchmark.tasks import generate_run_plan, load_tasks, write_run_plan


DEFAULT_AGENTS = ["codex", "claude-code", "gemini-cli"]
DEFAULT_CONDITIONS = ["baseline", "cgp"]
DEFAULT_AGENT_MODELS = {
    "codex": "openai/gpt-5-codex",
    "claude-code": "anthropic/claude-sonnet-4-5-20250929",
    "gemini-cli": "google/gemini-2.5-pro",
}
DEFAULT_AGENT_IMPORT_PATHS = {
    "claude-code": "harbor_oauth_agents:ClaudeCodeOAuth",
    "gemini-cli": "harbor_oauth_agents:GeminiCliOAuth",
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
                job_name = f"{args.preset}-{condition}-{agent}-r{replication}"
                job_dir = jobs_dir / job_name
                command = [
                    "harbor",
                    "run",
                    "--path",
                    condition_roots[condition],
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
                import_path = DEFAULT_AGENT_IMPORT_PATHS.get(agent)
                if import_path:
                    command.extend(["--agent-import-path", import_path])
                else:
                    command.extend(["--agent", agent])
                if args.n_tasks is not None:
                    command.extend(["--n-tasks", str(args.n_tasks)])
                run_command(
                    command,
                    args.dry_run,
                    monitor_job_dir=job_dir,
                    monitor_label=f"{condition}/{agent}/r{replication}",
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

    defaults = default_paths(args.preset)
    args.limit = args.limit if args.limit is not None else (3 if args.preset == "smoke" else 60)
    for key, value in defaults.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    return args


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
