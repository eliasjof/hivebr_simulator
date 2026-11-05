"""Quick test of the referee system."""

from sumo_referee import run_match, AggressiveStrategy, DefensiveStrategy, TournamentConfig

# Quick test with shorter duration
config = TournamentConfig(match_duration=5.0)
result = run_match(AggressiveStrategy, DefensiveStrategy, 'Agressivo', 'Defensivo', config=config)
print('Result:', result)