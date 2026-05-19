# CodexSaver v3.6 Pi Agent Benchmark — 2026-05-19

This benchmark runs five real readonly orchestration tasks on the current repository.
Worker cost is measured from Pi/DeepSeek usage events; Codex baseline cost is estimated from the same token volume.

## Summary

- `tasks`: `5`
- `successes`: `5`
- `success_rate`: `1.0`
- `average_latency_seconds`: `18.63`
- `total_worker_cost_usd`: `0.00968315`
- `estimated_codex_baseline_cost_usd`: `0.47955374`
- `estimated_savings_percent`: `98`
- `average_quality_score`: `1.0`
- `average_worker_participation_percent`: `100`

## Results

| Task | Status | Latency | Worker cost | Baseline cost | Savings | Quality | Worker participation |
|---|---:|---:|---:|---:|---:|---:|---:|
| Config explanation + performance review | `success` | 14.62s | $0.00161269 | $0.07753500 | 98% | 1.0 | 100% |
| Work packet sandbox risk review | `success` | 17.48s | $0.00236977 | $0.10714500 | 98% | 1.0 | 100% |
| Orchestrator routing review | `success` | 30.55s | $0.00244683 | $0.13920750 | 98% | 1.0 | 100% |
| Installer flow review | `success` | 13.33s | $0.00189657 | $0.08991562 | 98% | 1.0 | 100% |
| MCP server protocol review | `success` | 17.16s | $0.00135729 | $0.06575062 | 98% | 1.0 | 100% |

## Interpretation

- v3.6 is strongest on readonly specialist orchestration: explanation, review, risk notes, and performance hints.
- The measured worker cost is tiny because Pi routes to `deepseek-v4-flash` for this lane.
- The current benchmark does not claim patch-writing superiority; it validates the low-risk, high-signal specialist lane.
- Codex still owns final judgment and any code application.

Baseline note: Codex baseline cost is estimated from observed worker tokens using a conservative $1.25/M input + $10/M output blended index of $5.625/M total tokens. Worker cost is reported by Pi/DeepSeek usage events.
