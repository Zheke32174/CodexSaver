from __future__ import annotations

from typing import Dict, List

from .schema import SpecialistProfile


DEFAULT_SPECIALISTS: Dict[str, SpecialistProfile] = {
    "impl_worker": SpecialistProfile(
        name="impl_worker",
        provider="pi-agent",
        model="pi-agent-default",
        mode="bounded_patch",
        prompt_file="~/.codexsaver/prompts/impl_worker.md",
        description="Implements a bounded code change inside allowlisted files.",
    ),
    "test_writer": SpecialistProfile(
        name="test_writer",
        provider="pi-agent",
        model="pi-agent-default",
        mode="bounded_patch",
        prompt_file="~/.codexsaver/prompts/test_writer.md",
        description="Adds or updates focused tests for existing code.",
    ),
    "doc_writer": SpecialistProfile(
        name="doc_writer",
        provider="pi-agent",
        model="pi-agent-default",
        mode="bounded_patch",
        prompt_file="~/.codexsaver/prompts/doc_writer.md",
        description="Adds docstrings, JSDoc, and small docs updates.",
    ),
    "explainer": SpecialistProfile(
        name="explainer",
        provider="pi-agent",
        model="pi-agent-default",
        mode="readonly",
        prompt_file="~/.codexsaver/prompts/explainer.md",
        description="Explains code, intent, and implementation flow.",
    ),
    "perf_reviewer": SpecialistProfile(
        name="perf_reviewer",
        provider="pi-agent",
        model="pi-agent-default",
        mode="readonly",
        prompt_file="~/.codexsaver/prompts/perf_reviewer.md",
        description="Flags likely performance issues and cheap optimization ideas.",
    ),
}


class SpecialistRegistry:
    def __init__(self, specialists: Dict[str, SpecialistProfile] | None = None):
        self._specialists = specialists or dict(DEFAULT_SPECIALISTS)

    def get(self, name: str) -> SpecialistProfile:
        if name not in self._specialists:
            raise KeyError(f"Unknown specialist: {name}")
        return self._specialists[name]

    def list(self) -> List[SpecialistProfile]:
        return [self._specialists[name] for name in sorted(self._specialists)]
