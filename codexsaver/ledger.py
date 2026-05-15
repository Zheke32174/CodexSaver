from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LedgerEntry:
    route: str
    status: str
    node_count: int
    worker_calls: int
    estimated_savings_percent: int


class CostLedger:
    def summarize(self, entries: List[LedgerEntry]) -> Dict[str, int]:
        if not entries:
            return {
                "runs": 0,
                "worker_calls": 0,
                "average_node_count": 0,
                "average_estimated_savings_percent": 0,
            }
        return {
            "runs": len(entries),
            "worker_calls": sum(item.worker_calls for item in entries),
            "average_node_count": sum(item.node_count for item in entries) // len(entries),
            "average_estimated_savings_percent": (
                sum(item.estimated_savings_percent for item in entries) // len(entries)
            ),
        }
