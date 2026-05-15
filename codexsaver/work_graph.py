from __future__ import annotations

from itertools import count
from typing import List

from .schema import OrchestrateTaskInput, WorkGraph, WorkGraphNode
from .specialists import SpecialistRegistry


class WorkGraphPlanner:
    def __init__(self, registry: SpecialistRegistry | None = None):
        self.registry = registry or SpecialistRegistry()
        self._ids = count(1)

    def plan(self, request: OrchestrateTaskInput) -> WorkGraph:
        goal = request.goal.lower()
        nodes: List[WorkGraphNode] = []

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
            ))

        route = self._route_for(nodes)
        summary = f"Planned {len(nodes)} v3 node(s) with route={route}."
        return WorkGraph(
            graph_id=f"graph-{next(self._ids)}",
            route=route,
            summary=summary,
            nodes=nodes,
        )

    def _node(self, node_id: str, node_type: str, goal: str, depends_on: List[str],
              specialist: str, allowed_files: List[str], acceptance_criteria: List[str],
              allowed_commands: List[str] | None = None) -> WorkGraphNode:
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
        )

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
