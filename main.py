# Authors: Marc Aaron Africano, Alexander John Balagso

"""Interactive CLI for analyzing NYC crashes data.

Features:
  - Prompt for date range filter (yyyy/mm/dd to yyyy/mm/dd)
  - Auto-update from API with fallback to cache
  - Interactive menu with 8 analysis options
"""

from datetime import datetime, date
from pathlib import Path
import sys


def _ensure_project_path():
    here = Path(__file__).resolve().parent
    # Always put project root on sys.path so `accidents` and helpers resolve
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    # Also add parent if run from a nested location
    parent = here.parent
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))


_ensure_project_path()

from accidents.datapull import read_accidents_csv, pull_and_cache_nyc_crashes, filter_by_date_range, compute_stats, export_report_csv
from accidents import viz as _viz
from accidents import crashes_dictionaries as cd


def parse_date_input(date_str: str) -> date:
    """Parse date string in yyyy/mm/dd format."""
    try:
        return datetime.strptime(date_str.strip(), "%Y/%m/%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Please use yyyy/mm/dd")


def get_date_range() -> tuple[date | None, date | None]:
    """Prompt user for date range in yyyy/mm/dd to yyyy/mm/dd."""
    print("\n" + "=" * 60)
    print("DATE RANGE FILTER")
    print("=" * 60)
    print("Enter date range in format: yyyy/mm/dd to yyyy/mm/dd")
    print("(Leave empty to use all data)")

    user_input = input("\nDate range: ").strip()

    if not user_input:
        return None, None

    try:
        parts = user_input.split(" to ")
        if len(parts) != 2:
            raise ValueError("Use format: yyyy/mm/dd to yyyy/mm/dd")
        start = parse_date_input(parts[0])
        end = parse_date_input(parts[1])

        if start > end:
            raise ValueError("Start date must be before end date")

        return start, end
    except ValueError as e:
        print(f"❌ Error: {e}")
        return get_date_range()


def load_data_with_fallback(start_date: date = None, end_date: date = None):
    """Load data from API with fallback to cache."""
    print("\n" + "="*60)
    print("LOADING DATA")
    print("="*60)
    
    try:
        # Convert dates to ISO format if provided
        start_iso = start_date.isoformat() if start_date else None
        end_iso = end_date.isoformat() if end_date else None
        
        print("Attempting to fetch from NYC API...")
        cache_path, metadata = pull_and_cache_nyc_crashes(
            force_update=False,
            start_date=start_iso,
            end_date=end_iso
        )
        
        if metadata.get("source") == "api":
            print("✓ Successfully loaded data from API and cached it")
        else:
            print("⚠ Using cached data (no internet connection available)")
        
        data = read_accidents_csv(str(cache_path), use_pandas=True)
        
        # Filter by date range if provided
        if start_date or end_date:
            if start_date and end_date:
                data = filter_by_date_range(data, start_date, end_date)
            elif start_date:
                data = filter_by_date_range(data, start_date, date(2100, 12, 31))
            else:
                data = filter_by_date_range(data, date(1900, 1, 1), end_date)
        
        return data, metadata
    
    except FileNotFoundError as e:
        print(f"\n❌ Error: Failed to connect to API")
        print("❌ No cached data found")
        print("\nPlease check your internet connection to download the data.")
        print("The data will be cached locally for future offline use.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def show_brief_stats(data):
    """Display brief statistics."""
    stats = compute_stats(data)
    
    print("\n" + "="*60)
    print("BRIEF STATISTICS")
    print("="*60)
    
    total_accidents = stats.get('total_accidents', 0)
    injured = stats.get('number_of_persons_injured', 0)
    killed = stats.get('number_of_persons_killed', 0)
    
    print(f"Total Accidents: {total_accidents:,}")
    print(f"Persons Injured: {injured:,}")
    print(f"Persons Killed: {killed:,}")
    
    if stats.get('top_streets'):
        print("\nTop 5 Streets by Accidents:")
        for i, (street, count) in enumerate(list(stats['top_streets'].items())[:5], 1):
            print(f"  {i}. {street}: {count}")


def show_detailed_stats(data):
    """Display detailed statistics."""
    stats = compute_stats(data)
    
    print("\n" + "="*60)
    print("DETAILED STATISTICS")
    print("="*60)
    
    total_accidents = stats.get('total_accidents', 0)
    injured = stats.get('number_of_persons_injured', 0)
    killed = stats.get('number_of_persons_killed', 0)
    
    print(f"\nOverall Statistics:")
    print(f"  Total Accidents: {total_accidents:,}")
    print(f"  Persons Injured: {injured:,}")
    print(f"  Persons Killed: {killed:,}")
    
    if stats.get('top_streets'):
        print(f"\nTop 10 Streets by Accidents:")
        for i, (street, count) in enumerate(list(stats['top_streets'].items())[:10], 1):
            print(f"  {i}. {street}: {count}")
    
    if stats.get('top_vehicles'):
        print(f"\nTop 10 Vehicle Types:")
        for i, (vehicle, count) in enumerate(list(stats['top_vehicles'].items())[:10], 1):
            print(f"  {i}. {vehicle}: {count}")
    
    if stats.get('top_months'):
        print(f"\nTop 5 Months by Accidents:")
        for i, (month, count) in enumerate(list(stats['top_months'].items())[:5], 1):
            print(f"  {i}. {month}: {count}")


def search_by_vehicle_type(data):
    """Search and filter by vehicle type."""
    try:
        import pandas as pd
        has_pandas = True
    except:
        has_pandas = False
    
    print("\n" + "="*60)
    print("SEARCH BY VEHICLE TYPE")
    print("="*60)
    
    # Get unique vehicle types
    if has_pandas and hasattr(data, 'shape'):
        vehicle_cols = [col for col in data.columns if 'vehicle_type' in col.lower()]
        if not vehicle_cols:
            print("❌ No vehicle type columns found")
            return
        
        all_vehicles = {}
        for col in vehicle_cols:
            vehicles = data[col].value_counts().to_dict()
            for v, count in vehicles.items():
                if v and str(v).lower() != 'nan':
                    all_vehicles[v] = all_vehicles.get(v, 0) + count
        
        all_vehicles = dict(sorted(all_vehicles.items(), key=lambda x: x[1], reverse=True))
        
        print("\nAvailable Vehicle Types:")
        for i, (vehicle, count) in enumerate(list(all_vehicles.items())[:15], 1):
            print(f"  {i}. {vehicle} ({count})")
        
        choice = input("\nEnter vehicle type to search: ").strip().upper()
        
        # Search across all vehicle type columns
        mask = pd.Series([False] * len(data))
        for col in vehicle_cols:
            mask = mask | data[col].str.upper().str.contains(choice, na=False)
        filtered = data[mask]
        
        print(f"\nFound {len(filtered)} accidents with vehicle type containing '{choice}'")
        
        if len(filtered) > 0:
            stats = compute_stats(filtered)
            print(f"  Persons Injured: {stats.get('number_of_persons_injured', 0)}")
            print(f"  Persons Killed: {stats.get('number_of_persons_killed', 0)}")
    else:
        print("⚠ Pandas required for this feature")


def filter_by_borough(data):
    """Filter by borough with options for statistics or streets."""
    try:
        import pandas as pd
        has_pandas = True
    except:
        has_pandas = False
    
    if not has_pandas or not hasattr(data, 'shape'):
        print("⚠ Pandas required for this feature")
        return
    
    print("\n" + "="*60)
    print("FILTER BY BOROUGH")
    print("="*60)
    
    if 'borough' not in data.columns:
        print("❌ Borough column not found")
        return
    
    boroughs = data['borough'].value_counts().to_dict()
    boroughs_list = sorted([b for b in boroughs.keys() if pd.notna(b) and b])
    
    print("\nAvailable Boroughs:")
    for i, borough in enumerate(boroughs_list, 1):
        print(f"  {i}. {borough} ({boroughs[borough]} accidents)")
    
    try:
        choice = int(input("\nSelect borough (number): ")) - 1
        if 0 <= choice < len(boroughs_list):
            selected_borough = boroughs_list[choice]
            borough_data = data[data['borough'] == selected_borough]
            
            print(f"\nSelected: {selected_borough}")
            print("\nOptions:")
            print("  1. Show borough statistics")
            print("  2. Filter by specific streets")
            
            sub_choice = input("\nSelect option (1-2): ").strip()
            
            if sub_choice == '1':
                stats = compute_stats(borough_data)
                print(f"\n{selected_borough} Statistics:")
                print(f"  Total Accidents: {stats.get('total_accidents', 0):,}")
                print(f"  Persons Injured: {stats.get('number_of_persons_injured', 0):,}")
                print(f"  Persons Killed: {stats.get('number_of_persons_killed', 0):,}")
                
                if stats.get('top_streets'):
                    print(f"\n  Top Streets:")
                    for street, count in list(stats['top_streets'].items())[:5]:
                        print(f"    - {street}: {count}")
            
            elif sub_choice == '2':
                streets = borough_data['on_street_name'].value_counts().to_dict()
                streets_list = sorted(streets.keys(), key=lambda x: streets[x], reverse=True)[:10]
                
                print(f"\nTop Streets in {selected_borough}:")
                for i, street in enumerate(streets_list, 1):
                    if pd.notna(street) and street:
                        print(f"  {i}. {street} ({streets[street]})")
                
                street_choice = input("\nEnter street name to filter: ").strip()
                street_data = borough_data[borough_data['on_street_name'].str.contains(street_choice, case=False, na=False)]
                
                stats = compute_stats(street_data)
                print(f"\nResults for '{street_choice}':")
                print(f"  Accidents: {len(street_data)}")
                print(f"  Persons Injured: {stats.get('number_of_persons_injured', 0)}")
                print(f"  Persons Killed: {stats.get('number_of_persons_killed', 0)}")
        else:
            print("❌ Invalid selection")
    except ValueError:
        print("❌ Invalid input")


def plot_monthly_counts_menu(data):
    """Generate monthly counts plot."""
    print("\n" + "="*60)
    print("PLOTTING MONTHLY COUNTS")
    print("="*60)
    
    try:
        Path("static/plots").mkdir(parents=True, exist_ok=True)
        out = _viz.plot_monthly_counts(data, out_png="static/plots/monthly_counts.png")
        print(f"✓ Monthly chart saved to {out}")
    except Exception as e:
        print(f"❌ Error: {e}")


def plot_top_streets_menu(data):
    """Generate top streets by borough plot."""
    try:
        import pandas as pd
        has_pandas = True
    except:
        has_pandas = False
    
    print("\n" + "="*60)
    print("PLOTTING TOP STREETS BY BOROUGH")
    print("="*60)
    
    if not has_pandas or not hasattr(data, 'shape'):
        print("⚠ Pandas required for this feature")
        return
    
    if 'borough' not in data.columns:
        print("❌ Borough column not found")
        return
    
    boroughs = sorted([b for b in data['borough'].unique() if pd.notna(b) and b])
    
    print("\nAvailable Boroughs:")
    for i, borough in enumerate(boroughs, 1):
        print(f"  {i}. {borough}")
    
    try:
        choice = int(input("\nSelect borough (number): ")) - 1
        if 0 <= choice < len(boroughs):
            selected_borough = boroughs[choice]
            borough_data = data[data['borough'] == selected_borough]
            
            Path("static/plots").mkdir(parents=True, exist_ok=True)
            out = _viz.plot_top_streets(borough_data, out_png=f"static/plots/top_streets_{selected_borough}.png")
            print(f"✓ Chart saved to {out}")
        else:
            print("❌ Invalid selection")
    except ValueError:
        print("❌ Invalid input")
    except Exception as e:
        print(f"❌ Error: {e}")


def export_data(data):
    """Export data to CSV or detailed report."""
    print("\n" + "="*60)
    print("EXPORT OPTIONS")
    print("="*60)
    print("1. Export filtered data to CSV")
    print("2. Export detailed report")
    
    choice = input("\nSelect option (1-2): ").strip()
    
    Path("data").mkdir(parents=True, exist_ok=True)
    
    if choice == '1':
        try:
            output_path = "data/filtered_export.csv"
            cd.write_csv_header(output_path)
            
            if hasattr(data, "to_dict"):
                rows = data.to_dict(orient="records")
            else:
                rows = data
            
            cd.append_rows_to_csv(output_path, rows)
            print(f"✓ Data exported to {output_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    elif choice == '2':
        try:
            stats = compute_stats(data)
            output_path = "data/detailed_report.csv"
            export_report_csv(stats, output_path)
            print(f"✓ Detailed report exported to {output_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    else:
        print("❌ Invalid option")


def generate_heatmap(data):
    """Generate folium heatmap."""
    print("\n" + "="*60)
    print("GENERATING HEATMAP")
    print("="*60)
    
    try:
        Path("static/maps").mkdir(parents=True, exist_ok=True)
        out = _viz.generate_folium_heatmap(data, out_html="static/maps/heatmap.html")
        print(f"✓ Heatmap saved to {out}")
        print("  Open in a web browser to view the interactive map")
    except Exception as e:
        print(f"❌ Error: {e}")


def show_menu():
    """Display main menu."""
    print("\n" + "="*60)
    print("NYC CRASHES ANALYSIS MENU")
    print("="*60)
    print("1) Show brief statistics")
    print("2) Show detailed statistics")
    print("3) Search accidents by vehicle type")
    print("4) Filter by borough")
    print("5) Plot monthly counts")
    print("6) Plot top streets by borough")
    print("7) Export data")
    print("8) Generate folium heatmap")
    print("q) Quit")
    print("="*60)


def main():
    """Main interactive CLI loop."""
    print("\n" + "="*60)
    print("🚗 NYC CRASHES ANALYSIS TOOL")
    print("="*60)
    
    # Get date range from user
    start_date, end_date = get_date_range()
    
    # Load data with fallback
    data, metadata = load_data_with_fallback(start_date, end_date)
    
    # Show data summary
    if hasattr(data, 'shape'):
        row_count = data.shape[0]
    else:
        row_count = len(data)
    
    print(f"\n✓ Loaded {row_count:,} accident records")
    if metadata.get("source") == "cache":
        print("⚠ Using cached data - no internet connection available")
    
    # Main menu loop
    while True:
        show_menu()
        choice = input("\nSelect option: ").strip().lower()
        
        if choice == '1':
            show_brief_stats(data)
        elif choice == '2':
            show_detailed_stats(data)
        elif choice == '3':
            search_by_vehicle_type(data)
        elif choice == '4':
            filter_by_borough(data)
        elif choice == '5':
            plot_monthly_counts_menu(data)
        elif choice == '6':
            plot_top_streets_menu(data)
        elif choice == '7':
            export_data(data)
        elif choice == '8':
            generate_heatmap(data)
        elif choice == 'q':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid option. Please try again.")


if __name__ == '__main__':
    main()