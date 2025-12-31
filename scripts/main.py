"""Simple CLI to load, filter and report on the NYC crashes CSV.

Usage examples:
    python main.py nyc                              # Use all data
    python main.py nyc --start 2024-01-01 --end 2024-12-31  # Filter to 2024
    python main.py path/to/nyc_collisions.csv       # Use local file
    python main.py sample                           # Use built-in sample data

Special shortcuts:
    - "nyc" or "nyc:latest"  — Pull from NYC API, cache locally, auto-update if > 7 days old
    - "nyc:cached"           — Use cached data only (no internet)
    - "nyc:update"           — Force update from NYC API
    - "sample"               — Use built-in sample

Outputs are written to the data/ folder:
    - data/report.csv             — Summary statistics
    - data/filtered.csv           — Filtered crash records
    - data/search_matches.csv     — Search results (if --search used)
"""

from datetime import date
import argparse
from pathlib import Path
import sys

from pathlib import Path

def _ensure_project_path():
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        # prefer adding src to sys.path when present so package imports work
        src_dir = parent / "src"
        if src_dir.exists() and (src_dir / "accidents").exists():
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            return
        if (parent / "Datapull.py").exists() or (parent / "crashes_dictionaries.py").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return
    cwd = Path.cwd()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))

_ensure_project_path()

from accidents.Datapull import load_and_preview, filter_by_date_range, compute_stats, export_report_csv
from accidents import crashes_dictionaries as cd


def main():
    parser = argparse.ArgumentParser(description="Extract, filter and report on accidents CSV")
    parser.add_argument("file", nargs="?", default="nyc", help="Path, URL, or shortcut to accidents CSV file (default: 'nyc')")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD), default: no filter")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD), default: no filter")
    parser.add_argument("--out-report", default="data/report.csv", help="Path to write the report summary CSV")
    parser.add_argument("--out-filter", default="data/filtered.csv", help="Path to write filtered rows CSV")
    parser.add_argument("--no-pandas", action="store_true", help="Force not to use pandas even if available")
    parser.add_argument("--plot-monthly", action="store_true", help="Generate monthly counts PNG")
    parser.add_argument("--plot-streets", action="store_true", help="Generate top streets PNG")
    parser.add_argument("--search", help="Search substring for `on_street_name` and write matches to CSV")
    parser.add_argument("--search-out", default="data/search_matches.csv", help="CSV path for search matches")
    args = parser.parse_args()

    # handle special shortcuts
    path = args.file
    if path == "sample":
        path = "data/sample_2024.csv"

    print(f"Loading data from: {path}")
    data, summary = load_and_preview(path, preview=0, use_pandas=not args.no_pandas)

    # parse date range (optional)
    from datetime import datetime
    start = None
    end = None
    
    if args.start or args.end:
        try:
            if args.start:
                start = datetime.strptime(args.start, "%Y-%m-%d").date()
            if args.end:
                end = datetime.strptime(args.end, "%Y-%m-%d").date()
        except Exception:
            raise SystemExit("Start and End must be YYYY-MM-DD")
    
    # Filter if date range provided
    if start or end:
        if not start:
            start = datetime(1900, 1, 1).date()
        if not end:
            end = datetime(2100, 12, 31).date()
        print(f"Filtering data between {start} and {end}...")
        filtered = filter_by_date_range(data, start, end)
    else:
        print("Using all data (no date filter)")
        filtered = data

    stats = compute_stats(filtered)

    # print short summary
    print("=== Summary ===")
    if start and end:
        print(f"Range: {start} to {end}")
    else:
        print("Range: All data")
    print(f"Total accidents: {stats.get('total_accidents')}")
    print(f"Persons injured: {stats.get('number_of_persons_injured')}")
    print(f"Persons killed: {stats.get('number_of_persons_killed')}")
    print("Top streets:")
    for k, v in (stats.get("top_streets") or {}).items():
        print(f"  {k}: {v}")

    # Ensure data directory exists
    Path("data").mkdir(parents=True, exist_ok=True)

    # export report CSV
    print(f"Writing report to {args.out_report}...")
    export_report_csv(stats, args.out_report)

    # write filtered rows to CSV using crashes_dictionaries
    out_filter = Path(args.out_filter)
    out_filter.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing filtered rows to {out_filter}...")
    # ensure header
    cd.write_csv_header(out_filter)
    # get rows as list[dict]
    if hasattr(filtered, "to_dict"):
        rows = filtered.to_dict(orient="records")
    else:
        rows = filtered
    cd.append_rows_to_csv(out_filter, rows)

    # optional search extraction
    if args.search:
        term = args.search
        print(f"Searching for street terms containing '{term}'...")
        rows_list = rows
        matches = [r for r in rows_list if term.lower() in (r.get("on_street_name") or "").lower()]
        if matches:
            search_out = Path(args.search_out)
            search_out.parent.mkdir(parents=True, exist_ok=True)
            print(f"Writing search matches ({len(matches)}) to {args.search_out}")
            cd.write_csv_header(args.search_out)
            cd.append_rows_to_csv(args.search_out, matches)
        else:
            print("No matches found for the search term.")

    # optional plotting/heatmap
    if args.plot_monthly:
        try:
            from accidents import viz as _viz
            print(f"Monthly chart saved to {out}")
        except Exception as e:
            print("Monthly chart generation failed:", e)

    if args.plot_streets:
        try:
            from accidents import viz as _viz
            print(f"Top streets chart saved to {out}")
        except Exception as e:
            print("Top streets chart generation failed:", e)


    print("Done.")


if __name__ == '__main__':
    main()