"""Base classes shared by all competition simulators."""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from app import models
from app.simulator.ratings import compute_attack_defense_strengths


@dataclass
class TeamStanding:
    club_id: int
    club_name: str
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

    def copy(self) -> "TeamStanding":
        return TeamStanding(
            club_id=self.club_id,
            club_name=self.club_name,
            played=self.played,
            won=self.won,
            drawn=self.drawn,
            lost=self.lost,
            goals_for=self.goals_for,
            goals_against=self.goals_against,
            points=self.points,
        )


class CompetitionSimulator:
    """
    Base class for all competition format simulators.

    Subclasses implement `get_current_standings`, `simulate_season_once`,
    and `run_monte_carlo` for their specific format (league, group+knockout, etc.).
    """

    FALLBACK_RATING = {"xgf": 1.5, "xga": 1.5}

    def __init__(self, competition_id: str, season: str | None, db: Session):
        self.competition_id = competition_id
        self.season = season
        self.db = db
        self._played_games: list | None = None
        self._all_games: list | None = None
        self._team_ratings: dict | None = None
        self._clubs: dict[int, str] | None = None

    # ------------------------------------------------------------------
    # DB queries
    # ------------------------------------------------------------------

    def get_played_games(self) -> list:
        """All completed games (both goal columns populated) for this competition/season."""
        if self._played_games is None:
            q = self.db.query(models.Game).filter(
                models.Game.competition_id == self.competition_id,
                models.Game.home_club_goals.isnot(None),
                models.Game.away_club_goals.isnot(None),
            )
            if self.season:
                q = q.filter(models.Game.season == self.season)
            self._played_games = q.order_by(models.Game.date).all()
        return self._played_games

    def get_all_games(self) -> list:
        """All scheduled games (played + unplayed) for this competition/season."""
        if self._all_games is None:
            q = self.db.query(models.Game).filter(
                models.Game.competition_id == self.competition_id
            )
            if self.season:
                q = q.filter(models.Game.season == self.season)
            self._all_games = q.all()
        return self._all_games

    def get_teams(self) -> dict[int, str]:
        """Derive team set from the scheduled games."""
        if self._clubs is None:
            teams: dict[int, str] = {}
            for g in self.get_all_games():
                if g.home_club_id:
                    teams[g.home_club_id] = g.club_home_pretty_name or str(g.home_club_id)
                if g.away_club_id:
                    teams[g.away_club_id] = g.club_away_pretty_name or str(g.away_club_id)
            # Fall back to played games if schedule not stored
            if not teams:
                for g in self.get_played_games():
                    if g.home_club_id:
                        teams[g.home_club_id] = g.club_home_pretty_name or str(g.home_club_id)
                    if g.away_club_id:
                        teams[g.away_club_id] = g.club_away_pretty_name or str(g.away_club_id)
            self._clubs = teams
        return self._clubs

    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    def get_team_ratings(self) -> dict[int, dict]:
        """
        Compute attack/defense ratings from played games via Poisson regression.
        Falls back to neutral 1.5/1.5 if insufficient data.
        """
        if self._team_ratings is None:
            games = self.get_played_games()
            if len(games) < 5:
                self._team_ratings = {
                    cid: dict(self.FALLBACK_RATING) for cid in self.get_teams()
                }
            else:
                strengths = compute_attack_defense_strengths(games)
                self._team_ratings = {
                    cid: {"xgf": s["xgf"], "xga": s["xga"]}
                    for cid, s in strengths.items()
                }
                # Fill in any teams missing from the strength calculation
                for cid in self.get_teams():
                    if cid not in self._team_ratings:
                        self._team_ratings[cid] = dict(self.FALLBACK_RATING)
        return self._team_ratings

    def get_remaining_matchups(self) -> list[tuple[int, int]]:
        """
        Return (home_club_id, away_club_id) pairs that have not yet been played.

        Tries scheduled-but-unplayed games first; if the DB only stores results
        (not future fixtures), derives the full round-robin and subtracts played.
        """
        played = {
            (g.home_club_id, g.away_club_id)
            for g in self.get_played_games()
            if g.home_club_id and g.away_club_id
        }

        # Prefer DB-stored fixtures
        unplayed = [
            (g.home_club_id, g.away_club_id)
            for g in self.get_all_games()
            if g.home_club_id and g.away_club_id and g.home_club_goals is None
        ]
        if unplayed:
            return unplayed

        # Derive from full round-robin
        teams = list(self.get_teams().keys())
        return [
            (home, away)
            for home in teams
            for away in teams
            if home != away and (home, away) not in played
        ]
