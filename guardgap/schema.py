"""Common conversation schema (spec §11.1) + inspection helpers.
Every dataset loader normalises into these types; every product scores
whatever the policy hands it.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str          # "user" | "assistant"
    text: str


@dataclass
class Conversation:
    conv_id: str
    source: str                     # dataset name
    label: str                      # "attack" | "benign"
    turns: list[Turn]
    family: str | None = None       # escalation | drift | fragmentation | ...
    harm_turn: int | None = None    # 1-indexed harm-enabling turn, if annotated
    category: str | None = None     # dataset harm category / tactic (for slicing)

    def user_turns(self) -> list[str]:
        return [t.text for t in self.turns if t.role == "user"]

    def user_prefix(self, t: int) -> list[str]:
        """User turns u_1..u_t (1-indexed)."""
        return self.user_turns()[:t]

    @property
    def n_user_turns(self) -> int:
        return len(self.user_turns())


@dataclass
class Score:
    """Uniform result from any product.score() call."""
    blocked: bool
    r: float                        # risk score in [0,1] (binary -> 0/1)
    categories: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    cost_units: float = 0.0         # measured where the API reports it
    coverage: float | None = None   # fraction of submitted text inspected, if reported
    raw: dict = field(default_factory=dict)
