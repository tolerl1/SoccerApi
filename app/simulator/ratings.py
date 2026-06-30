"""
Elo-based team rating system derived from historical match data in the DB.

This module computes club-level attack / defense strengths from the `games`
table using an iterative Poisson-regression approach, mirroring the
Elo-style updating described in The Athletic's xGC methodology.
"""

import math
from collections import defaultdict
from typing import Any


# K-factor for Elo updates (controls how fast ratings adjust)
ELO_K = 32
ELO_INIT = 1500.0

# Learning rate for attack/defense strength updates
STRENGTH_LR = 0.05
STRENGTH_INIT = 1.0


def compute_elo_ratings(games: list[Any]) -> dict[int, float]:
    """
    Compute Elo ratings for clubs from a list of Game ORM objects.

    Returns dict: {club_id: elo_rating}
    """
    ratings: dict[int, float] = {}

    for game in games:
        home_id = game.home_club_id
        away_id = game.away_club_id
        if home_id is None or away_id is None:
            continue

        home_goals = game.home_club_goals or 0
        away_goals = game.away_club_goals or 0

        ratings.setdefault(home_id, ELO_INIT)
        ratings.setdefault(away_id, ELO_INIT)

        home_exp = 1.0 / (1.0 + 10 ** ((ratings[away_id] - ratings[home_id]) / 400))
        away_exp = 1.0 - home_exp

        if home_goals > away_goals:
            home_score, away_score = 1.0, 0.0
        elif home_goals < away_goals:
            home_score, away_score = 0.0, 1.0
        else:
            home_score, away_score = 0.5, 0.5

        ratings[home_id] += ELO_K * (home_score - home_exp)
        ratings[away_id] += ELO_K * (away_score - away_exp)

    return ratings


def compute_attack_defense_strengths(games: list[Any]) -> dict[int, dict[str, float]]:
    """
    Compute attack and defense strength multipliers for each club.

    Uses iterative gradient updates on the Poisson log-likelihood:
      expected_home_goals = attack[home] * defense[away] * HOME_ADVANTAGE
      expected_away_goals = attack[away] * defense[home]

    Returns dict: {club_id: {"attack": float, "defense": float}}
    """
    HOME_ADV = 1.1
    attack: dict[int, float] = defaultdict(lambda: STRENGTH_INIT)
    defense: dict[int, float] = defaultdict(lambda: STRENGTH_INIT)

    for _ in range(100):  # iterate to convergence
        for game in games:
            home_id = game.home_club_id
            away_id = game.away_club_id
            if home_id is None or away_id is None:
                continue

            home_goals = game.home_club_goals or 0
            away_goals = game.away_club_goals or 0

            lam_home = max(attack[home_id] * defense[away_id] * HOME_ADV, 1e-6)
            lam_away = max(attack[away_id] * defense[home_id], 1e-6)

            # Gradient of Poisson log-likelihood: d/d_attack = (goals/lambda - 1)
            grad_home_atk = (home_goals / lam_home - 1) * defense[away_id] * HOME_ADV
            grad_away_atk = (away_goals / lam_away - 1) * defense[home_id]
            grad_home_def = -(away_goals / lam_away - 1) * attack[away_id]
            grad_away_def = -(home_goals / lam_home - 1) * attack[home_id] * HOME_ADV

            attack[home_id] = max(attack[home_id] + STRENGTH_LR * grad_home_atk, 0.1)
            attack[away_id] = max(attack[away_id] + STRENGTH_LR * grad_away_atk, 0.1)
            defense[home_id] = max(defense[home_id] + STRENGTH_LR * grad_home_def, 0.1)
            defense[away_id] = max(defense[away_id] + STRENGTH_LR * grad_away_def, 0.1)

    result: dict[int, dict[str, float]] = {}
    for club_id in set(list(attack.keys()) + list(defense.keys())):
        result[club_id] = {
            "attack": round(attack[club_id], 4),
            "defense": round(defense[club_id], 4),
            "xgf": round(attack[club_id] * STRENGTH_INIT * HOME_ADV, 4),
            "xga": round(defense[club_id] * STRENGTH_INIT, 4),
        }

    return result
