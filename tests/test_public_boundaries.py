from __future__ import annotations

import json
import tempfile
from pathlib import Path

from codexsaver.agent_registry import AgentRegistry
from codexsaver.schema import FileContext, WorkPacketInput, WorkerTask, to_dict
from codexsaver.work_packet import packet_payload


def _write_card(path: Path, card_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": card_id,
                "name": card_id,
                "type": "custom",
                "status": "online",
                "capabilities": ["docs"],
                "languages": ["python"],
                "endpoint": "local:test",
            }
        ),
        encoding="utf-8",
    )


def test_worker_task_serialization_redacts_absolute_workspace():
    task = WorkerTask(
        instruction="Explain the file",
        task_type="explain",
        risk="low",
        constraints=[],
        workspace="/home/private-user/projects/secret-repo",
        files=[FileContext(path="src/example.py", content="print('ok')")],
    )
    payload = to_dict(task)
    assert payload["workspace"] == "."
    assert "/home/private-user" not in json.dumps(payload)


def test_work_packet_payload_refuses_unsafe_policy_paths():
    packet = WorkPacketInput(
        goal="Update documentation",
        files=["README.md", "/etc/passwd", "../outside.txt"],
        constraints=[],
        acceptance_criteria=[],
        allowed_files=["README.md", "/tmp/host-file", "../escape.py"],
        forbidden_paths=[".env", "../../private"],
        allowed_commands=[],
        workspace="/home/private-user/project",
    )
    payload = packet_payload(packet, [])
    assert payload["workspace"] == "."
    assert payload["files"] == ["README.md", "<refused-path>", "<refused-path>"]
    assert payload["allowed_files"] == ["README.md", "<refused-path>", "<refused-path>"]
    assert payload["forbidden_paths"] == [".env", "<refused-path>"]
    assert "/home/private-user" not in json.dumps(payload)


def test_project_agent_card_directory_cannot_escape_workspace():
    with tempfile.TemporaryDirectory() as parent:
        root = Path(parent, "workspace")
        outside = Path(parent, "outside-agents")
        root.joinpath(".pi").mkdir(parents=True)
        _write_card(outside / "outside.agent-card.json", "outside-card")
        root.joinpath(".pi", "codexsaver.json").write_text(
            json.dumps({"agent_card_dirs": ["../outside-agents"]}),
            encoding="utf-8",
        )

        cards = AgentRegistry().discover(str(root))
        assert "outside-card" not in {card.id for card in cards}


def test_workspace_agent_card_source_is_relative():
    with tempfile.TemporaryDirectory() as workspace:
        root = Path(workspace)
        card_path = root / ".pi-agents" / "local.agent-card.json"
        _write_card(card_path, "local-card")

        card = next(card for card in AgentRegistry().discover(workspace) if card.id == "local-card")
        assert card.source == ".pi-agents/local.agent-card.json"
        assert workspace not in card.source


def test_explicit_agent_registry_source_does_not_expose_host_path():
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as external:
        _write_card(Path(external, "trusted.agent-card.json"), "trusted-card")

        card = next(
            card
            for card in AgentRegistry(extra_dirs=[external]).discover(workspace)
            if card.id == "trusted-card"
        )
        assert card.source == "explicit-agent-registry/trusted.agent-card.json"
        assert external not in card.source
