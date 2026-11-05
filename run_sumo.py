#!/usr/bin/env python
"""
Robot Sumo Competition Runner
==============================
Simple script to run sumo matches between two group strategies.

Usage:
    python run_sumo.py group1_strategy.py group2_strategy.py
    python run_sumo.py --tournament group1_strategy.py group2_strategy.py
    python run_sumo.py --help
"""

import sys
import argparse
import importlib.util
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sumo_competition_advanced import run_competition, run_tournament


def load_agent_class(filepath: str, class_name: str = "MySumoAgent"):
    """Load agent class from a Python file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {filepath}")
    
    # Load module
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get agent class
    if not hasattr(module, class_name):
        raise AttributeError(f"Class '{class_name}' not found in {filepath}")
    
    return getattr(module, class_name)


def main():
    parser = argparse.ArgumentParser(
        description="Run Robot Sumo Competition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_sumo.py group1.py group2.py
  python run_sumo.py -t group1.py group2.py
  python run_sumo.py --group1 group1.py --group2 group2.py --matches 5
        """
    )
    
    parser.add_argument(
        "group1", nargs="?", 
        help="Path to Group 1 strategy file (default: group_strategy_template.py)"
    )
    parser.add_argument(
        "group2", nargs="?",
        help="Path to Group 2 strategy file (default: group_strategy_template.py)"
    )
    parser.add_argument(
        "-t", "--tournament", action="store_true",
        help="Run tournament mode (multiple matches)"
    )
    parser.add_argument(
        "-m", "--matches", type=int, default=3,
        help="Number of matches in tournament (default: 3)"
    )
    parser.add_argument(
        "--class-name", default="MySumoAgent",
        help="Agent class name in strategy files (default: MySumoAgent)"
    )
    parser.add_argument(
        "--list-examples", action="store_true",
        help="List available example strategies in template"
    )
    
    args = parser.parse_args()
    
    if args.list_examples:
        print("Available example strategies in group_strategy_template.py:")
        print("  - MySumoAgent (template - implement your own)")
        print("  - AggressiveRusher (always charge)")
        print("  - DefensiveCenter (stay in center)")
        print("  - SensorBasedBot (sensor-based decisions)")
        return
    
    # Default to template if not provided
    group1_file = args.group1 or "group_strategy_template.py"
    group2_file = args.group2 or "group_strategy_template.py"
    
    try:
        print(f"Loading Group 1 from: {group1_file}")
        Group1Agent = load_agent_class(group1_file, args.class_name)
        
        print(f"Loading Group 2 from: {group2_file}")
        Group2Agent = load_agent_class(group2_file, args.class_name)
        
    except (FileNotFoundError, AttributeError) as e:
        print(f"Error: {e}")
        print("\nMake sure your strategy file contains a class named 'MySumoAgent'")
        print("Or specify a different class name with --class-name")
        sys.exit(1)
    
    print(f"\nGroup 1: {Group1Agent.__name__} from {group1_file}")
    print(f"Group 2: {Group2Agent.__name__} from {group2_file}")
    
    if args.tournament:
        print(f"\nRunning tournament: {args.matches} matches")
        run_tournament(Group1Agent, Group2Agent, num_matches=args.matches)
    else:
        print("\nRunning single match...")
        run_competition(Group1Agent, Group2Agent)


if __name__ == "__main__":
    main()