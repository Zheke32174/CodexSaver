from __future__ import annotations

from typing import Any, Dict, List

from .router import PROTECTED_PATH_KEYWORDS
from .safe_checks import CheckRejected, run_provider_check
from .schema import RouteDecision, VerificationResult


REQUIRED_KEYS = {"status", "summary", "changed_files", "patch", "commands_to_run", "risk_notes"}
VALID_STATUS = {"success", "failed", "needs_codex"}


class Verifier:
    def verify(self, worker_result: Dict[str, Any], decision: RouteDecision,
               workspace: str = ".") -> VerificationResult:
        warnings: List[str] = []
        executed_commands: List[Dict[str, Any]] = []
        missing = REQUIRED_KEYS - set(worker_result.keys())
        if missing:
            return VerificationResult(False, True,
                f"Worker result missing required keys: {sorted(missing)}", warnings, executed_commands)
        status = worker_result.get("status")
        if status not in VALID_STATUS:
            return VerificationResult(False, True,
                f"Invalid worker status: {status}", warnings, executed_commands)
        if status != "success":
            return VerificationResult(False, True,
                f"Worker requested fallback with status={status}.", warnings, executed_commands)
        changed_files = worker_result.get("changed_files") or []
        if not isinstance(changed_files, list):
            return VerificationResult(False, True,
                "changed_files must be a list.", warnings, executed_commands)
        risky = [path for path in changed_files
                 if any(keyword in str(path).lower() for keyword in PROTECTED_PATH_KEYWORDS)]
        if risky and decision.risk != "low":
            return VerificationResult(False, True,
                f"Worker touched protected files under non-low risk: {risky}", warnings, executed_commands)
        patch = worker_result.get("patch", "")
        if patch and len(patch) > 120_000:
            return VerificationResult(False, True,
                "Patch is too large for safe automatic delegation.", warnings, executed_commands)
        commands = worker_result.get("commands_to_run") or []
        if not isinstance(commands, list):
            return VerificationResult(False, True,
                "commands_to_run must be a list.", warnings, executed_commands)
        if not commands:
            warnings.append("No verification commands suggested by worker.")
        else:
            command_check = self._run_commands(commands, workspace)
            executed_commands = command_check["results"]
            warnings.extend(command_check["warnings"])
            if not command_check["ok"]:
                return VerificationResult(
                    False,
                    True,
                    command_check["reason"],
                    warnings,
                    executed_commands,
                )
        return VerificationResult(True, False,
            "Worker result passed structural verification.", warnings, executed_commands)

    def _run_commands(self, commands: List[Any], workspace: str) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        warnings: List[str] = []
        if len(commands) > 8:
            return {
                "ok": False,
                "reason": "Worker suggested too many verification commands.",
                "results": results,
                "warnings": warnings,
            }
        for command in commands:
            try:
                result = run_provider_check(command, workspace)
            except CheckRejected as exc:
                return {
                    "ok": False,
                    "reason": f"Provider-suggested check was refused: {exc}",
                    "results": results,
                    "warnings": warnings,
                }
            results.append(result)
            if result["timed_out"]:
                return {
                    "ok": False,
                    "reason": "Verification check exceeded its time budget.",
                    "results": results,
                    "warnings": warnings,
                }
            if result["exit_code"] != 0:
                return {
                    "ok": False,
                    "reason": "Verification check failed.",
                    "results": results,
                    "warnings": warnings,
                }
            if result["stderr"].strip():
                warnings.append("Verification check produced redacted stderr.")
        return {
            "ok": True,
            "reason": "Approved verification checks passed.",
            "results": results,
            "warnings": warnings,
        }
