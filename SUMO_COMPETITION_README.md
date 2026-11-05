# Robot Sumo Competition - RoboCore Style

A complete framework for running autonomous robot sumo competitions using the HiveBR simulator.

## Overview

This package provides everything needed to run a **RoboCore Mini Sumo** style competition:

- **Circular arena (dohyo)**: 1.54m diameter with 5cm white border (shikiri-sen)
- **Two differential drive robots**: 20cm diameter, 3kg max weight class
- **Autonomous control only**: No remote control allowed
- **Group vs Group**: Each team provides their own robot AI strategy
- **Physics-based simulation**: Realistic collision, pushing, and kinematics

## Quick Start

### 1. Run the Demo Match

```bash
python sumo_competition_advanced.py
```

This runs a match between two built-in example strategies (Group 1 vs Group 2).

### 2. Create Your Own Strategy

Copy the template and implement your strategy:

```bash
cp group_strategy_template.py my_team_strategy.py
# Edit my_team_strategy.py with your algorithm
```

### 3. Run Your Strategy Against the Example

```bash
python run_sumo.py my_team_strategy.py
```

### 4. Run a Tournament

```bash
python run_sumo.py --tournament team1_strategy.py team2_strategy.py --matches 5
```

## Competition Rules (Simplified RoboCore Mini Sumo)

| Parameter | Value |
|-----------|-------|
| Ring Diameter | 1.54 m |
| Ring Border | 5 cm white (shikiri-sen) |
| Robot Max Diameter | 20 cm |
| Robot Max Weight | 3 kg |
| Match Duration | 30 seconds |
| Starting Distance | 45 cm from center |
| Control | Fully autonomous |

**Winning Conditions:**
- Push opponent completely out of the ring (over the white border)
- If time expires: robot closer to center wins
- If both out simultaneously: draw

## File Structure

```
hivebr_simulator/
├── sumo_competition.py           # Basic competition framework
├── sumo_competition_advanced.py  # Advanced with custom rendering
├── run_sumo.py                   # Command-line runner
├── group_strategy_template.py    # Template for team strategies
├── config/
│   └── sumo_competition.yaml     # YAML configuration
└── SUMO_COMPETITION_README.md    # This file
```

## Creating a Team Strategy

### 1. Copy the Template

```bash
cp group_strategy_template.py team_alpha_strategy.py
```

### 2. Implement Your Strategy

Edit `team_alpha_strategy.py` and modify the `MySumoAgent.loop()` method:

```python
def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
    # state: your robot's state (x, y, theta, v, omega, radius, battery)
    # neighbors: dict of visible robots {robot_id: RobotState}
    
    # Your strategy here!
    # Return Command(v, omega) where:
    #   v = linear velocity (-3.0 to 3.0 m/s)
    #   omega = angular velocity (-6.0 to 6.0 rad/s)
    
    return Command(v=1.0, omega=0.0)
```

### 3. Available Helper Methods

```python
# Check if position is in ring
self.is_in_ring(x, y, margin=0.0)

# Get opponent info
self.get_opponent(neighbors)                    # Returns RobotState or None
self.distance_to_opponent(state, neighbors)     # Float or None
self.angle_to_opponent(state, neighbors)        # Radians (-pi to pi) or None

# Navigation
self.distance_to_center(state)                  # Distance from ring center
self.angle_to_center(state)                     # Angle toward center
self.angle_to_target(state, tx, ty)             # Angle to any target

# Opponent tracking
self.update_opponent_tracking(neighbors, dt)    # Call each step
self.predict_opponent(lookahead=0.5)            # Predict future position
```

### 4. Example Strategies Included

The template includes ready-to-use examples:

- **AggressiveRusher**: Always charges at opponent
- **DefensiveCenter**: Stays in center, waits for opponent
- **SensorBasedBot**: Uses simulated sensor logic

Use them directly or as inspiration:

```python
# In your strategy file
from group_strategy_template import AggressiveRusher

class MySumoAgent(AggressiveRusher):
    def __init__(self, ...):
        super().__init__(...)
        self.team_name = "My Custom Rusher"
        # Override parameters
        self.attack_speed = 3.0
```

## Running Competitions

### Single Match (GUI)

```bash
python run_sumo.py team1.py team2.py
```

### Tournament Mode

```bash
python run_sumo.py --tournament team1.py team2.py --matches 7
```

### Using Built-in Examples

```bash
# Group 1 (custom) vs Built-in Advanced Agent
python run_sumo.py my_team.py

# Built-in Group 1 vs Group 2
python sumo_competition_advanced.py
```

## Configuration

The competition uses `config/sumo_competition.yaml` for arena and robot settings.

Key parameters you might want to adjust:

```yaml
robot:
  max_speed: 3.0      # Max linear speed (m/s)
  max_omega: 6.0      # Max angular speed (rad/s)

sumo:
  match_duration: 30.0   # Match time limit (seconds)
  ring_radius: 0.77      # Ring radius (meters)
```

## API Reference

### RobotState (input to your `loop` method)

```python
state.id          # Robot ID (0 or 1)
state.x, state.y  # Position (meters)
state.theta       # Orientation (radians, -pi to pi)
state.v           # Current linear velocity (m/s)
state.omega       # Current angular velocity (rad/s)
state.radius      # Robot radius (meters)
state.battery     # Battery level (0-100%)
```

### Command (return from your `loop` method)

```python
Command(v=1.5, omega=0.5)  # Forward 1.5 m/s, turn left 0.5 rad/s
Command(v=0.0, omega=2.0)  # Spin in place
Command(v=-1.0, omega=0.0) # Reverse
```

### Competition Runner Functions

```python
from sumo_competition_advanced import run_competition, run_tournament

# Single match
run_competition(Group1Agent, Group2Agent)

# Tournament
run_tournament(Group1Agent, Group2Agent, num_matches=5)
```

## Tips for Winning Strategies

1. **Edge Detection**: Always monitor distance to ring edge
2. **Opponent Tracking**: Predict opponent movement, don't just react
3. **Center Control**: Dominate the center for better positioning
4. **State Machine**: Use clear states (SEARCH, APPROACH, ATTACK, DEFEND, RETREAT)
5. **Speed Management**: Full speed isn't always best - control matters
6. **Test Extensively**: Run many matches against different styles

## Troubleshooting

### "Module not found" errors
```bash
# Install dependencies
pip install -r requirements.txt
# Or install package in development mode
pip install -e .
```

### Robot doesn't move
- Check that your `loop()` returns a `Command` object
- Verify `v` and `omega` are within limits
- Ensure you're not accidentally returning `None`

### Simulation runs too slow/fast
- Adjust `dt` in config (default 0.03 = 30ms = ~33 FPS)
- Check `max_speed` and `max_omega` limits

## Extending the Framework

### Add Sensors
Modify `SumoAgent` to process LiDAR data from `neighbors` or simulator.

### Add Logging
```python
# In your agent
import logging
logger = logging.getLogger(__name__)
logger.info(f"Attacking at distance {dist}")
```

### Custom Arena
Modify `create_competition_config()` in `sumo_competition_advanced.py`.

## License

Part of HiveBR Simulator project. See LICENSE file.

## Credits

Developed for robotics education and research using the HiveBR simulator framework.
Inspired by RoboCore Robot Sumo competitions in Brazil.