from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_AGENT_CARD_DIRS = [
    ".pi-agents",
    ".pi/agents",
]


@dataclass(frozen=True)
class AgentCard:
    id: str
    name: str
    type: str
    status: str
    capabilities: List[str]
    languages: List[str]
    endpoint: str
    command: List[str] = field(default_factory=list)
    cost_weight: float = 0.1
    success_rate: float = 1.0
    current_load: int = 0
    context_window: int = 64_000
    tags: List[str] = field(default_factory=list)
    auth: str = "none"
    streaming: bool = False
    worktree_path: str = ".pi-worktrees/pi-agent"
    permissions_config: str = ".pi/permissions.json"
    filesystem_policy: str = "worktree_write_only"
    network_policy: str = "package_repositories_only"
    source: str = "builtin"


class AgentRegistry:
    """Discovers worker Agent Cards without network calls."""

    def __init__(self, extra_dirs: List[str] | None = None):
        self.extra_dirs = extra_dirs or []

    def discover(self, workspace: str = ".") -> List[AgentCard]:
        root = Path(workspace).resolve()
        cards: Dict[str, AgentCard] = {builtin_pi_agent().id: builtin_pi_agent()}
        for directory in self._scan_dirs(root):
            if not directory.exists() or not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.agent-card.json")):
                card = self._load_card(path)
                if card:
                    cards[card.id] = card
        return [cards[key] for key in sorted(cards)]

    def ensure_builtin_card(self, workspace: str = ".") -> str:
        root = Path(workspace).resolve()
        target = root / ".pi-agents" / "pi-agent.agent-card.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(builtin_pi_agent(source=str(target))), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return str(target)

    def _scan_dirs(self, root: Path) -> List[Path]:
        configured = load_project_config(str(root)).get("agent_card_dirs", [])
        dirs = [root / item for item in DEFAULT_AGENT_CARD_DIRS]
        dirs.extend(root / str(item) for item in configured if isinstance(item, str))
        dirs.extend(Path(item).expanduser() for item in self.extra_dirs)
        dirs.append(Path.home() / ".codexsaver" / "agents")
        return list(dict.fromkeys(dirs))

    def _load_card(self, path: Path) -> AgentCard | None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return AgentCard(
                id=str(raw["id"]),
                name=str(raw.get("name") or raw["id"]),
                type=str(raw.get("type", "custom")),
                status=str(raw.get("status", "online")),
                capabilities=[str(item) for item in raw.get("capabilities", [])],
                languages=[str(item).lower() for item in raw.get("languages", [])],
                endpoint=str(raw.get("endpoint", "local:unknown")),
                command=[str(item) for item in raw.get("command", [])],
                cost_weight=float(raw.get("cost_weight", 0.5)),
                success_rate=float(raw.get("success_rate", 1.0)),
                current_load=int(raw.get("current_load", 0)),
                context_window=int(raw.get("context_window", 64_000)),
                tags=[str(item) for item in raw.get("tags", [])],
                auth=str(raw.get("auth", "none")),
                streaming=bool(raw.get("streaming", False)),
                worktree_path=str(raw.get("worktree_path", ".pi-worktrees/custom-agent")),
                permissions_config=str(raw.get("permissions_config", ".pi/permissions.json")),
                filesystem_policy=str(raw.get("filesystem_policy", "worktree_write_only")),
                network_policy=str(raw.get("network_policy", "llm_api_only")),
                source=str(path),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            return None


def builtin_pi_agent(source: str = "builtin") -> AgentCard:
    return AgentCard(
        id="pi-agent-default",
        name="Pi Agent Worker",
        type="pi",
        status="online",
        capabilities=[
            "code_generation",
            "testing",
            "docs",
            "code_explanation",
            "performance_review",
            "lint_fix",
        ],
        languages=["python", "javascript", "typescript", "markdown"],
        endpoint="local:pi-side-agents",
        command=[
            "pi",
            "--provider",
            "deepseek",
            "--model",
            "deepseek-v4-flash",
            "--mode",
            "json",
            "--no-session",
            "-p",
        ],
        cost_weight=0.1,
        success_rate=1.0,
        current_load=0,
        context_window=64_000,
        tags=["builtin", "codexsaver", "low_cost"],
        worktree_path=".pi-worktrees/pi-agent",
        permissions_config=".pi/permissions.json",
        filesystem_policy="worktree_write_only",
        network_policy="package_repositories_only",
        source=source,
    )


def load_project_config(workspace: str = ".") -> Dict[str, Any]:
    path = Path(workspace).resolve() / ".pi" / "codexsaver.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}
