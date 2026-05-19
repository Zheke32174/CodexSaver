from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class TaskRecord:
    task_id: str
    node_id: str
    worker_id: str
    status: str
    submitted_at: str
    updated_at: str
    events: List[Dict[str, Any]] = field(default_factory=list)


class TaskLifecycle:
    """Small A2A-compatible task state tracker."""

    def submitted(self, node_id: str, worker_id: str) -> TaskRecord:
        now = timestamp()
        return TaskRecord(
            task_id=f"task-{uuid4().hex[:12]}",
            node_id=node_id,
            worker_id=worker_id,
            status="submitted",
            submitted_at=now,
            updated_at=now,
            events=[{"status": "submitted", "at": now}],
        )

    def running(self, record: TaskRecord) -> TaskRecord:
        return self._transition(record, "running")

    def completed(self, record: TaskRecord) -> TaskRecord:
        return self._transition(record, "completed")

    def failed(self, record: TaskRecord) -> TaskRecord:
        return self._transition(record, "failed")

    def timed_out(self, record: TaskRecord) -> TaskRecord:
        return self._transition(record, "timed_out")

    def _transition(self, record: TaskRecord, status: str) -> TaskRecord:
        now = timestamp()
        record.status = status
        record.updated_at = now
        record.events.append({"status": status, "at": now})
        return record


def task_record_payload(record: TaskRecord) -> Dict[str, Any]:
    return asdict(record)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
