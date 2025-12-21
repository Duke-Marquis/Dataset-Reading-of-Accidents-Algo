"""Simple interactive CLI for the accidents pipeline.

This file is intentionally independent and easy to edit/remove. It provides a compact
menu allowing the user to:
 - load a CSV (file path or URL)
 - filter by date range
 - compute stats and export report
 - generate plots/heatmap (optional dependencies)
 - search by street name
"""
from datetime import date
from Datapull import load_and_preview, filter_by_date_range, compute_stats, export_report_csv
import crashes_dictionaries as cd
import viz


def prompt_date(prompt_text: str, default: str | None = None) -> date:
    while True:
        val = input(f"{prompt_text}" + (f" [{default}]" if default else "") + ": ")
        if not val and default:
            val = default
        try:
            y, m, d = val.split("-")
            return date(int(y), int(m), int(d))
        except Exception:
            print("Please provide a date in YYYY-MM-DD format")


def interactive():
    print("Accidents data UI (simple). Type 'quit' to exit.)")
    path = input("Enter CSV path or URL (or 'sample' for built-in sample): ")
    if path.strip().lower() == "sample":
        path = "data/sample_2024.csv"

    data, _ = load_and_preview(path, preview=0)

    start = prompt_date("Start date (YYYY-MM-DD)", "2024-01-01")
    end = prompt_date("End date (YYYY-MM-DD)", "2024-12-31")

    filtered = filter_by_date_range(data, start, end)

    while True:
        print("\nMenu:")
        print("1) Show brief stats")
        print("2) Export report CSV")
        print("3) Export filtered rows to CSV")
        print("4) Plot monthly counts (PNG)")
        print("5) Plot top streets (PNG)")
        print("6) Generate folium heatmap (HTML)")
        print("7) Search by street name")
        print("q) Quit")
        choice = input("Choice: ").strip().lower()
        if choice in ("q", "quit"):
            break
        if choice == "1":
            s = compute_stats(filtered)
            print(s)
        elif choice == "2":
            out = input("Report path [report_2024.csv]: ") or "report_2024.csv"
            export_report_csv(compute_stats(filtered), out)
            print(f"Wrote {out}")
        elif choice == "3":
            out = input("Filtered CSV path [filtered_2024.csv]: ") or "filtered_2024.csv"
            cd.write_csv_header(out)
            rows = filtered.to_dict(orient="records") if hasattr(filtered, "to_dict") else filtered
            cd.append_rows_to_csv(out, rows)
            print(f"Wrote {out}")
        elif choice == "4":
            out = input("PNG path [monthly_counts.png]: ") or "monthly_counts.png"
            try:
                viz.plot_monthly_counts(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Plotting failed:", e)
        elif choice == "5":
            out = input("PNG path [top_streets.png]: ") or "top_streets.png"
            try:
                viz.plot_top_streets(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Plotting failed:", e)
        elif choice == "6":
            out = input("HTML path [heatmap.html]: ") or "heatmap.html"
            try:
                viz.generate_folium_heatmap(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Heatmap failed:", e)
        elif choice == "7":
            term = input("Street name (case-sensitive, substring match): ")
            rows = filtered.to_dict(orient="records") if hasattr(filtered, "to_dict") else filtered
            matches = [r for r in rows if term in (r.get("on_street_name") or "")]
            print(f"Found {len(matches)} matches")
            for m in matches[:20]:
                print(m)
        else:
            print("Unknown choice")


if __name__ == "__main__":
    interactive()
