"""
Group-stage + knockout simulator — UCL (old format), UEFA Euro, Copa América, WC old.

Format:
  N groups of M teams → round-robin within group → top K per group (+ optional
  best third-place teams) → single-elimination knockout bracket.

Works from the DB (games filtered by competition_id / season), or can be
driven by an explicit team+rating dictionary for pre-season forecasting.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from app.simulator.match_simulator import simulate_match, MatchResult
from .base import CompetitionSimulator, TeamStanding


@dataclass
class KnockoutProbRow:
    club_id: int
    club_name: str
    make_knockout: float
    make_quarterfinals: float
    make_semifinals: float
    make_final: float
    win_competition: float
    simulations: int


def _update_standing(s: TeamStanding, goals_for: int, goals_against: int) -> None:
    s.played += 1
    s.goals_for += goals_for
    s.goals_against += goals_against
    if goals_for > goals_against:
        s.won += 1
        s.points += 3
    elif goals_against > goals_for:
        s.lost += 1
    else:
        s.drawn += 1
        s.points += 1


def simulate_group(
    group_teams: list[int],
    team_names: dict[int, str],
    team_ratings: dict[int, dict],
    fallback: dict,
) -> list[TeamStanding]:
    """Simulate a round-robin group and return sorted standings."""
    standings = {
        cid: TeamStanding(club_id=cid, club_name=team_names.get(cid, str(cid)))
        for cid in group_teams
    }

    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            home_id, away_id = group_teams[i], group_teams[j]
            hr = team_ratings.get(home_id, fallback)
            ar = team_ratings.get(away_id, fallback)
            result = simulate_match(
                str(home_id), hr["xgf"], hr["xga"],
                str(away_id), ar["xgf"], ar["xga"],
                knockout=False, neutral_venue=True,
            )
            _update_standing(standings[home_id], result.home_goals, result.away_goals)
            _update_standing(standings[away_id], result.away_goals, result.home_goals)

    return sorted(standings.values(), key=lambda s: s.sort_key(), reverse=True)


def simulate_knockout_bracket(
    seeds: list[int],
    team_names: dict[int, str],
    team_ratings: dict[int, dict],
    fallback: dict,
) -> dict[str, list[int]]:
    """
    Run a single-elimination bracket for `seeds` teams (must be a power of 2).
    Returns dict with participant lists per round.
    """
    rounds: dict[str, list[int]] = {}
    current = list(seeds)
    round_names = ["round_of_32", "round_of_16", "quarterfinals", "semifinals"]
    round_idx = 0

    while len(current) > 2:
        name = round_names[round_idx] if round_idx < len(round_names) else f"round_{len(current)}"
        rounds[name] = list(current)
        winners = []
        for i in range(0, len(current), 2):
            home_id, away_id = current[i], current[i + 1]
            hr = team_ratings.get(home_id, fallback)
            ar = team_ratings.get(away_id, fallback)
            result = simulate_match(
                str(home_id), hr["xgf"], hr["xga"],
                str(away_id), ar["xgf"], ar["xga"],
                knockout=True, neutral_venue=True,
            )
            winners.append(int(result.winner))
        current = winners
        round_idx += 1

    # Final
    rounds["final_participants"] = list(current)
    if len(current) == 2:
        home_id, away_id = current[0], current[1]
        hr = team_ratings.get(home_id, fallback)
        ar = team_ratings.get(away_id, fallback)
        result = simulate_match(
            str(home_id), hr["xgf"], hr["xga"],
            str(away_id), ar["xgf"], ar["xga"],
            knockout=True, neutral_venue=True,
        )
        rounds["winner"] = int(result.winner)
        rounds["runner_up"] = away_id if result.winner == str(home_id) else home_id
    return rounds


class GroupKnockoutSimulator(CompetitionSimulator):
    """
    Group stage + knockout bracket simulator.

    group_assignments: {group_letter: [club_id, ...]}
      If None, groups are inferred from the DB by clustering teams that
      appear in the same set of fixtures (heuristic for standard group-stage
      competition data).
    advance_per_group: how many from each group proceed (typically 2).
    best_third_count: how many best-third-place teams also qualify (0 = none).
    """

    def __init__(
        self,
        competition_id: str,
        season: str | None,
        db,
        group_assignments: dict[str, list[int]] | None = None,
        advance_per_group: int = 2,
        best_third_count: int = 0,
        home_advantage: float = 0.0,
    ):
        super().__init__(competition_id, season, db)
        self._group_assignments = group_assignments
        self.advance_per_group = advance_per_group
        self.best_third_count = best_third_count
        self.home_advantage = home_advantage

    def get_group_assignments(self) -> dict[str, list[int]]:
        """
        Return group assignments.  Uses the provided dict, or auto-detects
        from DB fixtures by grouping teams that only face each other (group stage pattern).
        """
        if self._group_assignments:
            return self._group_assignments

        # Auto-detect: build a graph of who played whom, then find cliques
        played = self.get_played_games()
        adjacency: dict[int, set[int]] = defaultdict(set)
        for g in played:
            if g.home_club_id and g.away_club_id:
                adjacency[g.home_club_id].add(g.away_club_id)
                adjacency[g.away_club_id].add(g.home_club_id)

        assigned: set[int] = set()
        groups: dict[str, list[int]] = {}
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, (seed, neighbors) in enumerate(adjacency.items()):
            if seed in assigned:
                continue
            group = [seed] + [n for n in neighbors if n not in assigned]
            for t in group:
                assigned.add(t)
            groups[letters[i % 26]] = group

        return groups

    def get_current_standings(self) -> list[TeamStanding]:
        """Group-stage standings from played games only."""
        groups = self.get_group_assignments()
        teams = self.get_teams()
        played_set = {g.home_club_id for g in self.get_played_games()} | {
            g.away_club_id for g in self.get_played_games()
        }

        all_standings: dict[int, TeamStanding] = {}
        for letter, members in groups.items():
            for cid in members:
                all_standings[cid] = TeamStanding(
                    club_id=cid, club_name=teams.get(cid, str(cid))
                )

        for g in self.get_played_games():
            h, a = g.home_club_id, g.away_club_id
            if h not in all_standings or a not in all_standings:
                continue
            hg, ag = int(g.home_club_goals), int(g.away_club_goals)
            _update_standing(all_standings[h], hg, ag)
            _update_standing(all_standings[a], ag, hg)

        return sorted(all_standings.values(), key=lambda s: s.sort_key(), reverse=True)

    def simulate_tournament_once(self) -> dict:
        """Run one full group+knockout simulation. Returns per-round participant IDs."""
        groups = self.get_group_assignments()
        team_names = self.get_teams()
        ratings = self.get_team_ratings()
        fallback = self.FALLBACK_RATING

        # Group stage
        group_winners: list[int] = []
        group_runners: list[int] = []
        third_place: list[TeamStanding] = []

        for _letter, members in sorted(groups.items()):
            table = simulate_group(members, team_names, ratings, fallback)
            group_winners.append(table[0].club_id)
            if self.advance_per_group >= 2:
                group_runners.append(table[1].club_id)
            if self.best_third_count > 0 and len(table) >= 3:
                third_place.append(table[2])

        # Best third-place teams
        best_thirds = sorted(third_place, key=lambda s: s.sort_key(), reverse=True)[
            : self.best_third_count
        ]
        qualifier_ids = group_winners + group_runners + [s.club_id for s in best_thirds]

        # Pad to next power of 2 if needed (re-seed top qualifiers vs extras)
        target = 1
        while target < len(qualifier_ids):
            target *= 2
        while len(qualifier_ids) < target:
            qualifier_ids.append(qualifier_ids[0])  # bye – best team gets double chance

        ko = simulate_knockout_bracket(qualifier_ids, team_names, ratings, fallback)
        ko["group_stage_qualifiers"] = qualifier_ids
        return ko

    def run_monte_carlo(self, n_simulations: int = 5_000) -> list[KnockoutProbRow]:
        """Run N simulations and return per-team stage-progression probabilities."""
        team_names = self.get_teams()
        counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for _ in range(n_simulations):
            result = self.simulate_tournament_once()
            for cid in result.get("group_stage_qualifiers", []):
                counts[cid]["knockout"] += 1
            for cid in result.get("quarterfinals", []):
                counts[cid]["qf"] += 1
            for cid in result.get("semifinals", []):
                counts[cid]["sf"] += 1
            for cid in result.get("final_participants", []):
                counts[cid]["final"] += 1
            winner = result.get("winner")
            if winner:
                counts[winner]["win"] += 1

        rows = []
        for cid, name in team_names.items():
            c = counts[cid]
            rows.append(KnockoutProbRow(
                club_id=cid,
                club_name=name,
                make_knockout=round(c["knockout"] / n_simulations, 4),
                make_quarterfinals=round(c["qf"] / n_simulations, 4),
                make_semifinals=round(c["sf"] / n_simulations, 4),
                make_final=round(c["final"] / n_simulations, 4),
                win_competition=round(c["win"] / n_simulations, 4),
                simulations=n_simulations,
            ))

        return sorted(rows, key=lambda r: r.win_competition, reverse=True)
