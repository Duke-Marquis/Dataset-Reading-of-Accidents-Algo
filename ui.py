"""Simple interactive CLI for the accidents pipeline.

This file is intentionally independent and easy to edit/remove. It provides a compact
menu allowing the user to:
 - load a CSV (file path or URL)
 - filter by date range
 - compute stats and export report
 - generate plots/heatmap (optional dependencies)
 - search by street name
 - view detailed statistics dashboard
 - search by vehicle type
"""
from datetime import date
from Datapull import load_and_preview, filter_by_date_range, compute_stats, export_report_csv
import crashes_dictionaries as cd
import viz
import statistics as stats_module


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
    print("Accidents data UI (simple). Type 'quit' to exit.")
    print("\nEnter CSV path, URL, or shortcut:")
    print("  - 'nyc' (default)    — NYC API with caching & auto-update")
    print("  - 'nyc:cached'       — Use cached data only")
    print("  - 'nyc:update'       — Force update from NYC API")
    print("  - 'sample'           — Built-in sample data")
    print("  - or a file path\n")
    
    path = input("Enter CSV path or shortcut (or 'nyc' for default): ").strip()
    if not path:
        path = "nyc"  # Default to NYC API
    elif path.strip().lower() == "sample":
        path = "data/sample_2024.csv"

    # If user selected the NYC shortcut, ask for an optional date range first
    path_lower = path.strip().lower()
    start_date_str = None
    end_date_str = None
    force_update = False
    if path_lower in ("nyc", "nyc:latest", "nyc:update"):
        if path_lower == "nyc:update":
            force_update = True
        apply_filter = input("\nApply NYC date filter? (y/n) [default: n]: ").strip().lower()
        if apply_filter == "y":
            # ask for ISO dates (YYYY-MM-DD)
            try:
                start = prompt_date("Start date (YYYY-MM-DD)")
                end = prompt_date("End date (YYYY-MM-DD)")
                if start > end:
                    print("Start date must be earlier than or equal to end date. Skipping date filter.")
                    start_date_str = None
                    end_date_str = None
                else:
                    start_date_str = start.isoformat()
                    end_date_str = end.isoformat()
                    print(f"Using date filter: {start_date_str} to {end_date_str}")
            except Exception:
                print("Invalid dates; proceeding without date filter.")

    # Load data (pass date-range for NYC requests when provided)
    data, _ = load_and_preview(path, preview=0, start_date=start_date_str, end_date=end_date_str, force_update=force_update)

    # If user didn't request an API-level filter, offer an interactive local filter
    if not (start_date_str and end_date_str):
        apply_filter = input("\nApply date filter locally? (y/n) [default: n]: ").strip().lower()
        if apply_filter == "y":
            while True:
                date_range = input("Enter start date and end date (yyyy/mm/dd to yyyy/mm/dd) [default: 2024/01/01 to 2024/12/31]: ").strip()
                # Use default if empty
                if not date_range:
                    date_range = "2024/01/01 to 2024/12/31"
                try:
                    parts = date_range.split(" to ")
                    if len(parts) != 2:
                        print("Please use format: yyyy/mm/dd to yyyy/mm/dd")
                        continue
                    start_str, end_str = parts[0].strip(), parts[1].strip()
                    start_parts = start_str.split("/")
                    end_parts = end_str.split("/")
                    if len(start_parts) != 3 or len(end_parts) != 3:
                        print("Please use format: yyyy/mm/dd to yyyy/mm/dd")
                        continue
                    start = date(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
                    end = date(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]))
                    break
                except (ValueError, IndexError):
                    print("Invalid format. Please use: yyyy/mm/dd to yyyy/mm/dd (e.g., 2020/01/01 to 2023/12/31)")
            filtered = filter_by_date_range(data, start, end)
            print(f"Filtered to {len(filtered)} records between {start} and {end}")
        else:
            filtered = data
            print(f"Using all {len(filtered)} records (no date filter)")
    else:
        # API-filtered data already loaded
        filtered = data
        print(f"Using API-filtered data: {len(filtered)} records (may be truncated by API limits)")

    while True:
        print("\nMenu:")
        print("1) Show brief stats")
        print("2) Show detailed statistics")
        print("3) Search accidents by vehicle type")
        print("4) Filter by borough")
        print("5) Plot monthly counts (PNG)")
        print("6) Plot top streets by borough (PNG)")
        print("7) Export report CSV")
        print("8) Export filtered rows to CSV")
        print("9) Generate folium heatmap (HTML)")
        print("q) Quit")
        choice = input("Choice: ").strip().lower()
        if choice in ("q", "quit"):
            break
        if choice == "1":
            s = compute_stats(filtered)
            print("\n" + "="*70)
            print("BRIEF STATISTICS")
            print("="*70)
            print(f"📊 Total Accidents: {s.get('total_accidents', 0)}")
            print(f"🚑 Total Injured: {s.get('number_of_persons_injured', 0)}")
            print(f"💀 Total Killed: {s.get('number_of_persons_killed', 0)}")
            
            if s.get("top_streets"):
                print(f"\n🏙️  Top 10 Streets by Accidents:")
                for i, (street, count) in enumerate(list(s["top_streets"].items())[:10], 1):
                    print(f"  {i:2d}. {street}: {count} accidents")
            
            if s.get("top_months"):
                print(f"\n📅 Top 6 Months by Accidents:")
                for i, (month, count) in enumerate(list(s["top_months"].items())[:6], 1):
                    print(f"  {i}. {month}: {count} accidents")
            print("="*70 + "\n")
        elif choice == "2":
            detailed_stats = stats_module.get_detailed_stats(filtered)
            stats_module.print_stats_dashboard(detailed_stats)
        elif choice == "3":
            # Option-based vehicle type search
            available_vehicles = stats_module.get_vehicle_types_list(filtered)
            if not available_vehicles:
                print("No vehicle types found in filtered data.")
                continue
            
            print("\n" + "="*70)
            print("VEHICLE TYPE SEARCH - SELECT FROM OPTIONS")
            print("="*70)
            print(f"\nFound {len(available_vehicles)} unique vehicle types:\n")
            
            # Display all options
            for i, vtype in enumerate(available_vehicles, 1):
                print(f"{i:3d}. {vtype}")
            
            print(f"\n0. Enter custom search term")
            print(f"q. Cancel")
            
            choice_input = input("\nEnter option number or search term: ").strip()
            
            if choice_input.lower() == "q":
                continue
            
            vehicle_term = None
            
            # Check if it's a number selection
            try:
                option_num = int(choice_input)
                if option_num == 0:
                    # Custom search
                    vehicle_term = input("Enter vehicle type to search: ").strip()
                elif 1 <= option_num <= len(available_vehicles):
                    vehicle_term = available_vehicles[option_num - 1]
                else:
                    print("Invalid option")
                    continue
            except ValueError:
                # User entered text directly
                vehicle_term = choice_input
            
            if vehicle_term:
                matches = stats_module.search_by_vehicle_type(filtered, vehicle_term)
                print(f"\n{'='*70}")
                print(f"RESULTS: Accidents with '{vehicle_term}'")
                print(f"{'='*70}")
                print(f"\nFound {len(matches)} crashes\n")
                
                if matches:
                    total_injured = 0
                    total_killed = 0
                    for m in matches:
                        try:
                            total_injured += int(m.get("number_of_persons_injured") or 0)
                        except:
                            pass
                        try:
                            total_killed += int(m.get("number_of_persons_killed") or 0)
                        except:
                            pass
                    
                    print(f"📊 Summary:")
                    print(f"   Total Injured: {total_injured}")
                    print(f"   Total Killed: {total_killed}")
                    print(f"   Average Injured Per Crash: {total_injured/len(matches):.2f}")
                    
                    show_details = input("\nShow detailed records? (y/n): ").lower()
                    if show_details == "y":
                        print(f"\n{'─'*70}")
                        for i, m in enumerate(matches[:10], 1):
                            print(f"\nRecord {i}:")
                            for k, v in list(m.items())[:8]:
                                print(f"  {k}: {v}")
                        if len(matches) > 10:
                            print(f"\n... and {len(matches) - 10} more records")
                        print(f"{'─'*70}")
        elif choice == "4":
            # Option-based borough filter
            available_boroughs = stats_module.get_boroughs_list(filtered)
            if not available_boroughs:
                print("No boroughs found in filtered data.")
                continue
            
            print("\n" + "="*70)
            print("BOROUGH FILTER - SELECT FROM OPTIONS")
            print("="*70)
            print(f"\nFound {len(available_boroughs)} boroughs:\n")
            
            # Display all options
            for i, borough in enumerate(available_boroughs, 1):
                print(f"{i}. {borough}")
            
            print(f"\n0. Enter custom search term")
            print(f"q. Cancel")
            
            choice_input = input("\nEnter option number or borough name: ").strip()
            
            if choice_input.lower() == "q":
                continue
            
            borough_term = None
            
            # Check if it's a number selection
            try:
                option_num = int(choice_input)
                if option_num == 0:
                    # Custom search
                    borough_term = input("Enter borough name to filter: ").strip()
                elif 1 <= option_num <= len(available_boroughs):
                    borough_term = available_boroughs[option_num - 1]
                else:
                    print("Invalid option")
                    continue
            except ValueError:
                # User entered text directly
                borough_term = choice_input
            
            if borough_term:
                matches = stats_module.filter_by_borough(filtered, borough_term)
                print(f"\n{'='*70}")
                print(f"RESULTS: Accidents in '{borough_term}'")
                print(f"{'='*70}")
                print(f"\nFound {len(matches)} crashes\n")
                
                if matches:
                    total_injured = 0
                    total_killed = 0
                    top_streets = {}
                    
                    for m in matches:
                        try:
                            total_injured += int(m.get("number_of_persons_injured") or 0)
                        except:
                            pass
                        try:
                            total_killed += int(m.get("number_of_persons_killed") or 0)
                        except:
                            pass
                        street = m.get("on_street_name", "")
                        if isinstance(street, str):
                            street = street.strip()
                        else:
                            street = ""
                        if street:
                            top_streets[street] = top_streets.get(street, 0) + 1
                    
                    print(f"📊 Summary for {borough_term}:")
                    print(f"   Total Accidents: {len(matches)}")
                    print(f"   Total Injured: {total_injured}")
                    print(f"   Total Killed: {total_killed}")
                    
                    if top_streets:
                        print(f"\n   Top Streets in {borough_term}:")
                        for street, count in sorted(top_streets.items(), key=lambda x: x[1], reverse=True)[:5]:
                            print(f"     - {street}: {count}")
                    
                    show_details = input("\nShow detailed records? (y/n): ").lower()
                    if show_details == "y":
                        print(f"\n{'─'*70}")
                        for i, m in enumerate(matches[:10], 1):
                            print(f"\nRecord {i}:")
                            for k, v in list(m.items())[:8]:
                                print(f"  {k}: {v}")
                        if len(matches) > 10:
                            print(f"\n... and {len(matches) - 10} more records")
                        print(f"{'─'*70}")
        elif choice == "5":
            out = input("PNG path [data/monthly_counts.png]: ") or "data/monthly_counts.png"
            try:
                viz.plot_monthly_counts(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Plotting failed:", e)
        elif choice == "6":
            out = input("PNG path [data/top_streets.png]: ") or "data/top_streets.png"
            try:
                viz.plot_top_streets(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Plotting failed:", e)
        elif choice == "7":
            out = input("Report path [data/report.csv]: ") or "data/report.csv"
            export_report_csv(compute_stats(filtered), out)
            print(f"Wrote {out}")
        elif choice == "8":
            out = input("Filtered CSV path [data/filtered.csv]: ") or "data/filtered.csv"
            cd.write_csv_header(out)
            rows = filtered.to_dict(orient="records") if hasattr(filtered, "to_dict") else filtered
            cd.append_rows_to_csv(out, rows)
            print(f"Wrote {out}")
        elif choice == "9":
            out = input("HTML path [data/heatmap.html]: ") or "data/heatmap.html"
            try:
                viz.generate_folium_heatmap(filtered, out)
                print(f"Saved {out}")
            except Exception as e:
                print("Heatmap failed:", e)
        else:
            print("Unknown choice")


if __name__ == "__main__":
    interactive()
    