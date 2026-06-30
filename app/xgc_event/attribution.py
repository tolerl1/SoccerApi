"""
Event-level Goal Contribution (GC) attribution.

For each StatsBomb event, compute how much each involved player's actions
changed the team's Goal Probability.  The delta GP is then split among
players based on event type:

  Shot    → shooter gets (xG - GP_start); no receiver credit
  Pass    → passer gets 70 % of ΔGP, receiver gets 30 %
  Carry   → carrier gets 100 % of ΔGP
  Pressure→ presser gets credit for reducing opponent's GP (negative ΔGP
             from opponent perspective = positive defensive GC)
  Interception / Clearance → defender credited with GP they denied
  Dribble → dribbler credited with ΔGP from start to end location

Negative GC (losing the ball, giving up a shot) is also attributed.

Units: same as GP (roughly "expected goals contributed").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .goal_probability import compute_gp

# Fraction of ΔGP credited to passer vs receiver
_PASS_PASSER_SHARE = 0.70
_PASS_RECEIVER_SHARE = 0.30


@dataclass
class PlayerContribution:
    player_id: int
    player_name: str
    team_id: int
    offensive_gc: float = 0.0
    defensive_gc: float = 0.0

    @property
    def net_gc(self) -> float:
        return self.offensive_gc + self.defensive_gc


@dataclass
class EventAttribution:
    """Single-event attribution result."""
    event_id: str
    event_type: str
    contributions: list[PlayerContribution] = field(default_factory=list)


def attribute_events(
    events: list,
    gp_fn: Callable[[float | None, float | None], float] = compute_gp,
) -> list[EventAttribution]:
    """
    Compute per-event GC attribution for a list of StatsBomb event ORM objects.

    `events` should be ordered by `index` within a match and possession.

    Returns one EventAttribution per processed event (only action types that
    generate GC are included; ball receipts, kick-offs, etc. are skipped).
    """
    attributions: list[EventAttribution] = []

    for ev in events:
        etype = ev.event_type or ""
        attr = _route_event(ev, etype, gp_fn)
        if attr is not None:
            attributions.append(attr)

    return attributions


# ---------------------------------------------------------------------------
# Internal routing
# ---------------------------------------------------------------------------

def _route_event(ev, etype: str, gp_fn) -> EventAttribution | None:
    if etype == "Shot":
        return _attr_shot(ev, gp_fn)
    if etype == "Pass":
        return _attr_pass(ev, gp_fn)
    if etype == "Carry":
        return _attr_carry(ev, gp_fn)
    if etype == "Pressure":
        return _attr_pressure(ev, gp_fn)
    if etype in ("Interception", "Clearance"):
        return _attr_defensive_clearance(ev, etype, gp_fn)
    if etype == "Dribble":
        return _attr_dribble(ev, gp_fn)
    return None


def _attr_shot(ev, gp_fn) -> EventAttribution:
    gp_start = gp_fn(ev.location_x, ev.location_y)
    # StatsBomb records statsbomb_xg for shots; fall back to GP at location
    xg = ev.statsbomb_xg if ev.statsbomb_xg is not None else gp_fn(ev.location_x, ev.location_y)
    delta = xg - gp_start

    contrib = PlayerContribution(
        player_id=ev.player_id or 0,
        player_name=ev.player_name or "",
        team_id=ev.team_id or 0,
        offensive_gc=delta,
    )
    return EventAttribution(event_id=ev.event_id, event_type="Shot", contributions=[contrib])


def _attr_pass(ev, gp_fn) -> EventAttribution | None:
    gp_start = gp_fn(ev.location_x, ev.location_y)
    gp_end = gp_fn(ev.end_location_x, ev.end_location_y)
    delta = gp_end - gp_start

    if abs(delta) < 1e-6:
        return None

    contribs = [
        PlayerContribution(
            player_id=ev.player_id or 0,
            player_name=ev.player_name or "",
            team_id=ev.team_id or 0,
            offensive_gc=delta * _PASS_PASSER_SHARE if delta > 0 else delta,
        )
    ]
    # Receiver credit only on positive passes (we don't have receiver ID in
    # StatsBomb events directly, so we record a placeholder player_id = -1)
    if delta > 0:
        contribs.append(
            PlayerContribution(
                player_id=-1,  # receiver unknown from single-event data
                player_name="<receiver>",
                team_id=ev.team_id or 0,
                offensive_gc=delta * _PASS_RECEIVER_SHARE,
            )
        )

    return EventAttribution(event_id=ev.event_id, event_type="Pass", contributions=contribs)


def _attr_carry(ev, gp_fn) -> EventAttribution | None:
    gp_start = gp_fn(ev.location_x, ev.location_y)
    gp_end = gp_fn(ev.end_location_x, ev.end_location_y)
    delta = gp_end - gp_start

    if abs(delta) < 1e-6:
        return None

    contrib = PlayerContribution(
        player_id=ev.player_id or 0,
        player_name=ev.player_name or "",
        team_id=ev.team_id or 0,
        offensive_gc=delta,
    )
    return EventAttribution(event_id=ev.event_id, event_type="Carry", contributions=[contrib])


def _attr_pressure(ev, gp_fn) -> EventAttribution | None:
    """
    Pressure is applied to the opponent; the presser gets defensive credit
    equal to the GP at the pressure location (approximating the threat denied).
    Small baseline to avoid noise from low-threat areas.
    """
    gp = gp_fn(ev.location_x, ev.location_y)
    if gp < 0.005:
        return None

    # Defensive GC: positive means the defender helped their team
    contrib = PlayerContribution(
        player_id=ev.player_id or 0,
        player_name=ev.player_name or "",
        team_id=ev.team_id or 0,
        defensive_gc=gp * 0.10,  # partial credit; pressure doesn't guarantee turnover
    )
    return EventAttribution(event_id=ev.event_id, event_type="Pressure", contributions=[contrib])


def _attr_defensive_clearance(ev, etype: str, gp_fn) -> EventAttribution | None:
    gp_start = gp_fn(ev.location_x, ev.location_y)
    gp_end = gp_fn(ev.end_location_x, ev.end_location_y)
    # Clearance/interception: threat at start location is what was denied
    threat_denied = gp_start - max(gp_end, 0.001)

    if threat_denied <= 0:
        return None

    contrib = PlayerContribution(
        player_id=ev.player_id or 0,
        player_name=ev.player_name or "",
        team_id=ev.team_id or 0,
        defensive_gc=threat_denied,
    )
    return EventAttribution(event_id=ev.event_id, event_type=etype, contributions=[contrib])


def _attr_dribble(ev, gp_fn) -> EventAttribution | None:
    gp_start = gp_fn(ev.location_x, ev.location_y)
    gp_end = gp_fn(ev.end_location_x, ev.end_location_y)
    delta = gp_end - gp_start

    if abs(delta) < 1e-6:
        return None

    contrib = PlayerContribution(
        player_id=ev.player_id or 0,
        player_name=ev.player_name or "",
        team_id=ev.team_id or 0,
        offensive_gc=delta,
    )
    return EventAttribution(event_id=ev.event_id, event_type="Dribble", contributions=[contrib])
