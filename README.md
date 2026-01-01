# Dataset Reading of Accidents – NYC Motor Vehicle Collisions

## 📚 Project Overview

This repository contains a small data‑science toolkit for exploring the NYC Motor Vehicle Collisions dataset. The data is pulled from the official NYC Open Data portal, cached locally, and can be visualised via a command‑line interface (`ui.py`) or a lightweight Tkinter GUI (`ui_tk.py`).

The main components are:

| File               | Purpose                                                              |
| ------------------ | -------------------------------------------------------------------- |
| `accidents/datapull.py` | Handles downloading, caching, and filtering of the CSV data.         |

## Project layout
- `accidents/` — core library (data pulling, stats, visualizations) 🔧
- `apps/` — GUI and CLI entry points (run `python ui_tk.py` or `python ui.py`) 🖥️
- `data/` — cached CSVs and sample datasets 📂
- `visuals/` — generated charts and images (monthly/top charts) 🖼️
- `tkinter` (GUI) — not a pip package; usually included with Python. On Debian/Ubuntu install via `sudo apt install python3-tk`. If the GUI fails to start, ensure Tcl/Tk is available in your Python installation.
- `docs/` — extra docs like data caching notes 📄

Charts are now written to `visuals/` by default. You can override the output path when calling the plotting functions.
| `ui.py`            | Interactive CLI menu – statistics, plots, CSV export, etc.           |
| `ui_tk.py`         | Tkinter GUI wrapper that simply calls the same logic as `ui.py`.     |
| `main.py`          | Entry point for the CLI when the repository is executed as a script. |
| `requirements.txt` | Python dependencies.                                                 |

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

> **Note**: If you prefer to use `pipenv` or `poetry`, you can adapt the above steps accordingly.

---

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

## 🖥️ Running the CLI (`ui.py`)

```bash
# From the repository root
python ui.py
```

You will be presented with a menu:

```
1) Show brief stats
2) Show detailed statistics
3) Search accidents by vehicle type
4) Filter by borough
5) Plot monthly counts (PNG)
6) Plot top streets by borough (PNG)
7) Export report CSV
8) Export filtered rows to CSV
9) Generate folium heatmap (HTML)
q) Quit
```

**Key points**:

- When you choose `nyc` as the data source, you will be prompted for an optional date range. If you skip it, the script will load the full cached dataset.
- All PNG and HTML outputs are written to the `data/` folder by default.
- The CLI is intentionally lightweight – no external UI libraries are required.

---

## 🎨 Running the GUI (`ui_tk.py`)

The Tkinter GUI is a thin wrapper around the same logic used by the CLI. It provides a simple window with buttons for each menu option.

```bash
python ui_tk.py
```

> **Tip**: The GUI requires the same dependencies as the CLI. If you followed the setup instructions above, it will work out of the box.

---

## 📦 Packaging & Distribution

If you want to distribute the project as a standalone executable, you can use `PyInstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile ui.py
```

This will create an executable in the `dist/` folder.

---

## 🤝 Contributing

Feel free to open issues or pull requests. The project is intentionally small, so any improvements – better caching, more visualisations, or additional filters – are welcome.

---

Happy exploring!
