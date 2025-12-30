"""Visualization helpers for accidents dataset.

Functions are optional and attempt to import matplotlib/folium at runtime. They accept
either a pandas.DataFrame or list[dict] (similar to Datapull helpers).
"""
from __future__ import annotations
from typing import Any


def _as_df(data: Any):
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None
    if pd is not None and hasattr(data, "shape"):
        return data
    # convert list[dict] to DataFrame if pandas present
    if pd is not None and isinstance(data, list):
        return pd.DataFrame(data)
    # no pandas available -> try to handle lists manually
    return data


def plot_monthly_counts(data: Any, out_png: str = "monthly_counts.png"):
    """Plot monthly counts (saves PNG)."""
    pd = None
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    # Ensure crash_datetime exists and has datetime dtype using Datapull helper
    from Datapull import _ensure_crash_datetime

    ensured = _ensure_crash_datetime(data)
    if hasattr(ensured, "shape"):
        df = ensured
    else:
        df = pd.DataFrame(ensured)
    # Ensure 'crash_datetime' is a datetime column
    if pd.api.types.is_datetime64_any_dtype(df['crash_datetime']):
        df["month"] = df["crash_datetime"].dt.to_period("M")
    else:
        raise ValueError("The 'crash_datetime' column must be of datetime type.")
    counts = df["month"].value_counts().sort_index()

    plt.figure(figsize=(10, 5))
    counts.plot(kind="bar")
    plt.title("Accidents per month")
    plt.xlabel("Month")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def plot_top_streets(data: Any, out_png: str = "top_streets.png", top_n: int = 10):
    """Plot top streets bar chart using counts from compute_stats or derived from data."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    from Datapull import compute_stats

    stats = compute_stats(data)

    top = stats.get("top_streets", {})
    names = list(top.keys())[:top_n]
    values = [top[n] for n in names]

    plt.figure(figsize=(10, 5))
    plt.barh(names[::-1], values[::-1])
    plt.title(f"Top {len(names)} streets by accidents")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def generate_folium_heatmap(data: Any, out_html: str = "heatmap.html"):
    """Generate a Folium heatmap HTML file using latitude/longitude if available.

    This requires `folium` and `folium.plugins.HeatMap`.
    """
    try:
        import folium  # type: ignore
        from folium.plugins import HeatMap  # type: ignore
    except Exception as exc:
        raise RuntimeError("folium is required for heatmap generation: pip install folium") from exc

    # extract lat/lon pairs
    rows = data if isinstance(data, list) else (data.to_dict(orient="records") if hasattr(data, "to_dict") else [])
    coords = []
    for r in rows:
        lat = r.get("latitude")
        lon = r.get("longitude")
        try:
            latf = float(lat)
            lonf = float(lon)
            coords.append([latf, lonf])
        except Exception:
            continue

    if not coords:
        raise RuntimeError("No valid latitude/longitude found to build heatmap")

    m = folium.Map(location=coords[0], zoom_start=11)
    HeatMap(coords).add_to(m)
    m.save(out_html)
    return out_html
