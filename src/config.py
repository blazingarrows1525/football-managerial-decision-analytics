"""Central configuration: thresholds, weights, timing bands, formation templates and role maps.

Every tunable number used by the analysis lives here so notebooks and the dashboard never rely on
scattered magic numbers. All values are analytical choices, not football truths."""
from __future__ import annotations

import copy
import os
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

# Versions of the shared data model. Bump when a parser, feature definition or registry field changes so that
# cached artefacts and the provenance manifest can never be confused across definitions.
SCHEMA_VERSION = "3.0.0"
PARSER_VERSION = "3.0.0"
FEATURE_VERSION = "3.0.0"

# Repository root (two levels above this file) so nothing depends on the caller's working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

REAL_OPEN_DATA = "REAL_OPEN_DATA"

USER_DATA = "USER_DATA"

DEMO_SYNTHETIC = "DEMO_SYNTHETIC"

DATA_MODES = (REAL_OPEN_DATA, USER_DATA, DEMO_SYNTHETIC)

SYNTHETIC_WARNING = "SYNTHETIC DEMO DATA — NOT REAL FOOTBALL OBSERVATIONS"

PITCH_LENGTH = 120.0

PITCH_WIDTH = 80.0

COORDINATE_SYSTEM = "statsbomb_120x80_attack_left_to_right"

POSITION_ROLE: dict[str, str] = {
    "Goalkeeper": "GK",
    "Right Back": "FB", "Left Back": "FB",
    "Right Center Back": "CB", "Center Back": "CB", "Left Center Back": "CB",
    "Right Wing Back": "WB", "Left Wing Back": "WB",
    "Right Defensive Midfield": "DM", "Center Defensive Midfield": "DM", "Left Defensive Midfield": "DM",
    "Right Center Midfield": "CM", "Center Midfield": "CM", "Left Center Midfield": "CM",
    "Right Midfield": "WM", "Left Midfield": "WM",
    "Right Attacking Midfield": "AM", "Center Attacking Midfield": "AM", "Left Attacking Midfield": "AM",
    "Right Wing": "W", "Left Wing": "W",
    "Right Center Forward": "CF", "Center Forward": "CF", "Left Center Forward": "CF",
    "Secondary Striker": "CF",
}

ROLE_FAMILY: dict[str, str] = {
    "GK": "Goalkeeper",
    "CB": "Defender", "FB": "Defender", "WB": "Defender",
    "DM": "Midfielder", "CM": "Midfielder", "AM": "Midfielder", "WM": "Midfielder",
    "W": "Forward", "CF": "Forward",
}

ROLE_LABEL: dict[str, str] = {
    "GK": "Goalkeeper", "CB": "Centre-back", "FB": "Full-back", "WB": "Wing-back",
    "DM": "Defensive midfielder", "CM": "Central midfielder", "AM": "Attacking midfielder",
    "WM": "Wide midfielder", "W": "Winger", "CF": "Centre-forward",
}

ROLE_COMPATIBILITY: dict[str, dict[str, float]] = {
    "GK": {"GK": 1.0},
    "CB": {"CB": 1.0, "FB": 0.6, "WB": 0.45, "DM": 0.55},
    "FB": {"FB": 1.0, "WB": 0.9, "CB": 0.55, "WM": 0.6, "DM": 0.4},
    "WB": {"WB": 1.0, "FB": 0.85, "WM": 0.8, "W": 0.6, "CB": 0.35},
    "DM": {"DM": 1.0, "CM": 0.85, "CB": 0.55, "AM": 0.45, "FB": 0.35},
    "CM": {"CM": 1.0, "DM": 0.8, "AM": 0.8, "WM": 0.6, "WB": 0.35},
    "AM": {"AM": 1.0, "CM": 0.75, "W": 0.8, "WM": 0.65, "CF": 0.6},
    "WM": {"WM": 1.0, "W": 0.85, "WB": 0.7, "AM": 0.65, "CM": 0.55, "FB": 0.5},
    "W": {"W": 1.0, "WM": 0.85, "AM": 0.75, "CF": 0.65, "WB": 0.5},
    "CF": {"CF": 1.0, "W": 0.6, "AM": 0.6},
}

FORMATION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "4-3-3": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RB", "role": "FB", "x": 30, "y": 70}, {"slot": "RCB", "role": "CB", "x": 24, "y": 52},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 28}, {"slot": "LB", "role": "FB", "x": 30, "y": 10},
        {"slot": "CDM", "role": "DM", "x": 44, "y": 40}, {"slot": "RCM", "role": "CM", "x": 58, "y": 56},
        {"slot": "LCM", "role": "CM", "x": 58, "y": 24},
        {"slot": "RW", "role": "W", "x": 84, "y": 70}, {"slot": "ST", "role": "CF", "x": 92, "y": 40},
        {"slot": "LW", "role": "W", "x": 84, "y": 10},
    ],
    "4-2-3-1": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RB", "role": "FB", "x": 30, "y": 70}, {"slot": "RCB", "role": "CB", "x": 24, "y": 52},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 28}, {"slot": "LB", "role": "FB", "x": 30, "y": 10},
        {"slot": "RDM", "role": "DM", "x": 46, "y": 52}, {"slot": "LDM", "role": "DM", "x": 46, "y": 28},
        {"slot": "RAM", "role": "W", "x": 76, "y": 68}, {"slot": "CAM", "role": "AM", "x": 74, "y": 40},
        {"slot": "LAM", "role": "W", "x": 76, "y": 12}, {"slot": "ST", "role": "CF", "x": 94, "y": 40},
    ],
    "4-4-2": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RB", "role": "FB", "x": 30, "y": 70}, {"slot": "RCB", "role": "CB", "x": 24, "y": 52},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 28}, {"slot": "LB", "role": "FB", "x": 30, "y": 10},
        {"slot": "RM", "role": "WM", "x": 62, "y": 70}, {"slot": "RCM", "role": "CM", "x": 54, "y": 50},
        {"slot": "LCM", "role": "CM", "x": 54, "y": 30}, {"slot": "LM", "role": "WM", "x": 62, "y": 10},
        {"slot": "RST", "role": "CF", "x": 90, "y": 50}, {"slot": "LST", "role": "CF", "x": 90, "y": 30},
    ],
    "3-5-2": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RCB", "role": "CB", "x": 24, "y": 58}, {"slot": "CB", "role": "CB", "x": 22, "y": 40},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 22},
        {"slot": "RWB", "role": "WB", "x": 56, "y": 72}, {"slot": "CDM", "role": "DM", "x": 46, "y": 40},
        {"slot": "RCM", "role": "CM", "x": 60, "y": 54}, {"slot": "LCM", "role": "CM", "x": 60, "y": 26},
        {"slot": "LWB", "role": "WB", "x": 56, "y": 8},
        {"slot": "RST", "role": "CF", "x": 90, "y": 50}, {"slot": "LST", "role": "CF", "x": 90, "y": 30},
    ],
    "3-4-3": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RCB", "role": "CB", "x": 24, "y": 58}, {"slot": "CB", "role": "CB", "x": 22, "y": 40},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 22},
        {"slot": "RWB", "role": "WB", "x": 54, "y": 72}, {"slot": "RCM", "role": "CM", "x": 50, "y": 50},
        {"slot": "LCM", "role": "CM", "x": 50, "y": 30}, {"slot": "LWB", "role": "WB", "x": 54, "y": 8},
        {"slot": "RW", "role": "W", "x": 84, "y": 66}, {"slot": "ST", "role": "CF", "x": 94, "y": 40},
        {"slot": "LW", "role": "W", "x": 84, "y": 14},
    ],
    "3-4-2-1": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RCB", "role": "CB", "x": 24, "y": 58}, {"slot": "CB", "role": "CB", "x": 22, "y": 40},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 22},
        {"slot": "RWB", "role": "WB", "x": 56, "y": 72}, {"slot": "RDM", "role": "DM", "x": 48, "y": 50},
        {"slot": "LDM", "role": "DM", "x": 48, "y": 30}, {"slot": "LWB", "role": "WB", "x": 56, "y": 8},
        {"slot": "RAM", "role": "AM", "x": 78, "y": 54}, {"slot": "LAM", "role": "AM", "x": 78, "y": 26},
        {"slot": "ST", "role": "CF", "x": 96, "y": 40},
    ],
    "4-1-4-1": [
        {"slot": "GK", "role": "GK", "x": 6, "y": 40},
        {"slot": "RB", "role": "FB", "x": 30, "y": 70}, {"slot": "RCB", "role": "CB", "x": 24, "y": 52},
        {"slot": "LCB", "role": "CB", "x": 24, "y": 28}, {"slot": "LB", "role": "FB", "x": 30, "y": 10},
        {"slot": "CDM", "role": "DM", "x": 42, "y": 40},
        {"slot": "RM", "role": "WM", "x": 66, "y": 70}, {"slot": "RCM", "role": "CM", "x": 60, "y": 52},
        {"slot": "LCM", "role": "CM", "x": 60, "y": 28}, {"slot": "LM", "role": "WM", "x": 66, "y": 10},
        {"slot": "ST", "role": "CF", "x": 94, "y": 40},
    ],
}

ROLE_METRIC_WEIGHTS: dict[str, dict[str, float]] = {
    "GK": {"gk_saves_p90": 0.35, "gk_claims_p90": 0.15, "pass_completion_pct": 0.25, "long_pass_completion_pct": 0.25},
    "CB": {"interceptions_p90": 0.15, "clearances_p90": 0.15, "aerials_won_p90": 0.15, "tackles_won_p90": 0.1,
           "ball_recoveries_p90": 0.1, "pass_completion_pct": 0.15, "progressive_passes_p90": 0.2},
    "FB": {"progressive_passes_p90": 0.15, "progressive_carries_p90": 0.15, "crosses_completed_p90": 0.1,
           "tackles_won_p90": 0.15, "interceptions_p90": 0.1, "pressures_p90": 0.1, "key_passes_p90": 0.1,
           "pass_completion_pct": 0.15},
    "WB": {"progressive_carries_p90": 0.2, "crosses_completed_p90": 0.15, "key_passes_p90": 0.15,
           "final_third_passes_p90": 0.1, "tackles_won_p90": 0.1, "pressures_p90": 0.1, "xg_p90": 0.05,
           "dribbles_completed_p90": 0.15},
    "DM": {"pass_completion_pct": 0.2, "progressive_passes_p90": 0.2, "interceptions_p90": 0.15,
           "ball_recoveries_p90": 0.15, "tackles_won_p90": 0.15, "pressures_p90": 0.15},
    "CM": {"progressive_passes_p90": 0.2, "pass_completion_pct": 0.15, "key_passes_p90": 0.15,
           "progressive_carries_p90": 0.15, "pressures_p90": 0.1, "ball_recoveries_p90": 0.1,
           "final_third_passes_p90": 0.15},
    "AM": {"key_passes_p90": 0.2, "xg_p90": 0.15, "xa_p90": 0.15, "progressive_carries_p90": 0.15,
           "dribbles_completed_p90": 0.15, "box_touches_p90": 0.1, "shots_p90": 0.1},
    "WM": {"crosses_completed_p90": 0.15, "key_passes_p90": 0.15, "progressive_carries_p90": 0.2,
           "dribbles_completed_p90": 0.15, "pressures_p90": 0.15, "final_third_passes_p90": 0.2},
    "W": {"xg_p90": 0.2, "key_passes_p90": 0.15, "dribbles_completed_p90": 0.2, "progressive_carries_p90": 0.15,
          "box_touches_p90": 0.15, "shots_p90": 0.15},
    "CF": {"xg_p90": 0.3, "shots_p90": 0.15, "goals_p90": 0.15, "box_touches_p90": 0.15, "key_passes_p90": 0.1,
           "aerials_won_p90": 0.05, "pressures_p90": 0.1},
}

SIDE_MATCH_BONUS = 2.0

XI_SCORE_WEIGHTS: dict[str, float] = {
    "role_fit": 0.40,          # season-to-date role-specific percentile composite
    "recent_form": 0.20,       # last-N appearance role composite (pre-decision)
    "sample_reliability": 0.15,  # evidence volume (minutes) behind the numbers
    "workload_suitability": 0.15,  # recent-minutes / rest-day proxy (not fatigue)
    "lineup_continuity": 0.10,  # started the team's previous match
}

SUB_CANDIDATE_WEIGHTS: dict[str, float] = {
    "role_compatibility": 0.35, "intent_fit": 0.35, "recent_form": 0.15, "sample_reliability": 0.15,
}

SUB_INTENT_METRICS: dict[str, dict[str, float]] = {
    "attack": {"xg_p90": 0.3, "shots_p90": 0.15, "key_passes_p90": 0.2, "box_touches_p90": 0.15,
               "progressive_carries_p90": 0.1, "dribbles_completed_p90": 0.1},
    "protect": {"interceptions_p90": 0.2, "tackles_won_p90": 0.2, "clearances_p90": 0.15,
                "aerials_won_p90": 0.15, "pass_completion_pct": 0.15, "ball_recoveries_p90": 0.15},
    "balance": {"progressive_passes_p90": 0.25, "pass_completion_pct": 0.2, "key_passes_p90": 0.2,
                "pressures_p90": 0.15, "ball_recoveries_p90": 0.2},
}

SUB_TIMING_BANDS: list[dict[str, Any]] = [
    {"label": "0-30", "periods": [1], "min": 0, "max": 30},
    {"label": "31-45+", "periods": [1], "min": 31, "max": 200},
    {"label": "46-60", "periods": [2], "min": 0, "max": 60},
    {"label": "61-70", "periods": [2], "min": 61, "max": 70},
    {"label": "71-80", "periods": [2], "min": 71, "max": 80},
    {"label": "81-90+", "periods": [2], "min": 81, "max": 200},
    {"label": "Extra time", "periods": [3, 4], "min": 0, "max": 200},
]

MATCH_PHASES: list[dict[str, Any]] = [
    {"label": "0-15", "periods": [1], "min": 0, "max": 15},
    {"label": "16-30", "periods": [1], "min": 16, "max": 30},
    {"label": "31-45+", "periods": [1], "min": 31, "max": 200},
    {"label": "46-60", "periods": [2], "min": 0, "max": 60},
    {"label": "61-75", "periods": [2], "min": 61, "max": 75},
    {"label": "76-90+", "periods": [2], "min": 76, "max": 200},
    {"label": "Extra time", "periods": [3, 4], "min": 0, "max": 200},
]

DEFAULT_SUB_RULES: dict[str, Any] = {
    "max_substitutions": 5,
    "max_windows": 3,
    "extra_time_additional_substitutions": 1,
    "extra_time_additional_windows": 1,
    "interval_changes_use_window": False,
    "window_grouping_seconds": 90,
    "source": "User-configured default (IFAB Law 3 five-substitute option). Verify against the competition's regulations.",
}


@dataclass
class Config:
    """Run configuration. Edit in the notebook's configuration cell."""

    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_mode: str = REAL_OPEN_DATA
    competition_id: int = 9          # 1. Bundesliga (StatsBomb open data)
    season_id: int = 281             # 2023/2024
    match_limit: int | None = None   # None = every available match in the competition-season
    focus_team: str | None = "Bayer Leverkusen"
    include_360: bool = False        # 360 freeze frames are large; not needed for core analysis
    statsbomb_base_url: str = "https://raw.githubusercontent.com/hudl/open-data/master/data"
    user_data_dir: str = "data/external/user_statsbomb"
    managers_csv: str = "data/external/managers.csv"
    request_timeout: int = 60
    max_retries: int = 4
    random_seed: int = 42
    min_minutes: float = 180.0                 # per-90 / percentile eligibility
    min_group_size: int = 8                    # smallest role group for role-level percentiles
    form_window: int = 5                       # appearances in recent-form window
    min_manager_matches: int = 10              # manager comparisons need this many matches
    impact_window_minutes: float = 10.0        # pre/post substitution-decision window (10 or 15 typical)
    reliability_full_minutes: float = 900.0    # minutes at which sample reliability = 100
    formation_templates: dict = field(default_factory=lambda: copy.deepcopy(FORMATION_TEMPLATES))
    role_metric_weights: dict = field(default_factory=lambda: copy.deepcopy(ROLE_METRIC_WEIGHTS))
    xi_score_weights: dict = field(default_factory=lambda: dict(XI_SCORE_WEIGHTS))
    sub_candidate_weights: dict = field(default_factory=lambda: dict(SUB_CANDIDATE_WEIGHTS))
    sub_intent_metrics: dict = field(default_factory=lambda: copy.deepcopy(SUB_INTENT_METRICS))
    sub_timing_bands: list = field(default_factory=lambda: copy.deepcopy(SUB_TIMING_BANDS))
    match_phases: list = field(default_factory=lambda: copy.deepcopy(MATCH_PHASES))
    sub_rules: dict = field(default_factory=lambda: dict(DEFAULT_SUB_RULES))
    role_compatibility: dict = field(default_factory=lambda: copy.deepcopy(ROLE_COMPATIBILITY))

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)
        if self.data_mode not in DATA_MODES:
            raise ValueError(f"data_mode must be one of {DATA_MODES}, got {self.data_mode!r}")

    # Paths -----------------------------------------------------------------
    @property
    def raw_dir(self) -> Path:
        sub = {REAL_OPEN_DATA: "statsbomb", USER_DATA: "user", DEMO_SYNTHETIC: "synthetic"}[self.data_mode]
        return self.project_root / "data" / "raw" / sub

    @property
    def _mode_suffix(self) -> str:
        # Synthetic outputs never share folders with real-data outputs.
        return "synthetic" if self.data_mode == DEMO_SYNTHETIC else ""

    @property
    def processed_dir(self) -> Path:
        return self.project_root / "data" / "processed" / self._mode_suffix

    @property
    def manifest_dir(self) -> Path:
        return self.project_root / "data" / "manifest" / self._mode_suffix

    @property
    def artifacts_dir(self) -> Path:
        """Generated outputs. Synthetic runs write to artifacts/synthetic and never touch real-data outputs."""
        return self.project_root / "artifacts" / self._mode_suffix

    @property
    def figures_dir(self) -> Path:
        return self.artifacts_dir / "figures"

    @property
    def html_dir(self) -> Path:
        return self.artifacts_dir / "html"

    @property
    def tables_dir(self) -> Path:
        return self.artifacts_dir / "tables"

    @property
    def reports_dir(self) -> Path:
        return self.artifacts_dir / "reports"

    @property
    def is_synthetic(self) -> bool:
        return self.data_mode == DEMO_SYNTHETIC

    def ensure_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)  # only the raw-data cache is written to disk

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["project_root"] = str(self.project_root)
        return d


def default_data_mode() -> str:
    """Data mode from the FMA_DATA_MODE environment variable (used by CI and layout tests), else real data."""
    mode = os.environ.get("FMA_DATA_MODE", REAL_OPEN_DATA).strip().upper()
    return mode if mode in DATA_MODES else REAL_OPEN_DATA


def default_config(**overrides: Any) -> Config:
    """Project configuration with the environment-selected data mode; keyword arguments override fields.

    ``FMA_DATA_MODE=DEMO_SYNTHETIC`` selects the generated fixture league (used by CI and layout tests) with
    settings that suit its small size. ``FMA_PROJECT_ROOT`` redirects every data and artefact path.
    """
    overrides.setdefault("data_mode", default_data_mode())
    if os.environ.get("FMA_PROJECT_ROOT"):
        overrides.setdefault("project_root", Path(os.environ["FMA_PROJECT_ROOT"]))
    if overrides["data_mode"] == DEMO_SYNTHETIC:
        for key, value in (("competition_id", 9999), ("season_id", 9999), ("focus_team", "Synthetic Albion"),
                           ("min_minutes", 90.0), ("min_group_size", 3)):
            overrides.setdefault(key, value)
    return Config(**overrides)


def format_formation(code: Any) -> str | None:
    """Convert a StatsBomb formation code (e.g. 3421) into '3-4-2-1'."""
    if code is None or (isinstance(code, float) and code != code):
        return None
    s = str(int(code)) if not isinstance(code, str) else code.replace("-", "")
    return "-".join(s) if s.isdigit() else None


def role_for_position(position_name: Any) -> str | None:
    """Map a StatsBomb position name onto a project role code (None if unknown)."""
    if not isinstance(position_name, str):
        return None
    return POSITION_ROLE.get(position_name)


def position_side(name: Any) -> str:
    """'R', 'L' or 'C' from a StatsBomb position name or a slot code (e.g. 'RCB', 'LWB', 'ST')."""
    if not isinstance(name, str) or not name:
        return "C"
    if name.startswith("Right") or (name[0] == "R" and name.isupper() and len(name) > 1):
        return "R"
    if name.startswith("Left") or (name[0] == "L" and name.isupper() and len(name) > 1):
        return "L"
    return "C"


def compatibility(player_role: str | None, slot_role: str, table: dict | None = None) -> float:
    """Position compatibility of a player's primary role for a slot role (0-1)."""
    table = table or ROLE_COMPATIBILITY
    if player_role is None:
        return 0.0
    return float(table.get(player_role, {}).get(slot_role, 0.0))
