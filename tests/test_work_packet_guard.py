from __future__ import annotations

import sys

from codexsaver.schema import WorkPacketInput
from codexsaver.work_packet import PatchSandbox


def _packet(tmp_path, command):
    return WorkPacketInput(
        goal="verify",
        files=[],
        constraints=[],
        acceptance_criteria=[],
        allowed_files=["example.py"],
        forbidden_paths=[],
        allowed_commands=[command],
        workspace=str(tmp_path),
    )


def test_package_import_installs_bounded_work_packet_guard(tmp_path):
    assert PatchSandbox._codexsaver_guard == "codexsaver-bounded-work-packet-v1"
    packet = _packet(tmp_path, f'"{sys.executable}" -c "print(123)"')
    sandbox = PatchSandbox(tmp_path, packet)

    result = sandbox.preflight_checks()

    assert result["type"] == "already_satisfied"
    assert result["guard"] == "codexsaver-bounded-work-packet-v1"
    assert result["results"][0]["argv_sha256"]
    assert result["results"][0]["stdout_sha256"]
    assert result["results"][0]["timed_out"] is False


def test_work_packet_guard_refuses_shell_chaining(tmp_path):
    packet = _packet(tmp_path, "pytest -q; cat ~/.ssh/id_rsa")
    sandbox = PatchSandbox(tmp_path, packet)

    result = sandbox.preflight_checks()

    assert result["type"] == "preflight_refused"
    assert result["results"] == []
    assert "refused" in result["reason"].lower()


def test_work_packet_guard_redacts_receipts(tmp_path):
    secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
    command = f'"{sys.executable}" -c "print({str(tmp_path)!r}, {secret!r})"'
    packet = _packet(tmp_path, command)
    sandbox = PatchSandbox(tmp_path, packet)

    result = sandbox.preflight_checks()["results"][0]

    assert str(tmp_path) not in result["stdout"]
    assert secret not in result["stdout"]
    assert "<workspace>" in result["stdout"]
    assert "<redacted>" in result["stdout"]


def test_work_packet_guard_rejects_excessive_recipe_count(tmp_path):
    packet = _packet(tmp_path, f'"{sys.executable}" -c "print(1)"')
    packet.allowed_commands = packet.allowed_commands * 9
    sandbox = PatchSandbox(tmp_path, packet)

    result = sandbox.preflight_checks()

    assert result["type"] == "preflight_refused"
    assert "count" in result["reason"].lower()
