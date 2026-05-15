from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import difflib
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .aggregator import PatchAggregator
from .context import ContextPacker
from .cost import CostEstimator
from .provider import ProviderClient, ProviderError
from .schema import (
    FileContext,
    OrchestrateTaskInput,
    SpecialistRunInput,
    WorkPacketInput,
    WorkGraphNode,
    to_dict,
)
from .specialists import SpecialistRegistry
from .work_graph import WorkGraphPlanner
from .work_packet import WorkPacketRuntime


class V3Orchestrator:
    def __init__(self, registry: SpecialistRegistry | None = None):
        self.registry = registry or SpecialistRegistry()
        self.planner = WorkGraphPlanner(self.registry)
        self.aggregator = PatchAggregator()
        self.cost = CostEstimator()

    def orchestrate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        request = OrchestrateTaskInput(
            goal=input_data["goal"],
            files=input_data.get("files", []),
            constraints=input_data.get("constraints", []),
            workspace=input_data.get("workspace", "."),
            max_parallel_workers=int(input_data.get("max_parallel_workers", 4)),
            dry_run=bool(input_data.get("dry_run", False)),
        )
        graph = self.planner.plan(request)
        preview = {
            "graph_id": graph.graph_id,
            "route": graph.route,
            "summary": graph.summary,
            "nodes": [to_dict(node) for node in graph.nodes],
        }

        if request.dry_run:
            return {
                "route": graph.route,
                "status": "dry_run",
                "summary": graph.summary,
                "graph": preview,
                "metrics": {
                    "node_count": len(graph.nodes),
                    "parallelizable_nodes": len([n for n in graph.nodes if n.mode != "readonly"]),
                    "estimated_savings_percent": self._estimate_savings(len(graph.nodes)),
                },
                "next_step": "Review the work graph, then execute individual nodes or continue implementing v3.",
            }

        return self._execute_graph(request, graph.nodes, preview)

    def specialist_preview(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        request = SpecialistRunInput(
            specialist=input_data["specialist"],
            goal=input_data["goal"],
            files=input_data.get("files", []),
            allowed_files=input_data.get("allowed_files", []),
            forbidden_paths=input_data.get("forbidden_paths", []),
            acceptance_criteria=input_data.get("acceptance_criteria", []),
            allowed_commands=input_data.get("allowed_commands", []),
            workspace=input_data.get("workspace", "."),
            dry_run=bool(input_data.get("dry_run", False)),
        )
        profile = self.registry.get(request.specialist)
        node = WorkGraphNode(
            id=f"{request.specialist}-preview",
            type="bounded_patch" if profile.mode != "readonly" else "explain",
            goal=request.goal,
            depends_on=[],
            specialist=request.specialist,
            allowed_files=request.allowed_files,
            forbidden_paths=request.forbidden_paths,
            allowed_commands=request.allowed_commands,
            acceptance_criteria=request.acceptance_criteria,
            mode=profile.mode,
        )
        return {
            "route": "single_worker",
            "status": "dry_run" if request.dry_run else "planned",
            "specialist": to_dict(profile),
            "node_preview": to_dict(node),
        }

    def run_specialist(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        request = SpecialistRunInput(
            specialist=input_data["specialist"],
            goal=input_data["goal"],
            files=input_data.get("files", []),
            allowed_files=input_data.get("allowed_files", []),
            forbidden_paths=input_data.get("forbidden_paths", []),
            acceptance_criteria=input_data.get("acceptance_criteria", []),
            allowed_commands=input_data.get("allowed_commands", []),
            workspace=input_data.get("workspace", "."),
            dry_run=bool(input_data.get("dry_run", False)),
        )
        preview = self.specialist_preview(input_data)
        if request.dry_run:
            return preview
        profile = self.registry.get(request.specialist)
        node = WorkGraphNode(
            id=f"{request.specialist}-run",
            type="bounded_patch" if profile.mode != "readonly" else "explain",
            goal=request.goal,
            depends_on=[],
            specialist=request.specialist,
            allowed_files=request.allowed_files,
            forbidden_paths=request.forbidden_paths,
            allowed_commands=request.allowed_commands,
            acceptance_criteria=request.acceptance_criteria,
            mode=profile.mode,
        )
        if profile.mode == "readonly":
            context = ContextPacker(workspace=request.workspace).load(request.files or request.allowed_files)
            result = self._run_readonly_node(node, context)
            result["route"] = "deepseek" if result["status"] == "success" else "codex"
            return result
        return self._run_patch_node(node, request.workspace, request.files or request.allowed_files)

    def _execute_graph(self, request: OrchestrateTaskInput, nodes: List[WorkGraphNode],
                       preview: Dict[str, Any]) -> Dict[str, Any]:
        original_workspace = Path(request.workspace).resolve()
        current_workspace = self._copy_workspace(original_workspace)
        pending = {node.id: node for node in nodes}
        completed: set[str] = set()
        readonly_results: List[Dict[str, Any]] = []
        patch_results: List[Dict[str, Any]] = []

        while pending:
            ready = [
                node for node in pending.values()
                if all(dep in completed for dep in node.depends_on)
            ]
            if not ready:
                return self._needs_codex(
                    "Work graph dependencies could not be resolved.",
                    preview,
                    readonly_results + patch_results,
                    len(nodes),
                )

            readonly_ready = [node for node in ready if node.mode == "readonly"]
            patch_ready = [node for node in ready if node.mode != "readonly"]

            if readonly_ready:
                batch = self._execute_readonly_batch(current_workspace, request.files, readonly_ready, request.max_parallel_workers)
                readonly_results.extend(batch)
                if any(item["status"] != "success" for item in batch):
                    return self._needs_codex(
                        "One or more readonly specialists failed; Codex should take over.",
                        preview,
                        readonly_results + patch_results,
                        len(nodes),
                    )
                for node in readonly_ready:
                    completed.add(node.id)
                    pending.pop(node.id, None)

            if patch_ready:
                batch = self._execute_patch_batch(current_workspace, request.files, patch_ready, request.max_parallel_workers)
                if batch["status"] != "success":
                    return self._needs_codex(
                        batch["summary"],
                        preview,
                        readonly_results + patch_results + batch.get("results", []),
                        len(nodes),
                    )
                patch_results.extend(batch["results"])
                for node in patch_ready:
                    completed.add(node.id)
                    pending.pop(node.id, None)

        aggregate = self._build_final_aggregate_patch(original_workspace, current_workspace, patch_results)
        return {
            "route": "deepseek",
            "status": "success",
            "summary": "v3 graph executed successfully.",
            "graph": preview,
            "results": readonly_results + patch_results,
            "aggregate_patch": aggregate["patch"],
            "changed_files": aggregate["changed_files"],
            "checks": [check for item in patch_results for check in item.get("checks", [])],
            "verification": {
                "ok": True,
                "fallback_to_codex": False,
                "reason": "All v3 nodes completed and aggregated successfully.",
                "warnings": [],
                "executed_commands": [check for item in patch_results for check in item.get("checks", [])],
            },
            "metrics": {
                "node_count": len(nodes),
                "readonly_nodes": len(readonly_results),
                "patch_nodes": len(patch_results),
                "worker_calls": len(readonly_results) + len(patch_results),
                "estimated_savings_percent": self._estimate_savings(len(nodes)),
            },
            "codex_review_notes": aggregate["notes"],
            "next_step": "Review the aggregate patch and specialist findings before applying changes.",
        }

    def _execute_readonly_batch(self, workspace: Path, base_files: List[str],
                                nodes: List[WorkGraphNode], max_parallel_workers: int) -> List[Dict[str, Any]]:
        context_files = base_files or [path for node in nodes for path in node.allowed_files]
        context = ContextPacker(workspace=str(workspace)).load(context_files)
        max_workers = min(max(1, max_parallel_workers), max(1, len(nodes)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(lambda node: self._run_readonly_node(node, context), nodes))

    def _execute_patch_batch(self, workspace: Path, base_files: List[str],
                             nodes: List[WorkGraphNode], max_parallel_workers: int) -> Dict[str, Any]:
        max_workers = min(max(1, max_parallel_workers), max(1, len(nodes)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(
                lambda node: self._run_patch_node(node, str(workspace), base_files),
                nodes,
            ))
        failed = [item for item in results if item["status"] != "success"]
        if failed:
            return {
                "status": "needs_codex",
                "summary": "One or more patch specialists failed verification.",
                "results": results,
            }
        aggregate = self.aggregator.aggregate(results)
        if not aggregate.ok:
            return {
                "status": "needs_codex",
                "summary": "Patch aggregation found overlapping file writes.",
                "results": results,
            }
        try:
            self._apply_results_to_workspace(workspace, results)
        except RuntimeError as e:
            return {
                "status": "needs_codex",
                "summary": f"Patch aggregation could not be materialized safely: {e}",
                "results": results,
            }
        return {
            "status": "success",
            "results": results,
        }

    def _execute_readonly_graph(self, request: OrchestrateTaskInput,
                                nodes: List[WorkGraphNode]) -> Dict[str, Any]:
        context = ContextPacker(workspace=request.workspace).load(request.files)
        max_workers = min(max(1, request.max_parallel_workers), max(1, len(nodes)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(lambda node: self._run_readonly_node(node, context), nodes))

        failed = [item for item in results if item["status"] != "success"]
        if failed:
            return {
                "route": "codex",
                "status": "needs_codex",
                "summary": "One or more readonly specialists failed; Codex should take over.",
                "results": results,
                "metrics": {
                    "node_count": len(nodes),
                    "worker_calls": len(results),
                    "estimated_savings_percent": 0,
                },
                "next_step": "Review the failing specialist result and continue in Codex.",
            }

        specialist_summaries = [
            f"{item['specialist']}: {item['summary']}" for item in results
        ]
        review_notes = []
        for item in results:
            review_notes.extend(item.get("risk_notes", []))
        return {
            "route": "deepseek",
            "status": "success",
            "summary": "Readonly specialists completed in parallel.",
            "results": results,
            "aggregate_patch": "",
            "changed_files": [],
            "checks": [],
            "verification": {
                "ok": True,
                "fallback_to_codex": False,
                "reason": "Readonly specialists completed without patch generation.",
                "warnings": [],
                "executed_commands": [],
            },
            "metrics": {
                "node_count": len(nodes),
                "worker_calls": len(results),
                "estimated_savings_percent": self._estimate_savings(len(nodes)),
            },
            "codex_review_notes": review_notes,
            "combined_summary": specialist_summaries,
            "next_step": "Review the readonly findings and decide whether to continue with bounded patch execution.",
        }

    def _run_readonly_node(self, node: WorkGraphNode, context: List[FileContext]) -> Dict[str, Any]:
        profile = self.registry.get(node.specialist)
        try:
            client = ProviderClient(provider=profile.provider, model=profile.model)
            response = client.complete_json(
                _readonly_system_prompt(profile.name),
                {
                    "specialist": profile.name,
                    "goal": node.goal,
                    "acceptance_criteria": node.acceptance_criteria,
                    "context": [to_dict(item) for item in context],
                },
            )
        except ProviderError as e:
            return {
                "node_id": node.id,
                "specialist": profile.name,
                "status": "failed",
                "summary": f"{profile.name} failed: {e}",
                "findings": [],
                "risk_notes": [str(e)],
            }
        return {
            "node_id": node.id,
            "specialist": profile.name,
            "status": response.get("status", "failed"),
            "summary": str(response.get("summary", "")),
            "findings": list(response.get("findings", [])),
            "risk_notes": list(response.get("risk_notes", [])),
        }

    def _run_patch_node(self, node: WorkGraphNode, workspace: str,
                        base_files: List[str]) -> Dict[str, Any]:
        profile = self.registry.get(node.specialist)
        context_files = list(dict.fromkeys((base_files or []) + node.allowed_files))
        try:
            runtime = WorkPacketRuntime(ProviderClient(provider=profile.provider, model=profile.model))
            result = runtime.run(WorkPacketInput(
                goal=node.goal,
                files=context_files,
                constraints=_specialist_constraints(profile.name),
                acceptance_criteria=node.acceptance_criteria,
                allowed_files=node.allowed_files,
                forbidden_paths=node.forbidden_paths,
                allowed_commands=node.allowed_commands,
                workspace=workspace,
                delegation_level="repair_loop" if node.allowed_commands else "bounded_impl",
                max_iterations=3,
                max_diff_lines=300,
            ))
        except ProviderError as e:
            return {
                "node_id": node.id,
                "specialist": profile.name,
                "status": "failed",
                "summary": f"{profile.name} failed: {e}",
                "changed_files": [],
                "patch": "",
                "checks": [],
                "risk_notes": [str(e)],
            }
        result["node_id"] = node.id
        result["specialist"] = profile.name
        return result

    def _copy_workspace(self, workspace: Path) -> Path:
        target = Path(tempfile.mkdtemp(prefix="codexsaver-v3-"))
        shutil.copytree(
            workspace,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git", ".omx", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", "node_modules", "*.pyc", "*.pyo",
            ),
        )
        return target

    def _apply_results_to_workspace(self, workspace: Path, results: List[Dict[str, Any]]) -> None:
        for item in results:
            self._materialize_patch_effects(str(workspace), item)

    def _materialize_patch_effects(self, workspace: str, result: Dict[str, Any]) -> None:
        packet = WorkPacketInput(
            goal=result.get("summary", ""),
            files=[],
            constraints=[],
            acceptance_criteria=[],
            allowed_files=result.get("changed_files", []),
            forbidden_paths=[],
            allowed_commands=[],
            workspace=workspace,
        )
        from .work_packet import PatchSandbox  # local import to avoid expanding public surface

        patch_sandbox = PatchSandbox(Path(workspace).resolve(), packet)
        observation = patch_sandbox.propose_patch(str(result.get("patch", "")))
        if observation["type"] != "patch_applied" or patch_sandbox.tempdir is None:
            raise RuntimeError(f"Failed to apply node patch to aggregate workspace: {result.get('specialist')}")
        workspace_path = Path(workspace)
        shutil.rmtree(workspace_path)
        shutil.copytree(patch_sandbox.tempdir, workspace_path, dirs_exist_ok=True)

    def _build_final_aggregate_patch(self, original_workspace: Path, current_workspace: Path,
                                     patch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        changed_files = list(dict.fromkeys(
            path for item in patch_results for path in item.get("changed_files", [])
        ))
        patches: List[str] = []
        notes: List[str] = []
        for rel in changed_files:
            original = original_workspace / rel
            current = current_workspace / rel
            old_text = original.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if original.exists() else []
            new_text = current.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if current.exists() else []
            diff = "".join(difflib.unified_diff(
                old_text,
                new_text,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            ))
            if diff:
                patches.append(diff)
        if not patches:
            notes.append("No aggregate patch was produced after executing patch nodes.")
        return {
            "patch": "".join(patches).strip(),
            "changed_files": changed_files,
            "notes": notes,
        }

    def _needs_codex(self, summary: str, preview: Dict[str, Any], results: List[Dict[str, Any]],
                     node_count: int) -> Dict[str, Any]:
        return {
            "route": "codex",
            "status": "needs_codex",
            "summary": summary,
            "graph": preview,
            "results": results,
            "metrics": {
                "node_count": node_count,
                "worker_calls": len(results),
                "estimated_savings_percent": 0,
            },
            "next_step": "Review partial specialist output and continue in Codex.",
        }

    def _estimate_savings(self, node_count: int) -> int:
        if node_count <= 1:
            return 45
        if node_count == 2:
            return 52
        return 58


def _readonly_system_prompt(specialist_name: str) -> str:
    if specialist_name == "perf_reviewer":
        role = "You are CodexSaver's readonly performance reviewer."
    else:
        role = "You are CodexSaver's readonly code explainer."
    return (
        f"{role}\n\n"
        "Return valid JSON only. No markdown fences.\n"
        "Do not propose patches.\n"
        "Do not claim changes were made.\n"
        "Keep output concise and specific to the provided files.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "status": "success | needs_codex | failed",\n'
        '  "summary": "short summary",\n'
        '  "findings": ["short note"],\n'
        '  "risk_notes": ["short note"]\n'
        "}\n"
    )


def _specialist_constraints(specialist_name: str) -> List[str]:
    if specialist_name == "test_writer":
        return [
            "Generate or update focused tests only.",
            "Prefer pytest for Python and Jest-style structure for JS/TS.",
            "Cover normal path, edge cases, and one failure path when practical.",
        ]
    if specialist_name == "doc_writer":
        return [
            "Add concise inline docs, docstrings, or README text only.",
            "Do not change runtime behavior unless documentation must match an existing implementation.",
        ]
    if specialist_name == "impl_worker":
        return [
            "Implement only the bounded requested behavior.",
            "Prefer minimal reviewable changes and avoid unrelated refactors.",
        ]
    return []
