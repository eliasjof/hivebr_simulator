from __future__ import annotations

from abc import ABC, abstractmethod

from .kinematics import normalize_command
from .state import Command, FleetState, RobotState


class Backend(ABC):
    """Execution backend contract shared by the simulator and ROS 2 arena.

    A backend is the only layer allowed to talk to a concrete engine, so that
    the public API never imports pygame or ROS 2 directly.
    """

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def get_states(self) -> dict[int, RobotState]: ...

    @abstractmethod
    def compute(self, states: dict[int, RobotState], dt: float) -> dict[int, Command]:
        """Return one command per robot id from a frozen fleet snapshot."""

    @abstractmethod
    def step(self, commands: dict[int, Command], dt: float) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class NavSim2DBackend(Backend):
    """Backend for local simulation using the hivebr.engine renderer/physics."""

    def __init__(self, experiment) -> None:
        self.experiment = experiment
        self._sim = None

    def reset(self) -> None:
        if self._sim is not None:
            self._sim.reset()

    def get_states(self) -> dict[int, RobotState]:
        if self._sim is None:
            return {}
        robots = getattr(self._sim, "robots", [self._sim.robot])
        states = {}
        for i, robot in enumerate(robots):
            goal = self._sim.robot_goal(i) if hasattr(self._sim, "robot_goal") else None
            states[i] = _state_from_robot(i, robot, goal)
        return states

    def compute(self, states: dict[int, RobotState], dt: float) -> dict[int, Command]:
        return self.experiment._dispatch(states, dt)

    def step(self, commands: dict[int, Command], dt: float) -> None:
        raise NotImplementedError(
            "Headless stepping is not available yet; use run() which drives the "
            "engine's interactive loop through the fleet controller."
        )

    def run(self) -> None:
        from .engine import Simulator

        config = self.experiment.build_engine_config()
        self._sim = Simulator(config=config, fleet_controller=self._fleet_controller)
        self._sim.run()

    def close(self) -> None:
        self._sim = None

    def _fleet_controller(self, robots, goals, config, dt, lidar_readings=None):
        states = {
            i: _state_from_robot(i, r, goals[i] if goals is not None else None)
            for i, r in enumerate(robots)
        }
        commands = self.experiment._dispatch(states, dt)
        return [_engine_command(r, commands.get(i, Command())) for i, r in enumerate(robots)]


class Ros2Backend(Backend):
    """Placeholder for the physical arena: one ROS 2 node per agent or a single
    overarching node for a SwarmController."""

    def __init__(self, experiment) -> None:
        self.experiment = experiment

    def reset(self) -> None:
        raise NotImplementedError("ROS 2 backend not implemented yet.")

    def get_states(self) -> dict[int, RobotState]:
        raise NotImplementedError("ROS 2 backend not implemented yet.")

    def compute(self, states: dict[int, RobotState], dt: float) -> dict[int, Command]:
        return self.experiment._dispatch(states, dt)

    def step(self, commands: dict[int, Command], dt: float) -> None:
        raise NotImplementedError("ROS 2 backend not implemented yet.")

    def run(self) -> None:
        raise NotImplementedError("ROS 2 backend not implemented yet.")

    def close(self) -> None:
        pass


def _state_from_robot(rid: int, robot, goal=None) -> RobotState:
    st = robot.state()
    goal_tuple = tuple(float(v) for v in goal) if goal is not None else None
    return RobotState(
        id=rid,
        x=float(st.get("x", getattr(robot, "x", 0.0))),
        y=float(st.get("y", getattr(robot, "y", 0.0))),
        theta=float(st.get("theta", getattr(robot, "theta", 0.0))),
        v=float(st.get("v", 0.0)),
        omega=float(st.get("omega", 0.0)),
        type=str(st.get("type", "differential")),
        radius=float(getattr(robot, "radius", 0.1375)),
        battery=float(getattr(robot, "battery_percent", 100.0)),
        goal=goal_tuple,
    )


def _engine_command(robot, command: Command) -> dict:
    rtype = str(robot.state().get("type", "differential"))
    if rtype == "holonomic":
        return {"vx": command.v, "vy": command.omega}
    if rtype == "ackermann":
        return {"speed": command.v, "steer": command.omega}
    return {"v": command.v, "omega": command.omega}


def create_backend(name: str, experiment) -> Backend:
    key = str(name).lower()
    if key in ("navsim2d", "nav_sim2d", "local", "sim"):
        return NavSim2DBackend(experiment)
    if key in ("ros2", "ros", "arena"):
        return Ros2Backend(experiment)
    raise ValueError(f"Unknown backend: {name!r} (use 'navsim2d' or 'ros2')")
