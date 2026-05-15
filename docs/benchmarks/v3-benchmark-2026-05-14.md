# CodexSaver v3 Benchmark

Date: 2026-05-14

Method: Codex-only is a normalized counterfactual baseline with cost index 1.00. CodexSaver v3 results are real orchestration runs over fixture workspaces.

| Task | Kind | Route | Status | Cost | Savings | Nodes | Workers | Latency |
|---|---|---|---|---:|---:|---:|---:|---:|
| Readonly explain and perf review | readonly_swarm | codex | needs_codex | 1.00 | 0% | 2 | 2 | 3.71s |
| Implement login and add tests | impl_plus_tests | codex | needs_codex | 1.00 | 0% | 2 | 1 | 10.75s |
| Implement parser, add docs, and explain risk | impl_docs_explain | deepseek | success | 0.42 | 58% | 3 | 3 | 16.21s |
