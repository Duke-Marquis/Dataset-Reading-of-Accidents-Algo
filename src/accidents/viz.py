# Authors: Alexander John Balagso, Marc Aaron Africano

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
    from accidents.Datapull import _ensure_crash_datetime

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

    from accidents.Datapull import compute_stats

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


def generate_folium_heatmap(data: Any, out_html: str = "data/heatmap.html"):
    """Generate a folium heatmap (HTML) from the dataset.

    Accepts a pandas.DataFrame or list[dict]. The function looks for latitude/longitude
    columns (case-insensitive: e.g. 'latitude'/'longitude', 'lat'/'lon') and will
    create an HTML heatmap saved to ``out_html`` (default: ``data/heatmap.html``).
    """
    try:
        import folium  # type: ignore
        from folium.plugins import HeatMap  # type: ignore
    except Exception as exc:
        raise RuntimeError("folium is required to generate heatmaps: pip install folium") from exc

    # Normalize input to a pandas-like structure if possible
    df = _as_df(data)

    # Try to work with pandas if available
    pd = None
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None

    lat_col = None
    lon_col = None

    if pd is not None and hasattr(df, "shape"):
        # DataFrame-like
        cols = {c.lower(): c for c in df.columns}
        for cand_lat in ("latitude", "lat"):
            if cand_lat in cols:
                lat_col = cols[cand_lat]
                break
        for cand_lon in ("longitude", "lon"):
            if cand_lon in cols:
                lon_col = cols[cand_lon]
                break
        if lat_col is None or lon_col is None:
            raise ValueError("Could not find latitude/longitude columns in DataFrame (looked for 'latitude'/'longitude' or 'lat'/'lon').")
        coords_df = df[[lat_col, lon_col]].dropna()
        coords = coords_df.values.tolist()
    else:
        # Assume list[dict] or similar
        rows = df if isinstance(df, list) else list(df or [])
        coords = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            # case-insensitive keys
            keys = {k.lower(): k for k in r.keys()}
            lat_key = keys.get("latitude") or keys.get("lat")
            lon_key = keys.get("longitude") or keys.get("lon")
            if lat_key and lon_key:
                lat = r.get(lat_key)
                lon = r.get(lon_key)
                try:
                    if lat is None or lon is None:
                        continue
                    coords.append([float(lat), float(lon)])
                except Exception:
                    continue

    if not coords:
        raise ValueError("No valid latitude/longitude coordinates found for heatmap generation.")

    # Center map on mean coordinates
    try:
        import statistics as _stats
        mean_lat = _stats.mean([c[0] for c in coords])
        mean_lon = _stats.mean([c[1] for c in coords])
    except Exception:
        mean_lat, mean_lon = coords[0]

    # Ensure output directory exists
    from pathlib import Path
    out_path = Path(out_html)
    if out_path.parent:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=11, tiles="CartoDB positron")
    HeatMap(coords, radius=10, blur=15, max_zoom=13).add_to(m)
    m.save(str(out_path))
    return str(out_path)


def plot_top_vehicles(data: Any, out_png: str = "top_vehicles.png", top_n: int = 5):
    """Plot top vehicles bar chart."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib is required for plotting: install via pip") from exc

    from accidents.statistics import get_top_vehicles

    vehicles = get_top_vehicles(data, top_n=top_n)
    
    if not vehicles:
        raise ValueError("No vehicle data available to plot")
    
    names = list(vehicles.keys())
    values = list(vehicles.values())

    plt.figure(figsize=(10, 5))
    plt.barh(names[::-1], values[::-1])
    plt.title(f"Top {len(names)} vehicles involved in accidents")
    plt.xlabel("Number of accidents")
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def plot_top_months(data: Any, out_png: str = "top_months.png", top_n: int = 5):
    """Plot top months bar chart."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as exc:
        raise RuntimeError("matplotlib is required for plotting: install via pip") from exc

    from accidents.statistics import get_top_months

    months = get_top_months(data, top_n=top_n)
    
    if not months:
        raise ValueError("No month data available to plot")
    
    names = list(months.keys())
    values = list(months.values())

    plt.figure(figsize=(10, 5))
    plt.bar(names, values, color="#0078d4")
    plt.title(f"Top {len(names)} months with most accidents")
    plt.xlabel("Month")
    plt.ylabel("Number of accidents")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png
