"""Export helpers for charts and tables.

Interactive HTML always works for Plotly figures. Static images of Plotly figures need the optional ``kaleido``
package; when it is missing the export reports that instead of failing or pretending. Matplotlib figures are
written directly as PNG, SVG or PDF.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

PLOTLY_FORMATS = ("html", "json", "png", "svg", "pdf")
MATPLOTLIB_FORMATS = ("png", "svg", "pdf")


def capabilities() -> dict[str, Any]:
    """What can be exported in this environment (checked, not assumed)."""
    kaleido = importlib.util.find_spec("kaleido") is not None
    return {"plotly_html": True, "plotly_json": True, "plotly_static_images": kaleido,
            "plotly_static_note": "" if kaleido else "PNG / SVG / PDF export of interactive charts needs the "
                                                    "optional 'kaleido' package (not installed).",
            "matplotlib_png_svg_pdf": True, "tables_csv": True, "markdown_report": True,
            "pdf_report": False, "pdf_report_note": "No PDF report backend is installed or tested; reports are "
                                                    "written as Markdown and HTML."}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")[:80] or "chart"


def figure_html(fig: go.Figure) -> str:
    """Stand-alone HTML for one Plotly figure (plotly.js loaded from the CDN to keep files small)."""
    return fig.to_html(include_plotlyjs="cdn", full_html=True)


def export_chart(fig: Any, directory: Path | str, name: str, formats: tuple[str, ...] = ("html",)
                 ) -> dict[str, str]:
    """Write a figure in the requested formats. Returns ``{format: path or the reason it was not written}``."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    base = directory / slug(name)
    if isinstance(fig, go.Figure):
        for f in formats:
            if f == "html":
                p = base.with_suffix(".html")
                p.write_text(figure_html(fig), encoding="utf-8")
                out[f] = str(p)
            elif f == "json":
                p = base.with_suffix(".json")
                p.write_text(fig.to_json(), encoding="utf-8")
                out[f] = str(p)
            elif f in ("png", "svg", "pdf"):
                if not capabilities()["plotly_static_images"]:
                    out[f] = "not written: optional package 'kaleido' is not installed"
                    continue
                try:
                    p = base.with_suffix(f".{f}")
                    fig.write_image(str(p), scale=2)
                    out[f] = str(p)
                except Exception as exc:
                    out[f] = f"not written: {type(exc).__name__}: {exc}"
            else:
                out[f] = "not written: unsupported format for an interactive chart"
        return out
    for f in formats:
        if f in MATPLOTLIB_FORMATS:
            p = base.with_suffix(f".{f}")
            fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            out[f] = str(p)
        else:
            out[f] = "not written: static figures support png, svg and pdf"
    return out


def table_csv(df: pd.DataFrame) -> bytes:
    """CSV bytes (UTF-8 with BOM so spreadsheet programs read accented names correctly)."""
    return df.to_csv(index=False).encode("utf-8-sig")


def export_table(df: pd.DataFrame, directory: Path | str, name: str) -> str:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / f"{slug(name)}.csv"
    p.write_bytes(table_csv(df))
    return str(p)


def export_eligible_charts(ws: Any, directory: Path | str, chart_ids: list[str] | None = None,
                           formats: tuple[str, ...] = ("html",), max_charts: int | None = None,
                           progress: Any = None) -> pd.DataFrame:
    """Batch mode: render and export every available chart (or the listed ones) with progress and a limit.

    Never called by default; a caller must ask for it explicitly.
    """
    from src.visualization import registry
    from src.visualization.availability import check

    specs = [s for s in registry.all_specs() if (chart_ids is None or s.chart_id in chart_ids)]
    specs = [s for s in specs if check(s, ws)[0] == registry.IMPLEMENTED_AVAILABLE]
    if max_charts:
        specs = specs[:max_charts]
    p = ws.params()
    rows = []
    for i, s in enumerate(specs, 1):
        try:
            fig = registry.render(s.chart_id, ws, p)
            fmts = formats if isinstance(fig, go.Figure) else tuple(f for f in ("png",) if True)
            written = export_chart(fig, directory, f"{s.chart_id}_{s.name}", fmts)
            rows.append({"chart_id": s.chart_id, "name": s.name, "status": "exported", **written})
            if not isinstance(fig, go.Figure):
                import matplotlib.pyplot as plt

                plt.close(fig)
        except Exception as exc:
            rows.append({"chart_id": s.chart_id, "name": s.name, "status": f"failed: {type(exc).__name__}: {exc}"})
        if progress is not None:
            progress(i, len(specs), s.chart_id)
    return pd.DataFrame(rows)
