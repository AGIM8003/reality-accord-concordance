"""REALITY ACCORD validators."""
from __future__ import annotations


def require_agent_id(agent_id: str) -> str:
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string")
    return agent_id.strip()


def require_position(pos: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(pos, tuple) or len(pos) != 2:
        raise ValueError("position must be a (x, y) tuple")
    return float(pos[0]), float(pos[1])
