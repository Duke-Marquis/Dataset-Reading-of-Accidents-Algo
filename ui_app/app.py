"""Tkinter desktop application for NYC crashes analysis.

Mirrors the Flask web_app functionality using a desktop-friendly UI.
"""
from __future__ import annotations

import os
import sys
import threading
import traceback
import webbrowser
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("Agg")  # headless-safe backend

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from accidents.datapull import (
    pull_and_cache_nyc_crashes,
    read_accidents_csv,
    filter_by_date_range,
    compute_stats,
    export_report_csv,
)
from accidents import viz as _viz
from accidents import crashes_dictionaries as cd


def _safe_browser_open(path: Path) -> None:
    try:
        webbrowser.open(path.as_uri())
    except Exception:
        messagebox.showinfo("Open File", f"Saved to: {path}")


class CrashApp:
    def __init__(self) -> None:
        os.chdir(project_root)
        self.root = tk.Tk()
        self.root.title("NYC Crashes Analysis (Desktop)")
        self.root.geometry("1200x780")
        
        # Match web_app color scheme
        bg_color = "#f7f9fc"
        panel_color = "#ffffff"
        text_color = "#0f172a"
        muted_color = "#475569"
        accent_color = "#2563eb"
        border_color = "#e2e8f0"
        
        # Configure root background
        self.root.configure(bg=bg_color)
        
        # Configure custom styles matching web_app
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure button style
        style.configure("Big.TButton", 
                       font=("Inter", 12, "bold"),
                       background=accent_color,
                       foreground="white",
                       borderwidth=0,
                       focuscolor="none",
                       padding=(20, 15))
        style.map("Big.TButton",
                 background=[("active", "#1d4ed8"), ("pressed", "#1e40af")])
        
        # Configure frame styles
        style.configure("TFrame", background=bg_color)
        style.configure("Card.TFrame", background=panel_color, relief="flat")
        
        # Configure label styles
        style.configure("TLabel", background=bg_color, foreground=text_color, font=("Inter", 10))
        style.configure("Title.TLabel", background=bg_color, foreground=text_color, font=("Inter", 18, "bold"))
        style.configure("Heading.TLabel", background=panel_color, foreground=text_color, font=("Inter", 12, "bold"))
        style.configure("Muted.TLabel", background=panel_color, foreground=muted_color, font=("Inter", 9))
        
        # Configure notebook (tabs)
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", 
                       font=("Inter", 10, "bold"),
                       padding=(16, 10),
                       background=panel_color,
                       foreground=text_color)
        style.map("TNotebook.Tab",
                 background=[("selected", accent_color)],
                 foreground=[("selected", "white")])
        
        # Configure entry fields
        style.configure("TEntry", 
                       fieldbackground=panel_color,
                       foreground=text_color,
                       borderwidth=1,
                       relief="solid")
        style.configure("TCombobox",
                       fieldbackground=panel_color,
                       foreground=text_color,
                       borderwidth=1,
                       relief="solid")

        self.status_var = tk.StringVar(value="Loading data…")
        self.record_count_var = tk.StringVar(value="Records: 0")
        self.filter_var = tk.StringVar(value="Filter: none")

        self.data = None
        self.filtered = None
        self.metadata = {}
        
        self.colors = {
            "bg": bg_color,
            "panel": panel_color,
            "text": text_color,
            "muted": muted_color,
            "accent": accent_color,
            "border": border_color
        }

        self._build_layout()
        self._load_data_async()

    def _build_layout(self) -> None:
        # Status bar with styling
        status_frame = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        status_frame.pack(fill="x", padx=15, pady=(10, 5))
        ttk.Label(status_frame, textvariable=self.status_var, style="TLabel").pack(side="left")
        ttk.Label(status_frame, textvariable=self.record_count_var, style="TLabel").pack(side="right")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.home_tab = ttk.Frame(notebook)
        self.filter_tab = ttk.Frame(notebook)
        self.stats_tab = ttk.Frame(notebook)
        self.visual_tab = ttk.Frame(notebook)
        self.vehicle_tab = ttk.Frame(notebook)
        self.heatmap_tab = ttk.Frame(notebook)
        self.export_tab = ttk.Frame(notebook)

        notebook.add(self.home_tab, text="Home")
        notebook.add(self.filter_tab, text="Filter")
        notebook.add(self.stats_tab, text="Statistics")
        notebook.add(self.visual_tab, text="Visualizations")
        notebook.add(self.vehicle_tab, text="Vehicles")
        notebook.add(self.heatmap_tab, text="Heatmap")
        notebook.add(self.export_tab, text="Export")

        self._build_home_tab()
        self._build_filter_tab()
        self._build_stats_tab()
        self._build_visual_tab()
        self._build_vehicle_tab()
        self._build_heatmap_tab()
        self._build_export_tab()

    def _build_home_tab(self) -> None:
        frame = self.home_tab
        ttk.Label(frame, text="NYC Crashes Analysis", style="Title.TLabel").pack(pady=15)
        
        # Styled text widget
        self.home_summary = tk.Text(frame, height=25, wrap="word", state="disabled",
                                   bg=self.colors["panel"], fg=self.colors["text"],
                                   font=("Inter", 10), relief="flat", borderwidth=0)
        self.home_summary.pack(fill="both", expand=True, padx=15, pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Reload Data", width=20, command=lambda: self._load_data_async(force=True), style="Big.TButton").pack(side="left", padx=5)

    def _build_filter_tab(self) -> None:
        frame = self.filter_tab
        
        card = ttk.Frame(frame, style="Card.TFrame", padding=20)
        card.pack(fill="x", padx=15, pady=15)
        
        ttk.Label(card, text="Filter by Date Range (YYYY-MM-DD)", style="Heading.TLabel").pack(anchor="w", pady=(0, 15))
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w")

        ttk.Label(form, text="Start date:", style="Heading.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        self.start_entry = ttk.Entry(form, width=15, font=("Inter", 10))
        self.start_entry.grid(row=0, column=1, sticky="w", padx=5, pady=8)

        ttk.Label(form, text="End date:", style="Heading.TLabel").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        self.end_entry = ttk.Entry(form, width=15, font=("Inter", 10))
        self.end_entry.grid(row=1, column=1, sticky="w", padx=5, pady=8)

        ttk.Button(form, text="Apply Filter", width=25, command=self._apply_filter, style="Big.TButton").grid(row=2, column=0, columnspan=2, pady=15)
        
        status_label = ttk.Label(card, textvariable=self.filter_var, style="Muted.TLabel")
        status_label.pack(anchor="w", pady=(10, 0))

    def _build_stats_tab(self) -> None:
        frame = self.stats_tab
        ttk.Label(frame, text="Statistics", style="Title.TLabel").pack(anchor="w", padx=15, pady=10)
        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="Brief", width=18, command=self._show_brief_stats, style="Big.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Detailed", width=18, command=self._show_detailed_stats, style="Big.TButton").pack(side="left", padx=4)

        self.stats_text = tk.Text(frame, wrap="word",
                                 bg=self.colors["panel"], fg=self.colors["text"],
                                 font=("Inter", 10), relief="flat", borderwidth=0)
        self.stats_text.pack(fill="both", expand=True, padx=15, pady=10)

    def _build_visual_tab(self) -> None:
        frame = self.visual_tab
        ttk.Label(frame, text="Visualizations", style="Title.TLabel").pack(anchor="w", padx=15, pady=10)
        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="Monthly Counts (PNG)", width=25, command=self._plot_monthly, style="Big.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Boroughs (PNG)", width=25, command=self._plot_boroughs, style="Big.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Top Streets (by borough)", width=25, command=self._plot_top_streets_prompt, style="Big.TButton").pack(side="left", padx=4)

    def _build_vehicle_tab(self) -> None:
        frame = self.vehicle_tab
        
        card = ttk.Frame(frame, style="Card.TFrame", padding=20)
        card.pack(fill="x", padx=15, pady=15)
        
        ttk.Label(card, text="Search by Vehicle Type", style="Heading.TLabel").pack(anchor="w", pady=(0, 15))
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w")
        ttk.Label(form, text="Vehicle type contains:", style="Heading.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.vehicle_entry = ttk.Entry(form, width=24, font=("Inter", 10))
        self.vehicle_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Button(form, text="Search", width=15, command=self._search_vehicle, style="Big.TButton").grid(row=0, column=2, padx=5, pady=2)

        self.vehicle_results = tk.Text(frame, wrap="word", height=18,
                                      bg=self.colors["panel"], fg=self.colors["text"],
                                      font=("Inter", 10), relief="flat", borderwidth=0)
        self.vehicle_results.pack(fill="both", expand=True, padx=15, pady=10)

    def _build_heatmap_tab(self) -> None:
        frame = self.heatmap_tab
        
        card = ttk.Frame(frame, style="Card.TFrame", padding=20)
        card.pack(fill="x", padx=15, pady=15)
        
        ttk.Label(card, text="Interactive Heatmap", style="Heading.TLabel").pack(anchor="w", pady=(0, 15))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w")

        ttk.Label(form, text="Start date (YYYY-MM-DD)", style="Heading.TLabel").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        self.hm_start = ttk.Entry(form, width=15, font=("Inter", 10))
        self.hm_start.grid(row=0, column=1, sticky="w", padx=4, pady=6)

        ttk.Label(form, text="End date (YYYY-MM-DD)", style="Heading.TLabel").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.hm_end = ttk.Entry(form, width=15, font=("Inter", 10))
        self.hm_end.grid(row=1, column=1, sticky="w", padx=4, pady=6)

        ttk.Label(form, text="Vehicle type contains", style="Heading.TLabel").grid(row=2, column=0, sticky="w", padx=4, pady=6)
        self.hm_vehicle = ttk.Entry(form, width=18, font=("Inter", 10))
        self.hm_vehicle.grid(row=2, column=1, sticky="w", padx=4, pady=6)

        ttk.Label(form, text="Borough", style="Heading.TLabel").grid(row=3, column=0, sticky="w", padx=4, pady=6)
        self.hm_borough = ttk.Combobox(form, values=[], width=18, state="readonly", font=("Inter", 10))
        self.hm_borough.grid(row=3, column=1, sticky="w", padx=4, pady=6)

        ttk.Button(form, text="Generate Heatmap", width=25, command=self._generate_heatmap, style="Big.TButton").grid(row=4, column=0, columnspan=2, pady=15)

        ttk.Label(card, text="The heatmap opens in your browser after generation.", style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

    def _build_export_tab(self) -> None:
        frame = self.export_tab
        ttk.Label(frame, text="Export", style="Title.TLabel").pack(anchor="w", padx=15, pady=10)
        btns = ttk.Frame(frame)
        btns.pack(anchor="w", padx=15, pady=10)
        ttk.Button(btns, text="Export filtered data (CSV)", width=28, command=self._export_csv, style="Big.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Export report (CSV)", width=28, command=self._export_report, style="Big.TButton").pack(side="left", padx=4)

    # --- Data loading and filtering ---
    def _load_data_async(self, force: bool = False) -> None:
        threading.Thread(target=self._load_data, args=(force,), daemon=True).start()

    def _load_data(self, force: bool) -> None:
        self._set_status("Loading data…")
        try:
            cache_path, metadata = pull_and_cache_nyc_crashes(force_update=force)
            df = read_accidents_csv(str(cache_path), use_pandas=True)
            self.data = df
            self.filtered = df
            self.metadata = metadata or {}
            self._set_record_count(len(df))
            self._set_status("Data loaded")
            self._update_home_summary()
            self._update_borough_options()
        except Exception as exc:
            self._set_status(f"Load error: {exc}")
            traceback.print_exc()

    def _apply_filter(self) -> None:
        if self.data is None:
            messagebox.showwarning("No data", "Load data first")
            return
        start = self._parse_date(self.start_entry.get())
        end = self._parse_date(self.end_entry.get())
        if start and end and start > end:
            messagebox.showwarning("Invalid range", "Start date must be before end date")
            return
        try:
            self.filtered = filter_by_date_range(self.data, start, end)
            self._set_record_count(len(self.filtered))
            self.filter_var.set(f"Filter: {start or 'min'} to {end or 'max'}")
            self._set_status("Filter applied")
            self._update_home_summary()
        except Exception as exc:
            messagebox.showerror("Filter error", str(exc))

    # --- Stats ---
    def _show_brief_stats(self) -> None:
        self._show_stats(detailed=False)

    def _show_detailed_stats(self) -> None:
        self._show_stats(detailed=True)

    def _show_stats(self, detailed: bool) -> None:
        if self.filtered is None:
            messagebox.showwarning("No data", "Load data first")
            return
        try:
            stats = compute_stats(self.filtered)
            lines = []
            lines.append(f"Total records: {len(self.filtered)}")
            if stats.get("crashes_per_borough"):
                lines.append("\nCrashes per borough:")
                for b, v in stats["crashes_per_borough"].items():
                    lines.append(f"  - {b}: {v}")
            # For brief mode, show a concise top 5; for detailed, show everything available
            top_limit = None if detailed else 5
            for key in ("top_streets", "top_vehicles", "top_months"):
                if stats.get(key):
                    lines.append(f"\n{key.replace('_', ' ').title()}:")
                    items = list(stats[key].items())
                    if top_limit:
                        items = items[:top_limit]
                    for name, count in items:
                        lines.append(f"  - {str(name):<36} {count:>10}")
            text = "\n".join(lines)
            self._set_text(self.stats_text, text)
            self._set_text(self.home_summary, text[:2000])
            self._set_status("Statistics updated")
        except Exception as exc:
            messagebox.showerror("Stats error", str(exc))

    # --- Visualizations ---
    def _plot_monthly(self) -> None:
        self._ensure_data()
        self._run_plot(lambda: _viz.plot_monthly_counts(self.filtered, out_png="static/plots/monthly_counts.png"), Path("static/plots/monthly_counts.png"))

    def _plot_boroughs(self) -> None:
        self._ensure_data()
        self._run_plot(lambda: _viz.plot_boroughs(self.filtered, out_png="static/plots/boroughs.png"), Path("static/plots/boroughs.png"))

    def _plot_top_streets_prompt(self) -> None:
        if self.filtered is None:
            messagebox.showwarning("No data", "Load data first")
            return
        import pandas as pd
        if "borough" not in self.filtered.columns:
            messagebox.showwarning("Missing column", "No borough column available")
            return
        boroughs = (
            self.filtered["borough"].dropna().astype(str).str.strip().str.lower().replace("", pd.NA).dropna().unique().tolist()
        )
        boroughs.sort()
        if not boroughs:
            messagebox.showinfo("No boroughs", "No borough values to plot")
            return
        popup = tk.Toplevel(self.root)
        popup.title("Select borough")
        ttk.Label(popup, text="Choose borough:").pack(padx=10, pady=5)
        combo = ttk.Combobox(popup, values=boroughs, state="readonly")
        combo.pack(padx=10, pady=5)
        combo.current(0)
        ttk.Button(popup, text="Plot", width=20, command=lambda: self._plot_top_streets(combo.get(), popup), style="Big.TButton").pack(pady=8)

    def _plot_top_streets(self, borough: str, popup: Optional[tk.Toplevel] = None) -> None:
        self._ensure_data()
        path = Path(f"static/plots/top_streets_{borough}.png")
        self._run_plot(lambda: _viz.plot_top_streets(self.filtered[self.filtered["borough"].str.lower() == borough], out_png=str(path)), path)
        if popup:
            popup.destroy()

    # --- Vehicles ---
    def _search_vehicle(self) -> None:
        if self.filtered is None:
            messagebox.showwarning("No data", "Load data first")
            return
        import pandas as pd
        query = self.vehicle_entry.get().strip()
        if not query:
            messagebox.showinfo("Enter value", "Please enter a vehicle type substring")
            return
        vehicle_cols = [c for c in self.filtered.columns if "vehicle_type" in c.lower()]
        mask = False
        for col in vehicle_cols:
            mask = mask | self.filtered[col].fillna("").astype(str).str.upper().str.contains(query.upper())
        results = self.filtered[mask]
        stats = compute_stats(results)
        lines = [f"Results: {len(results)}"]
        if stats.get("top_vehicles"):
            lines.append("Top vehicles:")
            for name, count in stats["top_vehicles"].items():
                lines.append(f"  - {name}: {count}")
        self._set_text(self.vehicle_results, "\n".join(lines))
        self._set_status("Vehicle search complete")

    # --- Heatmap ---
    def _generate_heatmap(self) -> None:
        self._ensure_data()
        start = self._parse_date(self.hm_start.get())
        end = self._parse_date(self.hm_end.get())
        vehicle_sub = self.hm_vehicle.get().strip().lower()
        borough = self.hm_borough.get().strip().lower()

        def build_and_open() -> None:
            import pandas as pd
            df = self.filtered.copy()
            if start:
                df = df[df["crash_datetime"].dt.date >= start] if "crash_datetime" in df else df
            if end:
                df = df[df["crash_datetime"].dt.date <= end] if "crash_datetime" in df else df
            if vehicle_sub:
                vehicle_cols = [
                    "vehicle_type_code1",
                    "vehicle_type_code2",
                    "vehicle_type_code3",
                    "vehicle_type_code4",
                    "vehicle_type_code5",
                ]
                mask = False
                for c in vehicle_cols:
                    if c in df.columns:
                        mask = mask | df[c].fillna("").astype(str).str.lower().str.contains(vehicle_sub)
                df = df[mask]
            if borough and "borough" in df.columns:
                df = df[df["borough"].fillna("").astype(str).str.lower() == borough]

            maps_dir = project_root / "static" / "maps"
            maps_dir.mkdir(parents=True, exist_ok=True)
            out = maps_dir / "heatmap.html"
            _viz.generate_folium_heatmap(df, out_html=str(out))
            _safe_browser_open(out)
            self._set_status("Heatmap generated")

        threading.Thread(target=build_and_open, daemon=True).start()

    # --- Export ---
    def _export_csv(self) -> None:
        self._ensure_data()
        try:
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            out = data_dir / "desktop_export.csv"
            cd.write_csv_header(out)
            rows = self.filtered.to_dict(orient="records") if hasattr(self.filtered, "to_dict") else self.filtered
            cd.append_rows_to_csv(out, rows)
            self._set_status(f"Exported to {out}")
            messagebox.showinfo("Export", f"Saved: {out}")
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    def _export_report(self) -> None:
        self._ensure_data()
        try:
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            stats = compute_stats(self.filtered)
            out = data_dir / "desktop_report.csv"
            export_report_csv(stats, out)
            self._set_status(f"Report saved to {out}")
            messagebox.showinfo("Export", f"Saved: {out}")
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    # --- Helpers ---
    def _run_plot(self, fn, path: Path) -> None:
        self._ensure_data()
        def task() -> None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                fn()
                self._set_status(f"Saved: {path}")
                self._show_image_popup(path)
            except Exception as exc:
                messagebox.showerror("Plot error", str(exc))
        threading.Thread(target=task, daemon=True).start()

    def _update_home_summary(self) -> None:
        if self.data is None:
            return
        summary = [f"Records: {len(self.filtered) if self.filtered is not None else 0}"]
        if self.metadata:
            summary.append(f"Source: {self.metadata.get('source', 'unknown')}")
            if self.metadata.get("cached_at"):
                summary.append(f"Cached at: {self.metadata['cached_at']}")
        self._set_text(self.home_summary, "\n".join(summary))

    def _update_borough_options(self) -> None:
        if self.data is None:
            return
        try:
            import pandas as pd
            if "borough" not in self.data.columns:
                return
            boroughs = (
                self.data["borough"].dropna().astype(str).str.strip().str.lower().replace("", pd.NA).dropna().unique().tolist()
            )
            boroughs.sort()
            self.hm_borough["values"] = boroughs
        except Exception:
            pass

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state="normal")

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _set_record_count(self, count: int) -> None:
        self.record_count_var.set(f"Records: {count}")

    @staticmethod
    def _parse_date(val: str) -> Optional[date]:
        val = val.strip()
        if not val:
            return None
        return datetime.strptime(val, "%Y-%m-%d").date()

    def _ensure_data(self) -> None:
        if self.filtered is None:
            raise RuntimeError("Data not loaded yet")

    def run(self) -> None:
        self.root.mainloop()

    def _show_image_popup(self, path: Path) -> None:
        """Show generated PNG in a popup; fall back to opening externally."""
        try:
            img = tk.PhotoImage(file=str(path))
        except Exception:
            _safe_browser_open(path)
            return

        win = tk.Toplevel(self.root)
        win.title(path.name)
        win.configure(bg=self.colors["panel"])
        
        frame = ttk.Frame(win, style="Card.TFrame", padding=20)
        frame.pack(fill="both", expand=True)

        label = ttk.Label(frame, image=img, background=self.colors["panel"])
        label.image = img 
        label.pack()

        meta = ttk.Label(frame, text=str(path), style="Muted.TLabel")
        meta.pack(pady=8)

        ttk.Button(frame, text="Open externally", width=20, command=lambda: _safe_browser_open(path), style="Big.TButton").pack(pady=10)


def main() -> None:
    app = CrashApp()
    app.run()


if __name__ == "__main__":
    main()
