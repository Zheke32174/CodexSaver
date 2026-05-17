from __future__ import annotations

from itertools import count
from typing import List

from .policy import classify_delegation_policy
from .schema import OrchestrateTaskInput, WorkGraph, WorkGraphNode
from .specialists import SpecialistRegistry


class WorkGraphPlanner:
    def __init__(self, registry: SpecialistRegistry | None = None):
        self.registry = registry or SpecialistRegistry()
        self._ids = count(1)

    def plan(self, request: OrchestrateTaskInput) -> WorkGraph:
        goal = request.goal.lower()
        nodes: List[WorkGraphNode] = []
        policy = classify_delegation_policy(request.goal, request.files)

        if not policy.worker_allowed:
            nodes.extend(self._safe_prep_nodes(request, policy))
            summary = (
                f"Planned {len(nodes)} safe prep node(s); blocked high-risk action for Codex. "
                f"{policy.reason}."
            )
            return WorkGraph(
                graph_id=f"graph-{next(self._ids)}",
                route="readonly_swarm" if nodes and all(node.mode == "readonly" for node in nodes) else "multi_worker",
                summary=summary,
                nodes=nodes,
                blocked_actions=policy.blocked_actions,
                codex_next_actions=policy.codex_next_actions,
                handoff_summary="Worker nodes cover safe preparation; Codex must retain blocked actions.",
            )

        impl_needed = any(word in goal for word in [
            "implement", "add ", "create ", "build ", "refactor", "fix ", "update ",
            "实现", "新增", "添加", "修复", "重构", "更新",
        ])
        docs_needed = any(word in goal for word in [
            "doc", "readme", "jsdoc", "docstring", "注释", "文档",
        ])
        tests_needed = any(word in goal for word in [
            "test", "pytest", "jest", "单测", "测试",
        ])
        explain_needed = any(word in goal for word in [
            "explain", "risk", "review", "explain", "解释", "风险",
        ])
        perf_needed = any(word in goal for word in [
            "perf", "performance", "optimiz", "性能", "优化",
        ])

        impl_id = ""
        if impl_needed:
            impl_id = self._next_id("impl")
            nodes.append(self._node(
                node_id=impl_id,
                node_type="bounded_patch",
                goal=request.goal,
                depends_on=[],
                specialist="impl_worker",
                allowed_files=request.files,
                acceptance_criteria=["Implementation patch stays inside allowed files."],
                action_type=policy.action_type,
                risk_domain=policy.risk_domain,
                execution_policy=policy.execution_policy,
            ))

        if tests_needed:
            test_files = self._guess_test_files(request.files)
            nodes.append(self._node(
                node_id=self._next_id("tests"),
                node_type="bounded_patch",
                goal=f"Add or update tests for: {request.goal}",
                depends_on=[impl_id] if impl_id else [],
                specialist="test_writer",
                allowed_files=test_files,
                allowed_commands=self._guess_test_commands(test_files),
                acceptance_criteria=["Test patch stays inside test files."],
                action_type="generate_patch",
                risk_domain=policy.risk_domain,
                execution_policy=policy.execution_policy,
            ))

        if docs_needed:
            nodes.append(self._node(
                node_id=self._next_id("docs"),
                node_type="bounded_patch",
                goal=f"Add docs for: {request.goal}",
                depends_on=[impl_id] if impl_id else [],
                specialist="doc_writer",
                allowed_files=request.files,
                acceptance_criteria=["Docs patch stays inside allowlisted files."],
                action_type="generate_patch",
                risk_domain=policy.risk_domain,
                execution_policy=policy.execution_policy,
            ))

        if explain_needed:
            nodes.append(self._node(
                node_id=self._next_id("explain"),
                node_type="explain",
                goal=f"Explain the implementation and risk of: {request.goal}",
                depends_on=[impl_id] if impl_id else [],
                specialist="explainer",
                allowed_files=request.files,
                acceptance_criteria=["Return a short explanation only."],
                action_type="readonly",
                risk_domain=policy.risk_domain,
                execution_policy="worker",
            ))

        if perf_needed:
            nodes.append(self._node(
                node_id=self._next_id("perf"),
                node_type="review_hint",
                goal=f"Review performance implications of: {request.goal}",
                depends_on=[impl_id] if impl_id else [],
                specialist="perf_reviewer",
                allowed_files=request.files,
                acceptance_criteria=["Return concise performance notes only."],
                action_type="readonly",
                risk_domain=policy.risk_domain,
                execution_policy="worker",
            ))

        if not nodes:
            nodes.append(self._node(
                node_id=self._next_id("explain"),
                node_type="explain",
                goal=request.goal,
                depends_on=[],
                specialist="explainer",
                allowed_files=request.files,
                acceptance_criteria=["Return a short explanation only."],
                action_type="readonly",
                risk_domain=policy.risk_domain,
                execution_policy="worker",
            ))

        route = self._route_for(nodes)
        summary = f"Planned {len(nodes)} v3 node(s) with route={route}."
        return WorkGraph(
            graph_id=f"graph-{next(self._ids)}",
            route=route,
            summary=summary,
            nodes=nodes,
            blocked_actions=policy.blocked_actions,
            codex_next_actions=policy.codex_next_actions,
            handoff_summary="Worker nodes can proceed under the selected execution policy.",
        )

    def _safe_prep_nodes(self, request: OrchestrateTaskInput, policy) -> List[WorkGraphNode]:
        nodes = [
            self._node(
                node_id=self._next_id("inspect"),
                node_type="explain",
                goal=(
                    "Readonly inspection only. Summarize relevant schema/data flow, existing scripts, "
                    f"and risks for: {request.goal}"
                ),
                depends_on=[],
                specialist="explainer",
                allowed_files=request.files,
                acceptance_criteria=["Return readonly findings only. Do not propose writes."],
                action_type="readonly",
                risk_domain=policy.risk_domain,
                execution_policy="worker",
            )
        ]
        if policy.risk_domain in {"database", "schema"}:
            nodes.append(self._node(
                node_id=self._next_id("validation"),
                node_type="bounded_patch",
                goal=(
                    "Generate validation SQL, dry-run notes, or non-executing checks only. "
                    "Do not execute database writes. Require --apply for any future write script. "
                    f"Task: {request.goal}"
                ),
                depends_on=[],
                specialist="doc_writer",
                allowed_files=self._safe_report_files(request.files),
                acceptance_criteria=[
                    "Artifact documents dry-run validation only.",
                    "No database writes are executed.",
                    "Any write path is documented as requiring Codex/user approval.",
                ],
                action_type="dry_run",
                risk_domain=policy.risk_domain,
                execution_policy="dry_run_only",
            ))
        return nodes

    def _node(self, node_id: str, node_type: str, goal: str, depends_on: List[str],
              specialist: str, allowed_files: List[str], acceptance_criteria: List[str],
              allowed_commands: List[str] | None = None,
              action_type: str = "readonly",
              risk_domain: str = "normal",
              execution_policy: str = "worker") -> WorkGraphNode:
        profile = self.registry.get(specialist)
        return WorkGraphNode(
            id=node_id,
            type=node_type,
            goal=goal,
            depends_on=depends_on,
            specialist=specialist,
            allowed_files=allowed_files,
            forbidden_paths=[],
            allowed_commands=allowed_commands or [],
            acceptance_criteria=acceptance_criteria,
            mode=profile.mode,
            action_type=action_type,
            risk_domain=risk_domain,
            execution_policy=execution_policy,
        )

    def _safe_report_files(self, files: List[str]) -> List[str]:
        if files:
            stem = files[0].split("/")[-1].rsplit(".", 1)[0]
            return [f"docs/codexsaver-dry-run-{stem}.md"]
        return ["docs/codexsaver-dry-run-report.md"]

    def _guess_test_files(self, files: List[str]) -> List[str]:
        guessed: List[str] = []
        for path in files:
            if path.endswith(".py"):
                guessed.append(f"tests/test_{path.split('/')[-1]}")
            elif path.endswith((".js", ".ts", ".tsx")):
                stem = path.split("/")[-1].rsplit(".", 1)[0]
                guessed.append(f"tests/{stem}.test.{path.rsplit('.', 1)[-1]}")
        return guessed or files

    def _guess_test_commands(self, files: List[str]) -> List[str]:
        commands: List[str] = []
        for path in files:
            if path.endswith(".py"):
                commands.append(f"python -m pytest {path} -q")
            elif path.endswith(".js"):
                commands.append(f"node --test {path}")
            elif path.endswith((".ts", ".tsx")):
                commands.append(f"npx jest {path}")
        return commands[:1]

    def _route_for(self, nodes: List[WorkGraphNode]) -> str:
        if nodes and all(node.mode == "readonly" for node in nodes):
            return "readonly_swarm"
        if len(nodes) == 1:
            return "single_worker"
        return "multi_worker"

    def _next_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"
