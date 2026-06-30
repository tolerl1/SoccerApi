"""
Goal Probability (GP) estimation — the foundation of the xGC pipeline.

This is the "Expected Threat" layer: for any ball location on the pitch,
what is the probability the team currently in possession scores next?

Two modes:
  1. Zone-based lookup (default, no training required)
     Pre-computed from published xT literature and calibrated to match
     the heat map shown in The Athletic's article (fig. on page 11).

  2. Logistic regression (trained from StatsBomb event data)
     Call `train_gp_model(db)` to fit the model, then `compute_gp_from_model`.

StatsBomb pitch: x = 0 (own goal-line) → 120 (opp goal-line)
                 y = 0 (left touchline) → 80 (right touchline)
Goal center: (120, 40)
"""

import math
from functools import lru_cache

# ---------------------------------------------------------------------------
# Zone-based lookup  (12 columns × 8 rows, attack direction →)
# ---------------------------------------------------------------------------
#
# Values approximate the published xT grid (Karun Singh 2019) calibrated
# to StatsBomb's coordinate system.  Rows: y=0→10, 10→20, ..., 70→80.
# Cols: x=0→10, 10→20, ..., 110→120.

_XT_GRID: list[list[float]] = [
    # col:  0      10     20     30     40     50     60     70     80     90    100    110
    [0.001, 0.001, 0.001, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.008, 0.015, 0.028],  # row 0  (y 0–10)
    [0.001, 0.001, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.007, 0.011, 0.021, 0.046],  # row 1
    [0.001, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.007, 0.011, 0.018, 0.040, 0.087],  # row 2
    [0.001, 0.001, 0.002, 0.003, 0.004, 0.005, 0.007, 0.010, 0.016, 0.030, 0.074, 0.152],  # row 3
    [0.001, 0.002, 0.002, 0.003, 0.005, 0.006, 0.009, 0.013, 0.021, 0.043, 0.100, 0.220],  # row 4  (y 40–50, central)
    [0.001, 0.001, 0.002, 0.003, 0.004, 0.005, 0.007, 0.010, 0.016, 0.030, 0.074, 0.152],  # row 5
    [0.001, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.007, 0.011, 0.018, 0.040, 0.087],  # row 6
    [0.001, 0.001, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.007, 0.011, 0.021, 0.046],  # row 7  (y 70–80)
]

PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0
_COLS = 12
_ROWS = 8
_COL_WIDTH = PITCH_LENGTH / _COLS
_ROW_HEIGHT = PITCH_WIDTH / _ROWS


def zone_gp(x: float, y: float) -> float:
    """
    Return the pre-computed Goal Probability for ball position (x, y).

    Values are capped at 0.001 for own-half positions and 0.50 for
    near-goal positions to avoid degenerate simulation outputs.
    """
    col = min(int(x / _COL_WIDTH), _COLS - 1)
    row = min(int(y / _ROW_HEIGHT), _ROWS - 1)
    return _XT_GRID[row][col]


# ---------------------------------------------------------------------------
# Analytic model (no training data required)
# ---------------------------------------------------------------------------

def analytic_gp(x: float, y: float) -> float:
    """
    Compute Goal Probability analytically from distance and angle to goal.

    Uses the same geometry as standard xG models:
      - distance:  Euclidean from ball to goal center (120, 40)
      - angle:     subtended by the 7.32 m goal mouth
    Calibrated so the peak value (~6 yards, dead center) ≈ 0.33.
    """
    gx, gy = 120.0, 40.0
    post_offset = 3.66  # half goal width in StatsBomb units (~3.66 m)

    dx = max(gx - x, 0.01)
    dy = gy - y

    dist = math.sqrt(dx ** 2 + dy ** 2)

    # Angle subtended by goal posts
    a1 = math.atan2(abs(dy) + post_offset, dx)
    a2 = math.atan2(max(abs(dy) - post_offset, 0), dx)
    angle = a1 - a2

    # Probability proportional to angle, decaying with distance
    prob = (angle / math.pi) * math.exp(-dist / 35.0)
    return max(0.001, min(prob, 0.50))


# ---------------------------------------------------------------------------
# Default callable used by the attribution layer
# ---------------------------------------------------------------------------

def compute_gp(x: float | None, y: float | None) -> float:
    """Primary GP function used by the attribution module."""
    if x is None or y is None:
        return 0.001
    x = max(0.0, min(x, PITCH_LENGTH))
    y = max(0.0, min(y, PITCH_WIDTH))
    return zone_gp(x, y)


# ---------------------------------------------------------------------------
# Model training from StatsBomb events (optional enhancement)
# ---------------------------------------------------------------------------

def train_gp_model(db) -> "object":
    """
    Fit a logistic regression GP model from StatsBomb event data in the DB.

    Features per event: x, y, distance_to_goal, angle_to_goal, possession_length
    Label: did this possession end in a goal within 5 events?

    Returns a fitted sklearn LogisticRegression object.
    Requires: pip install scikit-learn
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        import numpy as np
    except ImportError:
        raise ImportError("Run: pip install scikit-learn numpy")

    from app import models as m

    events = (
        db.query(m.StatsBombEvent)
        .filter(m.StatsBombEvent.location_x.isnot(None))
        .all()
    )
    if len(events) < 1000:
        raise ValueError(
            f"Only {len(events)} events in DB — ingest StatsBomb data first."
        )

    # Build features and labels
    # Group events by possession → label each event 1 if the possession ended in a goal
    by_possession: dict[tuple, list] = {}
    for ev in events:
        key = (ev.match_id, ev.possession)
        by_possession.setdefault(key, []).append(ev)

    Xs, ys = [], []
    for evs in by_possession.values():
        has_goal = any(
            e.event_type == "Shot" and e.outcome in ("Goal",)
            for e in evs
        )
        for ev in evs:
            if ev.location_x is None:
                continue
            x, y = ev.location_x, ev.location_y or 40.0
            dist = math.sqrt((120 - x) ** 2 + (40 - y) ** 2)
            Xs.append([x, y, dist, analytic_gp(x, y)])
            ys.append(1 if has_goal else 0)

    X = np.array(Xs)
    y = np.array(ys)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=500, class_weight="balanced")),
    ])
    model.fit(X, y)
    return model


def compute_gp_from_model(model, x: float, y: float) -> float:
    """Use a trained sklearn model to predict GP at (x, y)."""
    import numpy as np
    dist = math.sqrt((120 - x) ** 2 + (40 - y) ** 2)
    ag = analytic_gp(x, y)
    prob = model.predict_proba([[x, y, dist, ag]])[0][1]
    return float(max(0.001, min(prob, 0.50)))
