from __future__ import annotations

import json
from pathlib import Path

from cli import main
from codexsaver.agent_registry import AgentRegistry
from codexsaver.agent_router import AgentRouter
from codexsaver.engine import CodexSaverEngine
from codexsaver.pi_agent import PiAgentClient
from codexsaver.provider import ProviderError
from codexsaver.schema import WorkGraphNode
from codexsaver.specialists import SpecialistRegistry
from codexsaver.task_lifecycle import TaskLifecycle


def test_agent_registry_discovers_builtin_and_local_agent_card(tmp_path):
    agent_dir = tmp_path / ".pi-agents"
    agent_dir.mkdir()
    (agent_dir / "docs.agent-card.json").write_text(json.dumps({
        "id": "docs-worker",
        "name": "Docs Worker",
        "capabilities": ["docs"],
        "languages": ["markdown"],
        "endpoint": "local:docs-worker",
        "cost_weight": 0.05,
        "success_rate": 0.9,
    }), encoding="utf-8")

    cards = AgentRegistry().discover(str(tmp_path))
    ids = {card.id for card in cards}

    assert "pi-agent-default" in ids
    assert "docs-worker" in ids


def test_agent_router_scores_best_capability_match():
    cards = AgentRegistry().discover(".")
    router = AgentRouter()
    node = WorkGraphNode(
        id="tests-1",
        type="bounded_patch",
        goal="Add tests",
        depends_on=[],
        specialist="test_writer",
        allowed_files=["tests/test_config.py"],
        forbidden_paths=[],
        allowed_commands=[],
        acceptance_criteria=[],
        mode="bounded_patch",
    )

    selected = router.select(node, cards)

    assert selected["worker"]["id"] == "pi-agent-default"
    assert selected["required_capability"] == "testing"
    assert selected["score"] > 0


def test_v36_specialists_default_to_pi_agent():
    registry = SpecialistRegistry()

    assert all(profile.provider == "pi-agent" for profile in registry.list())
    assert all(profile.model == "pi-agent-default" for profile in registry.list())


def test_pi_agent_client_does_not_fallback_to_deepseek(monkeypatch):
    card = next(card for card in AgentRegistry().discover(".") if card.id == "pi-agent-default")
    monkeypatch.setenv("PATH", "")

    try:
        PiAgentClient(card).complete_json("system", {"goal": "explain"})
    except ProviderError as exc:
        assert "Pi Agent command" in str(exc)
    else:
        raise AssertionError("PiAgentClient should fail clearly when pi is unavailable.")


def test_task_lifecycle_records_a2a_compatible_status_flow():
    lifecycle = TaskLifecycle()
    record = lifecycle.submitted("node-1", "worker-1")
    lifecycle.running(record)
    lifecycle.completed(record)

    assert record.status == "completed"
    assert [event["status"] for event in record.events] == ["submitted", "running", "completed"]


def test_engine_orchestrate_dry_run_includes_agent_routing():
    result = CodexSaverEngine().orchestrate_task({
        "goal": "Explain config loader logic and review performance",
        "files": ["codexsaver/config.py"],
        "dry_run": True,
    })

    assert result["status"] == "dry_run"
    assert result["graph"]["agents"]["discovered"]
    assert result["graph"]["agents"]["routing"]
    first_route = next(iter(result["graph"]["agents"]["routing"].values()))
    assert first_route["worker"]["id"] == "pi-agent-default"


def test_cli_agents_init_and_list(tmp_path, capsys):
    assert main(["agents", "init", "--workspace", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)

    assert output["status"] == "ok"
    assert Path(output["initialized_card"]).exists()
    assert any(agent["id"] == "pi-agent-default" for agent in output["agents"])
