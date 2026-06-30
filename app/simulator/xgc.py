"""
Player xGC (Expected Goal Contribution) ratings.

In the full Athletic system, xGC is derived from Opta event data: passes,
carries, shots, and defensive spatial attribution. Since the SoccerApi DB
stores player market values rather than event-level data, we use
market_value_in_gbp as a quality proxy — the Athletic explicitly validates
xGC against Transfermarkt values (Pearson r = 0.65, 80 % pairwise accuracy).

Position groups follow the Athletic's broad definition:
  - Forward: attack_mid, second_striker, centre_forward, left_winger, right_winger
  - Midfielder: central_mid, defensive_mid, left_mid, right_mid
  - Defender: centre_back, left_back, right_back, left_wingback, right_wingback
  - Goalkeeper: goalkeeper
"""

import math
from typing import Any

# Top-player net xGC ceiling observed in the PDF (Lamine Yamal = 0.35)
XGC_MAX = 0.35
# Log-scale reference: £180 M ≈ top market value as of 2025
LOG_TOP_VALUE = math.log(180_000_000)
# Players below this value (£50K) are treated as minimum quality
MIN_MARKET_VALUE = 50_000

# Fraction of net_xgc assigned to the offensive component by position group
POSITION_ATTACK_WEIGHT = {
    "forward":    0.80,
    "midfielder": 0.50,
    "defender":   0.20,
    "goalkeeper": 0.05,
}

FORWARD_SUBS = {
    "attack", "attacking midfield", "second striker",
    "centre-forward", "left winger", "right winger",
    "left wing", "right wing",
}
MIDFIELDER_SUBS = {
    "central midfield", "defensive midfield",
    "left midfield", "right midfield", "midfield",
}
DEFENDER_SUBS = {
    "centre-back", "left-back", "right-back",
    "left wing-back", "right wing-back", "defence",
}
GOALKEEPER_SUBS = {"goalkeeper", "goal"}


def _position_group(position: str | None, sub_position: str | None) -> str:
    sub = (sub_position or "").lower()
    pos = (position or "").lower()
    combined = sub or pos

    if any(k in combined for k in FORWARD_SUBS) or pos == "attack":
        return "forward"
    if any(k in combined for k in MIDFIELDER_SUBS) or pos == "midfield":
        return "midfielder"
    if any(k in combined for k in GOALKEEPER_SUBS) or pos == "goalkeeper":
        return "goalkeeper"
    if any(k in combined for k in DEFENDER_SUBS) or pos == "defence":
        return "defender"
    return "midfielder"  # default


def _net_xgc_from_market_value(market_value: float | None) -> float:
    """
    Map market value (GBP) → net xGC using a log-linear scaling.

    Players at the 95th percentile (≈ top market value) get ~XGC_MAX.
    The median player (log-midpoint) gets ~0.
    Below-average players get negative values (capped at -XGC_MAX).
    """
    v = max(market_value or 0.0, MIN_MARKET_VALUE)
    log_v = math.log(v)
    # Midpoint roughly at £5M in log-scale
    log_mid = math.log(5_000_000)
    # Scale so that top value maps to XGC_MAX
    scale = XGC_MAX / (LOG_TOP_VALUE - log_mid)
    net = (log_v - log_mid) * scale
    return round(max(-XGC_MAX, min(XGC_MAX, net)), 4)


def compute_player_xgc(players: list[Any]) -> list[dict]:
    """
    Compute xGC ratings for a list of Player ORM objects.

    Returns a list of dicts with keys:
      player_id, name, team, position_group,
      net_xgc, offensive_xgc, defensive_xgc, market_value_gbp
    """
    results = []
    for player in players:
        net = _net_xgc_from_market_value(player.market_value_in_gbp)
        group = _position_group(player.position, player.sub_position)
        atk_w = POSITION_ATTACK_WEIGHT[group]

        results.append({
            "player_id": player.player_id,
            "name": player.pretty_name or player.name,
            "team": player.club_pretty_name or player.club_name,
            "position_group": group,
            "net_xgc": net,
            "offensive_xgc": round(net * atk_w, 4),
            "defensive_xgc": round(net * (1 - atk_w), 4),
            "market_value_gbp": player.market_value_in_gbp,
        })

    return sorted(results, key=lambda r: r["net_xgc"], reverse=True)


def compute_team_xgc_from_players(
    players: list[Any],
    top_n: int = 11,
) -> dict[str, dict]:
    """
    Aggregate player xGC into team-level ratings using an equal-minutes
    approximation (top-N players by market value represent the starting XI).

    Returns dict: {team_name: {"xgf": float, "xga": float, "net_gd": float}}
    """
    from .world_cup_2026 import AVERAGE_GOALS

    player_ratings = compute_player_xgc(players)

    # Group by team
    by_team: dict[str, list[dict]] = {}
    for pr in player_ratings:
        team = pr["team"] or "Unknown"
        by_team.setdefault(team, []).append(pr)

    team_ratings: dict[str, dict] = {}
    for team, roster in by_team.items():
        starters = sorted(roster, key=lambda r: r["net_xgc"], reverse=True)[:top_n]
        if not starters:
            continue
        avg_net = sum(r["net_xgc"] for r in starters) / len(starters)
        # xGF/xGA anchored at the league average; net rating shifts them equally
        xgf = round(AVERAGE_GOALS + avg_net / 2, 3)
        xga = round(AVERAGE_GOALS - avg_net / 2, 3)
        team_ratings[team] = {
            "xgf": max(xgf, 0.1),
            "xga": max(xga, 0.1),
            "net_gd": round(avg_net, 4),
        }

    return team_ratings
