"""Scenario descriptions. The answer key stays on the simulator side of the boundary."""

from dataclasses import dataclass, field
from typing import Literal

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Motion:
    actor: Literal["robot", "human", "human-left"]
    item: str
    target: Point
    style: Literal["lift", "slide", "touch", "offer", "stop", "hold", "point", "say"] = "lift"


@dataclass
class Case:
    command: str
    options: dict[str, str]
    expected: str
    default: str
    robot: dict[str, list[Motion]]
    human: list[Motion]
    # Public feedback options specific to this episode. A blank utterance is silent.
    utterances: dict[str, str] = field(
        default_factory=lambda: {"silent": "", "retry": "Try again."}
    )


def carry_clearance(item, delta):
    """Extra vertical height at the midpoint of the transport arc (meters)."""
    if item in {"near", "far", "organizer"} and abs(delta[2]) > 0.05:
        return 0.090
    return 0.054
