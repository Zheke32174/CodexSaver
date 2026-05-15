# CodexSaver v3 Project Benchmark

Date: 2026-05-15

Method: each task ran against a temporary copy of the current CodexSaver repository. Codex-only is a normalized counterfactual baseline with cost index 1.00.

| Task | Kind | Route | Status | Cost | Savings | Quality | Nodes | Workers | Latency |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Explain installer flow and review performance | readonly_swarm | deepseek | success | 0.48 | 52% | 0.75 | 2 | 2 | 6.45s |
| Document installer profile flow and explain risk | docs_plus_explain | deepseek | success | 0.48 | 52% | 0.90 | 2 | 2 | 42.51s |
| Generate tests for installer profile behavior | tests_only | codex | needs_codex | 1.00 | 0% | 0.00 | 1 | 1 | 0.71s |
| Implement ledger helper, add docs, and explain risk | impl_docs_explain | codex | needs_codex | 1.00 | 0% | 0.00 | 3 | 1 | 5.02s |
| Implement ledger normalization and add tests | impl_plus_tests | codex | needs_codex | 1.00 | 0% | 0.00 | 2 | 2 | 22.26s |
