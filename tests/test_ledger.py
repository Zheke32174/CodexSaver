from __future__ import annotations

from codexsaver.ledger import CostLedger, LedgerEntry


def test_cost_ledger_empty_summary_includes_participation_fields():
    assert CostLedger().summarize([]) == {
        "runs": 0,
        "worker_calls": 0,
        "average_node_count": 0,
        "average_estimated_savings_percent": 0,
        "average_deepseek_participation_percent": 0,
        "deepseek_majority_runs": 0,
    }


def test_cost_ledger_summarizes_deepseek_participation():
    summary = CostLedger().summarize([
        LedgerEntry(
            route="deepseek",
            status="success",
            node_count=2,
            worker_calls=2,
            estimated_savings_percent=52,
            deepseek_participation_percent=100,
        ),
        LedgerEntry(
            route="codex",
            status="needs_codex",
            node_count=2,
            worker_calls=2,
            estimated_savings_percent=0,
            deepseek_participation_percent=50,
        ),
    ])
    assert summary["average_deepseek_participation_percent"] == 75
    assert summary["deepseek_majority_runs"] == 2
