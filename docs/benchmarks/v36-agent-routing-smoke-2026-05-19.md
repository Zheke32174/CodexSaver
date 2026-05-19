# CodexSaver v3.6 Agent Routing Smoke Test — 2026-05-19

This smoke test verifies the first v3.6 slice: builtin Pi Agent discovery,
weighted worker routing, and task lifecycle metadata.

## Scope

v3.6 does not add a heavy multi-agent framework. It makes Pi Agent the default
v3 worker and adds a small dynamic worker selection layer for any compatible
local worker exposed through an Agent Card.

## Commands

```bash
python -m pytest tests/test_v3.py tests/test_v36.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
python cli.py agents list --workspace .
python cli.py orchestrate "Explain config loader logic and review performance" --files codexsaver/config.py --dry-run
codexsaver specialist explainer "Return a short JSON summary for config.py" --files codexsaver/config.py --workspace /Users/f/GitHub/CodexSaver
python cli.py orchestrate "Explain config loader logic and review performance" --files codexsaver/config.py --workspace .
```

## Results

| Check | Result |
|---|---:|
| Targeted tests | `22 passed in 0.20s` |
| Full test suite | `133 passed in 0.63s` |
| Discovered builtin Agent Card | yes |
| Dynamic routing visible in dry-run graph | yes |
| Weighted route score for readonly Python nodes | `0.98` |
| Live Pi Agent specialist | `route=pi_agent`, `status=success` |
| Live Pi Agent readonly swarm | `route=pi_agent`, `status=success`, `worker_participation_percent=100` |
| Task model implemented | `submitted -> running -> completed/failed/timed_out` |
| DeepSeek silent fallback | removed; v3.6 uses Pi CLI with DeepSeek provider explicitly |

## Observed Dry-Run Routing

The dry-run graph planned two readonly nodes:

- `explainer` required `code_explanation`
- `perf_reviewer` required `performance_review`

Both selected the builtin `pi-agent-default` card with a score of `0.98`,
using the weighted routing formula:

- capability match: `0.40`
- historical success: `0.25`
- cost weight: `0.20`
- current load: `0.10`
- context fit: `0.05`

## Interpretation

v3.6 confirms that CodexSaver can now build a worker capability matrix from
Agent Cards, select the builtin Pi Agent by default, and attach the selected
worker to orchestration output. This keeps the core small while making future
worker expansion plug-in based instead of hardcoded.

After installing Pi locally, the same v3.6 lane also completed live worker
execution through `pi --provider deepseek --model deepseek-v4-flash --mode json
--no-session -p`, using the locally persisted DeepSeek key.

The next benchmark should replace the builtin local worker with one or more
real `.pi-agents/*.agent-card.json` workers and compare routing choices under
different cost, load, and capability profiles.
