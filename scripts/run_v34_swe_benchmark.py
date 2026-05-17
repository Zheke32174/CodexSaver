#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from codexsaver.engine import CodexSaverEngine


TASKS: List[Dict[str, Any]] = [
    {
        "name": "Readonly route and performance triage",
        "kind": "readonly_swarm",
        "goal": "Explain the v3 work graph planner and review performance risks",
        "files": ["codexsaver/work_graph.py"],
    },
    {
        "name": "Safe database import workflow planning",
        "kind": "safe_data_workflow",
        "goal": (
            "Rebuild database schema and write imported OCR text into lessons. "
            "Use safe preparation only; do not execute writes."
        ),
        "files": ["codexsaver/work_packet.py"],
    },
    {
        "name": "Policy docs plus risk explanation",
        "kind": "docs_plus_explain",
        "goal": "Document the action-level delegation policy and explain risk",
        "files": ["codexsaver/policy.py"],
    },
    {
        "name": "Ledger participation tests",
        "kind": "tests_only",
        "goal": "Add focused tests for DeepSeek participation summary in CostLedger",
        "files": ["codexsaver/ledger.py"],
    },
    {
        "name": "Provider preset docs and verification notes",
        "kind": "docs_plus_explain",
        "goal": "Update provider preset docs and explain OpenCode Go verification risk",
        "files": ["README.md"],
    },
    {
        "name": "Config helper implementation with tests",
        "kind": "impl_plus_tests",
        "goal": "Implement a small config helper and add tests",
        "files": ["codexsaver/config.py"],
    },
]


def main() -> int:
    engine = CodexSaverEngine()
    results: List[Dict[str, Any]] = []
    for task in TASKS:
        with tempfile.TemporaryDirectory(prefix="codexsaver-v34-swe-") as tmpdir:
            workspace = Path(tmpdir) / "repo"
            copy_workspace(ROOT, workspace)
            started = time.perf_counter()
            try:
                result = engine.orchestrate_task({
                    "goal": task["goal"],
                    "files": task["files"],
                    "workspace": str(workspace),
                    "max_parallel_workers": 4,
                })
            except Exception as e:
                result = {
                    "route": "codex",
                    "status": "failed",
                    "summary": f"benchmark runner error: {e}",
                    "metrics": {
                        "estimated_savings_percent": 0,
                        "node_count": 0,
                        "readonly_nodes": 0,
                        "patch_nodes": 0,
                        "worker_calls": 0,
                        "deepseek_participation_percent": 0,
                    },
                    "verification": None,
                    "changed_files": [],
                    "results": [],
                    "handoff": None,
                }
            elapsed = time.perf_counter() - started
            results.append(record_result(task, result, elapsed))
    write_reports(results)
    print(json.dumps({"status": "ok", "summary": summarize(results), "results": results}, ensure_ascii=False, indent=2))
    return 0


def copy_workspace(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git", ".omx", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache",
            "node_modules", "*.pyc", "*.pyo",
        ),
    )


def record_result(task: Dict[str, Any], result: Dict[str, Any], elapsed: float) -> Dict[str, Any]:
    metrics = result.get("metrics", {})
    verification = result.get("verification")
    changed_files = result.get("changed_files", [])
    readonly_findings = sum(len(item.get("findings", [])) for item in result.get("results", []))
    checks = result.get("checks", [])
    participation = int(metrics.get("deepseek_participation_percent", 0) or 0)
    success = result.get("status") == "success"
    cost_index = round(1 - int(metrics.get("estimated_savings_percent", 0)) / 100, 2) if success else 1.0
    quality_score = score_quality(success, verification, readonly_findings, changed_files, checks, participation)
    return {
        "name": task["name"],
        "kind": task["kind"],
        "codex_only": {
            "cost_index": 1.0,
            "participation_percent": 0,
            "effect": "counterfactual_baseline",
        },
        "codexsaver_v34": {
            "route": result.get("route"),
            "status": result.get("status"),
            "summary": result.get("summary"),
            "cost_index": cost_index,
            "estimated_savings_percent": int(metrics.get("estimated_savings_percent", 0) or 0),
            "latency_seconds": round(elapsed, 2),
            "node_count": metrics.get("node_count", 0),
            "readonly_nodes": metrics.get("readonly_nodes", 0),
            "patch_nodes": metrics.get("patch_nodes", 0),
            "worker_calls": metrics.get("worker_calls", 0),
            "deepseek_participation_percent": participation,
            "changed_files": changed_files,
            "readonly_findings": readonly_findings,
            "quality_score": quality_score,
            "verification": verification,
            "blocked_actions": result.get("blocked_actions", []),
            "codex_next_actions": result.get("codex_next_actions", []),
            "partial_delegation": bool(result.get("partial_delegation")),
            "handoff": result.get("handoff"),
        },
    }


def score_quality(success: bool, verification: Dict[str, Any] | None,
                  readonly_findings: int, changed_files: List[str],
                  checks: List[Dict[str, Any]], participation: int) -> float:
    score = 0.0
    if success and verification and verification.get("ok"):
        score += 0.45
    if readonly_findings:
        score += 0.20
    if changed_files:
        score += 0.15
    if checks and all(item.get("exit_code") == 0 for item in checks):
        score += 0.10
    if participation >= 50:
        score += 0.10
    return min(1.0, round(score, 2))


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {}
    participation_values = [
        item["codexsaver_v34"]["deepseek_participation_percent"]
        for item in results
    ]
    successes = [
        item for item in results
        if item["codexsaver_v34"]["status"] == "success"
    ]
    return {
        "tasks": len(results),
        "successes": len(successes),
        "average_deepseek_participation_percent": round(sum(participation_values) / len(participation_values), 1),
        "tasks_at_or_above_50_percent": sum(1 for value in participation_values if value >= 50),
        "average_latency_seconds": round(sum(item["codexsaver_v34"]["latency_seconds"] for item in results) / len(results), 2),
        "average_quality_score": round(sum(item["codexsaver_v34"]["quality_score"] for item in results) / len(results), 2),
        "average_cost_index": round(sum(item["codexsaver_v34"]["cost_index"] for item in results) / len(results), 2),
    }


def write_reports(results: List[Dict[str, Any]]) -> None:
    out_dir = ROOT / "docs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    json_path = out_dir / f"v34-swe-benchmark-{today}.json"
    md_path = out_dir / f"v34-swe-benchmark-{today}.md"
    summary = summarize(results)
    json_path.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# CodexSaver v3.4 SWE-Style Benchmark",
        "",
        f"Date: {today}",
        "",
        "Method: each task ran against a temporary copy of the current CodexSaver repository. "
        "Tasks are SWE-style local maintenance tasks: triage, docs, tests, config changes, and safe data workflow planning. "
        "Codex-only is a normalized counterfactual baseline with cost index 1.00.",
        "",
        "## Summary",
        "",
        f"- Tasks: `{summary['tasks']}`",
        f"- Successes: `{summary['successes']}`",
        f"- Average DeepSeek participation: `{summary['average_deepseek_participation_percent']}%`",
        f"- Tasks at or above 50% DeepSeek participation: `{summary['tasks_at_or_above_50_percent']}/{summary['tasks']}`",
        f"- Average cost index: `{summary['average_cost_index']}`",
        f"- Average latency: `{summary['average_latency_seconds']}s`",
        f"- Average quality score: `{summary['average_quality_score']}`",
        "",
        "## Results",
        "",
        "| Task | Kind | Route | Status | DeepSeek % | Cost | Savings | Quality | Workers | Latency |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        cs = item["codexsaver_v34"]
        lines.append(
            f"| {item['name']} | {item['kind']} | {cs['route']} | {cs['status']} | "
            f"{cs['deepseek_participation_percent']}% | {cs['cost_index']:.2f} | "
            f"{cs['estimated_savings_percent']}% | {cs['quality_score']:.2f} | "
            f"{cs['worker_calls'] or 0} | {cs['latency_seconds']:.2f}s |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
