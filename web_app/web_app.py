# Authors: Alexander John Balagso, Marc Aaron Africano

"""Flask web application for NYC crashes data analysis.

Web-based interface with tables and visualizations instead of CLI prompts.
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from datetime import datetime, date
from pathlib import Path
import sys
import json
import os
import time

# Use a non-interactive matplotlib backend for server environments
import matplotlib
matplotlib.use("Agg")

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set working directory to project root to ensure data folder is accessible
os.chdir(project_root)

from accidents.datapull import (
    read_accidents_csv, 
    pull_and_cache_nyc_crashes, 
    filter_by_date_range, 
    compute_stats, 
    export_report_csv
)
from accidents import viz as _viz
from accidents import crashes_dictionaries as cd

# Configure Flask to use static folder from project root
app = Flask(__name__, static_folder='../static', static_url_path='/static')
app.config['SECRET_KEY'] = 'nyc-crashes-analysis-2026'

# Global variable to hold loaded data
loaded_data = None
data_metadata = {}


def load_initial_data():
    """Load data on startup."""
    global loaded_data, data_metadata
    try:
        # Verify data folder exists
        data_folder = project_root / "data"
        print(f"📁 Data folder: {data_folder}")
        print(f"📁 Data folder exists: {data_folder.exists()}")
        
        cache_path, metadata = pull_and_cache_nyc_crashes(force_update=False)
        print(f"📄 Cache path: {cache_path}")
        
        loaded_data = read_accidents_csv(str(cache_path), use_pandas=True)
        data_metadata = metadata
        print(f"✓ Loaded {len(loaded_data)} records from data folder")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        loaded_data = None


@app.route('/')
def index():
    """Home page with data overview and menu options."""
    if loaded_data is None:
        return render_template('error.html', message="Failed to load data. Please check your connection.")
    
    record_count = len(loaded_data) if hasattr(loaded_data, '__len__') else loaded_data.shape[0]
    return render_template('index.html', 
                         record_count=record_count,
                         data_source=data_metadata.get('source', 'unknown'))


@app.route('/filter', methods=['GET', 'POST'])
def filter_data():
    """Filter data by date range."""
    global loaded_data
    
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                
                # Reload original data
                cache_path, metadata = pull_and_cache_nyc_crashes(force_update=False)
                loaded_data = read_accidents_csv(str(cache_path), use_pandas=True)
                
                # Filter
                loaded_data = filter_by_date_range(loaded_data, start, end)
                
                return redirect(url_for('index'))
            except Exception as e:
                return render_template('error.html', message=f"Filter error: {e}")
    
    return render_template('filter.html')


@app.route('/statistics/brief')
def brief_statistics():
    """Show brief statistics in a table."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    stats = compute_stats(loaded_data)
    
    # Convert dict items to lists for Jinja2 template
    if stats.get('top_streets'):
        stats['top_streets_list'] = list(stats['top_streets'].items())
    
    return render_template('statistics_brief.html', stats=stats)


@app.route('/statistics/detailed')
def detailed_statistics():
    """Show detailed statistics with multiple tables and visualizations."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    stats = compute_stats(loaded_data)
    
    # Convert dict items to lists for Jinja2 template
    if stats.get('top_streets'):
        stats['top_streets_list'] = list(stats['top_streets'].items())
    if stats.get('top_vehicles'):
        stats['top_vehicles_list'] = list(stats['top_vehicles'].items())
    if stats.get('top_months'):
        stats['top_months_list'] = list(stats['top_months'].items())
    
    # Generate borough visualization
    try:
        static_plots = Path(app.static_folder) / "plots"
        static_plots.mkdir(parents=True, exist_ok=True)
        output_path = static_plots / "boroughs.png"
        _viz.plot_boroughs(loaded_data, out_png=str(output_path))
        borough_chart_url = url_for('static', filename='plots/boroughs.png')
        stats['borough_chart_url'] = borough_chart_url
    except Exception as e:
        print(f"Warning: Could not generate borough chart: {e}")
        stats['borough_chart_url'] = None
    
    return render_template('statistics_detailed.html', stats=stats)


@app.route('/search/vehicle')
def search_vehicle():
    """Search by vehicle type."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd
        
        # Get all vehicle types
        vehicle_cols = [col for col in loaded_data.columns if 'vehicle_type' in col.lower()]
        all_vehicles = {}
        
        for col in vehicle_cols:
            vehicles = loaded_data[col].value_counts().to_dict()
            for v, count in vehicles.items():
                if v and str(v).lower() != 'nan':
                    all_vehicles[v] = all_vehicles.get(v, 0) + count
        
        all_vehicles = dict(sorted(all_vehicles.items(), key=lambda x: x[1], reverse=True)[:20])
        
        return render_template('search_vehicle.html', vehicles=all_vehicles)
    except Exception as e:
        return render_template('error.html', message=f"Error: {e}")


@app.route('/search/vehicle/<vehicle_type>')
def vehicle_results(vehicle_type):
    """Show results for specific vehicle type."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd
        
        vehicle_cols = [col for col in loaded_data.columns if 'vehicle_type' in col.lower()]
        mask = pd.Series([False] * len(loaded_data))
        
        for col in vehicle_cols:
            mask = mask | loaded_data[col].str.upper().str.contains(vehicle_type.upper(), na=False)
        
        filtered = loaded_data[mask]
        stats = compute_stats(filtered)
        
        # Get sample records
        sample_records = filtered.head(50).to_dict('records') if hasattr(filtered, 'to_dict') else []
        
        return render_template('vehicle_results.html', 
                             vehicle_type=vehicle_type,
                             stats=stats,
                             record_count=len(filtered),
                             sample_records=sample_records)
    except Exception as e:
        return render_template('error.html', message=f"Error: {e}")


@app.route('/borough')
def borough_list():
    """List all boroughs."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd
        
        if 'borough' not in loaded_data.columns:
            return render_template('error.html', message="Borough column not found")
        
        boroughs = loaded_data['borough'].value_counts().to_dict()
        borough_list = sorted([(b, count) for b, count in boroughs.items() if pd.notna(b) and b], 
                            key=lambda x: x[1], reverse=True)
        
        return render_template('borough_list.html', boroughs=borough_list)
    except Exception as e:
        return render_template('error.html', message=f"Error: {e}")


@app.route('/borough/<borough_name>')
def borough_detail(borough_name):
    """Show borough statistics and top streets."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd
        
        borough_data = loaded_data[loaded_data['borough'] == borough_name]
        stats = compute_stats(borough_data)
        
        # Get top streets
        streets = borough_data['on_street_name'].value_counts().head(10).to_dict()
        street_list = [(street, count) for street, count in streets.items() if pd.notna(street) and street]
        
        return render_template('borough_detail.html', 
                             borough=borough_name,
                             stats=stats,
                             streets=street_list)
    except Exception as e:
        return render_template('error.html', message=f"Error: {e}")


@app.route('/visualizations')
def visualizations():
    """Visualization options page."""
    return render_template('visualizations.html')


@app.route('/visualizations/monthly')
def plot_monthly():
    """Generate and display monthly counts plot."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        static_plots = Path(app.static_folder) / "plots"
        static_plots.mkdir(parents=True, exist_ok=True)
        output_path = static_plots / "monthly_counts.png"
        _viz.plot_monthly_counts(loaded_data, out_png=str(output_path))
        image_url = url_for('static', filename='plots/monthly_counts.png')
        return render_template('plot_display.html', 
                             title="Monthly Accident Counts",
                             image_path=image_url)
    except Exception as e:
        return render_template('error.html', message=f"Plot error: {e}")


@app.route('/visualizations/streets/<borough>')
def plot_streets(borough):
    """Generate and display top streets plot for a borough."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd
        
        borough_data = loaded_data[loaded_data['borough'] == borough]
        static_plots = Path(app.static_folder) / "plots"
        static_plots.mkdir(parents=True, exist_ok=True)
        output_path = static_plots / f"top_streets_{borough}.png"
        _viz.plot_top_streets(borough_data, out_png=str(output_path))
        image_url = url_for('static', filename=f'plots/top_streets_{borough}.png')
        
        return render_template('plot_display.html',
                             title=f"Top Streets in {borough}",
                             image_path=image_url)
    except Exception as e:
        return render_template('error.html', message=f"Plot error: {e}")


@app.route('/heatmap')
def heatmap():
    """Generate and display heatmap."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        import pandas as pd

        df = loaded_data.copy()

        # Options for filters
        vehicle_cols = [
            "vehicle_type_code1",
            "vehicle_type_code2",
            "vehicle_type_code3",
            "vehicle_type_code4",
            "vehicle_type_code5",
        ]
        vehicle_options = []
        try:
            vehicle_series = [df[c] for c in vehicle_cols if c in df.columns]
            if vehicle_series:
                vehicle_options = (
                    pd.concat(vehicle_series)
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .head(50)
                    .index
                    .tolist()
                )
        except Exception:
            vehicle_options = []

        borough_options = []
        if "borough" in df.columns:
            borough_options = (
                df["borough"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.lower()
                .replace("", pd.NA)
                .dropna()
                .unique()
                .tolist()
            )
            borough_options.sort()

        # Apply filters
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        vehicle_type = request.args.get("vehicle_type", "").strip().lower()
        borough = request.args.get("borough", "").strip().lower()

        if "crash_datetime" in df.columns:
            df["crash_datetime"] = pd.to_datetime(df["crash_datetime"], errors="coerce")

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                df = df[df["crash_datetime"].dt.date >= start_date]
            except Exception:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                df = df[df["crash_datetime"].dt.date <= end_date]
            except Exception:
                pass

        if vehicle_type:
            mask = False
            for c in vehicle_cols:
                if c in df.columns:
                    mask = mask | df[c].fillna("").astype(str).str.lower().str.contains(vehicle_type)
            df = df[mask]

        if borough and "borough" in df.columns:
            df = df[df["borough"].fillna("").astype(str).str.lower() == borough]

        static_maps = Path(app.static_folder) / "maps"
        static_maps.mkdir(parents=True, exist_ok=True)
        output_path = static_maps / "heatmap.html"
        _viz.generate_folium_heatmap(df, out_html=str(output_path))

        heatmap_url = url_for('static', filename='maps/heatmap.html', v=int(time.time()))

        return render_template(
            'heatmap_display.html',
            heatmap_url=heatmap_url,
            start_date=start_date_str or "",
            end_date=end_date_str or "",
            vehicle_type=vehicle_type,
            borough=borough,
            vehicle_options=vehicle_options,
            borough_options=borough_options,
        )
    except Exception as e:
        return render_template('error.html', message=f"Heatmap error: {e}")


@app.route('/export')
def export():
    """Export options page."""
    return render_template('export.html')


@app.route('/export/csv')
def export_csv():
    """Export filtered data to CSV."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_path = data_dir / "web_export.csv"
        
        cd.write_csv_header(output_path)
        rows = loaded_data.to_dict(orient="records") if hasattr(loaded_data, "to_dict") else loaded_data
        cd.append_rows_to_csv(output_path, rows)
        
        return send_file(str(output_path), as_attachment=True, download_name="nyc_crashes_export.csv")
    except Exception as e:
        return render_template('error.html', message=f"Export error: {e}")


@app.route('/export/report')
def export_report():
    """Export detailed report."""
    if loaded_data is None:
        return render_template('error.html', message="No data loaded")
    
    try:
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        stats = compute_stats(loaded_data)
        output_path = data_dir / "web_report.csv"
        export_report_csv(stats, output_path)
        
        return send_file(str(output_path), as_attachment=True, download_name="nyc_crashes_report.csv")
    except Exception as e:
        return render_template('error.html', message=f"Export error: {e}")


if __name__ == '__main__':
    print("Loading initial data...")
    load_initial_data()
    print("Starting web server...")
    print("Open your browser to: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
