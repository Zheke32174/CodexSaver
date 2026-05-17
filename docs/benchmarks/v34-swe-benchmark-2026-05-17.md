# CodexSaver v3.4 SWE-Style Benchmark

Date: 2026-05-17

Method: each task ran against a temporary copy of the current CodexSaver repository. Tasks are SWE-style local maintenance tasks: triage, docs, tests, config changes, and safe data workflow planning. Codex-only is a normalized counterfactual baseline with cost index 1.00.

## Summary

- Tasks: `6`
- Successes: `2`
- Average DeepSeek participation: `55.7%`
- Tasks at or above 50% DeepSeek participation: `5/6`
- Average cost index: `0.83`
- Average latency: `24.82s`
- Average quality score: `0.39`

## Results

| Task | Kind | Route | Status | DeepSeek % | Cost | Savings | Quality | Workers | Latency |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Readonly route and performance triage | readonly_swarm | deepseek | success | 100% | 0.48 | 52% | 0.75 | 2 | 6.12s |
| Safe database import workflow planning | safe_data_workflow | deepseek | success | 67% | 0.48 | 52% | 0.90 | 2 | 30.54s |
| Policy docs plus risk explanation | docs_plus_explain | codex | needs_codex | 50% | 1.00 | 0% | 0.30 | 2 | 33.38s |
| Ledger participation tests | tests_only | codex | needs_codex | 50% | 1.00 | 0% | 0.10 | 2 | 28.49s |
| Provider preset docs and verification notes | docs_plus_explain | codex | needs_codex | 67% | 1.00 | 0% | 0.30 | 3 | 13.94s |
| Config helper implementation with tests | impl_plus_tests | codex | needs_codex | 0% | 1.00 | 0% | 0.00 | 1 | 36.45s |
