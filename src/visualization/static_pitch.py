"""Static pitch figures drawn with mplsoccer (optional dependency).

mplsoccer handles StatsBomb coordinates natively (120 x 80, origin top-left, y downwards), so no transform is
applied. These figures complement the interactive Plotly maps for reports and slides.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.visualization.theme import INK, MUTED, NAVY, PAPER, PITCH_LINE, TEAL


def _message(text: str, title: str) -> Any:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 2.6))
    fig.patch.set_facecolor(PAPER)
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    ax.text(0.5, 0.5, text, ha="center", va="center", color=MUTED, fontsize=11, wrap=True)
    return fig


def _pitch(figsize: tuple[float, float] = (10, 6.8)) -> tuple[Any, Any, Any]:
    from mplsoccer import Pitch

    pitch = Pitch(pitch_type="statsbomb", pitch_color=PAPER, line_color=PITCH_LINE, linewidth=1.2, line_zorder=2)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(PAPER)
    return pitch, fig, ax


def hexbin_map(ev: pd.DataFrame | None, title: str, end: bool = False) -> Any:
    """Hexagonal binning of event start (or end) locations."""
    cols = ["end_x", "end_y"] if end else ["x", "y"]
    if ev is None or any(c not in ev.columns for c in cols) or ev.dropna(subset=cols).empty:
        return _message("No located events for this selection.", title)
    d = ev.dropna(subset=cols)
    pitch, fig, ax = _pitch()
    hb = pitch.hexbin(d[cols[0]], d[cols[1]], ax=ax, gridsize=(18, 10), cmap="GnBu", edgecolors=PAPER, mincnt=1,
                      zorder=1)
    cb = fig.colorbar(hb, ax=ax, shrink=0.6, pad=0.01)
    cb.set_label("events per hexagon")
    pitch.arrows(42, 84, 78, 84, ax=ax, color=MUTED, width=1.2, headwidth=5)
    ax.text(60, 87.5, "attacking direction", ha="center", va="center", fontsize=8, color=MUTED)
    ax.set_title(f"{title}\n{len(d):,} {'end' if end else 'start'} locations · hexagons with no event are left "
                 f"empty (no smoothing)", loc="left", fontsize=10.5, color=INK, fontweight="bold")
    return fig


def pass_flow(passes: pd.DataFrame | None, title: str, bins: tuple[int, int] = (6, 4)) -> Any:
    """Pass-flow map: the average direction of passes starting in each zone, over a zone-count heatmap."""
    cols = ["x", "y", "end_x", "end_y"]
    if passes is None or any(c not in passes.columns for c in cols) or passes.dropna(subset=cols).empty:
        return _message("No passes with start and end locations for this selection.", title)
    d = passes.dropna(subset=cols)
    if len(d) < 50:
        return _message(f"A flow map needs at least 50 passes (selection has {len(d)}).", title)
    pitch, fig, ax = _pitch()
    stat = pitch.bin_statistic(d["x"], d["y"], statistic="count", bins=bins)
    pitch.heatmap(stat, ax=ax, cmap="GnBu", edgecolors=PAPER, alpha=0.75, zorder=1)
    pitch.flow(d["x"], d["y"], d["end_x"], d["end_y"], ax=ax, color=NAVY, arrow_type="same", arrow_length=9,
               bins=bins, zorder=3)
    ax.set_title(f"{title}\n{len(d):,} passes · arrow = mean pass direction from each of {bins[0]}×{bins[1]} zones "
                 f"(fixed length) · colour = passes starting in the zone", loc="left", fontsize=10.5, color=INK,
                 fontweight="bold")
    return fig


def pizza(season_pct: pd.DataFrame | None, player_id: Any, metrics: list[str], labels: list[str]) -> Any:
    """Pizza chart of role-group percentiles for one player (each slice 0-100, higher = higher percentile)."""
    title = "Percentile pizza"
    if season_pct is None or "player_id" not in season_pct.columns:
        return _message("Season table not available.", title)
    r = season_pct[season_pct["player_id"] == player_id]
    if r.empty:
        return _message("Player not found.", title)
    r = r.sort_values("minutes_played", ascending=False).iloc[0]
    pairs = [(lab, r.get(f"{m}_pct")) for m, lab in zip(metrics, labels) if f"{m}_pct" in season_pct.columns]
    pairs = [(lab, float(v)) for lab, v in pairs if pd.notna(v)]
    if len(pairs) < 3:
        return _message(f"{r['player_name']}: fewer than three percentiles available (below the minutes threshold "
                        f"or no benchmark group).", title)
    from mplsoccer import PyPizza

    baker = PyPizza(params=[p[0] for p in pairs], background_color=PAPER, straight_line_color="#d9d4c7",
                    straight_line_lw=1, last_circle_lw=1, last_circle_color="#bdb8ab", other_circle_lw=0.6,
                    other_circle_color="#d9d4c7", inner_circle_size=14)
    fig, ax = baker.make_pizza([round(p[1]) for p in pairs], figsize=(7.2, 7.6), color_blank_space="same",
                               blank_alpha=0.25, param_location=110,
                               slice_colors=[TEAL] * len(pairs), value_colors=["white"] * len(pairs),
                               value_bck_colors=[NAVY] * len(pairs),
                               kwargs_slices=dict(edgecolor=PAPER, zorder=2, linewidth=1),
                               kwargs_params=dict(color=INK, fontsize=9, va="center"),
                               kwargs_values=dict(color="white", fontsize=9, zorder=3,
                                                  bbox=dict(edgecolor=PAPER, facecolor=NAVY, boxstyle="round,pad=0.2",
                                                            lw=1)))
    fig.text(0.5, 0.975, f"{r['player_name']} — percentile pizza", ha="center", fontsize=13, color=INK,
             fontweight="bold")
    fig.text(0.5, 0.945, f"percentile within {r.get('benchmark_group', 'role group')} (n = "
                         f"{r.get('benchmark_n', float('nan')):.0f}) · {r['minutes_played']:.0f} minutes · all "
                         f"slices: higher = higher percentile", ha="center", fontsize=8.5, color=MUTED)
    return fig
