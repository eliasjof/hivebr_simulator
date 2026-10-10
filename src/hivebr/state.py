from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Velocity command emitted by agents/controllers for a B-bot."""

    v: float = 0.0
    omega: float = 0.0

    def as_tuple(self) -> tuple[float, float]:
        return (self.v, self.omega)


@dataclass(frozen=True)
class RobotState:
    """Immutable snapshot of a single B-bot at a given timestep.

    ``goal`` is the robot's current waypoint as a tuple, either ``(x, y)`` or
    ``(x, y, theta)``; ``None`` when the robot has no active target.
    """

    id: int
    x: float
    y: float
    theta: float
    v: float = 0.0
    omega: float = 0.0
    type: str = "differential"
    radius: float = 0.1375
    battery: float = 100.0
    goal: tuple[float, ...] | None = None

    @property
    def position(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def pose(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.theta)

    @property
    def goal_position(self) -> tuple[float, float] | None:
        if self.goal is None:
            return None
        return (self.goal[0], self.goal[1])


@dataclass(frozen=True)
class FleetState:
    """Immutable snapshot of the whole fleet at a given timestep."""

    t: float
    robots: dict[int, RobotState]

    def ids(self) -> tuple[int, ...]:
        return tuple(self.robots.keys())
