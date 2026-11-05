"""Run a full GUI match with referee."""

from sumo_referee import run_match, AggressiveStrategy, DefensiveStrategy, TournamentConfig

# Run a match with 10 second duration
config = TournamentConfig(match_duration=10.0)
result = run_match(AggressiveStrategy, DefensiveStrategy, 'Agressivo', 'Defensivo', config=config)

print('\nFINAL RESULT:')
print(f"  Winner: {result.winner_team_id}")
print(f"  Reason: {result.reason}")
print(f"  Duration: {result.duration:.1f}s")