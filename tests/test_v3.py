from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cli import main
from codexsaver.aggregator import PatchAggregator
from codexsaver.engine import CodexSaverEngine
from codexsaver.provider import ProviderError
from codexsaver.schema import WorkGraph, WorkGraphNode
from codexsaver.specialists import SpecialistRegistry
from codexsaver.work_graph import WorkGraphPlanner


def test_specialist_registry_lists_defaults():
    registry = SpecialistRegistry()
    names = [item.name for item in registry.list()]
    assert "doc_writer" in names
    assert "explainer" in names
    assert "impl_worker" in names
    assert "test_writer" in names


def test_work_graph_planner_builds_multi_worker_graph():
    planner = WorkGraphPlanner()
    graph = planner.plan(type("Req", (), {
        "goal": "Implement login, add tests, add docs, and explain risk",
        "files": ["src/user_auth.py"],
        "constraints": [],
        "workspace": ".",
        "max_parallel_workers": 4,
        "dry_run": True,
    })())
    assert graph.route == "multi_worker"
    assert len(graph.nodes) >= 3
    assert any(node.specialist == "test_writer" for node in graph.nodes)
    assert any(node.specialist == "doc_writer" for node in graph.nodes)
    test_nodes = [node for node in graph.nodes if node.specialist == "test_writer"]
    assert test_nodes[0].allowed_commands == ["python -m pytest tests/test_user_auth.py -q"]


def test_patch_aggregator_detects_conflicts():
    result = PatchAggregator().aggregate([
        {"changed_files": ["README.md"], "patch": "diff1"},
        {"changed_files": ["README.md"], "patch": "diff2"},
    ])
    assert result.ok is False
    assert result.conflicts == ["README.md"]


def test_engine_orchestrate_task_dry_run():
    result = CodexSaverEngine().orchestrate_task({
        "goal": "Implement login, add tests, and add docs",
        "files": ["src/user_auth.py"],
        "dry_run": True,
    })
    assert result["status"] == "dry_run"
    assert result["route"] == "multi_worker"
    assert result["graph"]["nodes"]


def test_engine_orchestrate_task_executes_readonly_specialists_in_parallel():
    with patch("codexsaver.orchestrator.ProviderClient") as MockClient:
        client = MockClient.return_value
        client.complete_json.side_effect = [
            {
                "status": "success",
                "summary": "Code path explained.",
                "findings": ["Main branch calls parse_config first."],
                "risk_notes": [],
            },
            {
                "status": "success",
                "summary": "Performance review completed.",
                "findings": ["Loop may become O(n^2) on large inputs."],
                "risk_notes": ["Consider caching repeated lookups."],
            },
        ]
        result = CodexSaverEngine().orchestrate_task({
            "goal": "Explain config loader logic and review performance",
            "files": ["codexsaver/config.py"],
        })

    assert result["status"] == "success"
    assert result["route"] == "deepseek"
    assert result["aggregate_patch"] == ""
    assert len(result["results"]) == 2
    assert result["results"][0]["status"] == "success"
    assert result["results"][1]["status"] == "success"
    assert result["metrics"]["worker_calls"] == 2


def test_engine_orchestrate_task_readonly_failure_returns_codex():
    with patch("codexsaver.orchestrator.ProviderClient") as MockClient:
        client = MockClient.return_value
        client.complete_json.side_effect = ProviderError("timeout")
        result = CodexSaverEngine().orchestrate_task({
            "goal": "Explain config loader logic",
            "files": ["codexsaver/config.py"],
        })

    assert result["status"] == "needs_codex"
    assert result["route"] == "codex"
    assert result["results"][0]["status"] == "failed"


def test_engine_orchestrate_task_executes_patch_nodes_and_aggregates():
    with patch("codexsaver.orchestrator.ProviderClient"), \
            patch("codexsaver.orchestrator.WorkPacketRuntime") as MockRuntime, \
            patch("codexsaver.orchestrator.V3Orchestrator._apply_results_to_workspace"), \
            patch("codexsaver.orchestrator.V3Orchestrator._build_final_aggregate_patch", return_value={
                "patch": "aggregate",
                "changed_files": ["src/user_auth.py", "tests/test_user_auth.py"],
                "notes": [],
            }):
        runtime = MockRuntime.return_value
        runtime.run.side_effect = [
            {
                "route": "deepseek",
                "status": "success",
                "summary": "implemented login",
                "changed_files": ["src/user_auth.py"],
                "patch": (
                    "--- a/src/user_auth.py\n"
                    "+++ b/src/user_auth.py\n"
                    "@@ -1 +1,2 @@\n"
                    "-pass\n"
                    "+pass\n"
                    "+return True\n"
                ),
                "checks": [],
                "risk_notes": [],
            },
            {
                "route": "deepseek",
                "status": "success",
                "summary": "added tests",
                "changed_files": ["tests/test_user_auth.py"],
                "patch": (
                    "--- a/tests/test_user_auth.py\n"
                    "+++ b/tests/test_user_auth.py\n"
                    "@@ -0,0 +1,1 @@\n"
                    "+def test_login(): pass\n"
                ),
                "checks": [{"command": "pytest tests/test_user_auth.py -q", "exit_code": 0}],
                "risk_notes": [],
            },
        ]
        result = CodexSaverEngine().orchestrate_task({
            "goal": "Implement login and add tests",
            "files": ["src/user_auth.py"],
            "workspace": ".",
        })

    assert result["status"] == "success"
    assert result["route"] == "deepseek"
    assert "src/user_auth.py" in result["changed_files"]
    assert "tests/test_user_auth.py" in result["changed_files"]
    assert result["metrics"]["patch_nodes"] == 2


def test_engine_orchestrate_task_patch_conflict_returns_codex():
    with patch("codexsaver.orchestrator.ProviderClient"), \
            patch("codexsaver.orchestrator.WorkPacketRuntime") as MockRuntime, \
            patch("codexsaver.orchestrator.V3Orchestrator._apply_results_to_workspace"), \
            patch("codexsaver.orchestrator.WorkGraphPlanner.plan", return_value=WorkGraph(
                graph_id="graph-conflict",
                route="multi_worker",
                summary="conflict graph",
                nodes=[
                    WorkGraphNode(
                        id="docs-1",
                        type="bounded_patch",
                        goal="update readme first",
                        depends_on=[],
                        specialist="doc_writer",
                        allowed_files=["README.md"],
                        forbidden_paths=[],
                        allowed_commands=[],
                        acceptance_criteria=[],
                        mode="bounded_patch",
                    ),
                    WorkGraphNode(
                        id="docs-2",
                        type="bounded_patch",
                        goal="update readme second",
                        depends_on=[],
                        specialist="doc_writer",
                        allowed_files=["README.md"],
                        forbidden_paths=[],
                        allowed_commands=[],
                        acceptance_criteria=[],
                        mode="bounded_patch",
                    ),
                ],
            )):
        runtime = MockRuntime.return_value
        runtime.run.side_effect = [
            {
                "route": "deepseek",
                "status": "success",
                "summary": "doc patch",
                "changed_files": ["README.md"],
                "patch": "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-a\n+b\n",
                "checks": [],
                "risk_notes": [],
            },
            {
                "route": "deepseek",
                "status": "success",
                "summary": "another doc patch",
                "changed_files": ["README.md"],
                "patch": "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-a\n+c\n",
                "checks": [],
                "risk_notes": [],
            },
        ]
        result = CodexSaverEngine().orchestrate_task({
            "goal": "Add docs and update README docs",
            "files": ["README.md"],
            "workspace": ".",
        })

    assert result["status"] == "needs_codex"
    assert result["route"] == "codex"


def test_engine_run_specialist_preview():
    result = CodexSaverEngine().run_specialist({
        "specialist": "test_writer",
        "goal": "Add tests for parse_config",
        "allowed_files": ["tests/test_config.py"],
        "dry_run": True,
    })
    assert result["status"] == "dry_run"
    assert result["specialist"]["name"] == "test_writer"
    assert result["node_preview"]["specialist"] == "test_writer"


def test_engine_run_specialist_executes_readonly(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("def f():\n    return 1\n", encoding="utf-8")
    with patch("codexsaver.orchestrator.ProviderClient") as MockClient:
        client = MockClient.return_value
        client.complete_json.return_value = {
            "status": "success",
            "summary": "Function explained.",
            "findings": ["Returns a constant integer."],
            "risk_notes": [],
        }
        result = CodexSaverEngine().run_specialist({
            "specialist": "explainer",
            "goal": "Explain this function",
            "files": [str(sample)],
            "workspace": str(tmp_path),
        })

    assert result["route"] == "deepseek"
    assert result["status"] == "success"
    assert result["summary"] == "Function explained."


def test_cli_orchestrate_dry_run(capsys):
    assert main([
        "orchestrate",
        "Implement login, add tests, and add docs",
        "--files",
        "src/user_auth.py",
        "--dry-run",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "dry_run"
    assert output["graph"]["route"] == "multi_worker"
