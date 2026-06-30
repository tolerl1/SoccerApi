"""
World Cup 2026 tournament simulator.

Covers:
  - Group stage (12 groups of 4, round-robin)
  - Qualifier selection (top 2 per group + 8 best 3rd-place teams = 32)
  - Knockout bracket (R32 → R16 → QF → SF → Final)
"""

from dataclasses import dataclass, field
from typing import Optional

from .match_simulator import MatchResult, simulate_match
from .world_cup_2026 import GROUPS


@dataclass
class GroupStanding:
    team: str
    group: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def sort_key(self) -> tuple:
        return (self.points, self.goal_difference, self.goals_for)


@dataclass
class TournamentResult:
    champion: str
    finalist: str
    semifinalists: list[str]
    quarterfinalists: list[str]
    round_of_16: list[str]
    round_of_32: list[str]
    group_stage_exit: list[str]


def _sort_standings(standings: list[GroupStanding]) -> list[GroupStanding]:
    return sorted(standings, key=lambda s: s.sort_key(), reverse=True)


def simulate_group(group_name: str, teams: list[str], team_ratings: dict) -> list[GroupStanding]:
    """Simulate all 6 round-robin matches in one group and return sorted standings."""
    standings = {t: GroupStanding(team=t, group=group_name) for t in teams}

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            home, away = teams[i], teams[j]
            home_r = team_ratings[home]
            away_r = team_ratings[away]

            result = simulate_match(
                home, home_r["xgf"], home_r["xga"],
                away, away_r["xgf"], away_r["xga"],
                knockout=False,
                neutral_venue=True,
            )

            standings[home].played += 1
            standings[away].played += 1
            standings[home].goals_for += result.home_goals
            standings[home].goals_against += result.away_goals
            standings[away].goals_for += result.away_goals
            standings[away].goals_against += result.home_goals

            if result.home_goals > result.away_goals:
                standings[home].won += 1
                standings[home].points += 3
                standings[away].lost += 1
            elif result.away_goals > result.home_goals:
                standings[away].won += 1
                standings[away].points += 3
                standings[home].lost += 1
            else:
                standings[home].drawn += 1
                standings[home].points += 1
                standings[away].drawn += 1
                standings[away].points += 1

    return _sort_standings(list(standings.values()))


def simulate_group_stage(team_ratings: dict) -> dict[str, list[GroupStanding]]:
    """Simulate all 12 group-stage groups. Returns standings per group."""
    return {
        group_name: simulate_group(group_name, teams, team_ratings)
        for group_name, teams in GROUPS.items()
    }


def get_qualifiers(
    group_standings: dict[str, list[GroupStanding]],
) -> tuple[dict[str, GroupStanding], dict[str, GroupStanding], list[GroupStanding]]:
    """
    Returns:
      winners   – {group_letter: GroupStanding}  (12 teams)
      runners_up – {group_letter: GroupStanding} (12 teams)
      best_third – [GroupStanding]               (8 teams, sorted desc)
    """
    winners: dict[str, GroupStanding] = {}
    runners_up: dict[str, GroupStanding] = {}
    third_places: list[GroupStanding] = []

    for group_letter, standings in group_standings.items():
        winners[group_letter] = standings[0]
        runners_up[group_letter] = standings[1]
        third_places.append(standings[2])

    best_third = sorted(third_places, key=lambda s: s.sort_key(), reverse=True)[:8]
    return winners, runners_up, best_third


def _simulate_round(pairs: list[tuple[str, str]], team_ratings: dict) -> list[str]:
    """Play one knockout round and return the list of winners."""
    match_winners = []
    for home, away in pairs:
        home_r = team_ratings[home]
        away_r = team_ratings[away]
        result = simulate_match(
            home, home_r["xgf"], home_r["xga"],
            away, away_r["xgf"], away_r["xga"],
            knockout=True,
            neutral_venue=True,
        )
        match_winners.append(result.winner)
    return match_winners


def _make_bracket(teams: list[str]) -> list[tuple[str, str]]:
    """Pair teams as (1st vs last, 2nd vs 2nd-last, …) – standard seeded bracket."""
    n = len(teams)
    return [(teams[i], teams[n - 1 - i]) for i in range(n // 2)]


def simulate_knockout_stage(
    winners: dict[str, GroupStanding],
    runners_up: dict[str, GroupStanding],
    best_third: list[GroupStanding],
    team_ratings: dict,
) -> dict:
    """
    Simulate the full knockout stage and return a dict with each round's participants.

    R32 structure:
      - 12 matches: each group winner vs. runner-up from the *next* group (cyclically)
      - 4 matches: best 4 third-place teams vs. worst 4 third-place teams
        (i.e. 3rd-place seeded bracket among themselves)
    """
    group_letters = sorted(winners.keys())

    # Build the 24 fixed R32 pairings: winner[i] vs runner_up[i+1 mod 12]
    fixed_pairs: list[tuple[str, str]] = []
    for idx, letter in enumerate(group_letters):
        next_letter = group_letters[(idx + 1) % len(group_letters)]
        fixed_pairs.append((winners[letter].team, runners_up[next_letter].team))

    # 8 best third-place teams play each other (seeded bracket within themselves)
    third_teams = [s.team for s in best_third]
    third_pairs: list[tuple[str, str]] = _make_bracket(third_teams)

    r32_pairs = fixed_pairs + third_pairs  # 16 total matches

    r32_participants = [t for pair in r32_pairs for t in pair]
    r32_winners = _simulate_round(r32_pairs, team_ratings)

    r16_pairs = _make_bracket(r32_winners)
    r16_participants = list(r32_winners)
    r16_winners = _simulate_round(r16_pairs, team_ratings)

    qf_pairs = _make_bracket(r16_winners)
    qf_participants = list(r16_winners)
    qf_winners = _simulate_round(qf_pairs, team_ratings)

    sf_pairs = _make_bracket(qf_winners)
    sf_participants = list(qf_winners)
    sf_winners = _simulate_round(sf_pairs, team_ratings)

    final_pair = [(sf_winners[0], sf_winners[1])]
    final_result = _simulate_round(final_pair, team_ratings)
    champion = final_result[0]
    finalist = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]

    return {
        "round_of_32": r32_participants,
        "round_of_16": r16_participants,
        "quarterfinals": qf_participants,
        "semifinals": sf_participants,
        "finalist": finalist,
        "champion": champion,
    }


def simulate_full_tournament(team_ratings: dict) -> TournamentResult:
    """Run one complete World Cup 2026 simulation and return the result."""
    group_standings = simulate_group_stage(team_ratings)
    winners, runners_up, best_third = get_qualifiers(group_standings)

    ko = simulate_knockout_stage(winners, runners_up, best_third, team_ratings)

    all_teams = set(team_ratings.keys())
    r32_set = set(ko["round_of_32"])
    group_stage_exit = sorted(all_teams - r32_set)

    return TournamentResult(
        champion=ko["champion"],
        finalist=ko["finalist"],
        semifinalists=ko["semifinals"],
        quarterfinalists=ko["quarterfinals"],
        round_of_16=ko["round_of_16"],
        round_of_32=ko["round_of_32"],
        group_stage_exit=group_stage_exit,
    )
