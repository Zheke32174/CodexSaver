from __future__ import annotations

import sys

import pytest

from codexsaver.safe_checks import CheckRejected, run_provider_check


def test_literal_print_recipe_runs_without_shell(tmp_path):
    result = run_provider_check(f'"{sys.executable}" -c "print(123)"', str(tmp_path))
    assert result["exit_code"] == 0
    assert result["stdout"].strip() == "123"
    assert result["timed_out"] is False
    assert len(result["argv_sha256"]) == 64


@pytest.mark.parametrize(
    "command",
    [
        "sh -c 'cat ~/.ssh/id_rsa'",
        "python -c \"import os; print(os.environ)\"",
        "python ../outside.py",
        "pytest --override-ini addopts=-pno:cacheprovider",
        "echo ok && cat /etc/passwd",
    ],
)
def test_unsafe_provider_recipes_fail_closed(tmp_path, command):
    with pytest.raises(CheckRejected):
        run_provider_check(command, str(tmp_path))


def test_workspace_and_secret_output_are_redacted(tmp_path):
    secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
    command = f'"{sys.executable}" -c "print({str(tmp_path)!r}, {secret!r})"'
    result = run_provider_check(command, str(tmp_path))
    assert result["exit_code"] == 0
    assert str(tmp_path) not in result["stdout"]
    assert secret not in result["stdout"]
    assert "<workspace>" in result["stdout"]
    assert "<redacted>" in result["stdout"]
