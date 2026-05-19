from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from .agent_registry import AgentCard
from .provider import ProviderError


class PiAgentClient:
    """Minimal Pi Agent adapter.

    The adapter is intentionally protocol-thin: CodexSaver owns routing and
    safety, while the Pi command owns actual worker execution.
    """

    def __init__(self, card: AgentCard, timeout_seconds: int = 120):
        self.card = card
        self.timeout_seconds = timeout_seconds

    def complete_json(self, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        command = self._command()
        request = {
            "protocol": "codexsaver.task.v1",
            "agent_card": {
                "id": self.card.id,
                "name": self.card.name,
                "type": self.card.type,
                "endpoint": self.card.endpoint,
                "worktree_path": self.card.worktree_path,
                "permissions_config": self.card.permissions_config,
                "filesystem_policy": self.card.filesystem_policy,
                "network_policy": self.card.network_policy,
            },
            "system_prompt": system_prompt,
            "task_spec": payload,
        }
        prompt = (
            f"{system_prompt}\n\n"
            "Return one JSON object only in your final text response. "
            "Do not use markdown fences.\n\n"
            f"TaskSpec:\n{json.dumps(request, ensure_ascii=False)}"
        )
        run_command = command + ([prompt] if command[-1] == "-p" else [])
        try:
            completed = subprocess.run(
                run_command,
                input=prompt if command[-1] != "-p" else None,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as e:
            raise ProviderError(
                "Pi Agent command not found. Install Pi Agent or provide an Agent Card "
                "with a valid command before running v3.6 live worker execution."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise ProviderError("Pi Agent task timed out.") from e
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout)[-4000:]
            raise ProviderError(f"Pi Agent exited with code {completed.returncode}: {detail}")
        return self._parse_json_result(completed.stdout)

    def _command(self) -> list[str]:
        override = os.environ.get("CODEXSAVER_PI_AGENT_COMMAND")
        if override:
            return override.split()
        if self.card.command:
            command = self.card.command
        else:
            command = [
                "pi",
                "--provider",
                "deepseek",
                "--model",
                "deepseek-v4-flash",
                "--mode",
                "json",
                "--no-session",
                "-p",
            ]
        if not shutil.which(command[0]):
            raise ProviderError(
                f"Pi Agent command '{command[0]}' is not available on PATH. "
                "Use `codexsaver agents list` to inspect the default Pi Agent card, "
                "or add a custom .agent-card.json with a valid command."
            )
        return command

    def _parse_json_result(self, stdout: str) -> Dict[str, Any]:
        final_text = ""
        usage: Dict[str, Any] = {}
        provider = ""
        model = ""
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") in {"turn_end", "agent_end"}:
                message = event.get("message") or {}
                final_text = extract_text(message) or final_text
                usage = message.get("usage") or usage
                provider = str(message.get("provider") or provider)
                model = str(message.get("responseModel") or message.get("model") or model)
        if not final_text:
            raise ProviderError(f"Pi Agent produced no final text output: {stdout[:1000]}")
        try:
            result = json.loads(strip_json_fences(final_text))
        except json.JSONDecodeError as e:
            raise ProviderError(f"Pi Agent final text was not JSON: {final_text[:1000]}") from e
        if isinstance(result, dict):
            result.setdefault("_worker_usage", usage)
            result.setdefault("_worker_provider", provider or "deepseek")
            result.setdefault("_worker_model", model or "deepseek-v4-flash")
        return result


def extract_text(message: Dict[str, Any]) -> str:
    chunks = []
    for item in message.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            chunks.append(str(item.get("text", "")))
    return "".join(chunks).strip()


def strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def save_pi_deepseek_auth(api_key: str, auth_path: str | None = None) -> Dict[str, Any]:
    path = Path(auth_path).expanduser() if auth_path else Path.home() / ".pi" / "agent" / "auth.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data["deepseek"] = {"type": "api_key", "key": api_key}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return {
        "path": str(path),
        "saved": True,
        "mode": oct(path.stat().st_mode & 0o777)[2:],
    }
