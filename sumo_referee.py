"""
SUMO REFEREE SYSTEM - RoboCore Style
====================================
Complete competition framework with referee, match management, and tournament support.
"""

import math
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
from pathlib import Path

import pygame
import numpy as np

from hivebr import SwarmExperiment, HiveBrAgent
from hivebr.state import RobotState, Command
from hivebr.kinematics import wrap_to_pi
from hivebr.bridge import _state_from_robot


# ============================================================
# COMPETITION DATA STRUCTURES
# ============================================================

class MatchStatus(Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    DRAW = "draw"


class RobotStatus(Enum):
    IN_RING = "in_ring"
    OUT_OF_RING = "out_of_ring"
    DISABLED = "disabled"


@dataclass
class TeamInfo:
    """Information about a competing team."""
    team_id: str
    name: str
    agent_class: type  # The agent class
    color: Tuple[int, int, int] = (30, 144, 255)
    logo: Optional[str] = None  # Path to logo image


@dataclass
class RobotCompetitionState:
    """Competition-specific state for a robot."""
    robot_id: int
    team_id: str
    status: RobotStatus = RobotStatus.IN_RING
    exit_time: Optional[float] = None
    exit_position: Optional[Tuple[float, float]] = None
    push_count: int = 0
    time_in_ring: float = 0.0
    

@dataclass
class MatchResult:
    """Result of a single match."""
    match_id: str
    team1_id: str
    team2_id: str
    winner_team_id: Optional[str] = None  # None = draw
    reason: str = ""
    duration: float = 0.0
    team1_final_pos: Tuple[float, float] = (0, 0)
    team2_final_pos: Tuple[float, float] = (0, 0)
    team1_exited: bool = False
    team2_exited: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class TournamentConfig:
    """Tournament configuration."""
    match_duration: float = 30.0  # seconds
    max_matches_per_pair: int = 3  # Best of N
    ring_radius: float = 0.77
    robot_radius: float = 0.10
    border_width: float = 0.05
    start_distance: float = 0.45
    max_speed: float = 3.0
    max_omega: float = 6.0


# ============================================================
# SUMO REFEREE - Core competition logic
# ============================================================

class SumoReferee:
    """
    Referee for robot sumo matches.
    
    Responsibilities:
    - Detect when robots leave the ring (dohyo)
    - Determine winner based on RoboCore rules
    - Manage match timing
    - Track statistics
    """
    
    def __init__(self, config: TournamentConfig = None):
        self.config = config or TournamentConfig()
        self.match_id: Optional[str] = None
        self.start_time: float = 0.0
        self.match_duration: float = self.config.match_duration
        
        # Ring parameters
        self.ring_radius = self.config.ring_radius
        self.robot_radius = self.config.robot_radius
        self.effective_radius = self.ring_radius - self.robot_radius - self.config.border_width
        
        # Robot states
        self.robot_states: Dict[int, RobotCompetitionState] = {}
        self.team_info: Dict[str, TeamInfo] = {}
        
        # Match state
        self.status = MatchStatus.WAITING
        self.winner: Optional[str] = None
        self.result: Optional[MatchResult] = None
        
        # Callbacks
        self.on_match_end: Optional[Callable[[MatchResult], None]] = None
        self.on_robot_exit: Optional[Callable[[int, RobotCompetitionState], None]] = None
        
    def register_team(self, robot_id: int, team: TeamInfo):
        """Register a team for a robot."""
        self.team_info[team.team_id] = team
        self.robot_states[robot_id] = RobotCompetitionState(
            robot_id=robot_id,
            team_id=team.team_id
        )
    
    def start_match(self, match_id: str = None):
        """Start a new match."""
        self.match_id = match_id or str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.status = MatchStatus.IN_PROGRESS
        self.winner = None
        
        # Reset robot states
        for state in self.robot_states.values():
            state.status = RobotStatus.IN_RING
            state.exit_time = None
            state.exit_position = None
            state.push_count = 0
            state.time_in_ring = 0.0
    
    def update(self, robot_states: Dict[int, RobotState], dt: float) -> Optional[MatchResult]:
        """
        Update referee with current robot states.
        Returns MatchResult if match ended, None otherwise.
        """
        if self.status != MatchStatus.IN_PROGRESS:
            return None
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # Check time limit
        if elapsed >= self.match_duration:
            return self._end_match_timeout(elapsed)
        
        # Check each robot
        robots_in_ring = []
        robots_out = []
        
        for robot_id, comp_state in self.robot_states.items():
            if robot_id not in robot_states:
                continue
            
            state = robot_states[robot_id]
            dist_from_center = math.hypot(state.x, state.y)
            
            # Update time in ring
            if comp_state.status == RobotStatus.IN_RING:
                comp_state.time_in_ring += dt
            
            # Check if robot left the ring
            if dist_from_center > self.effective_radius:
                if comp_state.status == RobotStatus.IN_RING:
                    # Just exited!
                    comp_state.status = RobotStatus.OUT_OF_RING
                    comp_state.exit_time = elapsed
                    comp_state.exit_position = (state.x, state.y)
                    
                    if self.on_robot_exit:
                        self.on_robot_exit(robot_id, comp_state)
                
                robots_out.append((robot_id, comp_state, dist_from_center))
            else:
                robots_in_ring.append((robot_id, comp_state, dist_from_center))
        
        # Determine winner based on RoboCore rules
        if len(robots_out) == 1:
            # One robot out - other wins
            winner_id = robots_in_ring[0][0]
            loser_id = robots_out[0][0]
            return self._end_match_push_out(winner_id, loser_id, elapsed, robots_out[0][2])
        
        elif len(robots_out) == 2:
            # Both out simultaneously - check who exited first
            if robots_out[0][1].exit_time < robots_out[1][1].exit_time:
                return self._end_match_push_out(robots_out[1][0], robots_out[0][0], 
                                               elapsed, robots_out[0][2])
            elif robots_out[1][1].exit_time < robots_out[0][1].exit_time:
                return self._end_match_push_out(robots_out[0][0], robots_out[1][0], 
                                               elapsed, robots_out[1][2])
            else:
                return self._end_match_draw(elapsed, "both_exited_simultaneous")
        
        return None
    
    def _end_match_push_out(self, winner_id: int, loser_id: int, 
                            elapsed: float, exit_dist: float) -> MatchResult:
        """End match: one robot pushed the other out."""
        self.status = MatchStatus.FINISHED
        
        winner_comp = self.robot_states[winner_id]
        loser_comp = self.robot_states[loser_id]
        winner_team = winner_comp.team_id
        loser_team = loser_comp.team_id
        
        self.winner = winner_team
        
        result = MatchResult(
            match_id=self.match_id,
            team1_id=list(self.team_info.keys())[0] if len(self.team_info) > 0 else winner_team,
            team2_id=list(self.team_info.keys())[1] if len(self.team_info) > 1 else loser_team,
            winner_team_id=winner_team,
            reason=f"push_out: {self.team_info[winner_team].name} pushed {self.team_info[loser_team].name} out",
            duration=elapsed,
            team1_final_pos=(self.robot_states[0].exit_position or (0,0)) if 0 in self.robot_states else (0,0),
            team2_final_pos=(self.robot_states[1].exit_position or (0,0)) if 1 in self.robot_states else (0,0),
            team1_exited=(0 == loser_id),
            team2_exited=(1 == loser_id)
        )
        
        self.result = result
        if self.on_match_end:
            self.on_match_end(result)
        
        return result
    
    def _end_match_timeout(self, elapsed: float) -> MatchResult:
        """End match: time limit reached."""
        self.status = MatchStatus.FINISHED
        
        # Robot closer to center wins
        positions = {}
        for robot_id, comp_state in self.robot_states.items():
            # Need to get actual position - simplified here
            pass
        
        # For now, determine by time in ring
        times = [(r.team_id, r.time_in_ring) for r in self.robot_states.values()]
        times.sort(key=lambda x: x[1], reverse=True)
        
        if times[0][1] > times[1][1]:
            winner_team = times[0][0]
            reason = "timeout: more time in ring"
        else:
            winner_team = None
            reason = "timeout: draw"
        
        self.winner = winner_team
        self.status = MatchStatus.DRAW if winner_team is None else MatchStatus.FINISHED
        
        result = MatchResult(
            match_id=self.match_id,
            team1_id=list(self.team_info.keys())[0],
            team2_id=list(self.team_info.keys())[1] if len(self.team_info) > 1 else "",
            winner_team_id=winner_team,
            reason=reason,
            duration=elapsed
        )
        
        self.result = result
        if self.on_match_end:
            self.on_match_end(result)
        
        return result
    
    def _end_match_draw(self, elapsed: float, reason: str) -> MatchResult:
        """End match in draw."""
        self.status = MatchStatus.DRAW
        self.winner = None
        
        result = MatchResult(
            match_id=self.match_id,
            team1_id=list(self.team_info.keys())[0],
            team2_id=list(self.team_info.keys())[1] if len(self.team_info) > 1 else "",
            winner_team_id=None,
            reason=f"draw: {reason}",
            duration=elapsed
        )
        
        self.result = result
        if self.on_match_end:
            self.on_match_end(result)
        
        return result
    
    def get_match_time_remaining(self) -> float:
        """Get remaining match time."""
        if self.status != MatchStatus.IN_PROGRESS:
            return 0.0
        elapsed = time.time() - self.start_time
        return max(0.0, self.match_duration - elapsed)
    
    def get_status_text(self) -> str:
        """Get human-readable status."""
        if self.status == MatchStatus.WAITING:
            return "AGUARDANDO INÍCIO"
        elif self.status == MatchStatus.IN_PROGRESS:
            rem = self.get_match_time_remaining()
            return f"EM ANDAMENTO - {rem:.1f}s"
        elif self.status == MatchStatus.DRAW:
            return f"EMPATE - {self.result.reason if self.result else ''}"
        else:
            winner_name = self.team_info[self.winner].name if self.winner and self.winner in self.team_info else "DESCONHECIDO"
            return f"VITÓRIA: {winner_name} - {self.result.reason if self.result else ''}"


# ============================================================
# TOURNAMENT MANAGER
# ============================================================

class TournamentManager:
    """Manages a tournament bracket between multiple teams."""
    
    def __init__(self, config: TournamentConfig = None):
        self.config = config or TournamentConfig()
        self.teams: List[TeamInfo] = []
        self.matches: List[MatchResult] = []
        self.current_match_index: int = 0
        self.match_pairings: List[Tuple[str, str]] = []
        
    def add_team(self, team: TeamInfo):
        """Add a team to the tournament."""
        self.teams.append(team)
    
    def generate_pairings(self) -> List[Tuple[str, str]]:
        """Generate all pairings for round-robin."""
        pairings = []
        for i in range(len(self.teams)):
            for j in range(i + 1, len(self.teams)):
                pairings.append((self.teams[i].team_id, self.teams[j].team_id))
        self.match_pairings = pairings
        return pairings
    
    def get_next_match(self) -> Optional[Tuple[str, str]]:
        """Get next match pairing."""
        if self.current_match_index < len(self.match_pairings):
            pairing = self.match_pairings[self.current_match_index]
            self.current_match_index += 1
            return pairing
        return None
    
    def record_match(self, result: MatchResult):
        """Record a match result."""
        self.matches.append(result)
    
    def get_standings(self) -> List[Dict]:
        """Get tournament standings."""
        stats = {team.team_id: {"name": team.name, "wins": 0, "losses": 0, "draws": 0, "points": 0} 
                 for team in self.teams}
        
        for match in self.matches:
            t1 = stats.get(match.team1_id, {"name": match.team1_id, "wins": 0, "losses": 0, "draws": 0, "points": 0})
            t2 = stats.get(match.team2_id, {"name": match.team2_id, "wins": 0, "losses": 0, "draws": 0, "points": 0})
            
            if match.winner_team_id is None:
                t1["draws"] += 1
                t2["draws"] += 1
                t1["points"] += 1
                t2["points"] += 1
            elif match.winner_team_id == match.team1_id:
                t1["wins"] += 1
                t2["losses"] += 1
                t1["points"] += 3
            else:
                t2["wins"] += 1
                t1["losses"] += 1
                t2["points"] += 3
        
        standings = []
        for team_id, data in stats.items():
            data["team_id"] = team_id
            standings.append(data)
        
        standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
        return standings
    
    def export_results(self, filepath: str):
        """Export tournament results to JSON."""
        data = {
            "config": asdict(self.config),
            "teams": [asdict(t) for t in self.teams],
            "matches": [asdict(m) for m in self.matches],
            "standings": self.get_standings()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


# ============================================================
# COMPETITION AGENT BASE CLASS
# ============================================================

class CompetitionAgent(HiveBrAgent):
    """
    Base agent for competition.
    
    Groups should extend this and implement loop().
    Provides helper methods for sumo competition.
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        
        # Competition parameters (from config)
        self.ring_radius = config.get("sumo", {}).get("ring_radius", 0.77) if config else 0.77
        self.robot_radius = config.get("sumo", {}).get("robot_radius", 0.10) if config else 0.10
        self.border_width = config.get("sumo", {}).get("border_width", 0.05) if config else 0.05
        self.max_speed = config.get("robot", {}).get("max_speed", 3.0) if config else 3.0
        self.max_omega = config.get("robot", {}).get("max_omega", 6.0) if config else 6.0
        
        # Effective ring boundary (accounting for robot size + border)
        self.effective_radius = self.ring_radius - self.robot_radius - self.border_width
        
        # Opponent tracking
        self.opponent_id: Optional[int] = None
        self.last_opp_pos: Optional[Tuple[float, float]] = None
        self.opp_velocity: Tuple[float, float] = (0.0, 0.0)
        
        # State machine
        self.behavior_state = "SEARCH"
        self.state_timer = 0.0
        
        # Custom parameters (override in subclasses)
        self.attack_distance = 0.5
        self.defend_distance = 0.8
        self.edge_margin = 0.15
        self.search_omega = 2.0
        self.approach_speed = 1.5
        self.attack_speed = 3.0
        self.retreat_speed = 2.0
    
    def set_opponent(self, opponent_id: int):
        self.opponent_id = opponent_id
    
    # ========================================================
    # HELPER METHODS - Available to all competition agents
    # ========================================================
    
    def is_in_ring(self, x: float, y: float, margin: float = 0.0) -> bool:
        """Check if position is inside the sumo ring."""
        effective_r = self.effective_radius - margin
        return (x * x + y * y) <= (effective_r * effective_r)
    
    def distance_to_center(self, state: RobotState) -> float:
        return math.hypot(state.x, state.y)
    
    def angle_to_center(self, state: RobotState) -> float:
        return math.atan2(-state.y, -state.x)
    
    def distance_to_edge(self, state: RobotState) -> float:
        """Distance to ring edge (positive = inside, negative = outside)."""
        return self.effective_radius - self.distance_to_center(state)
    
    def get_opponent(self, neighbors: Dict[int, RobotState]) -> Optional[RobotState]:
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        return neighbors[self.opponent_id]
    
    def distance_to_opponent(self, state: RobotState, 
                             neighbors: Dict[int, RobotState]) -> Optional[float]:
        opp = self.get_opponent(neighbors)
        if opp is None:
            return None
        return math.hypot(state.x - opp.x, state.y - opp.y)
    
    def angle_to_opponent(self, state: RobotState,
                          neighbors: Dict[int, RobotState]) -> Optional[float]:
        opp = self.get_opponent(neighbors)
        if opp is None:
            return None
        dx = opp.x - state.x
        dy = opp.y - state.y
        absolute = math.atan2(dy, dx)
        return wrap_to_pi(absolute - state.theta)
    
    def angle_to_target(self, state: RobotState, tx: float, ty: float) -> float:
        absolute = math.atan2(ty - state.y, tx - state.x)
        return wrap_to_pi(absolute - state.theta)
    
    def update_opponent_tracking(self, neighbors: Dict[int, RobotState], dt: float):
        """Track opponent position and estimate velocity."""
        opp = self.get_opponent(neighbors)
        if opp is None:
            return
        
        current_pos = (opp.x, opp.y)
        
        if self.last_opp_pos is not None:
            vx = (current_pos[0] - self.last_opp_pos[0]) / dt
            vy = (current_pos[1] - self.last_opp_pos[1]) / dt
            alpha = 0.3
            self.opp_velocity = (
                alpha * vx + (1 - alpha) * self.opp_velocity[0],
                alpha * vy + (1 - alpha) * self.opp_velocity[1]
            )
        
        self.last_opp_pos = current_pos
    
    def predict_opponent(self, lookahead: float = 0.5) -> Optional[Tuple[float, float]]:
        if self.last_opp_pos is None:
            return None
        return (
            self.last_opp_pos[0] + self.opp_velocity[0] * lookahead,
            self.last_opp_pos[1] + self.opp_velocity[1] * lookahead
        )
    
    def get_ring_quadrant(self, state: RobotState) -> str:
        """Get which quadrant of the ring robot is in."""
        if state.x >= 0 and state.y >= 0:
            return "NE"
        elif state.x < 0 and state.y >= 0:
            return "NW"
        elif state.x < 0 and state.y < 0:
            return "SW"
        else:
            return "SE"
    
    # ========================================================
    # BEHAVIOR METHODS - Override in subclasses
    # ========================================================
    
    def search_behavior(self, state: RobotState) -> Command:
        """Default search: spin slowly."""
        return Command(v=0.0, omega=self.search_omega)
    
    def approach_behavior(self, state: RobotState, dist: float, angle: float) -> Command:
        """Default approach: turn toward opponent, move forward."""
        if abs(angle) > 0.3:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.5, omega=turn)
        return Command(v=self.approach_speed, omega=0.0)
    
    def attack_behavior(self, state: RobotState, dist: float, angle: float) -> Command:
        """Default attack: charge with prediction."""
        pred = self.predict_opponent(0.3)
        if pred:
            target_angle = self.angle_to_target(state, pred[0], pred[1])
        else:
            target_angle = angle
        
        if abs(target_angle) > 0.2:
            turn = self.max_omega if target_angle > 0 else -self.max_omega
            return Command(v=1.0, omega=turn)
        return Command(v=self.attack_speed, omega=0.0)
    
    def defend_behavior(self, state: RobotState) -> Command:
        """Default defend: go to center."""
        angle = self.angle_to_center(state)
        dist = self.distance_to_center(state)
        if abs(angle) > 0.3:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.0, omega=turn)
        return Command(v=1.5, omega=0.0)
    
    def retreat_behavior(self, state: RobotState) -> Command:
        """Emergency retreat from edge."""
        angle = self.angle_to_center(state)
        if abs(angle) > 0.2:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.5, omega=turn)
        return Command(v=self.retreat_speed, omega=0.0)
    
    # ========================================================
    # MAIN LOOP - Override completely for custom logic
    # ========================================================
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        """Main control loop - override for custom strategy."""
        dt = 0.03
        self.state_timer += dt
        
        # Update opponent tracking
        self.update_opponent_tracking(neighbors, dt)
        
        # Check if out of ring
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # Get opponent info
        opp = self.get_opponent(neighbors)
        has_opponent = opp is not None
        
        if has_opponent:
            opp_dist = self.distance_to_opponent(state, neighbors)
            opp_angle = self.angle_to_opponent(state, neighbors)
        else:
            opp_dist = float('inf')
            opp_angle = 0.0
        
        dist_center = self.distance_to_center(state)
        edge_margin = self.distance_to_edge(state)
        
        # State machine (override for custom logic)
        self._update_state(has_opponent, opp_dist, opp_angle, dist_center, edge_margin)
        
        return self._execute_state(state, has_opponent, opp_dist, opp_angle, dist_center, edge_margin)
    
    def _update_state(self, has_opponent: bool, opp_dist: float, opp_angle: float, 
                      dist_center: float, edge_margin: float):
        """Default state machine - override for custom logic."""
        prev = self.behavior_state
        
        if edge_margin < self.edge_margin:
            self.behavior_state = "RETREAT"
        elif has_opponent:
            if opp_dist < self.attack_distance:
                self.behavior_state = "ATTACK"
            elif opp_dist < self.defend_distance:
                self.behavior_state = "APPROACH"
            else:
                self.behavior_state = "SEARCH"
        elif dist_center > 0.4:
            self.behavior_state = "DEFEND"
        else:
            self.behavior_state = "SEARCH"
        
        if self.behavior_state != prev:
            self.state_timer = 0.0
    
    def _execute_state(self, state: RobotState, has_opponent: bool, opp_dist: float,
                       opp_angle: float, dist_center: float, edge_margin: float) -> Command:
        if self.behavior_state == "SEARCH":
            return self.search_behavior(state)
        elif self.behavior_state == "APPROACH":
            return self.approach_behavior(state, opp_dist, opp_angle)
        elif self.behavior_state == "ATTACK":
            return self.attack_behavior(state, opp_dist, opp_angle)
        elif self.behavior_state == "DEFEND":
            return self.defend_behavior(state)
        elif self.behavior_state == "RETREAT":
            return self.retreat_behavior(state)
        return Command(v=0.0, omega=0.0)


# ============================================================
# EXAMPLE STRATEGIES
# ============================================================

class AggressiveStrategy(CompetitionAgent):
    """Always charge at opponent."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Aggressive"
        self.attack_distance = 1.0  # Attack from anywhere
        self.attack_speed = 3.0
        self.search_omega = 3.0
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        opp = self.get_opponent(neighbors)
        if opp is None:
            return Command(v=0.0, omega=self.search_omega)
        
        angle = self.angle_to_opponent(state, neighbors)
        if abs(angle) > 0.15:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=1.0, omega=turn)
        return Command(v=self.attack_speed, omega=0.0)


class DefensiveStrategy(CompetitionAgent):
    """Stay in center, counter-attack."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Defensive"
        self.attack_distance = 0.35
        self.defend_distance = 0.6
        self.edge_margin = 0.2
        self.attack_speed = 2.5
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        dist_center = self.distance_to_center(state)
        opp = self.get_opponent(neighbors)
        
        if opp is None or dist_center > 0.3:
            return self.defend_behavior(state)
        
        angle = self.angle_to_opponent(state, neighbors)
        dist = self.distance_to_opponent(state, neighbors)
        
        if dist < self.attack_distance:
            if abs(angle) > 0.15:
                turn = self.max_omega if angle > 0 else -self.max_omega
                return Command(v=0.5, omega=turn)
            return Command(v=self.attack_speed, omega=0.0)
        
        return self.defend_behavior(state)


class SensorStrategy(CompetitionAgent):
    """Uses simulated sensor logic for edge/opponent detection."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Sensor-Based"
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # Simulated sensors
        edge_dist = self.distance_to_edge(state)
        opp = self.get_opponent(neighbors)
        
        # Edge sensor triggered
        if edge_dist < 0.15:
            angle = self.angle_to_center(state)
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=1.5, omega=turn * 0.5)
        
        if opp is None:
            return Command(v=1.0, omega=0.5)  # Patrol
        
        dist = self.distance_to_opponent(state, neighbors)
        angle = self.angle_to_opponent(state, neighbors)
        
        if dist < 0.4:
            # Close combat
            if abs(angle) > 0.1:
                turn = self.max_omega if angle > 0 else -self.max_omega
                return Command(v=1.0, omega=turn)
            return Command(v=3.0, omega=0.0)
        else:
            # Approach
            if abs(angle) > 0.3:
                turn = self.max_omega if angle > 0 else -self.max_omega
                return Command(v=0.5, omega=turn)
            return Command(v=1.5, omega=0.0)


# ============================================================
# COMPETITION GUI OVERLAY
# ============================================================

class CompetitionGUI:
    """GUI overlay for sumo competition."""
    
    def __init__(self, config: TournamentConfig):
        self.config = config
        self.referee: Optional[SumoReferee] = None
        
    def set_referee(self, referee: SumoReferee):
        self.referee = referee
    
    def draw(self, screen, font, robot_states: Dict[int, RobotState], 
             team1_name: str = "TIME 1", team2_name: str = "TIME 2",
             team1_color: Tuple[int, int, int] = (30, 144, 255),
             team2_color: Tuple[int, int, int] = (220, 20, 60)):
        """Draw competition overlay."""
        if not self.referee:
            return
        
        self.screen = screen
        self.font = font
        
        # Match info panel (top center)
        self._draw_match_panel(team1_name, team2_name, team1_color, team2_color)
        
        # Robot status indicators (bottom)
        self._draw_robot_status(robot_states, team1_color, team2_color)
    
    def _draw_match_panel(self, team1_name, team2_name, c1, c2):
        """Draw match info at top center."""
        w, h = self.screen.get_size()
        panel_w = 500
        panel_h = 100
        x = (w - panel_w) // 2
        y = 10
        
        # Background
        overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (x, y))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, panel_w, panel_h), 2)
        
        # Status text
        status = self.referee.get_status_text()
        status_surf = self.font.render(status, True, (255, 255, 255))
        self.screen.blit(status_surf, (x + 10, y + 10))
        
        # Team names and scores
        time_rem = self.referee.get_match_time_remaining()
        time_surf = self.font.render(f"TEMPO: {time_rem:.1f}s", True, (255, 255, 0))
        self.screen.blit(time_surf, (x + 10, y + 35))
        
        # Team 1
        t1_surf = self.font.render(f"● {team1_name}", True, c1)
        self.screen.blit(t1_surf, (x + 10, y + 60))
        
        # Team 2
        t2_surf = self.font.render(f"● {team2_name}", True, c2)
        t2_rect = t2_surf.get_rect(right=x + panel_w - 10, top=y + 60)
        self.screen.blit(t2_surf, t2_rect)
    
    def _draw_robot_status(self, robot_states, c1, c2):
        """Draw robot status at bottom."""
        w, h = self.screen.get_size()
        
        for i, (robot_id, state) in enumerate(robot_states.items()):
            color = c1 if robot_id == 0 else c2
            dist_center = math.hypot(state.x, state.y)
            effective_radius = self.config.ring_radius - self.config.robot_radius - self.config.border_width
            edge_dist = effective_radius - dist_center
            
            status = "DENTRO" if edge_dist > 0 else "FORA!"
            text = f"BOT{robot_id}: ({state.x:.2f}, {state.y:.2f}) | Centro: {dist_center:.2f}m | Borda: {edge_dist:.2f}m | {status}"
            
            surf = self.font.render(text, True, color)
            y = h - 30 - i * 25
            x = 10
            
            # Background
            overlay = pygame.Surface((surf.get_width() + 20, surf.get_height() + 4), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (x - 5, y - 2))
            
            self.screen.blit(surf, (x, y))


# ============================================================
# COMPETITION RUNNER
# ============================================================

def create_competition_config(config: TournamentConfig = None) -> dict:
    """Create simulation config for competition."""
    cfg = config or TournamentConfig()
    
    # Create circular boundary obstacles
    num_segments = 48
    obstacles = []
    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        r = cfg.ring_radius + cfg.robot_radius + 0.015
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        obstacles.append([x, y, 0.025])
    
    return {
        "window": {
            "width": 1200,
            "height": 900,
            "min_width": 1000,
            "min_height": 700,
            "panel_width": 350,
            "title": "Robot Sumo Competition - RoboCore"
        },
        "world": {
            "width": 3.0,
            "height": 3.0,
            "grid_size": 0.5,
            "show_origin": True,
            "show_axes": False,
            "default_obstacle_radius": 0.4,
            "obstacles": obstacles
        },
        "camera": {
            "initial_zoom": 1.8, "min_zoom": 0.25, "max_zoom": 8.0,
            "zoom_step": 1.1, "margin_x": 1.0, "margin_y": 1.0
        },
        "robot": {
            "type": "differential",
            "radius": cfg.robot_radius,
            "length": 0.20,
            "width": 0.20,
            "wheel_base": 0.16,
            "max_speed": cfg.max_speed,
            "max_omega": cfg.max_omega,
            "max_steer": 0.52,
            "path_max_length": 2000,
            "tau_v": 0.2
        },
        "colors": {
            "background": [20, 20, 30],
            "grid": [40, 40, 55],
            "panel": [15, 15, 25],
            "robot": [30, 144, 255],
            "obstacle": [255, 255, 255],
            "waypoint": [255, 140, 0],
            "goal": [57, 255, 20],
            "path": [30, 144, 255],
            "lidar": [0, 255, 255],
            "red": [220, 50, 50],
            "green": [0, 255, 0],
            "white": [255, 255, 255],
            "black": [0, 0, 0],
            "silver": [192, 192, 186],
            "fleet": [[30, 144, 255], [220, 20, 60]]
        },
        "interaction": {
            "collision_policy": "resolve",
            "robot_collision": True,
            "robot_safety_margin": 0.0,
            "resolve_push": 0.08,
            "comm_radius": 3.0,
            "show_robot_links": False
        },
        "lidar": {"enabled": True, "num_rays": 72, "range": 2.0, "fov_deg": 360},
        "noise": {"enabled": False, "sigma_v": 0.0, "sigma_omega": 0.0, "limit": 3.0},
        "controller": {"enabled": False},
        "waypoints": {"goal_tolerance": 0.5, "define_orientation": False, 
                     "show_tolerance_circle": False, "points": []},
        "theme": "dark",
        "running_simulation": False,
        # Sumo-specific
        "sumo": {
            "ring_radius": cfg.ring_radius,
            "robot_radius": cfg.robot_radius,
            "border_width": cfg.border_width,
            "start_distance": cfg.start_distance,
            "match_duration": cfg.match_duration
        }
    }


def run_match(team1_agent, team2_agent, team1_name="TIME 1", team2_name="TIME 2",
              team1_color=(30, 144, 255), team2_color=(220, 20, 60),
              config: TournamentConfig = None):
    """Run a single sumo match with referee and GUI."""
    
    cfg = config or TournamentConfig()
    sim_config = create_competition_config(cfg)
    
    # Starting positions: Y-axis, facing each other
    sim_config["robots"] = [
        {"id": 0, "initial_pose": [0.0, cfg.start_distance, -math.pi/2], "color": list(team1_color)},
        {"id": 1, "initial_pose": [0.0, -cfg.start_distance, math.pi/2], "color": list(team2_color)}
    ]
    
    # Create experiment
    experiment = SwarmExperiment(
        robots=sim_config["robots"],
        backend="navsim2d",
        config=sim_config,
        dt=0.03,
        comm_radius=3.0
    )
    
    # Assign agents
    experiment.assign_agent(robot_id=0, agent_class=team1_agent)
    experiment.assign_agent(robot_id=1, agent_class=team2_agent)
    
    # Build and set opponents
    experiment._build()
    agent1 = experiment.agents.get(0)
    agent2 = experiment.agents.get(1)
    if agent1 and agent2:
        agent1.set_opponent(1)
        agent2.set_opponent(0)
    
    # Create referee
    referee = SumoReferee(cfg)
    referee.register_team(0, TeamInfo("team1", team1_name, team1_agent, team1_color))
    referee.register_team(1, TeamInfo("team2", team2_name, team2_agent, team2_color))
    referee.start_match()
    
    # Create competition GUI
    comp_gui = CompetitionGUI(cfg)
    comp_gui.set_referee(referee)
    
    # Hook referee into simulation
    original_build = experiment._ensure_backend
    
    def custom_build():
        backend = original_build()
        if hasattr(backend, '_sim') and backend._sim:
            sim = backend._sim
            
            # Store original update_simulation
            original_update = sim.update_simulation
            
            def update_with_referee():
                original_update()
                
                # Update referee after physics step
                if referee.status == MatchStatus.IN_PROGRESS:
                    robot_states = {}
                    for i, robot in enumerate(sim.robots):
                        robot_states[i] = _state_from_robot(i, robot, None)
                    
                    result = referee.update(robot_states, sim.dt)
                    if result:
                        print(f"\n{'='*50}")
                        print(f"MATCH ENDED: {referee.get_status_text()}")
                        print(f"Duration: {result.duration:.1f}s")
                        print(f"Winner: {referee.team_info[result.winner_team_id].name if result.winner_team_id else 'DRAW'}")
                        print(f"{'='*50}")
                        # Stop simulation
                        sim.running_simulation = False
            
            sim.update_simulation = update_with_referee
            
            # Add draw callback for competition GUI
            original_draw = sim.draw
            def draw_with_comp(fps):
                original_draw(fps)
                # Get robot states for GUI
                robot_states = {}
                for i, robot in enumerate(sim.robots):
                    robot_states[i] = _state_from_robot(i, robot, None)
                comp_gui.draw(sim.screen, sim.font, robot_states, 
                             team1_name, team2_name, team1_color, team2_color)
            sim.draw = draw_with_comp
        
        return backend
    
    experiment._ensure_backend = custom_build
    
    # Run
    experiment.run()
    
    return referee.result


# ============================================================
# TEAM STRATEGY TEMPLATE
# ============================================================

"""
COMO CRIAR SEU ROBÔ PARA A COMPETIÇÃO:

1. Copie este arquivo para: minha_equipe.py

2. Crie sua classe herdando de CompetitionAgent:

```python
from sumo_referee import CompetitionAgent, Command, RobotState
from typing import Dict
import math

class MinhaEquipeAgent(CompetitionAgent):
    def __init__(self, robot_id=None, config=None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Minha Equipe"
        
        # Ajuste estes parâmetros para sua estratégia:
        self.attack_distance = 0.5    # Distância para atacar
        self.defend_distance = 0.8    # Distância para se aproximar
        self.edge_margin = 0.15       # Margem de segurança da borda
        self.attack_speed = 3.0       # Velocidade de ataque
        self.approach_speed = 1.5     # Velocidade de aproximação
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # SEU CÓDIGO AQUI!
        # Use os métodos helper:
        # - self.is_in_ring(x, y)
        # - self.distance_to_opponent(state, neighbors)
        # - self.angle_to_opponent(state, neighbors)
        # - self.distance_to_center(state)
        # - self.angle_to_center(state)
        # - self.distance_to_edge(state)
        # - self.predict_opponent(0.5)
        # - self.get_ring_quadrant(state)
        
        # Retorne Command(v, omega)
        return Command(v=0.0, omega=0.0)
```

3. Para testar:
```python
from sumo_referee import run_match, AggressiveStrategy
from minha_equipe import MinhaEquipeAgent

run_match(MinhaEquipeAgent, AggressiveStrategy, "Minha Equipe", "Agressivo")
```

4. Para torneio:
```python
from sumo_referee import TournamentManager, TeamInfo

tourney = TournamentManager()
tourney.add_team(TeamInfo("eq1", "Equipe 1", MinhaEquipeAgent))
tourney.add_team(TeamInfo("eq2", "Equipe 2", OutraEquipeAgent))
tourney.add_team(TeamInfo("eq3", "Equipe 3", TerceiraEquipeAgent))
tourney.generate_pairings()
# ... rodar partidas
```
"""


# ============================================================
# MAIN - Demo
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SUMO REFEREE SYSTEM - RoboCore")
    print("=" * 60)
    print()
    print("Este módulo fornece:")
    print("  - SumoReferee: Árbitro que detecta saída do dohyo")
    print("  - TournamentManager: Gerencia campeonatos")
    print("  - CompetitionAgent: Classe base para estratégias")
    print("  - run_match(): Executa partida única com GUI")
    print()
    print("Estratégias de exemplo incluídas:")
    print("  - AggressiveStrategy: Sempre ataca")
    print("  - DefensiveStrategy: Fica no centro, contra-ataca")
    print("  - SensorStrategy: Usa lógica de sensores simulados")
    print()
    print("Para usar:")
    print("  from sumo_referee import run_match, AggressiveStrategy")
    print("  from sua_equipe import SuaEquipeAgent")
    print("  run_match(SuaEquipeAgent, AggressiveStrategy)")