"""Workspace: the bundle plus memoised analytical results shared by the charts, the dashboard and the notebooks.

Expensive derivations (expected points, the xT grid, network centrality, the model comparison, historical
agreement backtests) are computed once per workspace on first use. Results are treated as read-only: callers
must not mutate the returned frames.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from src.analytics import clustering, descriptive, explainability, models
from src.analytics import lineup_optimizer as xi
from src.analytics import manager_patterns, statistical_tests, substitution_analysis
from src.data.schemas import Bundle
from src.features import network_features, values
from src.features.lineup_features import lineup_continuity
from src.features.team_features import expected_points
from src.pipeline import build_bundle, focus_team

CORRELATION_VARIABLES = ["xg", "xg_against", "shots", "shots_against", "possession_proxy_pct", "field_tilt_pct",
                         "pass_completion_pct", "progressive_passes", "pressures", "ppda", "set_piece_shots"]
EDA_METRICS = ["xg_p90", "xa_p90", "key_passes_p90", "progressive_passes_p90", "progressive_carries_p90",
               "pressures_p90", "tackles_won_p90", "interceptions_p90", "pass_completion_pct"]


@dataclass
class Params:
    """User selections a chart may need. Unused fields are ignored by a renderer."""
    team: str | None = None
    match_id: Any = None
    player_id: Any = None
    compare_id: Any = None
    metric: str = "xg_p90"
    metric_y: str = "xa_p90"
    team_metric: str = "xg_diff"
    group: str = "role_family"
    kind: str = "Touches"
    formation: str | None = None
    minute: float = 65.0
    min_minutes: float | None = None
    method: str = "spearman"
    period: int | None = None


@dataclass
class Workspace:
    bundle: Bundle
    seed: int = 42
    _memo: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ basics
    @classmethod
    def load(cls, config: Any = None, **kwargs: Any) -> "Workspace":
        return cls(build_bundle(config, **kwargs))

    def memo(self, key: tuple, fn: Callable[[], Any]) -> Any:
        if key not in self._memo:
            self._memo[key] = fn()
        return self._memo[key]

    @property
    def cfg(self) -> Any:
        return self.bundle.config

    @property
    def flags(self) -> pd.DataFrame:
        return self.bundle.flags

    @property
    def tables(self) -> dict:
        return self.bundle.tables

    @property
    def synthetic(self) -> bool:
        return self.cfg.is_synthetic

    @property
    def focus(self) -> str:
        return self.memo(("focus",), lambda: focus_team(self.bundle))

    def teams(self) -> list[str]:
        ts = self.bundle.team_stats
        return ts["team_name"].value_counts().index.tolist()

    def team_id(self, team: str | None = None) -> Any:
        return descriptive.team_id_of(self.bundle, team or self.focus)

    def team_matches(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("team_matches", team), lambda: descriptive.team_matches(self.bundle, team))

    def match_ids(self, team: str | None = None) -> list:
        return self.team_matches(team)["match_id"].tolist()

    def match_label(self, match_id: Any) -> str:
        m = self.tables["matches"]
        r = m[m["match_id"] == match_id]
        if r.empty:
            return str(match_id)
        r = r.iloc[0]
        return f"{r['match_date']:%d %b %Y}: {r['home_team']} {r['home_score']}-{r['away_score']} {r['away_team']}"

    def default_match(self, team: str | None = None) -> Any:
        """A representative match: the team's match with the median xG difference (not the best or worst)."""
        tm = self.team_matches(team)
        if tm.empty:
            return None
        return tm.sort_values("xg_diff").iloc[len(tm) // 2]["match_id"]

    def squad(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        sp = self.bundle.season_pct
        return sp[sp["team_name"] == team].sort_values("minutes_played", ascending=False)

    def default_player(self, team: str | None = None) -> Any:
        """Most-used outfield player of the team."""
        s = self.squad(team)
        s = s[s["primary_role"] != "GK"]
        return s["player_id"].iloc[0] if len(s) else None

    def player_name(self, player_id: Any) -> str:
        sp = self.bundle.season_pct
        hit = sp.loc[sp["player_id"] == player_id, "player_name"]
        return str(hit.iloc[0]) if len(hit) else str(player_id)

    def names(self) -> pd.Series:
        return self.memo(("names",), lambda: self.tables["appearances"].drop_duplicates("player_id")
                         .set_index("player_id")["player_name"])

    def params(self, **overrides: Any) -> Params:
        """Default selections for this workspace, with overrides."""
        team = overrides.pop("team", None) or self.focus
        p = Params(team=team, match_id=self.default_match(team), player_id=self.default_player(team),
                   min_minutes=self.cfg.min_minutes)
        squad = self.squad(team)
        role = squad.loc[squad["player_id"] == p.player_id, "primary_role"]
        same = squad[(squad["primary_role"] == (role.iloc[0] if len(role) else None))
                     & (squad["player_id"] != p.player_id)]
        p.compare_id = same["player_id"].iloc[0] if len(same) else None
        tm = self.team_matches(team)
        f = tm.loc[tm["match_id"] == p.match_id, "starting_formation"]
        p.formation = f.iloc[0] if len(f) and f.iloc[0] in self.cfg.formation_templates else next(
            iter(self.cfg.formation_templates))
        for k, v in overrides.items():
            setattr(p, k, v)
        return p

    def eligible(self, min_minutes: float | None = None) -> pd.DataFrame:
        sp = self.bundle.season_pct
        return sp[sp["minutes_played"] >= (self.cfg.min_minutes if min_minutes is None else min_minutes)]

    # ------------------------------------------------------- season-level results
    def xpts(self) -> pd.DataFrame:
        return self.memo(("xpts",), lambda: expected_points(self.flags, self.bundle.team_stats, n_sims=5000,
                                                            seed=self.seed))

    def xt_grid(self) -> Any:
        return self.memo(("xt",), lambda: values.fit_xt(self.flags))

    def player_xt(self) -> pd.DataFrame | None:
        g = self.xt_grid()
        return None if g is None else self.memo(("player_xt",), lambda: values.player_xt(
            self.flags, self.bundle.season_pct, g, self.cfg.min_minutes))

    def centrality(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("centrality", team), lambda: network_features.network_centrality(
            self.flags, self.bundle.team_stats, team))

    def centrality_summary(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("centrality_summary", team), lambda: network_features.centrality_summary(
            self.centrality(team), self.names()))

    def state_time(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("state_time", team), lambda: descriptive.score_state_time(self.bundle, team))

    def event_state(self, team: str | None = None) -> pd.Series:
        team = team or self.focus
        return self.memo(("event_state", team), lambda: descriptive.event_score_state(self.bundle, team))

    def consistency(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("consistency", team), lambda: descriptive.player_consistency(self.bundle, team,
                                                                                      seed=self.seed))

    def correlations(self, team: str | None = None, target: str = "goal_diff") -> pd.DataFrame:
        team = team or self.focus
        tm = self.team_matches(team)
        cols = [c for c in CORRELATION_VARIABLES if c in tm.columns and tm[c].nunique() > 1]
        return self.memo(("corr", team, target), lambda: statistical_tests.correlation_suite(
            tm, target, cols, seed=self.seed) if len(tm) >= 6 and cols else pd.DataFrame())

    def group_tests(self, team: str | None = None) -> list[dict]:
        """Venue, season-half and shot-quality comparisons (Mann-Whitney, Cliff's delta, bootstrap CI)."""
        team = team or self.focus

        def run() -> list[dict]:
            tm = self.team_matches(team)
            out = []
            home, away = tm.loc[tm["home_away"] == "home", "xg_diff"], tm.loc[tm["home_away"] == "away", "xg_diff"]
            if len(home) >= 3 and len(away) >= 3:
                out.append(statistical_tests.compare_groups(home, away, "home", "away", seed=self.seed))
            if len(tm) >= 8:
                cut = tm["match_date"].sort_values().iloc[len(tm) // 2]
                out.append(statistical_tests.compare_groups(
                    tm.loc[tm["match_date"] < cut, "xg_diff"], tm.loc[tm["match_date"] >= cut, "xg_diff"],
                    "first half of season", "second half", seed=self.seed))
            fl, ids = self.flags, set(tm["match_id"])
            shots = fl[(fl["type"] == "Shot") & fl["match_id"].isin(ids)]
            a, b = shots.loc[shots["team_name"] == team, "shot_xg"], shots.loc[shots["team_name"] != team, "shot_xg"]
            if a.notna().sum() >= 5 and b.notna().sum() >= 5:
                out.append(statistical_tests.compare_groups(a, b, f"{team} shot xG", "opponent shot xG",
                                                            seed=self.seed))
            return out

        return self.memo(("group_tests", team), run)

    def pca(self) -> dict | None:
        return self.memo(("pca",), lambda: clustering.pca_summary(self.bundle.season_pct, clustering.ARCHETYPE_METRICS,
                                                                  self.cfg.min_minutes, seed=self.seed))

    def clusters(self) -> dict | None:
        return self.memo(("clusters",), lambda: clustering.clustering_comparison(
            self.bundle.season_pct, clustering.ARCHETYPE_METRICS, self.cfg.min_minutes, seed=self.seed))

    def cluster_stability(self) -> pd.DataFrame | None:
        cl = self.clusters()
        return None if cl is None else self.memo(("stability",), lambda: clustering.cluster_stability(
            cl["X"], cl["k_best"], n_boot=40, seed=self.seed))

    def archetypes(self) -> dict | None:
        return self.memo(("archetypes",), lambda: clustering.player_archetypes(
            self.bundle.season_pct, clustering.ARCHETYPE_METRICS, self.cfg.min_minutes, seed=self.seed))

    def outliers(self) -> pd.DataFrame | None:
        return self.memo(("outliers",), lambda: clustering.outlier_scores(
            self.bundle.season_pct, clustering.ARCHETYPE_METRICS, self.cfg.min_minutes, seed=self.seed))

    def models(self, team: str | None = None) -> dict:
        team = team or self.focus
        return self.memo(("models", team), lambda: models.compare_start_models(self.bundle, team, seed=self.seed))

    def permutation(self, team: str | None = None) -> pd.DataFrame | None:
        res = self.models(team)
        return self.memo(("perm", team or self.focus), lambda: explainability.permutation_table(
            res, seed=self.seed)) if res.get("fitted") else None

    def pdp(self, team: str | None = None, feature: str | None = None) -> dict | None:
        res = self.models(team)
        if not res.get("fitted"):
            return None
        perm = self.permutation(team)
        feature = feature or perm["feature"].iloc[-1]
        return self.memo(("pdp", team or self.focus, feature), lambda: explainability.partial_dependence_table(
            res, feature, seed=self.seed))

    def shap(self, team: str | None = None) -> dict:
        res = self.models(team)
        if not res.get("fitted"):
            return {"status": "No model was fitted (sample gate not met)."}
        return self.memo(("shap", team or self.focus), lambda: explainability.shap_values_table(res))

    # ------------------------------------------------------------ decision support
    def xi_context(self, team: str | None = None, match_id: Any = None) -> Any:
        team = team or self.focus
        match_id = match_id if match_id is not None else self.default_match(team)
        return self.memo(("xi_ctx", team, match_id), lambda: xi.decision_context(self.bundle, team,
                                                                                  match_id=match_id))

    def xi_result(self, team: str | None = None, match_id: Any = None, formation: str | None = None) -> Any:
        team = team or self.focus
        match_id = match_id if match_id is not None else self.default_match(team)
        formation = formation or self.params(team=team).formation
        ctx = self.xi_context(team, match_id)
        return self.memo(("xi_res", team, match_id, formation), lambda: xi.optimize_xi(ctx, formation, self.cfg))

    def xi_scores(self, team: str | None = None, match_id: Any = None, formation: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        match_id = match_id if match_id is not None else self.default_match(team)
        formation = formation or self.params(team=team).formation
        ctx = self.xi_context(team, match_id)
        return self.memo(("xi_long", team, match_id, formation), lambda: xi.score_candidates(ctx, formation,
                                                                                             self.cfg)[0])

    def formation_comparison(self, team: str | None = None, match_id: Any = None) -> pd.DataFrame:
        team = team or self.focus
        match_id = match_id if match_id is not None else self.default_match(team)
        ctx = self.xi_context(team, match_id)
        return self.memo(("xi_forms", team, match_id), lambda: xi.compare_formations(ctx, self.cfg))

    def xi_agreement(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("xi_agree", team), lambda: xi.xi_historical_agreement(self.bundle, team))

    def sub_agreement(self, team: str | None = None) -> pd.DataFrame:
        team = team or self.focus
        return self.memo(("sub_agree", team), lambda: substitution_analysis.sub_historical_agreement(
            self.bundle, team, top_k=3))

    def sub_scenario(self, team: str | None, match_id: Any, minute: float, intent: str | None = None) -> dict:
        team = team or self.focus
        return self.memo(("sub_scen", team, match_id, float(minute), intent),
                         lambda: substitution_analysis.recommend_substitution(self.bundle, match_id, team,
                                                                              float(minute), intent=intent))

    def impact(self) -> pd.DataFrame:
        return self.memo(("impact",), lambda: substitution_analysis.impact_windows(self.bundle))

    def manager_profiles(self) -> pd.DataFrame:
        return self.memo(("mgr",), lambda: manager_patterns.manager_profiles(self.bundle))

    def response(self) -> pd.DataFrame:
        return self.memo(("response",), lambda: manager_patterns.response_after_conceding(self.bundle))

    def continuity(self) -> pd.DataFrame:
        return self.memo(("continuity",), lambda: lineup_continuity(self.tables["appearances"],
                                                                    self.tables["matches"]))

    def focus_manager(self, team: str | None = None) -> str | None:
        tm = self.team_matches(team)
        if "manager_name" not in tm or tm["manager_name"].dropna().empty:
            return None
        return str(tm["manager_name"].mode().iloc[0])

    def pooled_reference(self, team: str | None = None) -> pd.DataFrame | None:
        mgr = self.focus_manager(team)
        prof = self.manager_profiles()
        if mgr is None or prof.empty:
            return None
        return manager_patterns.pooled_reference(prof, mgr, self.cfg)

    def has_360(self) -> bool:
        """True when at least one optional 360 file is in the raw cache."""
        d = self.cfg.raw_dir / "three-sixty"
        return d.exists() and any(d.glob("*.json"))

    def load_360(self, match_id: Any, offline: bool = False) -> bool:
        """Download (once) the optional 360 file of one match from the source. Returns True when available."""
        from src.data.statsbomb_client import DataStore

        frames = DataStore(self.cfg, offline=offline).three_sixty(int(match_id))
        self._memo.pop(("360", match_id), None)
        return frames is not None

    def frames_360(self, match_id: Any) -> dict | None:
        """StatsBomb 360 frames of one match keyed by event id, when the optional file has been downloaded."""
        path = self.cfg.raw_dir / "three-sixty" / f"{match_id}.json"
        if not path.exists():
            return None

        def load() -> dict:
            import json

            return {f["event_uuid"]: f for f in json.loads(path.read_text(encoding="utf-8"))}

        return self.memo(("360", match_id), load)
