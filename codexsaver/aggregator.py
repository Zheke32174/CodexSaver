from __future__ import annotations

from typing import Any, Dict, List, Set

from .schema import AggregationResult


class PatchAggregator:
    def aggregate(self, node_results: List[Dict[str, Any]]) -> AggregationResult:
        changed_files: List[str] = []
        aggregate_patches: List[str] = []
        conflicts: List[str] = []
        seen: Set[str] = set()

        for item in node_results:
            for path in item.get("changed_files", []):
                if path in seen:
                    conflicts.append(path)
                else:
                    seen.add(path)
                    changed_files.append(path)
            patch = str(item.get("patch", "")).strip()
            if patch:
                aggregate_patches.append(patch)

        notes = []
        if conflicts:
            notes.append("Overlapping changed_files detected; Codex review required.")
        if not aggregate_patches:
            notes.append("No aggregate patch was produced.")

        return AggregationResult(
            ok=not conflicts,
            aggregate_patch="\n\n".join(aggregate_patches).strip(),
            changed_files=changed_files,
            conflicts=conflicts,
            codex_review_notes=notes,
        )
