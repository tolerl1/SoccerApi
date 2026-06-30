"""Poisson-based match outcome simulator."""

import math
import random
from dataclasses import dataclass, field

from .world_cup_2026 import AVERAGE_GOALS

# Home advantage multiplier when not at a neutral venue
HOME_ADVANTAGE = 1.10


@dataclass
class MatchResult:
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    went_to_extra_time: bool = False
    went_to_penalties: bool = False
    penalty_winner: str | None = None

    @property
    def winner(self) -> str | None:
        if self.went_to_penalties:
            return self.penalty_winner
        if self.home_goals > self.away_goals:
            return self.home_team
        if self.away_goals > self.home_goals:
            return self.away_team
        return None  # draw (only valid in group stage)


def _poisson_sample(lam: float) -> int:
    """Sample from a Poisson distribution using Knuth's algorithm."""
    if lam <= 0:
        return 0
    L = math.exp(-min(lam, 700))  # cap to avoid underflow
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def compute_match_lambdas(
    home_xgf: float,
    home_xga: float,
    away_xgf: float,
    away_xga: float,
    neutral_venue: bool = True,
) -> tuple[float, float]:
    """
    Derive per-match Poisson goal-rate parameters from team ratings.

    Formula: lambda_home = (home_xgf * away_xga) / AVERAGE_GOALS
    This preserves the definition that xGF/xGA are expressed vs. an average team.
    """
    lam_home = (home_xgf * away_xga) / AVERAGE_GOALS
    lam_away = (away_xgf * home_xga) / AVERAGE_GOALS

    if not neutral_venue:
        lam_home *= HOME_ADVANTAGE
        lam_away /= HOME_ADVANTAGE

    return max(lam_home, 0.01), max(lam_away, 0.01)


def simulate_match(
    home_team: str,
    home_xgf: float,
    home_xga: float,
    away_team: str,
    away_xgf: float,
    away_xga: float,
    knockout: bool = False,
    neutral_venue: bool = True,
) -> MatchResult:
    """
    Simulate a single match.

    In group-stage mode (knockout=False) draws are final.
    In knockout mode (knockout=True) a draw triggers extra time (~30 min),
    and if still level, a penalty shootout (50/50).
    """
    lam_home, lam_away = compute_match_lambdas(
        home_xgf, home_xga, away_xgf, away_xga, neutral_venue
    )

    home_goals = _poisson_sample(lam_home)
    away_goals = _poisson_sample(lam_away)

    went_to_extra_time = False
    went_to_penalties = False
    penalty_winner: str | None = None

    if knockout and home_goals == away_goals:
        went_to_extra_time = True
        # Extra time ≈ 30 min → ~33 % of a normal 90-min game
        et_home = _poisson_sample(lam_home * 0.33)
        et_away = _poisson_sample(lam_away * 0.33)
        home_goals += et_home
        away_goals += et_away

        if home_goals == away_goals:
            went_to_penalties = True
            penalty_winner = home_team if random.random() < 0.5 else away_team

    return MatchResult(
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        home_xg=round(lam_home, 3),
        away_xg=round(lam_away, 3),
        went_to_extra_time=went_to_extra_time,
        went_to_penalties=went_to_penalties,
        penalty_winner=penalty_winner,
    )
