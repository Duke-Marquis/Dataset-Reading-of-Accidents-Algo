# Dataset Reading of Accidents – NYC Motor Vehicle Collisions

## 📚 Project Overview

This repository contains a data-science toolkit for exploring the NYC Motor Vehicle Collisions dataset. The data is pulled from the official NYC Open Data portal, cached locally, and can be accessed via:

- **CLI** (`main.py`) — Interactive command-line interface
- **Web App** (`web_app/web_app.py`) — Flask web interface with modern design
- **Desktop GUI** (`ui_app/app.py`) — Tkinter desktop application with tabbed interface

The main components are:

| File                    | Purpose                                                       |
| ----------------------- | ------------------------------------------------------------- |
| `accidents/datapull.py` | Downloading, caching, and filtering of CSV data.              |
| `main.py`               | Interactive CLI menu for stats, plots, heatmap, and exports.  |
| `web_app/web_app.py`    | Flask web interface with dashboard and charts.                |
| `ui_app/app.py`         | Tkinter desktop GUI with 7 interactive tabs.                  |
| `accidents/viz.py`      | Plotting and folium heatmap generation.                       |
| `data/`                 | Cached CSV and metadata; created on first run.                |
| `static/`               | Generated plots and maps (shared by web app and desktop GUI). |

## Project Layout

```
.
├── accidents/              # Core library (data pulling, stats, visualizations) 🔧
│   ├── __init__.py
│   ├── datapull.py        # Data downloading and caching
│   ├── crashes_dictionaries.py  # NYC data mappings
│   ├── statistics.py      # Statistical computations
│   └── viz.py             # Plotting and heatmap generation
├── web_app/               # Flask web application 🖥️
│   ├── web_app.py         # Flask app (port 5001)
│   ├── run-web_app.py     # Launcher script
│   └── templates/         # HTML templates
├── ui_app/                # Tkinter desktop GUI 💻
│   ├── app.py             # Main desktop application
│   └── run-ui_app.py      # Launcher script
├── static/                # Generated outputs 🖼️
│   ├── css/               # Web app stylesheets
│   ├── plots/             # PNG charts
│   └── maps/              # HTML heatmaps
├── data/                  # Cached data 📂
│   ├── nyc_crashes_cached.csv
│   └── nyc_crashes_meta.json
├── main.py                # CLI entry point 🎛️
├── requirements.txt       # Python dependencies
└── README.md              # This file

```

Charts and maps are written to `static/plots/` and `static/maps/` respectively. The dataset is cached in `data/`. The first run will download the full dataset and store it as `nyc_crashes_cached.csv`.

---

## ⚙️ Prerequisites

- **Python 3.10+** (developed with 3.13.7)
- `pip` and `venv` (standard with Python)
- For desktop GUI on Linux: `sudo apt install python3-tk` (Tkinter)

---

## 🚀 Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd Dataset-Reading-of-Accidents-Algo

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

**Dependencies** (in `requirements.txt`):

- `pandas>=2.0.0` — Data processing
- `matplotlib>=3.7.0` — Static charts
- `folium>=0.15.0` — Interactive heatmaps
- `flask>=3.0.0` — Web framework
- `requests>=2.31.0` — API calls
- `python-dateutil>=2.8.0` — Date parsing

---

## 📦 Data Caching

The first time you run any interface, the script will:

1. Check for cached data in `data/nyc_crashes_cached.csv`
2. If cache is older than 7 days or missing, download latest from NYC Open Data
3. Store data and metadata in `data/`

You can manually download from:

```
https://data.cityofnewyork.us/resource/h9gi-nx95.csv
```

---

## 🎛️ Running the CLI

```bash
python3 main.py
```

Interactive menu with options for:

- View statistics (brief/detailed)
- Search by vehicle type
- Filter by borough
- Generate visualizations (PNG plots)
- Generate heatmap (interactive HTML)
- Export reports (CSV)

---

## 🖥️ Running the Web App

```bash
python3 run-web_app.py
```

Opens **http://localhost:5001** with:

- Dashboard with statistics cards
- Searchable data tables
- Interactive visualizations
- Borough analysis and vehicle type breakdown
- Heatmap preview

---

## 💻 Running the Desktop GUI

```bash
python3 run-ui_app.py
```

Launches a tabbed Tkinter application with:

1. **Home** — Dataset overview and quick stats
2. **Filter** — Date range filtering
3. **Statistics** — Brief/detailed stats with borough breakdown
4. **Visualizations** — Monthly counts, borough charts, top streets
5. **Vehicles** — Search by vehicle type
6. **Heatmap** — Interactive geographic heatmap builder
7. **Export** — Save filtered data or reports as CSV

Features:

- Modern design matching the web app
- Blue accent color (#2563eb) and light theme
- Large, responsive buttons
- Async data loading with status indicators
- PNG image popups for charts
- Inter font typography

---

## 🤝 Contributing

Feel free to open issues or pull requests. Contributions welcome!

---

**Authors**: Marc Aaron Africano, Alexander John Balagso

Happy exploring! 🚀
