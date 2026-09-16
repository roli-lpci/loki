from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


def _token_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class SessionTokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    reported_total_tokens: int = 0

    @property
    def cache_tokens(self) -> int:
        return self.cache_read_tokens + self.cache_write_tokens

    @property
    def calculated_total_tokens(self) -> int:
        return self.input_tokens + self.cache_tokens + self.output_tokens

    @property
    def total_tokens(self) -> int:
        return self.calculated_total_tokens or self.reported_total_tokens

    @property
    def has_detail(self) -> bool:
        return bool(self.input_tokens or self.output_tokens or self.cache_tokens or self.reasoning_tokens)

    @classmethod
    def from_agent(cls, agent: Any) -> "SessionTokenUsage":
        if agent is None:
            return cls()
        return cls(
            input_tokens=_token_count(getattr(agent, "session_input_tokens", 0)),
            output_tokens=_token_count(getattr(agent, "session_output_tokens", 0)),
            cache_read_tokens=_token_count(getattr(agent, "session_cache_read_tokens", 0)),
            cache_write_tokens=_token_count(getattr(agent, "session_cache_write_tokens", 0)),
            reasoning_tokens=_token_count(getattr(agent, "session_reasoning_tokens", 0)),
            reported_total_tokens=_token_count(getattr(agent, "session_total_tokens", 0)),
        )

    @classmethod
    def from_session_row(cls, session: Optional[Mapping[str, Any]]) -> "SessionTokenUsage":
        row = session or {}
        return cls(
            input_tokens=_token_count(row.get("input_tokens")),
            output_tokens=_token_count(row.get("output_tokens")),
            cache_read_tokens=_token_count(row.get("cache_read_tokens")),
            cache_write_tokens=_token_count(row.get("cache_write_tokens")),
            reasoning_tokens=_token_count(row.get("reasoning_tokens")),
            reported_total_tokens=_token_count(row.get("total_tokens")),
        )

    def render(self, label: str = "Tokens") -> str:
        if not self.has_detail:
            return f"{label}:         {self.total_tokens:,} total"

        details = [f"in {self.input_tokens:,}", f"out {self.output_tokens:,}"]
        if self.cache_tokens:
            details.append(f"cache {self.cache_tokens:,}")
        detail_text = ", ".join(details)
        if self.reasoning_tokens:
            detail_text += f"; reasoning {self.reasoning_tokens:,} of out"
        return f"{label}:         {self.total_tokens:,} total ({detail_text})"


def resolve_session_token_usage(
    *, session: Optional[Mapping[str, Any]] = None, agent: Any = None
) -> SessionTokenUsage:
    persisted = SessionTokenUsage.from_session_row(session)
    if persisted.total_tokens or persisted.has_detail:
        return persisted
    return SessionTokenUsage.from_agent(agent)
