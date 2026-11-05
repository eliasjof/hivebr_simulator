"""
web_simulator.py
----------------
Wrapper that combines SimulatorCore with SwarmExperiment API for Pyodide/WASM.

This runs inside the Web Worker and handles:
- User code execution (HiveBrAgent, SwarmController classes)
- SwarmExperiment dispatch (decentralized/centralized control)
- SimulatorCore step execution
- JSON serialization for communication with main thread
"""

from __future__ import annotations
import json
import sys
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict

# Import core simulation
from hivebr.engine.core import SimulatorCore, SimStepResult
from hivebr.core import SwarmExperiment, HiveBrAgent, SwarmController
from hivebr.state import Command, RobotState
from hivebr.kinematics import normalize_command


class WebSimulator:
    """Web-compatible simulator that runs in Pyodide Web Worker."""
    
    def __init__(self):
        self.core: Optional[SimulatorCore] = None
        self.experiment: Optional[SwarmExperiment] = None
        self.user_code_globals: Dict[str, Any] = {}
        self._step_count = 0
        self._last_log_export = 0
    
    def init(self, config: dict, user_code: str) -> dict:
        """Initialize simulator with config and user code."""
        try:
            # Execute user code to define Agent/Controller classes
            self.user_code_globals = {
                "HiveBrAgent": HiveBrAgent,
                "SwarmController": SwarmController,
                "SwarmExperiment": SwarmExperiment,
                "Command": Command,
                "RobotState": RobotState,
                "normalize_command": normalize_command,
                "np": __import__("numpy"),
                "math": __import__("math"),
            }
            exec(user_code, self.user_code_globals)
            
            # Create experiment from config
            robots = config.get("robots", 1)
            backend = config.get("backend", "navsim2d")
            dt = config.get("dt", 0.03)
            
            self.experiment = SwarmExperiment(
                robots=robots,
                backend=backend,
                config=config,
                dt=dt,
                orientation=config.get("orientation"),
                goal_tolerance=config.get("goal_tolerance"),
                comm_radius=config.get("comm_radius"),
            )
            
            # Configure agents from user code
            self._configure_agents(config)
            
            # Build engine config and create core
            engine_config = self.experiment.build_engine_config()
            self.core = SimulatorCore(engine_config)
            
            self._step_count = 0
            
            return {"success": True, "message": "Simulator initialized"}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"WebSimulator step error:\n{tb}", file=sys.stderr)
            return {"success": False, "error": str(e), "type": type(e).__name__, "traceback": tb}
    
    def _configure_agents(self, config: dict):
        """Configure agents/controllers from user code and config."""
        if not self.experiment:
            return
            
        # Check for agent classes in user code
        agent_classes = config.get("agent_classes", {})
        controller_class = config.get("controller_class")
        routes = config.get("routes", {})
        agent_params = config.get("agent_params", {})
        
        # Assign agents
        for robot_id, class_name in agent_classes.items():
            if class_name in self.user_code_globals:
                agent_cls = self.user_code_globals[class_name]
                params = agent_params.get(robot_id, {})
                self.experiment.assign_agent(robot_id=int(robot_id), agent_class=agent_cls, **params)
        
        # Assign controller
        if controller_class and controller_class in self.user_code_globals:
            controller_cls = self.user_code_globals[controller_class]
            self.experiment.set_controller(controller_cls())
        
        # Assign routes
        for robot_id, waypoints in routes.items():
            self.experiment.assign_route(int(robot_id), waypoints)
    
    def step(self, dt: float, external_commands: dict = None) -> dict:
        """Run one simulation step and return serializable state.
        
        If external_commands is provided, use those instead of dispatching to agents.
        This is useful for testing and manual control.
        """
        if not self.core or not self.experiment:
            return {"error": "Simulator not initialized"}
        
        try:
            n_robots = self.core.num_robots
            
            if external_commands is not None:
                # Use provided commands directly (for testing/manual control)
                # Convert to dict with integer keys expected by core
                command_dicts = {}
                for rid, cmd in external_commands.items():
                    idx = int(rid)
                    if 0 <= idx < n_robots:
                        command_dicts[idx] = cmd
            else:
                # Normal operation: dispatch to agents/controller
                # 1. Get states from core
                states = self._get_states_from_core()
                
                # 2. Dispatch to agents/controller (user logic)
                commands = self.experiment._dispatch(states, dt)
                
                # 3. Convert Command objects to dicts for core
                command_dicts = {}
                for rid, cmd in commands.items():
                    if hasattr(cmd, '__dataclass_fields__'):
                        command_dicts[rid] = {k: getattr(cmd, k) for k in cmd.__dataclass_fields__ if getattr(cmd, k) is not None}
                    elif isinstance(cmd, dict):
                        command_dicts[rid] = cmd
                    else:
                        command_dicts[rid] = {}
            
            # 4. Step core simulation
            result = self.core.step(dt, command_dicts)
            
            # 4. Serialize for main thread
            self._step_count += 1
            
            return {
                "success": True,
                "states": self._serialize_states(result.states),
                "lidar": self._serialize_lidar(result.lidar_readings),
                "collisions": result.collisions,
                "sim_time": result.sim_time,
                "collision_events": result.collision_events,
                "log_data": self._get_recent_log_data() if self._step_count % 10 == 0 else None,
            }
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"WebSimulator step error:\n{tb}", file=sys.stderr)
            return {"success": False, "error": str(e), "type": type(e).__name__, "traceback": tb}
    
    def _get_states_from_core(self) -> Dict[int, RobotState]:
        """Get RobotState objects from core for dispatch."""
        states = {}
        for i, robot in enumerate(self.core.robots):
            goal = self.core.waypoint_managers[i].get_current_waypoint()
            goal_tuple = tuple(float(v) for v in goal) if goal is not None else None
            
            st = robot.state()
            states[i] = RobotState(
                id=i,
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
        return states
    
    def _serialize_states(self, states: Dict[int, RobotState]) -> Dict[str, Any]:
        """Serialize RobotState dict to JSON-compatible format."""
        result = {}
        for rid, state in states.items():
            result[str(rid)] = {
                "id": state.id,
                "x": state.x,
                "y": state.y,
                "theta": state.theta,
                "v": state.v,
                "omega": state.omega,
                "type": state.type,
                "radius": state.radius,
                "battery": state.battery,
                "goal": list(state.goal) if state.goal else None,
            }
        return result
    
    def _serialize_lidar(self, lidar_readings: List[List[Tuple]]) -> List[List[List[float]]]:
        """Serialize LiDAR readings to JSON-compatible format."""
        result = []
        for robot_readings in lidar_readings:
            robot_result = []
            for angle, dist, hit in robot_readings:
                robot_result.append([
                    float(angle),
                    float(dist),
                    [float(hit[0]), float(hit[1])]
                ])
            result.append(robot_result)
        return result
    
    def _get_recent_log_data(self) -> Optional[Dict[str, Any]]:
        """Get recent log data for plotting."""
        if not self.core or not self.core.logger._has_data():
            return None
        
        try:
            log_result = self.core.logger.result()
            data = {}
            for robot_id, log in log_result.logs.items():
                arrays = log.to_numpy()
                if arrays:
                    # Return last 100 samples for real-time plotting
                    n = min(100, len(arrays.get("t", [])))
                    if n > 0:
                        data[str(robot_id)] = {
                            k: v[-n:].tolist() if hasattr(v, 'tolist') else v[-n:]
                            for k, v in arrays.items()
                        }
            return data if data else None
        except Exception:
            return None
    
    def set_waypoints(self, robot_id: int, waypoints: List) -> dict:
        if self.core:
            self.core.set_waypoints(robot_id, waypoints)
            return {"success": True}
        return {"success": False, "error": "Core not initialized"}
    
    def add_obstacle(self, x: float, y: float, radius: float) -> dict:
        if self.core:
            self.core.add_obstacle(x, y, radius)
            return {"success": True}
        return {"success": False, "error": "Core not initialized"}
    
    def load_occupancy_map(self, image_bytes: list, resolution: float) -> dict:
        if self.core:
            try:
                # Convert list to bytes
                img_bytes = bytes(image_bytes)
                robot_radius = self.core.robots[0].radius if self.core.robots else 0.25
                self.core.load_occupancy_map(img_bytes, resolution, robot_radius)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Core not initialized"}
    
    def load_line_map(self, image_bytes: list, resolution: float) -> dict:
        if self.core:
            try:
                img_bytes = bytes(image_bytes)
                self.core.load_line_map(img_bytes, resolution)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Core not initialized"}
    
    def reset(self) -> dict:
        if self.core:
            self.core.reset()
            self._step_count = 0
            return {"success": True}
        return {"success": False, "error": "Core not initialized"}
    
    def export_log(self, format: str = "pkl") -> dict:
        if self.core:
            try:
                data = self.core.export_log(format)
                return {"success": True, "data": list(data), "format": format}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Core not initialized"}


# Global instance for worker
_web_simulator: Optional[WebSimulator] = None


def get_simulator() -> WebSimulator:
    global _web_simulator
    if _web_simulator is None:
        _web_simulator = WebSimulator()
    return _web_simulator


def handle_message(msg: dict) -> dict:
    """Handle incoming message from main thread."""
    sim = get_simulator()
    msg_type = msg.get("type")
    
    if msg_type == "init":
        return sim.init(msg.get("config", {}), msg.get("user_code", ""))
    
    elif msg_type == "step":
        return sim.step(msg.get("dt", 0.03))
    
    elif msg_type == "set_waypoints":
        return sim.set_waypoints(msg.get("robot_id", 0), msg.get("waypoints", []))
    
    elif msg_type == "add_obstacle":
        return sim.add_obstacle(msg.get("x", 0), msg.get("y", 0), msg.get("radius", 0.4))
    
    elif msg_type == "load_map":
        return sim.load_occupancy_map(msg.get("image_bytes", []), msg.get("resolution", 0.1))
    
    elif msg_type == "load_line_map":
        return sim.load_line_map(msg.get("image_bytes", []), msg.get("resolution", 0.1))
    
    elif msg_type == "reset":
        return sim.reset()
    
    elif msg_type == "export_log":
        return sim.export_log(msg.get("format", "pkl"))
    
    else:
        return {"success": False, "error": f"Unknown message type: {msg_type}"}


# For direct execution in Pyodide (testing)
if __name__ == "__main__":
    # Test initialization
    config = {
        "robots": 1,
        "backend": "navsim2d",
        "dt": 0.03,
    }
    user_code = """
class TestAgent(HiveBrAgent):
    def loop(self, state, neighbors):
        return (0.5, 0.0)
"""
    sim = WebSimulator()
    result = sim.init(config, user_code)
    print(json.dumps(result))