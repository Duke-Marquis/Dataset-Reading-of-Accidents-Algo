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


def plot_monthly_counts(data: Any, out_png: str = "visuals/monthly_counts.png"):
    """Plot monthly counts (saves PNG)."""
    pd = None
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    # Ensure crash_datetime exists and has datetime dtype using Datapull helper
    from .datapull import _ensure_crash_datetime

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


def plot_top_streets(data: Any, out_png: str = "visuals/top_streets.png", top_n: int = 10):
    """Plot top streets bar chart using counts from compute_stats or derived from data."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    from .datapull import compute_stats

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


def plot_top_months(data: Any, out_png: str = "visuals/top_months.png", top_n: int = 5):
    """Plot top N months by accident count."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    from .datapull import compute_stats
    stats = compute_stats(data)
    top = stats.get("top_months", {})
    names = [str(n) for n in list(top.keys())[:top_n]]
    values = [top[n] for n in list(top.keys())[:top_n]]

    plt.figure(figsize=(8, 4))
    plt.barh(names[::-1], values[::-1])
    plt.title(f"Top {len(names)} months by accidents")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def plot_top_vehicles(data: Any, out_png: str = "visuals/top_vehicles.png", top_n: int = 5):
    """Plot top N vehicle types by occurrence across all vehicle columns."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib and pandas are required for plotting: install via pip") from exc

    from .datapull import compute_stats
    stats = compute_stats(data)
    top = stats.get("top_vehicles", {})
    names = list(top.keys())[:top_n]
    values = [top[n] for n in names]

    plt.figure(figsize=(8, 4))
    plt.barh(names[::-1], values[::-1])
    plt.title(f"Top {len(names)} vehicle types")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def generate_folium_heatmap(data: Any, out_html: str = "heatmap.html"):
    """Generate a folium heatmap HTML file from latitude/longitude columns.

    Requires `folium` be installed.
    """
    try:
        import folium  # type: ignore
        from folium.plugins import HeatMap  # type: ignore
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise RuntimeError("folium and pandas are required for heatmap generation: install via pip") from exc

    # Ensure DataFrame
    df = _as_df(data)
    if not hasattr(df, "shape"):
        df = pd.DataFrame(df)

    # filter rows with valid lat/lon
    lat_col = "latitude" if "latitude" in df.columns else "lat" if "lat" in df.columns else None
    lon_col = "longitude" if "longitude" in df.columns else "lon" if "lon" in df.columns else None
    if lat_col is None or lon_col is None:
        raise ValueError("No latitude/longitude columns found for heatmap generation")

    coords = df[[lat_col, lon_col]].copy()
    # coerce to numeric where possible
    coords[lat_col] = pd.to_numeric(coords[lat_col], errors="coerce")
    coords[lon_col] = pd.to_numeric(coords[lon_col], errors="coerce")
    coords = coords.dropna()

    # If no numeric coords found, try to parse from a 'location' column like "(lat,lon)"
    if coords.empty and "location" in df.columns:
        import re
        parsed = []
        for v in df["location"].dropna().astype(str):
            # Try robust float extraction (handles formats like "(lat,lon)", "lat, lon", or "lat lon")
            m = re.search(r"([+-]?\d+\.\d+).*?([+-]?\d+\.\d+)", v)
            if m:
                parsed.append((float(m.group(1)), float(m.group(2))))
        if parsed:
            coords = pd.DataFrame(parsed, columns=[lat_col, lon_col])

    if coords.empty:
        raise ValueError("No valid coordinates available for heatmap")

    # center map on median location
    center = [float(coords[lat_col].median()), float(coords[lon_col].median())]
    m = folium.Map(location=center, zoom_start=11)
    HeatMap(coords.values.tolist(), radius=8, blur=15).add_to(m)
    m.save(out_html)
    return out_html
