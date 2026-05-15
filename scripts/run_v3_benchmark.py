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
        "name": "Readonly explain and perf review",
        "kind": "readonly_swarm",
        "goal": "Explain analytics logic and review performance",
        "files": ["src/analytics.py"],
    },
    {
        "name": "Implement login and add tests",
        "kind": "impl_plus_tests",
        "goal": "Implement login and add tests",
        "files": ["src/user_auth.py"],
    },
    {
        "name": "Implement parser, add docs, and explain risk",
        "kind": "impl_docs_explain",
        "goal": "Implement parse_v3_config, add docs, and explain risk",
        "files": ["src/v3_config.py"],
    },
]


def main() -> int:
    engine = CodexSaverEngine()
    with tempfile.TemporaryDirectory(prefix="codexsaver-v3-bench-") as tmpdir:
        workspace = Path(tmpdir)
        prepare_fixture_workspace(workspace)
        results: List[Dict[str, Any]] = []
        for task in TASKS:
            started = time.perf_counter()
            result = engine.orchestrate_task({
                "goal": task["goal"],
                "files": task["files"],
                "workspace": str(workspace),
            })
            elapsed = time.perf_counter() - started
            metrics = result.get("metrics", {})
            results.append({
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
                    "cost_index": (
                        round(1 - int(metrics.get("estimated_savings_percent", 0)) / 100, 2)
                        if result.get("status") == "success" else 1.0
                    ),
                    "estimated_savings_percent": int(metrics.get("estimated_savings_percent", 0) or 0),
                    "latency_seconds": round(elapsed, 2),
                    "node_count": metrics.get("node_count"),
                    "readonly_nodes": metrics.get("readonly_nodes", 0),
                    "patch_nodes": metrics.get("patch_nodes", 0),
                    "worker_calls": metrics.get("worker_calls", 0),
                    "summary": result.get("summary"),
                    "verification": result.get("verification"),
                    "changed_files": result.get("changed_files", []),
                },
            })
        write_reports(results)
        print(json.dumps({"status": "ok", "results": results}, ensure_ascii=False, indent=2))
    return 0


def prepare_fixture_workspace(workspace: Path) -> None:
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text("# CodexSaver v3 Fixture\n", encoding="utf-8")
    (workspace / "src" / "analytics.py").write_text(
        "def load_scores(items):\n"
        "    results = []\n"
        "    for item in items:\n"
        "        score = 0\n"
        "        for inner in items:\n"
        "            if inner == item:\n"
        "                score += 1\n"
        "        results.append(score)\n"
        "    return results\n",
        encoding="utf-8",
    )
    (workspace / "src" / "user_auth.py").write_text(
        "def login(username, password):\n"
        "    raise NotImplementedError('implement me')\n",
        encoding="utf-8",
    )
    (workspace / "src" / "v3_config.py").write_text(
        "def parse_v3_config(path):\n"
        "    raise NotImplementedError('implement me')\n",
        encoding="utf-8",
    )
    shutil.copy(ROOT / "pyproject.toml", workspace / "pyproject.toml")


def write_reports(results: List[Dict[str, Any]]) -> None:
    out_dir = ROOT / "docs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    json_path = out_dir / f"v3-benchmark-{today}.json"
    md_path = out_dir / f"v3-benchmark-{today}.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CodexSaver v3 Benchmark",
        "",
        f"Date: {today}",
        "",
        "Method: Codex-only is a normalized counterfactual baseline with cost index 1.00. "
        "CodexSaver v3 results are real orchestration runs over fixture workspaces.",
        "",
        "| Task | Kind | Route | Status | Cost | Savings | Nodes | Workers | Latency |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        cs = item["codexsaver_v3"]
        lines.append(
            f"| {item['name']} | {item['kind']} | {cs['route']} | {cs['status']} | "
            f"{cs['cost_index']:.2f} | {cs['estimated_savings_percent']}% | "
            f"{cs['node_count'] or 0} | {cs['worker_calls'] or 0} | {cs['latency_seconds']:.2f}s |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
