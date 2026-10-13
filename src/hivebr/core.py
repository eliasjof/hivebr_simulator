from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import math

from .bridge import create_backend
from .kinematics import normalize_command
from .state import Command, RobotState


class HiveBrAgent(ABC):
    """Decentralized (agent-centric) behavior for a single B-bot.

    The engine instantiates this class once per robot and calls ``loop`` with a
    frozen state snapshot plus the states of its neighbors.
    """

    def __init__(self, robot_id: int | None = None, config: dict | None = None,
                 **params):
        self.id = robot_id
        # The engine config is exposed so controllers can read values such as
        # `waypoints.goal_tolerance` straight from the YAML file.
        self.cfg = config
        self.config = config
        self.params = params

    def setup(self) -> None:
        """Optional one-time initialization."""

    @abstractmethod
    def loop(
        self,
        state: RobotState,
        neighbors: dict[int, RobotState],
    ) -> "Command | tuple[float, float]":
        """Return the desired (v, omega) for this agent."""

    def reset(self) -> None:
        """Optional per-episode reset."""


class SwarmController(ABC):
    """Centralized (global-centric) control for the whole fleet.

    The engine instantiates this class exactly once and passes the states of
    all robots, expecting one command per robot id back.
    """

    def setup(self) -> None:
        """Optional one-time initialization."""

    @abstractmethod
    def loop(self, states: dict[int, RobotState]) -> dict[int, "Command | tuple[float, float]"]:
        """Return a mapping ``{robot_id: command}``."""

    def reset(self) -> None:
        """Optional per-episode reset."""


class SwarmExperiment:
    """Entry point that binds user code to a backend (navsim2d or ROS 2)."""

    def __init__(
        self,
        robots=1,
        backend: str = "navsim2d",
        config=None,
        dt: float = 0.03,
        orientation: bool | None = None,
        goal_tolerance: float | None = None,
        comm_radius: float | None = None,
    ):
        self.dt = float(dt)
        self.backend_name = backend
        self.config = config
        self.orientation = orientation
        self.goal_tolerance = goal_tolerance
        self.comm_radius = comm_radius
        self.agent_classes: dict[int, type[HiveBrAgent]] = {}
        self.agent_params: dict[int, dict] = {}
        self.routes: dict[int, list] = {}
        self.controller: SwarmController | None = None
        self.agents: dict[int, HiveBrAgent] = {}
        self._mode: str | None = None
        self._backend = None
        self._num_robots, self._fleet = _parse_robots(robots)

    def assign_agent(self, robot_id=None, robot_ids=None, agent_class=None, **params) -> "SwarmExperiment":
        if agent_class is None:
            raise ValueError("assign_agent requires an agent_class.")
        ids = []
        if robot_id is not None:
            ids.append(int(robot_id))
        if robot_ids is not None:
            ids.extend(int(i) for i in robot_ids)
        for rid in ids:
            self.agent_classes[rid] = agent_class
            self.agent_params[rid] = dict(params)
        return self

    def set_controller(self, controller: SwarmController) -> "SwarmExperiment":
        self.controller = controller
        return self

    def assign_route(self, robot_id, waypoints) -> "SwarmExperiment":
        """Give a B-bot its waypoint route (each item ``(x, y)`` or ``(x, y, theta)``)."""
        self.routes[int(robot_id)] = [list(wp) for wp in waypoints]
        return self

    def _build(self) -> None:
        if self.controller is not None:
            self._mode = "centralized"
            self.controller.setup()
            return

        self._mode = "decentralized"

        # Build the effective engine config and hand it to every agent so
        # controllers can read `waypoints.goal_tolerance` from the YAML file
        # instead of a hard-coded value.
        engine_cfg = self.build_engine_config()

        goal_tol = self.goal_tolerance
        if goal_tol is None and isinstance(engine_cfg, dict):
            goal_tol = engine_cfg.get("waypoints", {}).get("goal_tolerance")

        self.agents = {}
        for rid, cls in self.agent_classes.items():
            params = dict(self.agent_params.get(rid, {}))
            if goal_tol is not None:
                params.setdefault("goal_tolerance", float(goal_tol))
            self.agents[rid] = cls(robot_id=rid, config=engine_cfg, **params)
        for agent in self.agents.values():
            agent.setup()

    def _dispatch(self, states: dict[int, RobotState], dt: float) -> dict[int, Command]:
        if self._mode is None:
            self._build()

        if self._mode == "centralized":
            raw = self.controller.loop(states)
            return {int(rid): normalize_command(cmd) for rid, cmd in raw.items()}

        comm_radius = self.comm_radius
        if comm_radius is None and isinstance(self.config, dict):
            comm_radius = self.config.get("interaction", {}).get("comm_radius")

        neighbors = {}
        for rid, st in states.items():
            visible = {}
            for j, other in states.items():
                if j == rid:
                    continue
                if comm_radius is None or math.hypot(st.x - other.x, st.y - other.y) <= comm_radius:
                    visible[j] = other
            neighbors[rid] = visible

        commands: dict[int, Command] = {}
        for rid, st in states.items():
            agent = self.agents.get(rid)
            commands[rid] = normalize_command(agent.loop(st, neighbors[rid])) if agent else Command()
        return commands

    def reset(self) -> None:
        for agent in self.agents.values():
            agent.reset()
        if self.controller is not None:
            self.controller.reset()
        if self._backend is not None:
            self._backend.reset()

    def step(self) -> None:
        backend = self._ensure_backend()
        states = backend.get_states()
        commands = self._dispatch(states, self.dt)
        backend.step(commands, self.dt)

    def run(self) -> None:
        self._build()
        self._ensure_backend().run()

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
            self._backend = None

    def build_engine_config(self) -> dict:
        cfg = deepcopy(self.config) if self.config is not None else None
        if cfg is None:
            from .engine.simulator import DEFAULT_CONFIG

            cfg = deepcopy(DEFAULT_CONFIG)
        cfg["robots"] = [deepcopy(meta) for meta in self._fleet]
        for index, meta in enumerate(cfg["robots"]):
            meta.setdefault("initial_pose", list(_spread_pose(index)))
            if index in self.routes:
                meta["waypoints"] = [list(wp) for wp in self.routes[index]]

        cfg.setdefault("waypoints", {})
        if self.orientation is not None:
            cfg["waypoints"]["define_orientation"] = bool(self.orientation)
        if self.goal_tolerance is not None:
            cfg["waypoints"]["goal_tolerance"] = float(self.goal_tolerance)
        return cfg

    def _ensure_backend(self):
        if self._backend is None:
            self._backend = create_backend(self.backend_name, self)
        return self._backend


def _spread_pose(index: int, spacing: float = 1.0) -> tuple[float, float, float]:
    """Default spawn layout: a row starting near the world origin."""
    return (1.0 + spacing * index, 1.0, 0.0)


def _parse_robots(robots) -> tuple[int, list[dict]]:
    if isinstance(robots, int):
        return robots, [{"id": i} for i in range(robots)]
    fleet = [dict(meta) for meta in robots]
    for i, meta in enumerate(fleet):
        meta.setdefault("id", i)
    return len(fleet), fleet
