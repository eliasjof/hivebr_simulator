from __future__ import annotations
import numpy as np


def wrap_to_pi(angle: float) -> float:
    """Wrap angle to [-pi, pi] range."""
    return float((angle + np.pi) % (2 * np.pi) - np.pi)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value to [min_value, max_value] range."""
    return max(min_value, min(value, max_value))


def distance_between(a, b) -> float:
    """Euclidean distance between two points."""
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))