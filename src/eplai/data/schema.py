"""Column groups for the 2024/25 Premier League player-stats dataset.

These lists are the single source of truth shared by the notebooks, the
training scripts and the serving layer, so a feature is never renamed in one
place and forgotten in another.
"""

from __future__ import annotations

# Columns stored as "12.3%" strings in the raw CSV.
PERCENTAGE_COLS: list[str] = [
    "Conversion %",
    "Passes%",
    "Crosses %",
    "fThird Passes %",
    "gDuels %",
    "aDuels %",
    "Saves %",
]

# Counting stats that only become comparable once normalised by minutes played.
PER90_COLS: list[str] = [
    "Goals",
    "Assists",
    "Shots",
    "Shots On Target",
    "Big Chances Missed",
    "Hit Woodwork",
    "Offsides",
    "Touches",
    "Passes",
    "Successful Passes",
    "Crosses",
    "Successful Crosses",
    "fThird Passes",
    "Successful fThird Passes",
    "Through Balls",
    "Carries",
    "Progressive Carries",
    "Carries Ended with Goal",
    "Carries Ended with Assist",
    "Carries Ended with Shot",
    "Carries Ended with Chance",
    "Possession Won",
    "Dispossessed",
    "Clean Sheets",
    "Clearances",
    "Interceptions",
    "Blocks",
    "Tackles",
    "Ground Duels",
    "gDuels Won",
    "Aerial Duels",
    "aDuels Won",
    "Goals Conceded",
    "xGoT Conceded",
    "Own Goals",
    "Fouls",
    "Yellow Cards",
    "Red Cards",
    "Saves",
    "Penalties Saved",
    "Clearances Off Line",
    "Punches",
    "High Claims",
    "Goals Prevented",
]

IDENTITY_COLS: list[str] = ["Player Name", "Club", "Position"]

# The human-readable subset surfaced to the language model and the website.
IMPORTANT_STATS: list[str] = [
    "Minutes",
    "Goals",
    "Assists",
    "Shots",
    "Shots On Target",
    "Passes%",
    "Conversion %",
    "Touches_per90",
    "Passes_per90",
    "Shots_per90",
    "Assists_per90",
    "Goals_per90",
    "Carries_per90",
    "Progressive Carries_per90",
    "Through Balls_per90",
    "Crosses_per90",
    "Tackles_per90",
    "Interceptions_per90",
    "Ground Duels_per90",
    "Aerial Duels_per90",
    "Saves_per90",
    "Clearances_per90",
    "Fouls_per90",
]

POSITION_LABELS: dict[str, str] = {
    "GKP": "Goalkeeper",
    "DEF": "Defender",
    "MID": "Midfielder",
    "FWD": "Forward",
}


def model_feature_columns() -> list[str]:
    """The full feature space before correlation pruning."""
    return [f"{col}_per90" for col in PER90_COLS] + PERCENTAGE_COLS
