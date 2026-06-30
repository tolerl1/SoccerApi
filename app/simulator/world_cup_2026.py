"""
World Cup 2026 team data and group structure.

xGF/xGA values are sourced from The Athletic's xGC (Expected Goal Contribution)
rating system. They represent expected goals for/against vs. an average team.
Net GD = xGF - xGA.
"""

# Average expected goals across all WC 2026 teams, used as the neutral baseline
# in the Poisson match model: lambda = (team_xgf * opp_xga) / AVERAGE_GOALS
AVERAGE_GOALS = 1.55

TEAM_RATINGS: dict[str, dict] = {
    "Spain":               {"xgf": 3.12, "xga": 1.14, "net_gd": 1.98},
    "France":              {"xgf": 3.06, "xga": 1.09, "net_gd": 1.96},
    "England":             {"xgf": 2.60, "xga": 1.12, "net_gd": 1.48},
    "Argentina":           {"xgf": 2.62, "xga": 1.18, "net_gd": 1.44},
    "Portugal":            {"xgf": 2.48, "xga": 1.16, "net_gd": 1.32},
    "Brazil":              {"xgf": 2.30, "xga": 1.21, "net_gd": 1.09},
    "Germany":             {"xgf": 2.28, "xga": 1.27, "net_gd": 1.01},
    "Belgium":             {"xgf": 2.16, "xga": 1.21, "net_gd": 0.95},
    "Netherlands":         {"xgf": 2.22, "xga": 1.31, "net_gd": 0.91},
    "Colombia":            {"xgf": 1.95, "xga": 1.37, "net_gd": 0.57},
    "Norway":              {"xgf": 1.95, "xga": 1.38, "net_gd": 0.56},
    "Croatia":             {"xgf": 2.00, "xga": 1.45, "net_gd": 0.56},
    "Senegal":             {"xgf": 1.80, "xga": 1.30, "net_gd": 0.50},
    "Uruguay":             {"xgf": 1.79, "xga": 1.37, "net_gd": 0.42},
    "Turkey":              {"xgf": 1.85, "xga": 1.46, "net_gd": 0.39},
    "Japan":               {"xgf": 1.74, "xga": 1.38, "net_gd": 0.37},
    "Ivory Coast":         {"xgf": 1.75, "xga": 1.48, "net_gd": 0.27},
    "Austria":             {"xgf": 1.64, "xga": 1.46, "net_gd": 0.18},
    "Morocco":             {"xgf": 1.58, "xga": 1.40, "net_gd": 0.17},
    "Switzerland":         {"xgf": 1.66, "xga": 1.51, "net_gd": 0.14},
    "United States":       {"xgf": 1.62, "xga": 1.49, "net_gd": 0.13},
    "Mexico":              {"xgf": 1.64, "xga": 1.55, "net_gd": 0.09},
    "Ecuador":             {"xgf": 1.52, "xga": 1.48, "net_gd": 0.05},
    "Scotland":            {"xgf": 1.44, "xga": 1.44, "net_gd": -0.01},
    "Algeria":             {"xgf": 1.50, "xga": 1.55, "net_gd": -0.05},
    "Canada":              {"xgf": 1.48, "xga": 1.56, "net_gd": -0.08},
    "Paraguay":            {"xgf": 1.40, "xga": 1.50, "net_gd": -0.10},
    "South Korea":         {"xgf": 1.40, "xga": 1.52, "net_gd": -0.12},
    "Sweden":              {"xgf": 1.43, "xga": 1.57, "net_gd": -0.14},
    "Czech Republic":      {"xgf": 1.41, "xga": 1.58, "net_gd": -0.16},
    "Egypt":               {"xgf": 1.32, "xga": 1.61, "net_gd": -0.29},
    "Ghana":               {"xgf": 1.24, "xga": 1.55, "net_gd": -0.31},
    "Bosnia-Herzegovina":  {"xgf": 1.27, "xga": 1.61, "net_gd": -0.34},
    "Congo DR":            {"xgf": 1.24, "xga": 1.59, "net_gd": -0.35},
    "Australia":           {"xgf": 1.17, "xga": 1.65, "net_gd": -0.49},
    "IR Iran":             {"xgf": 1.14, "xga": 1.71, "net_gd": -0.56},
    "Uzbekistan":          {"xgf": 1.12, "xga": 1.72, "net_gd": -0.61},
    "Tunisia":             {"xgf": 1.12, "xga": 1.75, "net_gd": -0.63},
    "Panama":              {"xgf": 1.02, "xga": 1.78, "net_gd": -0.76},
    "New Zealand":         {"xgf": 1.01, "xga": 1.78, "net_gd": -0.77},
    "South Africa":        {"xgf": 1.01, "xga": 1.82, "net_gd": -0.81},
    "Cape Verde":          {"xgf": 1.02, "xga": 1.84, "net_gd": -0.82},
    "Haiti":               {"xgf": 0.98, "xga": 1.83, "net_gd": -0.86},
    "Iraq":                {"xgf": 0.98, "xga": 1.85, "net_gd": -0.87},
    "Jordan":              {"xgf": 0.98, "xga": 1.85, "net_gd": -0.87},
    "Saudi Arabia":        {"xgf": 0.96, "xga": 1.86, "net_gd": -0.89},
    "Curacao":             {"xgf": 0.92, "xga": 1.90, "net_gd": -0.98},
    "Qatar":               {"xgf": 0.79, "xga": 2.03, "net_gd": -1.24},
}

# Groups A, B, C are confirmed from The Athletic's WC 2026 coverage.
# Groups D-L are estimated based on seeding logic and the 48-team draw.
GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Korea", "Czech Republic", "South Africa"],
    "B": ["Canada", "Switzerland", "Bosnia-Herzegovina", "Qatar"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["Spain", "Ivory Coast", "Tunisia", "New Zealand"],
    "E": ["France", "Sweden", "Algeria", "Jordan"],
    "F": ["England", "Colombia", "Ghana", "Saudi Arabia"],
    "G": ["Argentina", "Ecuador", "Panama", "Iraq"],
    "H": ["Portugal", "Uruguay", "Paraguay", "Cape Verde"],
    "I": ["Germany", "Croatia", "Congo DR", "Australia"],
    "J": ["Belgium", "Turkey", "Egypt", "Curacao"],
    "K": ["Netherlands", "Senegal", "Norway", "IR Iran"],
    "L": ["Austria", "Japan", "United States", "Uzbekistan"],
}

# Round of 32 bracket: which group positions play each other.
# Format: (group_letter, position) where position is 0=1st, 1=2nd
# 8 best third-place teams are slotted into the remaining 8 R32 spots.
KNOCKOUT_BRACKET_R32 = [
    ("A", 0), ("B", 1),
    ("C", 0), ("D", 1),
    ("E", 0), ("F", 1),
    ("G", 0), ("H", 1),
    ("I", 0), ("J", 1),
    ("K", 0), ("L", 1),
    ("B", 0), ("A", 1),
    ("D", 0), ("C", 1),
    ("F", 0), ("E", 1),
    ("H", 0), ("G", 1),
    ("J", 0), ("I", 1),
    ("L", 0), ("K", 1),
]
# The 4 remaining R32 spots are filled by the 8 best 3rd-place teams (4 matches).
