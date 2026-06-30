"""
Round-robin league simulator — Premier League, La Liga, Bundesliga, etc.

Simulates remaining fixtures from current standings, then runs Monte Carlo
to produce title / European-qualification / relegation probabilities.
"""

from collections import defaultdict
from dataclasses import dataclass

from app.simulator.match_simulator import simulate_match
from .base import CompetitionSimulator, TeamStanding


@dataclass
class LeagueProbRow:
    club_id: int
    club_name: str
    avg_final_position: float
    win_title: float
    qualify_ucl: float
    qualify_uel: float
    qualify_uecl: float
    relegated: float
    simulations: int


class LeagueSimulator(CompetitionSimulator):
    """
    Simulate a round-robin domestic league.

    Parameters match typical configurations:
      PL / La Liga / Serie A : 20 teams, top 4 UCL, +1 UEL, bottom 3 relegate
      Bundesliga             : 18 teams, top 4 UCL, +1 UEL, bottom 2 relegate (+1 playoff)
      Ligue 1                : 18 teams, top 2 UCL, +2 UEL, bottom 3 relegate
    """

    def __init__(
        self,
        competition_id: str,
        season: str | None,
        db,
        top_n_ucl: int = 4,
        top_n_uel: int = 1,
        top_n_uecl: int = 1,
        relegation_spots: int = 3,
        home_advantage: float = 0.08,
    ):
        super().__init__(competition_id, season, db)
        self.top_n_ucl = top_n_ucl
        self.top_n_uel = top_n_uel
        self.top_n_uecl = top_n_uecl
        self.relegation_spots = relegation_spots
        self.home_advantage = home_advantage

    # ------------------------------------------------------------------

    def get_current_standings(self) -> list[TeamStanding]:
        """Build standings table from all played games."""
        standings: dict[int, TeamStanding] = {
            cid: TeamStanding(club_id=cid, club_name=name)
            for cid, name in self.get_teams().items()
        }

        for g in self.get_played_games():
            h, a = g.home_club_id, g.away_club_id
            if h not in standings or a not in standings:
                continue
            hg, ag = int(g.home_club_goals), int(g.away_club_goals)

            standings[h].played += 1
            standings[a].played += 1
            standings[h].goals_for += hg
            standings[h].goals_against += ag
            standings[a].goals_for += ag
            standings[a].goals_against += hg

            if hg > ag:
                standings[h].won += 1
                standings[h].points += 3
                standings[a].lost += 1
            elif ag > hg:
                standings[a].won += 1
                standings[a].points += 3
                standings[h].lost += 1
            else:
                standings[h].drawn += 1
                standings[h].points += 1
                standings[a].drawn += 1
                standings[a].points += 1

        return sorted(standings.values(), key=lambda s: s.sort_key(), reverse=True)

    # ------------------------------------------------------------------

    def simulate_season_once(
        self, current_standings: list[TeamStanding] | None = None
    ) -> list[TeamStanding]:
        """
        Simulate remaining fixtures and return final standings.
        Starts from `current_standings` (real data) if provided.
        """
        if current_standings is None:
            current_standings = self.get_current_standings()

        standings: dict[int, TeamStanding] = {
            s.club_id: s.copy() for s in current_standings
        }
        ratings = self.get_team_ratings()
        fallback = self.FALLBACK_RATING

        for home_id, away_id in self.get_remaining_matchups():
            hr = ratings.get(home_id, fallback)
            ar = ratings.get(away_id, fallback)

            result = simulate_match(
                str(home_id), hr["xgf"], hr["xga"],
                str(away_id), ar["xgf"], ar["xga"],
                knockout=False,
                neutral_venue=False,
            )

            if home_id in standings:
                s = standings[home_id]
                s.played += 1
                s.goals_for += result.home_goals
                s.goals_against += result.away_goals
            if away_id in standings:
                s = standings[away_id]
                s.played += 1
                s.goals_for += result.away_goals
                s.goals_against += result.home_goals

            if result.home_goals > result.away_goals:
                if home_id in standings:
                    standings[home_id].won += 1
                    standings[home_id].points += 3
                if away_id in standings:
                    standings[away_id].lost += 1
            elif result.away_goals > result.home_goals:
                if away_id in standings:
                    standings[away_id].won += 1
                    standings[away_id].points += 3
                if home_id in standings:
                    standings[home_id].lost += 1
            else:
                for cid in (home_id, away_id):
                    if cid in standings:
                        standings[cid].drawn += 1
                        standings[cid].points += 1

        return sorted(standings.values(), key=lambda s: s.sort_key(), reverse=True)

    # ------------------------------------------------------------------

    def run_monte_carlo(self, n_simulations: int = 5_000) -> list[LeagueProbRow]:
        """
        Run N complete season simulations from the current standings.
        Returns per-team probabilities sorted by title likelihood.
        """
        current = self.get_current_standings()
        n_teams = len(current)
        ucl_cutoff = self.top_n_ucl
        uel_cutoff = ucl_cutoff + self.top_n_uel
        uecl_cutoff = uel_cutoff + self.top_n_uecl
        rel_start = n_teams - self.relegation_spots

        counts: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for _ in range(n_simulations):
            table = self.simulate_season_once(current)
            for rank, s in enumerate(table, 1):
                cid = s.club_id
                counts[cid]["pos"] += rank
                if rank == 1:
                    counts[cid]["title"] += 1
                if rank <= ucl_cutoff:
                    counts[cid]["ucl"] += 1
                if ucl_cutoff < rank <= uel_cutoff:
                    counts[cid]["uel"] += 1
                if uel_cutoff < rank <= uecl_cutoff:
                    counts[cid]["uecl"] += 1
                if rank > rel_start:
                    counts[cid]["rel"] += 1

        rows = []
        for s in current:
            cid = s.club_id
            c = counts[cid]
            rows.append(LeagueProbRow(
                club_id=cid,
                club_name=s.club_name,
                avg_final_position=round(c["pos"] / n_simulations, 2),
                win_title=round(c["title"] / n_simulations, 4),
                qualify_ucl=round(c["ucl"] / n_simulations, 4),
                qualify_uel=round(c["uel"] / n_simulations, 4),
                qualify_uecl=round(c["uecl"] / n_simulations, 4),
                relegated=round(c["rel"] / n_simulations, 4),
                simulations=n_simulations,
            ))

        return sorted(rows, key=lambda r: r.win_title, reverse=True)
