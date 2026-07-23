from __future__ import annotations

import ast
import hashlib
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s]+"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
]
_ALLOWED_PYTEST_FLAGS = {
    "-q", "--quiet", "-x", "--exitfirst", "--disable-warnings",
    "--strict-markers", "--strict-config", "-s",
}
_MAX_COMMAND_CHARS = 4096
_MAX_OUTPUT_BYTES = 64 * 1024
_TIMEOUT_SECONDS = 60


class CheckRejected(ValueError):
    pass


def run_provider_check(command: Any, workspace: str) -> Dict[str, Any]:
    """Run one narrowly approved verification recipe without a shell.

    The same executor is used for provider suggestions and steward-configured
    work-packet checks. Unsupported recipes fail closed. The child receives a
    minimal environment, bounded time/output, and returns redacted digest
    receipts rather than unbounded host transcripts.
    """
    argv = _normalize(command)
    _validate_recipe(argv)
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise CheckRejected("verification workspace does not exist")

    env = _clean_environment(root)
    try:
        completed = subprocess.run(
            argv,
            cwd=str(root),
            shell=False,
            text=False,
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
        stdout = completed.stdout[-_MAX_OUTPUT_BYTES:]
        stderr = completed.stderr[-_MAX_OUTPUT_BYTES:]
        return _receipt(argv, completed.returncode, stdout, stderr, root, timed_out=False)
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"")[-_MAX_OUTPUT_BYTES:]
        stderr = (exc.stderr or b"")[-_MAX_OUTPUT_BYTES:]
        return _receipt(argv, 124, stdout, stderr, root, timed_out=True)


def _normalize(command: Any) -> List[str]:
    if not isinstance(command, str) or not command.strip():
        raise CheckRejected("verification command must be a non-empty string")
    if len(command) > _MAX_COMMAND_CHARS or any(ch in command for ch in ("\x00", "\r", "\n")):
        raise CheckRejected("verification command is outside bounds")
    try:
        argv = shlex.split(command, posix=(os.name != "nt"))
    except ValueError as exc:
        raise CheckRejected("verification command could not be parsed") from exc
    if not argv or len(argv) > 32 or any(len(arg) > 1024 for arg in argv):
        raise CheckRejected("verification argv is outside bounds")
    return argv


def _validate_recipe(argv: List[str]) -> None:
    executable = Path(argv[0]).name.lower()
    if executable in {"python", "python3", Path(sys.executable).name.lower()}:
        _validate_python(argv)
        return
    if executable in {"pytest", "py.test"}:
        _validate_pytest(argv[1:])
        return
    raise CheckRejected("verification executable is not approved")


def _validate_python(argv: List[str]) -> None:
    if len(argv) >= 3 and argv[1] == "-c":
        _validate_inline_python(argv[2])
        if len(argv) != 3:
            raise CheckRejected("inline Python recipe has unexpected arguments")
        return
    if len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]:
        _validate_pytest(argv[3:])
        return
    if len(argv) >= 3 and argv[1:3] == ["-m", "compileall"]:
        _validate_relative_arguments(argv[3:], allowed_flags={"-q", "-f"})
        return
    raise CheckRejected("Python verification recipe is not approved")


def _validate_inline_python(source: str) -> None:
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise CheckRejected("inline Python is invalid") from exc
    if _is_literal_print(tree):
        return
    if _is_import_assertion(tree):
        return
    raise CheckRejected("inline Python recipe is not an approved literal check")


def _is_literal_print(tree: ast.Module) -> bool:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        return False
    call = tree.body[0].value
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "print"
        and not call.keywords
        and all(isinstance(arg, ast.Constant) for arg in call.args)
    )


def _is_import_assertion(tree: ast.Module) -> bool:
    """Accept the legacy work-packet smoke shape only.

    Example: ``import hello; assert hello.greet() == 'hello'``.
    It executes workspace code, as pytest does, but cannot import os/sys,
    inspect environment values, call builtins, pass arguments, assign values,
    or perform multiple operations.
    """
    if len(tree.body) != 2:
        return False
    imported, assertion = tree.body
    if not isinstance(imported, ast.Import) or len(imported.names) != 1:
        return False
    alias = imported.names[0]
    if alias.asname is not None or not _safe_module_name(alias.name):
        return False
    if alias.name.split(".")[0] in {"os", "sys", "subprocess", "pathlib", "socket", "shutil"}:
        return False
    if not isinstance(assertion, ast.Assert) or assertion.msg is not None:
        return False
    test = assertion.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)):
        return False
    if not isinstance(test.comparators[0], ast.Constant):
        return False
    call = test.left
    if not isinstance(call, ast.Call) or call.args or call.keywords:
        return False
    function = call.func
    return (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == alias.name
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", function.attr) is not None
    )


def _safe_module_name(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", value) is not None


def _validate_pytest(args: List[str]) -> None:
    for arg in args:
        if arg in _ALLOWED_PYTEST_FLAGS or re.fullmatch(r"--maxfail=[1-9][0-9]?", arg):
            continue
        if arg.startswith("-"):
            raise CheckRejected("pytest option is not approved")
        _validate_relative_path(arg)


def _validate_relative_arguments(args: List[str], allowed_flags: set[str]) -> None:
    for arg in args:
        if arg in allowed_flags:
            continue
        if arg.startswith("-"):
            raise CheckRejected("verification option is not approved")
        _validate_relative_path(arg)


def _validate_relative_path(raw: str) -> None:
    path = Path(raw)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise CheckRejected("verification path escapes workspace")


def _clean_environment(workspace: Path) -> Dict[str, str]:
    home = workspace / ".codexsaver-home"
    env: Dict[str, str] = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(home),
        "USERPROFILE": str(home),
        "NO_PROXY": "*",
        "no_proxy": "*",
        "PIP_CONFIG_FILE": os.devnull,
    }
    if os.name == "nt":
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"):
            if os.environ.get(key):
                env[key] = os.environ[key]
    home.mkdir(mode=0o700, exist_ok=True)
    return env


def _receipt(
    argv: List[str],
    exit_code: int,
    stdout: bytes,
    stderr: bytes,
    workspace: Path,
    timed_out: bool,
) -> Dict[str, Any]:
    return {
        "command": shlex.join(argv),
        "argv_sha256": _digest("\0".join(argv).encode("utf-8")),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": _redact(stdout.decode("utf-8", errors="replace"), workspace),
        "stderr": _redact(stderr.decode("utf-8", errors="replace"), workspace),
        "stdout_sha256": _digest(stdout),
        "stderr_sha256": _digest(stderr),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
    }


def _redact(value: str, workspace: Path) -> str:
    redacted = value.replace(str(workspace), "<workspace>")
    home = str(Path.home())
    if home:
        redacted = redacted.replace(home, "<home>")
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted[-4000:]


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
