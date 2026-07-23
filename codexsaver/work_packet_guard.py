from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .safe_checks import CheckRejected, run_provider_check

_GUARD_MARKER = "codexsaver-bounded-work-packet-v1"


def _redact_original_workspace(result: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    """Redact the source workspace as well as the copied check workspace.

    ``run_provider_check`` redacts the directory in which the child executes.
    Work-packet checks execute in a copied sandbox, but workspace code can still
    print a path captured from the original tree. Preserve the raw-output hashes
    and byte counts while removing that second host-topology identity from the
    human-readable receipt.
    """
    source = str(workspace.resolve())
    if source:
        result["stdout"] = str(result.get("stdout", "")).replace(source, "<workspace>")
        result["stderr"] = str(result.get("stderr", "")).replace(source, "<workspace>")
    return result


def _bounded_preflight_checks(self) -> Dict[str, Any]:
    commands = self.packet.allowed_commands
    if not commands:
        return {"type": "preflight_skipped", "reason": "No allowed commands."}
    if len(commands) > 8:
        self.executed_commands = []
        self.tempdir = None
        return {
            "type": "preflight_refused",
            "reason": "Allowed check count exceeds the bounded recipe limit.",
            "results": [],
            "guard": _GUARD_MARKER,
        }
    tempdir = self._fresh_workspace()
    results: List[Dict[str, Any]] = []
    for command in commands:
        try:
            result = run_provider_check(command, str(tempdir))
            result = _redact_original_workspace(result, self.workspace)
        except CheckRejected as exc:
            self.executed_commands = []
            self.tempdir = None
            return {
                "type": "preflight_refused",
                "reason": f"Allowed check was refused: {exc}",
                "results": results,
                "guard": _GUARD_MARKER,
            }
        results.append(result)
        if result["exit_code"] != 0 or result["timed_out"]:
            self.executed_commands = []
            self.tempdir = None
            return {
                "type": "preflight_failed",
                "results": results,
                "guard": _GUARD_MARKER,
            }
    self.executed_commands = results
    return {
        "type": "already_satisfied",
        "results": results,
        "guard": _GUARD_MARKER,
    }


def _bounded_run_check(self, command_id: int) -> Dict[str, Any]:
    if self.tempdir is None:
        return {"type": "check_rejected", "reason": "No patch has been applied in sandbox."}
    if command_id < 0 or command_id >= len(self.packet.allowed_commands):
        return {"type": "check_rejected", "reason": f"Unknown command_id: {command_id}"}
    if len(self.packet.allowed_commands) > 8:
        return {"type": "check_rejected", "reason": "Allowed check count exceeds the bounded recipe limit."}
    command = self.packet.allowed_commands[command_id]
    try:
        result = run_provider_check(command, str(self.tempdir))
        result = _redact_original_workspace(result, self.workspace)
    except CheckRejected as exc:
        return {"type": "check_rejected", "reason": f"Allowed check was refused: {exc}"}
    self.executed_commands.append(result)
    return {"type": "check_result", "result": result, "guard": _GUARD_MARKER}


def install_work_packet_guard() -> None:
    """Replace legacy work-packet shell methods with bounded recipe methods.

    Kept as a small compatibility layer so existing public APIs remain stable
    while the larger work-packet module is refactored. Importing the package is
    sufficient to install the guard, including direct submodule imports.
    """
    from .work_packet import PatchSandbox

    if getattr(PatchSandbox, "_codexsaver_guard", None) == _GUARD_MARKER:
        return
    PatchSandbox.preflight_checks = _bounded_preflight_checks
    PatchSandbox.run_check = _bounded_run_check
    PatchSandbox._codexsaver_guard = _GUARD_MARKER
