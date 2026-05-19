#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from codexsaver.engine import CodexSaverEngine


WORKSPACE = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
OUT_JSON = WORKSPACE / "docs" / "benchmarks" / f"v36-pi-agent-benchmark-{TODAY}.json"
OUT_MD = WORKSPACE / "docs" / "benchmarks" / f"v36-pi-agent-benchmark-{TODAY}.md"


TASKS = [
    {
        "name": "Config explanation + performance review",
        "goal": "Explain config loader logic and review performance",
        "files": ["codexsaver/config.py"],
        "expected": ["provider", "config", "performance"],
    },
    {
        "name": "Work packet sandbox risk review",
        "goal": "Explain work packet sandbox flow and review performance risk",
        "files": ["codexsaver/work_packet.py"],
        "expected": ["sandbox", "patch", "risk"],
    },
    {
        "name": "Orchestrator routing review",
        "goal": "Explain v3 orchestrator routing logic and review performance",
        "files": ["codexsaver/orchestrator.py"],
        "expected": ["routing", "worker", "graph"],
    },
    {
        "name": "Installer flow review",
        "goal": "Explain installer flow and review performance",
        "files": ["codexsaver/installer.py"],
        "expected": ["install", "config", "global"],
    },
    {
        "name": "MCP server protocol review",
        "goal": "Explain MCP server tool dispatch and review performance",
        "files": ["codexsaver_mcp.py"],
        "expected": ["mcp", "tool", "json"],
    },
]


def main() -> int:
    engine = CodexSaverEngine()
    results: List[Dict[str, Any]] = []
    for task in TASKS:
        start = time.perf_counter()
        result = engine.orchestrate_task({
            "goal": task["goal"],
            "files": task["files"],
            "workspace": str(WORKSPACE),
            "max_parallel_workers": 2,
        })
        latency = time.perf_counter() - start
        worker_cost = total_worker_cost(result)
        worker_tokens = total_worker_tokens(result)
        baseline_cost = estimate_codex_cost(worker_tokens)
        quality = quality_score(result, task["expected"])
        results.append({
            "name": task["name"],
            "goal": task["goal"],
            "files": task["files"],
            "route": result.get("route"),
            "status": result.get("status"),
            "latency_seconds": round(latency, 2),
            "worker_calls": result.get("metrics", {}).get("worker_calls", 0),
            "worker_participation_percent": result.get("metrics", {}).get("worker_participation_percent", 0),
            "worker_cost_usd": round(worker_cost, 8),
            "worker_tokens": worker_tokens,
            "codex_baseline_cost_usd": round(baseline_cost, 8),
            "estimated_savings_percent": savings(worker_cost, baseline_cost),
            "quality_score": quality,
            "findings_count": sum(len(item.get("findings", [])) for item in result.get("results", [])),
            "risk_notes_count": sum(len(item.get("risk_notes", [])) for item in result.get("results", [])),
            "model": sorted(set(
                item.get("worker_model", "")
                for item in result.get("results", [])
                if item.get("worker_model")
            )),
            "summary": result.get("summary", ""),
        })

    payload = {
        "version": "0.3.6",
        "date": TODAY,
        "benchmark": "v36-pi-agent-real-tasks",
        "workspace": str(WORKSPACE),
        "baseline_note": (
            "Codex baseline cost is estimated from observed worker tokens using a conservative "
            "$1.25/M input + $10/M output blended index of $5.625/M total tokens. "
            "Worker cost is reported by Pi/DeepSeek usage events."
        ),
        "summary": summarize(results),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "json": str(OUT_JSON),
        "markdown": str(OUT_MD),
        "summary": payload["summary"],
    }, ensure_ascii=False, indent=2))
    return 0


def total_worker_cost(result: Dict[str, Any]) -> float:
    total = 0.0
    for item in result.get("results", []):
        cost = item.get("worker_usage", {}).get("cost", {})
        if isinstance(cost, dict):
            total += float(cost.get("total", 0) or 0)
    return total


def total_worker_tokens(result: Dict[str, Any]) -> int:
    return sum(
        int(item.get("worker_usage", {}).get("totalTokens", 0) or 0)
        for item in result.get("results", [])
    )


def estimate_codex_cost(tokens: int) -> float:
    return tokens / 1_000_000 * 5.625


def savings(worker_cost: float, baseline_cost: float) -> int:
    if baseline_cost <= 0:
        return 0
    return round(max(0.0, 1 - worker_cost / baseline_cost) * 100)


def quality_score(result: Dict[str, Any], expected: List[str]) -> float:
    if result.get("status") != "success":
        return 0.0
    text = json.dumps(result.get("results", []), ensure_ascii=False).lower()
    keyword_score = sum(1 for item in expected if item.lower() in text) / max(1, len(expected))
    findings = sum(len(item.get("findings", [])) for item in result.get("results", []))
    risk_notes = sum(len(item.get("risk_notes", [])) for item in result.get("results", []))
    evidence_score = min(1.0, findings / 6)
    risk_score = min(1.0, risk_notes / 2)
    return round(0.45 * keyword_score + 0.40 * evidence_score + 0.15 * risk_score, 2)


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    count = len(results)
    successes = [item for item in results if item["status"] == "success"]
    total_worker_cost = sum(item["worker_cost_usd"] for item in results)
    total_baseline_cost = sum(item["codex_baseline_cost_usd"] for item in results)
    return {
        "tasks": count,
        "successes": len(successes),
        "success_rate": round(len(successes) / max(1, count), 2),
        "average_latency_seconds": round(sum(item["latency_seconds"] for item in results) / max(1, count), 2),
        "total_worker_cost_usd": round(total_worker_cost, 8),
        "estimated_codex_baseline_cost_usd": round(total_baseline_cost, 8),
        "estimated_savings_percent": savings(total_worker_cost, total_baseline_cost),
        "average_quality_score": round(sum(item["quality_score"] for item in results) / max(1, count), 2),
        "average_worker_participation_percent": round(
            sum(item["worker_participation_percent"] for item in results) / max(1, count)
        ),
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        f"# CodexSaver v3.6 Pi Agent Benchmark — {payload['date']}",
        "",
        "This benchmark runs five real readonly orchestration tasks on the current repository.",
        "Worker cost is measured from Pi/DeepSeek usage events; Codex baseline cost is estimated from the same token volume.",
        "",
        "## Summary",
        "",
    ]
    summary = payload["summary"]
    for key, value in summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Results",
        "",
        "| Task | Status | Latency | Worker cost | Baseline cost | Savings | Quality | Worker participation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in payload["results"]:
        lines.append(
            f"| {item['name']} | `{item['status']}` | {item['latency_seconds']}s | "
            f"${item['worker_cost_usd']:.8f} | ${item['codex_baseline_cost_usd']:.8f} | "
            f"{item['estimated_savings_percent']}% | {item['quality_score']} | "
            f"{item['worker_participation_percent']}% |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- v3.6 is strongest on readonly specialist orchestration: explanation, review, risk notes, and performance hints.",
        "- The measured worker cost is tiny because Pi routes to `deepseek-v4-flash` for this lane.",
        "- The current benchmark does not claim patch-writing superiority; it validates the low-risk, high-signal specialist lane.",
        "- Codex still owns final judgment and any code application.",
        "",
        f"Baseline note: {payload['baseline_note']}",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
