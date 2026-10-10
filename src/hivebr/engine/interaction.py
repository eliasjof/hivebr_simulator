from __future__ import annotations

import numpy as np


def radius_of(robot) -> float:
    return float(getattr(robot, "radius", 0.0))


def detect_robot_collisions(robots, safety_margin: float = 0.0) -> list[tuple[int, int, float]]:
    """Return every overlapping pair ``(i, j, distance)`` in the fleet.

    Uses an O(n^2) sweep, which is fine for the fleet sizes this simulator
    targets; swap in spatial hashing later if N grows large.
    """
    pairs: list[tuple[int, int, float]] = []
    n = len(robots)
    for i in range(n):
        pi = robots[i].position
        ri = radius_of(robots[i])
        for j in range(i + 1, n):
            d = float(np.linalg.norm(pi - robots[j].position))
            if d < ri + radius_of(robots[j]) + safety_margin:
                pairs.append((i, j, d))
    return pairs


def build_neighbors(robots, comm_radius: float | None = None) -> dict[int, set[int]]:
    """Communication topology: ``{robot_id: {neighbor_ids}}``.

    ``comm_radius=None`` gives full visibility; otherwise only robots within
    the communication radius are considered reachable.
    """
    n = len(robots)
    neighbors: dict[int, set[int]] = {i: set() for i in range(n)}
    for i in range(n):
        pi = robots[i].position
        for j in range(i + 1, n):
            d = float(np.linalg.norm(pi - robots[j].position))
            if comm_radius is None or d <= comm_radius:
                neighbors[i].add(j)
                neighbors[j].add(i)
    return neighbors


def resolve_robot_overlaps(robots, safety_margin: float = 0.0, max_push: float = 0.05) -> None:
    """Separate overlapping robots by nudging them apart along the normal.

    Mutates robot positions in place. Called after integration as an optional
    relaxation to avoid permanently stuck fleets.
    """
    for i, j, d in detect_robot_collisions(robots, safety_margin):
        pi = robots[i].position
        pj = robots[j].position
        normal = pi - pj
        norm = float(np.linalg.norm(normal))
        if norm < 1e-9:
            normal = np.array([1.0, 0.0])
            norm = 1.0
        overlap = radius_of(robots[i]) + radius_of(robots[j]) + safety_margin - d
        push = min(max(overlap * 0.5, 0.0), max_push)
        direction = normal / norm
        robots[i].x += direction[0] * push
        robots[i].y += direction[1] * push
        robots[j].x -= direction[0] * push
        robots[j].y -= direction[1] * push
