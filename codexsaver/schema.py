from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Literal

RiskLevel = Literal["low", "medium", "high"]
Route = Literal["codex", "deepseek"]
ActionType = Literal[
    "readonly",
    "generate_patch",
    "generate_script",
    "dry_run",
    "execute_write",
    "destructive",
]
RiskDomain = Literal[
    "normal",
    "auth",
    "payment",
    "database",
    "schema",
    "infra",
    "secrets",
]
TaskType = Literal[
    "code_search",
    "explain",
    "write_tests",
    "fix_lint",
    "docs",
    "boilerplate",
    "simple_refactor",
    "review_draft",
    "unknown",
]
DelegationLevel = Literal["research", "draft_patch", "bounded_impl", "repair_loop"]
OrchestratorRoute = Literal["codex_only", "single_worker", "multi_worker", "readonly_swarm"]
SpecialistMode = Literal["readonly", "bounded_patch", "repair_loop"]


@dataclass
class FileContext:
    path: str
    content: str


@dataclass
class DelegateTaskInput:
    instruction: str
    files: List[str]
    constraints: List[str]
    workspace: str = "."
    max_files: int = 8
    max_chars_per_file: int = 24_000
    max_total_chars: int = 120_000
    dry_run: bool = False


@dataclass
class RouteDecision:
    route: Route
    task_type: TaskType
    risk: RiskLevel
    reason: str
    protected_hits: List[str]


@dataclass
class WorkerTask:
    instruction: str
    task_type: TaskType
    risk: RiskLevel
    constraints: List[str]
    workspace: str
    files: List[FileContext]


@dataclass
class WorkPacketInput:
    goal: str
    files: List[str]
    constraints: List[str]
    acceptance_criteria: List[str]
    allowed_files: List[str]
    forbidden_paths: List[str]
    allowed_commands: List[str]
    workspace: str = "."
    delegation_level: DelegationLevel = "bounded_impl"
    max_iterations: int = 3
    max_diff_lines: int = 300
    max_files: int = 8
    max_chars_per_file: int = 24_000
    max_total_chars: int = 120_000
    dry_run: bool = False


@dataclass
class WorkerAction:
    action: str
    args: Dict[str, Any]


@dataclass
class WorkPacketVerification:
    ok: bool
    fallback_to_codex: bool
    reason: str
    warnings: List[str]
    executed_commands: List[Dict[str, Any]]
    changed_files: List[str]
    diff_lines: int


@dataclass
class VerificationResult:
    ok: bool
    fallback_to_codex: bool
    reason: str
    warnings: List[str]
    executed_commands: List[Dict[str, Any]]


@dataclass
class SpecialistProfile:
    name: str
    provider: str
    model: str
    mode: SpecialistMode
    prompt_file: str
    description: str


@dataclass
class WorkGraphNode:
    id: str
    type: str
    goal: str
    depends_on: List[str]
    specialist: str
    allowed_files: List[str]
    forbidden_paths: List[str]
    allowed_commands: List[str]
    acceptance_criteria: List[str]
    mode: SpecialistMode
    action_type: ActionType = "readonly"
    risk_domain: RiskDomain = "normal"
    execution_policy: str = "worker"


@dataclass
class WorkGraph:
    graph_id: str
    route: OrchestratorRoute
    summary: str
    nodes: List[WorkGraphNode]
    blocked_actions: List[str] = field(default_factory=list)
    codex_next_actions: List[str] = field(default_factory=list)
    handoff_summary: str = ""


@dataclass
class OrchestrateTaskInput:
    goal: str
    files: List[str]
    constraints: List[str]
    workspace: str = "."
    max_parallel_workers: int = 4
    dry_run: bool = False


@dataclass
class SpecialistRunInput:
    specialist: str
    goal: str
    files: List[str]
    allowed_files: List[str]
    forbidden_paths: List[str]
    acceptance_criteria: List[str]
    allowed_commands: List[str]
    workspace: str = "."
    dry_run: bool = False


@dataclass
class AggregationResult:
    ok: bool
    aggregate_patch: str
    changed_files: List[str]
    conflicts: List[str]
    codex_review_notes: List[str]


def to_dict(obj: Any) -> Dict[str, Any]:
    return asdict(obj)
