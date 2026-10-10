from __future__ import annotations

import math

from .state import Command

TWO_PI = 2.0 * math.pi


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wrap_to_pi(angle: float) -> float:
    return (angle + math.pi) % TWO_PI - math.pi


def wheel_speeds(command: Command, wheel_base: float) -> tuple[float, float]:
    """Map a (v, omega) twist to left/right wheel linear speeds."""
    half = 0.5 * wheel_base
    return (command.v - command.omega * half, command.v + command.omega * half)


def apply_limits(
    command: Command,
    max_speed: float,
    max_omega: float,
) -> Command:
    """Saturate a twist according to differential-drive kinematic limits."""
    return Command(
        v=clamp(command.v, -max_speed, max_speed),
        omega=clamp(command.omega, -max_omega, max_omega),
    )


def normalize_command(raw, max_speed: float = None, max_omega: float = None) -> Command:
    """Accept a Command, a (v, omega) tuple, or a mapping and return a Command."""
    if isinstance(raw, Command):
        cmd = raw
    elif isinstance(raw, (tuple, list)):
        cmd = Command(v=float(raw[0]), omega=float(raw[1]))
    elif isinstance(raw, dict):
        cmd = Command(v=float(raw.get("v", 0.0)), omega=float(raw.get("omega", 0.0)))
    else:
        raise TypeError(f"Unsupported command type: {type(raw)!r}")

    if max_speed is not None and max_omega is not None:
        cmd = apply_limits(cmd, max_speed, max_omega)
    return cmd
