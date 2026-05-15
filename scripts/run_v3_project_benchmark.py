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
        "name": "Explain installer flow and review performance",
        "kind": "readonly_swarm",
        "goal": "Explain installer workflow and review performance",
        "files": ["codexsaver/installer.py"],
    },
    {
        "name": "Document installer profile flow and explain risk",
        "kind": "docs_plus_explain",
        "goal": "Document install_superpower_profile and explain risk",
        "files": ["codexsaver/installer.py"],
    },
    {
        "name": "Generate tests for installer profile behavior",
        "kind": "tests_only",
        "goal": "Test install_superpower_profile behavior",
        "files": ["codexsaver/installer.py"],
    },
    {
        "name": "Implement ledger helper, add docs, and explain risk",
        "kind": "impl_docs_explain",
        "goal": "Implement ledger summary normalization helper, add docs, and explain risk",
        "files": ["codexsaver/ledger.py"],
    },
    {
        "name": "Implement ledger normalization and add tests",
        "kind": "impl_plus_tests",
        "goal": "Implement ledger summary normalization and add tests",
        "files": ["codexsaver/ledger.py"],
    },
]


def main() -> int:
    engine = CodexSaverEngine()
    results: List[Dict[str, Any]] = []
    for task in TASKS:
        with tempfile.TemporaryDirectory(prefix="codexsaver-v3-project-") as tmpdir:
            workspace = Path(tmpdir) / "repo"
            copy_workspace(ROOT, workspace)
            started = time.perf_counter()
            try:
                result = engine.orchestrate_task({
                    "goal": task["goal"],
                    "files": task["files"],
                    "workspace": str(workspace),
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
                    },
                    "verification": None,
                    "changed_files": [],
                    "results": [],
                }
            elapsed = time.perf_counter() - started
            results.append(record_result(task, result, elapsed))
    write_reports(results)
    print(json.dumps({"status": "ok", "results": results}, ensure_ascii=False, indent=2))
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
    success = result.get("status") == "success"
    if success:
        cost_index = round(1 - int(metrics.get("estimated_savings_percent", 0)) / 100, 2)
    else:
        cost_index = 1.0
    quality_score = 0.0
    quality_notes: List[str] = []
    if success and verification and verification.get("ok"):
        quality_score += 0.5
        quality_notes.append("verification passed")
    if readonly_findings > 0:
        quality_score += 0.25
        quality_notes.append(f"{readonly_findings} readonly findings")
    if changed_files:
        quality_score += 0.15
        quality_notes.append(f"{len(changed_files)} changed files")
    if checks and all(item.get("exit_code") == 0 for item in checks):
        quality_score += 0.10
        quality_notes.append("allowlisted checks passed")
    quality_score = min(1.0, round(quality_score, 2))
    return {
        "name": task["name"],
        "kind": task["kind"],
        "codex_only": {
            "cost_index": 1.0,
            "effect": "counterfactual_baseline",
            "notes": "Codex-only is a normalized baseline and was not executed separately.",
        },
        "codexsaver_v3": {
            "route": result.get("route"),
            "status": result.get("status"),
            "summary": result.get("summary"),
            "cost_index": cost_index,
            "estimated_savings_percent": int(metrics.get("estimated_savings_percent", 0) or 0),
            "latency_seconds": round(elapsed, 2),
            "node_count": metrics.get("node_count"),
            "readonly_nodes": metrics.get("readonly_nodes", 0),
            "patch_nodes": metrics.get("patch_nodes", 0),
            "worker_calls": metrics.get("worker_calls", 0),
            "changed_files": changed_files,
            "readonly_findings": readonly_findings,
            "quality_score": quality_score,
            "quality_notes": quality_notes,
            "verification": verification,
        },
    }


def write_reports(results: List[Dict[str, Any]]) -> None:
    out_dir = ROOT / "docs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    json_path = out_dir / f"v3-project-benchmark-{today}.json"
    md_path = out_dir / f"v3-project-benchmark-{today}.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CodexSaver v3 Project Benchmark",
        "",
        f"Date: {today}",
        "",
        "Method: each task ran against a temporary copy of the current CodexSaver repository. "
        "Codex-only is a normalized counterfactual baseline with cost index 1.00.",
        "",
        "| Task | Kind | Route | Status | Cost | Savings | Quality | Nodes | Workers | Latency |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        cs = item["codexsaver_v3"]
        lines.append(
            f"| {item['name']} | {item['kind']} | {cs['route']} | {cs['status']} | "
            f"{cs['cost_index']:.2f} | {cs['estimated_savings_percent']}% | {cs['quality_score']:.2f} | "
            f"{cs['node_count'] or 0} | {cs['worker_calls'] or 0} | {cs['latency_seconds']:.2f}s |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
