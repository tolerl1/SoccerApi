"""
Monte Carlo tournament simulator.

Runs N independent full-tournament simulations and aggregates the results
into per-team stage-progression probabilities, matching the output format
described in The Athletic's World Cup Tracker.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from .tournament import simulate_full_tournament
from .world_cup_2026 import TEAM_RATINGS


@dataclass
class TeamProbabilities:
    team: str
    make_round_of_32: float = 0.0
    make_round_of_16: float = 0.0
    make_quarterfinals: float = 0.0
    make_semifinals: float = 0.0
    make_final: float = 0.0
    win_world_cup: float = 0.0
    simulations: int = 0


def run_monte_carlo(
    n_simulations: int = 10_000,
    team_ratings: dict | None = None,
) -> dict[str, TeamProbabilities]:
    """
    Run `n_simulations` complete WC 2026 tournament simulations.

    Returns a dict mapping team name → TeamProbabilities with stage
    probabilities expressed as floats in [0, 1].
    """
    if team_ratings is None:
        team_ratings = TEAM_RATINGS

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for _ in range(n_simulations):
        result = simulate_full_tournament(team_ratings)

        counts[result.champion]["champion"] += 1
        counts[result.finalist]["finalist"] += 1
        for team in result.semifinalists:
            counts[team]["semifinal"] += 1
        for team in result.quarterfinalists:
            counts[team]["quarterfinal"] += 1
        for team in result.round_of_16:
            counts[team]["round_of_16"] += 1
        for team in result.round_of_32:
            counts[team]["round_of_32"] += 1

    probabilities: dict[str, TeamProbabilities] = {}
    for team in team_ratings:
        c = counts[team]
        r32 = c["round_of_32"] / n_simulations
        r16 = c["round_of_16"] / n_simulations
        qf = c["quarterfinal"] / n_simulations
        sf = c["semifinal"] / n_simulations
        final = c["finalist"] / n_simulations
        win = c["champion"] / n_simulations

        probabilities[team] = TeamProbabilities(
            team=team,
            make_round_of_32=round(r32, 4),
            make_round_of_16=round(r16, 4),
            make_quarterfinals=round(qf, 4),
            make_semifinals=round(sf, 4),
            make_final=round(final, 4),
            win_world_cup=round(win, 4),
            simulations=n_simulations,
        )

    return probabilities
