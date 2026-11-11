"""Pass-network tables and NetworkX centrality measures."""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
from typing import Any


def pass_network(flags: pd.DataFrame, appearances: pd.DataFrame, match_id: Any, team_id: Any,
                 min_passes: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, float | None]:
    """Nodes (average pass origin) and edges (completed passer->recipient counts).

    Restricted to the period before the team's first substitution so all nodes
    represent players on the pitch together. Returns (nodes, edges, cutoff_minute).
    """
    ev = flags[(flags["match_id"] == match_id) & (flags["team_id"] == team_id)]
    if ev.empty:
        return pd.DataFrame(), pd.DataFrame(), None
    subs = ev[ev["type"] == "Substitution"]["elapsed_min"]
    cutoff = float(subs.min()) if len(subs) else float(ev["elapsed_min"].max())
    p = ev[(ev["type"] == "Pass") & (ev["elapsed_min"] < cutoff) & ev["x"].notna()]
    comp = p[p["outcome"].isna() & p["pass_recipient_id"].notna()]
    nodes = (p.groupby(["player_id", "player_name"]).agg(x=("x", "mean"), y=("y", "mean"), passes=("x", "size"))
             .reset_index())
    names = appearances[(appearances["match_id"] == match_id)].set_index("player_id")["player_name"]
    nodes["display_name"] = nodes["player_id"].map(names).fillna(nodes["player_name"])
    edges = (comp.groupby(["player_id", "pass_recipient_id"]).size().rename("count").reset_index())
    edges = edges[edges["count"] >= min_passes]
    pos = nodes.set_index("player_id")[["x", "y"]]
    edges = edges[edges["player_id"].isin(pos.index) & edges["pass_recipient_id"].isin(pos.index)]
    if not edges.empty:
        edges = edges.assign(x0=edges["player_id"].map(pos["x"]), y0=edges["player_id"].map(pos["y"]),
                             x1=edges["pass_recipient_id"].map(pos["x"]), y1=edges["pass_recipient_id"].map(pos["y"]))
    return nodes, edges, cutoff


def match_pass_graph(flags: pd.DataFrame, match_id, team_id) -> nx.DiGraph:
    """Directed weighted graph of completed passes before the team's first substitution."""
    ev = flags[(flags.match_id == match_id) & (flags.team_id == team_id)]
    subs_t = ev.loc[ev.type == "Substitution", "elapsed_min"]
    cut = subs_t.min() if len(subs_t) else np.inf
    p = ev[(ev.passes_completed == 1) & (ev.elapsed_min < cut) & ev.pass_recipient_id.notna()]
    G = nx.DiGraph()
    for (a, b), n in p.groupby(["player_id", "pass_recipient_id"]).size().items():
        G.add_edge(a, b, weight=float(n), dist=1.0 / n)
    return G


def network_centrality(flags: pd.DataFrame, team_stats: pd.DataFrame, team: str) -> pd.DataFrame:
    """Per-match centralities, averaged per player over the season."""
    rows = []
    for _, m in team_stats[team_stats.team_name == team].iterrows():
        G = match_pass_graph(flags, m.match_id, m.team_id)
        if G.number_of_nodes() < 5:
            continue
        tot = sum(d["weight"] for *_, d in G.edges(data=True))
        btw = nx.betweenness_centrality(G, weight="dist", normalized=True)
        pr = nx.pagerank(G, weight="weight")
        for n in G.nodes:
            rows.append({"match_id": m.match_id, "player_id": n, "pagerank": pr[n], "betweenness": btw[n],
                         "pass_share": (G.out_degree(n, weight="weight") + G.in_degree(n, weight="weight")) / (2 * tot)})
    return pd.DataFrame(rows)


def aggregate_network(passes: pd.DataFrame, min_passes: int = 5, top_players: int = 14
                      ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Nodes and edges from any set of passes (several matches, a score state, a time window).

    Nodes sit at the mean origin of each player's passes; edges count completed passes between a pair. Unlike
    the single-match network, players here were not necessarily on the pitch together, so the node layout is a
    summary of pass origins and the caller must say which matches or minutes were pooled.
    """
    p = passes[(passes["type"] == "Pass")].dropna(subset=["x", "y", "player_id"])
    if p.empty:
        return pd.DataFrame(), pd.DataFrame()
    nodes = (p.groupby(["player_id", "player_name"]).agg(x=("x", "mean"), y=("y", "mean"), passes=("x", "size"))
             .reset_index().sort_values("passes", ascending=False).head(top_players))
    nodes["display_name"] = nodes["player_name"]
    comp = p[p["outcome"].isna() & p["pass_recipient_id"].notna()]
    edges = comp.groupby(["player_id", "pass_recipient_id"]).size().rename("count").reset_index()
    pos = nodes.set_index("player_id")[["x", "y"]]
    edges = edges[(edges["count"] >= min_passes) & edges["player_id"].isin(pos.index)
                  & edges["pass_recipient_id"].isin(pos.index)]
    if not edges.empty:
        edges = edges.assign(x0=edges["player_id"].map(pos["x"]), y0=edges["player_id"].map(pos["y"]),
                             x1=edges["pass_recipient_id"].map(pos["x"]), y1=edges["pass_recipient_id"].map(pos["y"]))
    return nodes.reset_index(drop=True), edges.reset_index(drop=True)


def centrality_summary(net: pd.DataFrame, names: pd.Series, min_matches: int = 5) -> pd.DataFrame:
    """Season-average centralities per player (players with at least ``min_matches`` match networks)."""
    if net is None or net.empty:
        return pd.DataFrame()
    out = (net.groupby("player_id").agg(matches=("match_id", "nunique"), pagerank=("pagerank", "mean"),
                                        betweenness=("betweenness", "mean"), pass_share=("pass_share", "mean"),
                                        pagerank_sd=("pagerank", "std")).reset_index())
    out = out[out["matches"] >= min_matches]
    out["player"] = out["player_id"].map(names)
    return out.sort_values("pagerank").reset_index(drop=True)


def pair_pass_matrix(passes: pd.DataFrame, top_players: int = 14) -> pd.DataFrame:
    """Completed passes from each passer (rows) to each recipient (columns) among the most involved players."""
    comp = passes[(passes["type"] == "Pass") & passes["outcome"].isna() & passes["pass_recipient_id"].notna()]
    if comp.empty:
        return pd.DataFrame()
    vol = pd.concat([comp["player_name"], comp["pass_recipient_name"]]).value_counts().head(top_players).index
    tab = pd.crosstab(comp["player_name"], comp["pass_recipient_name"])
    return tab.reindex(index=vol, columns=vol, fill_value=0)


def role_interaction_matrix(passes: pd.DataFrame, appearances: pd.DataFrame) -> pd.DataFrame:
    """Completed passes between match roles (passer role in rows, recipient role in columns)."""
    comp = passes[(passes["type"] == "Pass") & passes["outcome"].isna() & passes["pass_recipient_id"].notna()]
    if comp.empty:
        return pd.DataFrame()
    role = appearances.dropna(subset=["match_role"]).set_index(["match_id", "player_id"])["match_role"]
    a = [role.get((m, p)) for m, p in zip(comp["match_id"], comp["player_id"])]
    b = [role.get((m, p)) for m, p in zip(comp["match_id"], comp["pass_recipient_id"])]
    d = pd.DataFrame({"from": a, "to": b}).dropna()
    return pd.crosstab(d["from"], d["to"])


def remove_node_scenario(graph: nx.DiGraph, names: pd.Series | dict | None = None) -> pd.DataFrame:
    """Simulation: how the pass graph's connectivity changes when each player is removed in turn.

    Reports the share of completed passes that involved the player and the change in weighted global
    efficiency. This is a property of the recorded graph, not a prediction of how the team would play without
    the player (team-mates would redistribute their passes).
    """
    if graph.number_of_nodes() < 4:
        return pd.DataFrame()
    und = nx.Graph()
    for u, v, d in graph.edges(data=True):
        w = und.get_edge_data(u, v, {"weight": 0.0})["weight"] + d["weight"]
        und.add_edge(u, v, weight=w, dist=1.0 / w)

    def efficiency(g: nx.Graph) -> float:
        n = g.number_of_nodes()
        if n < 2:
            return 0.0
        total = 0.0
        for _, lengths in nx.all_pairs_dijkstra_path_length(g, weight="dist"):
            total += sum(1.0 / l for l in lengths.values() if l > 0)
        return total / (n * (n - 1))

    base = efficiency(und)
    tot = sum(d["weight"] for *_, d in graph.edges(data=True))
    rows = []
    for node in list(und.nodes):
        g2 = und.copy()
        g2.remove_node(node)
        involved = sum(d["weight"] for u, v, d in graph.edges(data=True) if node in (u, v))
        rows.append({"player_id": node, "player": (names.get(node, node) if names is not None else node),
                     "pass_share_involved": involved / tot if tot else np.nan,
                     "efficiency_change_pct": 100 * (efficiency(g2) - base) / base if base else np.nan,
                     "still_connected": nx.is_connected(g2) if g2.number_of_nodes() else False})
    return pd.DataFrame(rows).sort_values("efficiency_change_pct").reset_index(drop=True)
