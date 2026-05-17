from __future__ import annotations

from dataclasses import dataclass
from typing import List


DATABASE_TERMS = [
    "database", "db", "sql", "sqlite", "postgres", "mysql", "schema",
    "migration", "migrate", "table", "index", "write database", "写库",
    "数据库", "表结构", "迁移", "入库",
]

DESTRUCTIVE_TERMS = [
    "delete", "drop", "truncate", "destroy", "overwrite", "rebuild",
    "remove old", "清空", "删除", "重建", "覆盖",
]

WRITE_TERMS = [
    "apply", "execute", "write", "insert", "update rows", "commit",
    "运行", "执行", "写入", "提交",
]

AUTH_TERMS = ["auth", "oauth", "jwt", "session", "permission", "rbac", "认证", "权限"]
PAYMENT_TERMS = ["payment", "billing", "invoice", "checkout", "支付", "账单"]
INFRA_TERMS = ["deploy", "terraform", "infra", "kubernetes", "生产", "部署"]
SECRET_TERMS = ["secret", "token", "api key", "credential", "密钥", "令牌"]


@dataclass(frozen=True)
class DelegationPolicy:
    action_type: str
    risk_domain: str
    worker_allowed: bool
    execution_policy: str
    blocked_actions: List[str]
    codex_next_actions: List[str]
    reason: str


def classify_delegation_policy(goal: str, files: List[str] | None = None) -> DelegationPolicy:
    text = f"{goal}\n{' '.join(files or [])}".lower()
    risk_domain = _risk_domain(text)
    action_type = _action_type(text)

    blocked_actions: List[str] = []
    codex_next_actions: List[str] = []
    worker_allowed = True
    execution_policy = "worker"

    if risk_domain in {"auth", "payment", "infra", "secrets"} and action_type != "readonly":
        worker_allowed = False
        execution_policy = "codex_only"
        blocked_actions.append(f"{risk_domain} write/change requires Codex control.")
        codex_next_actions.append("Keep this task in Codex and use workers only for readonly context gathering.")
    elif risk_domain in {"database", "schema"}:
        if action_type in {"execute_write", "destructive"}:
            worker_allowed = False
            execution_policy = "codex_only"
            blocked_actions.append("Database writes, migrations, deletes, or rebuilds require Codex/user approval.")
            codex_next_actions.append("Use workers for inspection, draft scripts, validation SQL, and dry-run plans only.")
        elif action_type in {"generate_script", "generate_patch", "dry_run"}:
            execution_policy = "dry_run_only"
            blocked_actions.append("Generated scripts must not execute writes by default.")
            codex_next_actions.append("Review generated artifacts, run dry-run checks, then request approval before --apply.")
    elif action_type in {"execute_write", "destructive"}:
        worker_allowed = False
        execution_policy = "codex_only"
        blocked_actions.append("Direct writes or destructive operations require Codex control.")
        codex_next_actions.append("Convert the task into a dry-run script or validation plan before delegation.")

    reason = f"action_type={action_type}, risk_domain={risk_domain}, execution_policy={execution_policy}"
    return DelegationPolicy(
        action_type=action_type,
        risk_domain=risk_domain,
        worker_allowed=worker_allowed,
        execution_policy=execution_policy,
        blocked_actions=blocked_actions,
        codex_next_actions=codex_next_actions,
        reason=reason,
    )


def _risk_domain(text: str) -> str:
    if _has(text, AUTH_TERMS):
        return "auth"
    if _has(text, PAYMENT_TERMS):
        return "payment"
    if _has(text, SECRET_TERMS):
        return "secrets"
    if _has(text, INFRA_TERMS):
        return "infra"
    if "schema" in text or "表结构" in text:
        return "schema"
    if _has(text, DATABASE_TERMS):
        return "database"
    return "normal"


def _action_type(text: str) -> str:
    if _has(text, DESTRUCTIVE_TERMS):
        return "destructive"
    if _has(text, WRITE_TERMS) and _has(text, DATABASE_TERMS):
        return "execute_write"
    if "dry-run" in text or "dry run" in text or "试运行" in text:
        return "dry_run"
    if "script" in text or "importer" in text or "导入脚本" in text or "脚本" in text:
        return "generate_script"
    if _has(text, ["implement", "add ", "create ", "build ", "refactor", "fix ", "update ", "实现", "新增", "添加", "修复", "重构", "更新"]):
        return "generate_patch"
    return "readonly"


def _has(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)
