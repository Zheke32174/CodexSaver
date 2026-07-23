from __future__ import annotations

from pathlib import Path
from typing import List

from .schema import FileContext


class ContextPacker:
    """Load bounded, workspace-confined file context for delegated workers."""

    def __init__(
        self,
        max_files: int = 8,
        max_chars_per_file: int = 24_000,
        max_total_chars: int = 120_000,
        workspace: str = ".",
    ):
        self.max_files = max_files
        self.max_chars_per_file = max_chars_per_file
        self.max_total_chars = max_total_chars
        self.workspace = Path(workspace).resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError("workspace must resolve to a directory")

    def load(self, file_paths: List[str]) -> List[FileContext]:
        contexts: List[FileContext] = []
        total = 0
        for raw in file_paths[: self.max_files]:
            try:
                path = self._resolve_path(raw)
            except (OSError, ValueError) as exc:
                contexts.append(
                    FileContext(
                        path=raw,
                        content=f"/* CodexSaver: refused context path: {raw} ({exc}) */",
                    )
                )
                continue

            if not path.exists() or not path.is_file():
                contexts.append(
                    FileContext(
                        path=raw,
                        content=f"/* CodexSaver: file not found: {raw} */",
                    )
                )
                continue

            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > self.max_chars_per_file:
                content = content[: self.max_chars_per_file] + "\n\n/* ... truncated by CodexSaver ... */"
            remaining = self.max_total_chars - total
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[:remaining] + "\n\n/* ... total context truncated by CodexSaver ... */"

            relative_identity = path.relative_to(self.workspace).as_posix()
            contexts.append(FileContext(path=relative_identity, content=content))
            total += len(content)
        return contexts

    def _resolve_path(self, raw: str) -> Path:
        path = Path(raw)
        if path.is_absolute():
            raise ValueError("absolute paths are not allowed")
        if any(part == ".." for part in path.parts):
            raise ValueError("parent traversal is not allowed")

        candidate = (self.workspace / path).resolve(strict=False)
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("path resolves outside the workspace") from exc
        return candidate
