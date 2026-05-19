from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from .agent_registry import AgentCard
from .schema import WorkGraphNode


DEFAULT_ROUTING_WEIGHTS = {
    "capability": 0.40,
    "history": 0.25,
    "cost": 0.20,
    "load": 0.10,
    "context": 0.05,
}


SPECIALIST_CAPABILITIES = {
    "impl_worker": "code_generation",
    "test_writer": "testing",
    "doc_writer": "docs",
    "explainer": "code_explanation",
    "perf_reviewer": "performance_review",
}


LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".md": "markdown",
    ".json": "json",
    ".toml": "toml",
}


class AgentRouter:
    def __init__(self, weights: Dict[str, float] | None = None):
        self.weights = dict(DEFAULT_ROUTING_WEIGHTS)
        if weights:
            self.weights.update(weights)

    def select(self, node: WorkGraphNode, cards: List[AgentCard],
               estimated_context_tokens: int = 0) -> Dict[str, Any]:
        candidates = [card for card in cards if card.status == "online"]
        if not candidates:
            return {
                "worker": None,
                "score": 0.0,
                "reason": "No online Agent Cards discovered.",
                "breakdown": {},
            }
        scored = [
            self.score(card, node, estimated_context_tokens)
            for card in candidates
        ]
        best = max(scored, key=lambda item: item["score"])
        return best

    def score(self, card: AgentCard, node: WorkGraphNode,
              estimated_context_tokens: int = 0) -> Dict[str, Any]:
        capability = required_capability(node)
        language = infer_language(node.allowed_files)
        capability_score = 1.0 if capability in card.capabilities else 0.0
        language_score = 1.0 if not language or language in card.languages else 0.6
        capability_match = capability_score * language_score
        history_score = clamp(card.success_rate)
        cost_score = clamp(1.0 - card.cost_weight)
        load_score = 1.0 / max(1, card.current_load + 1)
        context_score = 1.0 if estimated_context_tokens <= card.context_window else 0.35
        breakdown = {
            "capability": round(capability_match, 4),
            "history": round(history_score, 4),
            "cost": round(cost_score, 4),
            "load": round(load_score, 4),
            "context": round(context_score, 4),
        }
        total = sum(breakdown[key] * self.weights[key] for key in self.weights)
        return {
            "worker": asdict(card),
            "score": round(total, 4),
            "required_capability": capability,
            "language": language,
            "breakdown": breakdown,
            "reason": (
                f"Selected by weighted Agent Card score for capability={capability} "
                f"language={language or 'any'}."
            ),
        }


def required_capability(node: WorkGraphNode) -> str:
    if node.specialist in SPECIALIST_CAPABILITIES:
        return SPECIALIST_CAPABILITIES[node.specialist]
    if node.mode == "readonly":
        return "code_explanation"
    return "code_generation"


def infer_language(files: List[str]) -> str:
    for path in files:
        for suffix, language in LANGUAGE_BY_SUFFIX.items():
            if path.lower().endswith(suffix):
                return language
    return ""


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
