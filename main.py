"""Simple CLI to load, filter and report on the NYC crashes CSV (2024 analysis).

Usage example:
    python main.py path/to/nyc_collisions.csv

The script will filter to Jan 1 2024 - Dec 31 2024, compute simple stats and write
`report_2024.csv` and `filtered_2024.csv` in the current directory.
"""

from datetime import date
import argparse
from pathlib import Path

from Datapull import load_and_preview, filter_by_date_range, compute_stats, export_report_csv
import crashes_dictionaries as cd


def main():
    parser = argparse.ArgumentParser(description="Extract, filter and report on accidents CSV")
    parser.add_argument("file", nargs="?", default="sample", help="Path or URL to the accidents CSV file (or 'sample')")
    parser.add_argument("--start", default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--out-report", default="report_2024.csv", help="Path to write the report summary CSV")
    parser.add_argument("--out-filter", default="filtered_2024.csv", help="Path to write filtered rows CSV")
    parser.add_argument("--no-pandas", action="store_true", help="Force not to use pandas even if available")
    parser.add_argument("--plot-monthly", action="store_true", help="Generate monthly counts PNG")
    parser.add_argument("--plot-streets", action="store_true", help="Generate top streets PNG")
    parser.add_argument("--heatmap", action="store_true", help="Generate folium heatmap HTML")
    parser.add_argument("--search", help="Search substring for `on_street_name` and write matches to CSV")
    parser.add_argument("--search-out", default="search_matches.csv", help="CSV path for search matches")
    args = parser.parse_args()

    # handle 'sample' alias
    path = args.file
    if path == "sample":
        path = "data/sample_2024.csv"

    print(f"Loading data from: {path}")
    data, summary = load_and_preview(path, preview=0, use_pandas=not args.no_pandas)

    # parse date range
    from datetime import datetime
    try:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
    except Exception:
        raise SystemExit("Start and End must be YYYY-MM-DD")

    print(f"Filtering data between {start} and {end}...")
    filtered = filter_by_date_range(data, start, end)

    stats = compute_stats(filtered)

    # print short summary
    print("=== Summary ===")
    print(f"Range: {start} to {end}")
    print(f"Total accidents: {stats.get('total_accidents')}")
    print(f"Persons injured: {stats.get('number_of_persons_injured')}")
    print(f"Persons killed: {stats.get('number_of_persons_killed')}")
    print("Top streets:")
    for k, v in (stats.get("top_streets") or {}).items():
        print(f"  {k}: {v}")

    # export report CSV
    print(f"Writing report to {args.out_report}...")
    export_report_csv(stats, args.out_report)

    # write filtered rows to CSV using crashes_dictionaries
    out_filter = Path(args.out_filter)
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
            print(f"Writing search matches ({len(matches)}) to {args.search_out}")
            cd.write_csv_header(args.search_out)
            cd.append_rows_to_csv(args.search_out, matches)
        else:
            print("No matches found for the search term.")

    # optional plotting/heatmap
    if args.plot_monthly:
        try:
            import viz as _viz
            out = _viz.plot_monthly_counts(filtered, out_png="monthly_counts.png")
            print(f"Monthly chart saved to {out}")
        except Exception as e:
            print("Monthly chart generation failed:", e)

    if args.plot_streets:
        try:
            import viz as _viz
            out = _viz.plot_top_streets(filtered, out_png="top_streets.png")
            print(f"Top streets chart saved to {out}")
        except Exception as e:
            print("Top streets chart generation failed:", e)

    if args.heatmap:
        try:
            import viz as _viz
            out = _viz.generate_folium_heatmap(filtered, out_html="heatmap.html")
            print(f"Heatmap saved to {out}")
        except Exception as e:
            print("Heatmap generation failed:", e)

    print("Done.")


if __name__ == '__main__':
    main()