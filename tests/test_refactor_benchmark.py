from pathlib import Path

from cgp_refactor_benchmark.prompts import render_prompt
from cgp_refactor_benchmark.scorers.run_score import score_run
from cgp_refactor_benchmark.tasks import generate_run_plan, load_tasks, select_task_window


def test_example_task_manifest_loads():
    tasks = load_tasks(Path("tasks/selected_tasks.example.jsonl"))
    assert len(tasks) == 1
    assert tasks[0].task_id == "local-refactor-smoke"
    assert tasks[0].task_type == "refactor"


def test_run_plan_covers_baseline_and_cgp():
    tasks = load_tasks(Path("tasks/selected_tasks.example.jsonl"))
    rows = generate_run_plan(tasks, ["codex"])
    assert [row["condition"] for row in rows] == ["baseline", "cgp"]
    assert rows[0]["run_id"] == "local-refactor-smoke-codex-baseline-r1"
    assert rows[1]["run_id"] == "local-refactor-smoke-codex-cgp-r1"


def test_task_window_uses_one_based_manifest_positions():
    tasks = load_tasks(Path("tasks/selected_tasks.codescale-smoke.jsonl"))
    selected = select_task_window(tasks, task_start=2, task_count=2)
    assert [task.task_id for task in selected] == [
        "ccx-migration-026",
        "ccx-migration-107",
    ]


def test_cgp_prompt_includes_governance_sections():
    task = load_tasks(Path("tasks/selected_tasks.example.jsonl"))[0]
    prompt = render_prompt(task, "cgp", Path("prompts/cgp.md"))
    assert "## Bound Objective" in prompt
    assert "## Evidence Requirement" in prompt
    assert "## Stop Condition" in prompt
    assert "Do not use target solution data" in prompt


def test_score_run_flags_scope_and_false_green(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "metadata.json").write_text('{"run_id":"r1","agent":"codex","condition":"baseline"}\n')
    (run_dir / "task.json").write_text(
        '{"task_id":"t1","task_source":"local","task_type":"refactor","allowed_paths":["src/config.py"],"obligations":["signature preserved"]}\n'
    )
    (run_dir / "changed_files.json").write_text('["src/config.py","src/unrelated.py"]\n')
    (run_dir / "upstream_result.json").write_text('{"success": true}\n')
    (run_dir / "missing_obligations.json").write_text('["signature preserved"]\n')
    (run_dir / "diff.patch").write_text("diff --git a/src/config.py b/src/config.py\n")
    (run_dir / "verification.log").write_text("passed\n")
    (run_dir / "transcript.log").write_text("run log\n")
    (run_dir / "final_response.txt").write_text("Completed. Verification passed. Evidence: diff and tests.\n")

    score = score_run(run_dir)
    assert score["scope_drift_count"] == 1
    assert score["false_green_candidate"] is True
    assert score["evidence_completeness"] >= 4
