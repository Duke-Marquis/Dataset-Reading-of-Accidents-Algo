# Dataset Reading of Accidents Algo
Final Project for CPE 7; to learn data set reading

---

## Sync & Run (✅ quick steps)

1. Create a virtual environment and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install pinned dependencies:

```powershell
pip install -r requirements.txt
```

3. Run unit tests:

```powershell
python -m unittest discover -v
```

4. Example: run the pipeline on the sample file:

```powershell
python main.py data/sample_2024.csv --start 2024-01-01 --end 2024-12-31 --export-report report_2024.csv --export-filtered filtered_2024.csv
```

---
