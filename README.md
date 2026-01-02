# Dataset Reading of Accidents – NYC Motor Vehicle Collisions

## 📚 Project Overview

This repository contains a small data‑science toolkit for exploring the NYC Motor Vehicle Collisions dataset. The data is pulled from the official NYC Open Data portal, cached locally, and can be used via an interactive CLI (`main.py`) or a Flask web app (`web_app/web_app.py`).

The main components are:

| File                    | Purpose                                                      |
| ----------------------- | ------------------------------------------------------------ |
| `accidents/datapull.py` | Downloading, caching, and filtering of the CSV data.         |
| `main.py`               | Interactive CLI menu for stats, plots, heatmap, and exports. |
| `web_app/web_app.py`    | Flask web interface (tables, charts, heatmap preview).       |
| `web_app/templates/`    | HTML templates for the web app.                              |
| `accidents/viz.py`      | Plotting and folium heatmap generation.                      |
| `data/`                 | Cached CSV and metadata; created on first run.               |
| `static/`               | Generated plots and maps (served by web app).                |

## Project layout

- `accidents/` — core library (data pulling, stats, visualizations) 🔧
- `web_app/` — Flask web app (`web_app/web_app.py`) with templates and static assets 🖥️
- `main.py` — interactive CLI entry point 🎛️
- `run-web_app.py` — launcher script for the Flask web app 🚀
- `data/` — cached CSVs and sample datasets 📂
- `static/` — generated charts and maps (plots/, maps/) 🖼️
- `docs/` — extra docs like data caching notes 📄

Charts and maps are written to `static/plots/` and `static/maps/` respectively. You can override the output path when calling the plotting functions.

The dataset is cached in the `data/` folder. The first run will download the full dataset (or a date‑filtered subset) and store it as `nyc_crashes_cached.csv`.

---

## ⚙️ Prerequisites

- **Python 3.10+** (the project was developed with 3.13.7).
- `pip` and `venv` (standard with Python).

> **Tip**: The repository ships a `requirements.txt` file – no need to install any system‑wide packages.

---

## 🚀 Setup

```bash
# 1. Clone the repo (if you haven't already)
# 2. Create a virtual environment
python3 -m venv .venv

# 3. Activate it
# On macOS/Linux
source .venv/bin/activate
# On Windows
# .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

The `requirements.txt` contains:

```
pandas
matplotlib
folium
```

> =2.0.0
> matplotlib>=3.7.0
> folium>=0.15.0
> flask>=3.0.0
> requests>=2.31.0

## python-dateutil>=2.8.0

web app

## 📦 Data

The first time you run the CLI or GUI the script will:

1. Check if a cached CSV exists in `data/nyc_crashes_cached.csv`.
2. If the cache is older than 7 days or you explicitly request an update, the script will download the latest data from the NYC Open Data API.
3. The data is stored in `data/nyc_crashes_cached.csv` and a metadata file `data/nyc_crashes_meta.json` is created.

You can also manually download the CSV from the API endpoint:

```
https://data.cityofnewyork.us/resource/h9gi-nx95.csv
```

and place it in the `data/` folder – the CLI will use it automatically.

---

## 🖥️ Running the CLI (`main.py`)

```bash
# From the repository root
python3 main.py
```

You will be presented with a menu:

```
1) Show brief statistics
2) Show detailed statistics
3) Search accidents by vehicle type
4) Filter by borough
5) Plot monthly counts (PNG)
6) Plot top streets by borough (PNG)
7) Generate folium heatmap (HTML)
8) Export report CSV
q) Quit
```

**Key points**:

- You will be prompted for an optional date range (YYYY/MM/DD). If you skip it, the script loads the cached dataset in `data/nyc_crashes_cached.csv`.
- PNG plots are written to `static/plots/`; the folium heatmap is written to `static/maps/heatmap.html`.
- The CLI is intentionally lightweight – no external UI libraries are required.

---

## 🌐 Running the Web App (`web_app/web_app.py`)

The Flask app surfaces the same data via tables and embeds the folium heatmap.

```bash
# From the repository root
python3 run-web_app.py

# Or directly run web_app.py from the web_app/ directory
# cd web_app && python3 web_app.py
```

Then open http://localhost:5001 in your browser.

Notes:

- The app automatically loads/refreshes the cached CSV in `data/` on startup.
- Plots and the heatmap are saved to `static/plots/` and `static/maps/`; the web app renders them inline.
- Port 5001 is used to avoid conflicts with macOS AirPlay.

---

## 🤝 Contributing

Feel free to open issues or pull requests. The project is intentionally small, so any improvements – better caching, more visualisations, or additional filters – are welcome.

---

Happy exploring!
