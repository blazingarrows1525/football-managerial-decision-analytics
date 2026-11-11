"""Project-computed Expected Threat (xT) on a pitch grid.

Method (Singh 2019, as implemented in common open-source xT code): the pitch is divided into a grid; for each
cell we estimate the probability of shooting, the scoring value of a shot and the probability of moving the
ball to every other cell. xT is the fixed point of

    xT(c) = P(shot | c) * value(shot | c) + P(move | c) * sum_c' T(c -> c') * xT(c')

solved by value iteration. Choices specific to this project, all visible to the caller:

* move actions are passes (any outcome) and carries; only completed passes and carries transfer value, so a
  failed pass contributes zero continuation value;
* the value of a shot from a cell is the mean StatsBomb xG of shots taken there (source field ``shot_xg``),
  which is smoother than the raw goal rate at this sample size;
* the grid is fitted on the analysed matches only (in-sample). With one team-season it is a descriptive
  surface for these matches, not a league-wide model.

xT is a derived project value and is never presented as a StatsBomb source field.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.config import PITCH_LENGTH, PITCH_WIDTH

XT_METHOD = "value iteration on a grid; moves = passes + carries; shot value = mean StatsBomb xG per cell"


@dataclass
class XTGrid:
    """Fitted xT surface. ``grid[row, col]``: row = y band (0 at y = 0), col = x band (0 at own goal line)."""
    grid: np.ndarray
    shot_prob: np.ndarray
    move_prob: np.ndarray
    shot_value: np.ndarray
    counts: pd.DataFrame
    nx: int
    ny: int
    iterations: int
    converged: bool
    n_moves: int
    n_shots: int
    n_matches: int
    history: list[float]

    def cell(self, x: Any, y: Any) -> tuple[np.ndarray, np.ndarray]:
        cx = np.clip((np.asarray(x, float) / PITCH_LENGTH * self.nx).astype(int), 0, self.nx - 1)
        cy = np.clip((np.asarray(y, float) / PITCH_WIDTH * self.ny).astype(int), 0, self.ny - 1)
        return cy, cx

    def value_at(self, x: Any, y: Any) -> np.ndarray:
        cy, cx = self.cell(x, y)
        return self.grid[cy, cx]


def move_actions(flags: pd.DataFrame) -> pd.DataFrame:
    """Passes and carries with start and end coordinates; ``successful`` marks actions that kept the ball."""
    ev = flags[flags["type"].isin(["Pass", "Carry"])].dropna(subset=["x", "y", "end_x", "end_y"]).copy()
    ev["successful"] = np.where(ev["type"] == "Pass", ev["outcome"].isna(), True)
    return ev


def fit_xt(flags: pd.DataFrame, nx: int = 16, ny: int = 12, max_iter: int = 200, tol: float = 1e-6
           ) -> XTGrid | None:
    """Fit the xT grid; ``None`` when there are too few actions to estimate transition probabilities."""
    moves = move_actions(flags)
    shots = flags[(flags["type"] == "Shot")].dropna(subset=["x", "y", "shot_xg"])
    if len(moves) < 20 * nx * ny or len(shots) < 50:
        return None
    n_cells = nx * ny

    def idx(x: pd.Series, y: pd.Series) -> np.ndarray:
        cx = np.clip((x.to_numpy(float) / PITCH_LENGTH * nx).astype(int), 0, nx - 1)
        cy = np.clip((y.to_numpy(float) / PITCH_WIDTH * ny).astype(int), 0, ny - 1)
        return cy * nx + cx

    start = idx(moves["x"], moves["y"])
    end = idx(moves["end_x"], moves["end_y"])
    ok = moves["successful"].to_numpy(bool)
    move_count = np.bincount(start, minlength=n_cells).astype(float)
    shot_cell = idx(shots["x"], shots["y"])
    shot_count = np.bincount(shot_cell, minlength=n_cells).astype(float)
    xg_sum = np.bincount(shot_cell, weights=shots["shot_xg"].to_numpy(float), minlength=n_cells)
    total = move_count + shot_count
    with np.errstate(divide="ignore", invalid="ignore"):
        p_shot = np.where(total > 0, shot_count / total, 0.0)
        p_move = np.where(total > 0, move_count / total, 0.0)
        shot_value = np.where(shot_count > 0, xg_sum / shot_count, 0.0)
    trans = np.zeros((n_cells, n_cells))
    np.add.at(trans, (start[ok], end[ok]), 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        trans = np.where(move_count[:, None] > 0, trans / move_count[:, None], 0.0)
    xt = np.zeros(n_cells)
    history, converged, it = [], False, 0
    for it in range(1, max_iter + 1):
        new = p_shot * shot_value + p_move * (trans @ xt)
        delta = float(np.abs(new - xt).max())
        history.append(delta)
        xt = new
        if delta < tol:
            converged = True
            break
    counts = pd.DataFrame({"cell": np.arange(n_cells), "row": np.arange(n_cells) // nx, "col": np.arange(n_cells) % nx,
                           "moves": move_count, "shots": shot_count})
    return XTGrid(grid=xt.reshape(ny, nx), shot_prob=p_shot.reshape(ny, nx), move_prob=p_move.reshape(ny, nx),
                  shot_value=shot_value.reshape(ny, nx), counts=counts, nx=nx, ny=ny, iterations=it,
                  converged=converged, n_moves=int(len(moves)), n_shots=int(len(shots)),
                  n_matches=int(flags["match_id"].nunique()), history=history)


def add_xt(flags: pd.DataFrame, grid: XTGrid) -> pd.DataFrame:
    """Successful passes and carries with ``xt_start``, ``xt_end`` and ``xt_added`` (end minus start)."""
    mv = move_actions(flags)
    mv = mv[mv["successful"]].copy()
    mv["xt_start"] = grid.value_at(mv["x"], mv["y"])
    mv["xt_end"] = grid.value_at(mv["end_x"], mv["end_y"])
    mv["xt_added"] = mv["xt_end"] - mv["xt_start"]
    return mv


def player_xt(flags: pd.DataFrame, season: pd.DataFrame, grid: XTGrid, min_minutes: float = 180) -> pd.DataFrame:
    """xT added per player from completed passes and carries, in total and per 90 minutes played."""
    mv = add_xt(flags, grid)
    agg = (mv.groupby(["player_id", "team_id", "type"])["xt_added"].sum().unstack(fill_value=0.0)
           .rename(columns={"Pass": "xt_pass", "Carry": "xt_carry"}).reset_index())
    for c in ("xt_pass", "xt_carry"):
        if c not in agg:
            agg[c] = 0.0
    agg["xt_total"] = agg["xt_pass"] + agg["xt_carry"]
    cols = ["player_id", "team_id", "player_name", "team_name", "primary_role", "role_family", "minutes_played"]
    out = season[cols].merge(agg, on=["player_id", "team_id"], how="left").fillna({"xt_pass": 0.0, "xt_carry": 0.0,
                                                                                    "xt_total": 0.0})
    out["xt_p90"] = np.where(out["minutes_played"] >= min_minutes, out["xt_total"] / out["minutes_played"] * 90,
                             np.nan)
    return out.sort_values("xt_total", ascending=False).reset_index(drop=True)


def xt_sanity(grid: XTGrid) -> pd.DataFrame:
    """Checks a valid surface must pass: bounded values, convergence and more threat closer to goal."""
    g = grid.grid
    third = grid.nx // 3
    own, final = float(g[:, :third].mean()), float(g[:, -third:].mean())
    best = np.unravel_index(int(g.argmax()), g.shape)
    checks = [
        ("Value iteration converged", grid.converged, f"{grid.iterations} iterations"),
        ("All values within [0, 1]", bool((g >= 0).all() and (g <= 1).all()), f"min {g.min():.4f}, max {g.max():.4f}"),
        ("Final third more valuable than own third", final > own, f"{final:.4f} vs {own:.4f}"),
        ("Highest-value cell lies in the attacking penalty-area band", best[1] >= grid.nx - max(2, grid.nx // 6),
         f"cell row {best[0]}, col {best[1]} of {grid.ny} x {grid.nx}"),
    ]
    return pd.DataFrame(checks, columns=["check", "passed", "detail"])
