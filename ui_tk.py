"""Tkinter GUI for the accidents pipeline.

This GUI intentionally keeps optional dependencies optional:
- If Pillow is installed, PNGs are displayed inside the window.
- Otherwise generated images are opened in the default image viewer.
- Folium heatmap opens in the browser.

Run:
    python ui_tk.py
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from typing import Any
import threading
import importlib.util
import subprocess
import sys

import crashes_dictionaries as cd
from Datapull import load_and_preview, filter_by_date_range, compute_stats, export_report_csv
import viz

# Optional image support
try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class AccidentsGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        master.title("Accidents Explorer")
        self.data = None
        self.filtered = None

        frm = ttk.Frame(master, padding=10)
        frm.grid(sticky="nsew")

        # File input
        ttk.Label(frm, text="CSV path or URL:").grid(column=0, row=0, sticky="w")
        self.path_var = tk.StringVar(value="data/sample_2024.csv")
        self.path_entry = ttk.Entry(frm, textvariable=self.path_var, width=60)
        self.path_entry.grid(column=0, row=1, columnspan=3, sticky="w")
        ttk.Button(frm, text="Browse", command=self.browse_file).grid(column=3, row=1, sticky="e")

        # Date range
        ttk.Label(frm, text="Start (YYYY-MM-DD):").grid(column=0, row=2, sticky="w")
        self.start_var = tk.StringVar(value="2024-01-01")
        ttk.Entry(frm, textvariable=self.start_var, width=12).grid(column=1, row=2, sticky="w")
        ttk.Label(frm, text="End (YYYY-MM-DD):").grid(column=2, row=2, sticky="w")
        self.end_var = tk.StringVar(value="2024-12-31")
        ttk.Entry(frm, textvariable=self.end_var, width=12).grid(column=3, row=2, sticky="w")

        # Actions
        ttk.Button(frm, text="Load", command=self.load_data).grid(column=0, row=3, sticky="w")
        ttk.Button(frm, text="Filter & Show Stats", command=self.filter_and_show).grid(column=1, row=3)
        ttk.Button(frm, text="Export Report", command=self.export_report_dialog).grid(column=2, row=3)
        ttk.Button(frm, text="Export Filtered CSV", command=self.export_filtered_dialog).grid(column=3, row=3)
        ttk.Button(frm, text="Check Dependencies", command=self.check_dependencies).grid(column=4, row=3, sticky="e")

        # Visuals
        ttk.Separator(frm).grid(column=0, row=4, columnspan=4, sticky="ew", pady=8)
        ttk.Button(frm, text="Show Monthly Chart", command=self.show_monthly_chart).grid(column=0, row=5, sticky="w")
        ttk.Button(frm, text="Show Top Streets Chart", command=self.show_top_streets_chart).grid(column=1, row=5)
        ttk.Button(frm, text="Show Folium Heatmap", command=self.show_heatmap).grid(column=2, row=5)

        # Search
        ttk.Label(frm, text="Search street:").grid(column=0, row=6, sticky="w")
        self.search_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.search_var, width=30).grid(column=1, row=6, sticky="w")
        ttk.Button(frm, text="Search", command=self.search_street).grid(column=2, row=6, sticky="w")

        # Output area
        self.output = tk.Text(frm, width=100, height=20)
        self.output.grid(column=0, row=7, columnspan=4, pady=8)

        # Status
        self.status = ttk.Label(frm, text="Ready")
        self.status.grid(column=0, row=8, columnspan=4, sticky="w")

    def browse_file(self):
        path = filedialog.askopenfilename(title="Open CSV file", filetypes=[("CSV files", "*.csv"), ("All files", "*")])
        if path:
            self.path_var.set(path)

    def load_data(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Input required", "Please provide a CSV path or URL")
            return
        try:
            self.status.config(text="Loading...")
            self.master.update_idletasks()
            data, summary = load_and_preview(path, preview=0)
            self.data = data
            self.filtered = data
            self.output.insert(tk.END, f"Loaded: rows={summary.get('rows')}\n")
            self.status.config(text="Loaded data")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            self.status.config(text="Load failed")

    def parse_date(self, s: str):
        from datetime import datetime
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d").date()
        except Exception:
            raise ValueError("Date must be in YYYY-MM-DD format")

    def filter_and_show(self):
        if self.data is None:
            messagebox.showwarning("No data", "Load data first")
            return
        try:
            start = self.parse_date(self.start_var.get())
            end = self.parse_date(self.end_var.get())
        except ValueError as e:
            messagebox.showerror("Bad date", str(e))
            return
        self.status.config(text="Filtering...")
        self.master.update_idletasks()
        self.filtered = filter_by_date_range(self.data, start, end)
        stats = compute_stats(self.filtered)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "=== Stats ===\n")
        for k, v in stats.items():
            self.output.insert(tk.END, f"{k}: {v}\n")
        self.status.config(text="Filtered and displayed stats")

    def export_report_dialog(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Save report as")
        if not path:
            return
        try:
            export_report_csv(compute_stats(self.filtered), path)
            messagebox.showinfo("Saved", f"Report saved to {path}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def export_filtered_dialog(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Save filtered CSV as")
        if not path:
            return
        try:
            cd.write_csv_header(path)
            rows = self.filtered.to_dict(orient="records") if hasattr(self.filtered, "to_dict") else self.filtered
            cd.append_rows_to_csv(path, rows)
            messagebox.showinfo("Saved", f"Filtered CSV saved to {path}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

    def show_monthly_chart(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        try:
            out = viz.plot_monthly_counts(self.filtered, out_png="monthly_counts.png")
            self._display_image_or_open(out)
        except Exception as e:
            messagebox.showerror("Plot failed", str(e))

    def show_top_streets_chart(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        try:
            out = viz.plot_top_streets(self.filtered, out_png="top_streets.png")
            self._display_image_or_open(out)
        except Exception as e:
            messagebox.showerror("Plot failed", str(e))

    def show_heatmap(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        try:
            out = viz.generate_folium_heatmap(self.filtered, out_html="heatmap.html")
            webbrowser.open_new_tab(out)
        except Exception as e:
            messagebox.showerror("Heatmap failed", str(e))

    def _display_image_or_open(self, path: str):
        if PIL_AVAILABLE:
            # show in a new window
            win = tk.Toplevel(self.master)
            win.title(path)
            img = Image.open(path)
            img_tk = ImageTk.PhotoImage(img)
            lbl = ttk.Label(win, image=img_tk)
            lbl.image = img_tk
            lbl.pack()
        else:
            # fallback: open with default external viewer
            webbrowser.open_new_tab(path)

    def check_dependencies(self):
        """Open a dialog that lists optional deps and can install them."""
        deps = [
            ("pandas", "pandas"),
            ("matplotlib", "matplotlib"),
            ("folium", "folium"),
            ("Pillow (images)", "Pillow"),
        ]

        top = tk.Toplevel(self.master)
        top.title("Dependency check & install")
        ttk.Label(top, text="Optional dependencies for enhanced features:").grid(column=0, row=0, sticky="w", padx=8, pady=6)

        # container for list
        list_frame = ttk.Frame(top, padding=6)
        list_frame.grid(column=0, row=1, sticky="nsew")

        status_vars = []
        for i, (label, pkg) in enumerate(deps):
            v = tk.StringVar()
            ok = importlib.util.find_spec(pkg if pkg != "Pillow" else "PIL") is not None
            v.set("Installed" if ok else "Missing")
            ttk.Label(list_frame, text=label).grid(column=0, row=i, sticky="w")
            ttk.Label(list_frame, textvariable=v).grid(column=1, row=i, sticky="w")
            status_vars.append((pkg, v))

        # output log
        from tkinter import scrolledtext
        log = scrolledtext.ScrolledText(top, width=80, height=10)
        log.grid(column=0, row=2, padx=6, pady=6)

        def _install(pkgs):
            def worker():
                for p in pkgs:
                    log.insert(tk.END, f"Installing {p}...\n")
                    log.see(tk.END)
                    # run pip install
                    try:
                        proc = subprocess.run([sys.executable, "-m", "pip", "install", p], capture_output=True, text=True)
                        log.insert(tk.END, proc.stdout + "\n")
                        if proc.returncode != 0:
                            log.insert(tk.END, proc.stderr + "\n")
                        else:
                            log.insert(tk.END, f"{p} installed successfully.\n")
                    except Exception as e:
                        log.insert(tk.END, f"Failed to install {p}: {e}\n")
                    finally:
                        log.see(tk.END)
                # refresh status vars
                for pkg, var in status_vars:
                    ok = importlib.util.find_spec(pkg if pkg != "Pillow" else "PIL") is not None
                    var.set("Installed" if ok else "Missing")
                log.insert(tk.END, "\nAll installations attempted.\n")
                log.see(tk.END)

            th = threading.Thread(target=worker, daemon=True)
            th.start()

        btn_frame = ttk.Frame(top)
        btn_frame.grid(column=0, row=3, sticky="ew", pady=6)
        def on_install_all():
            pkgs = [pkg for pkg, _ in status_vars]
            _install(pkgs)

        def on_install_selected():
            sel = [pkg for pkg, var in status_vars if var.get() == "Missing"]
            if not sel:
                messagebox.showinfo("Nothing to install", "All dependencies appear installed.")
                return
            _install(sel)

        ttk.Button(btn_frame, text="Install Missing", command=on_install_selected).grid(column=0, row=0, padx=6)
        ttk.Button(btn_frame, text="Install All", command=on_install_all).grid(column=1, row=0, padx=6)
        ttk.Button(btn_frame, text="Close", command=top.destroy).grid(column=2, row=0, padx=6)

    def search_street(self):
        if self.filtered is None:
            messagebox.showwarning("No data", "Load and filter data first")
            return
        term = self.search_var.get().strip()
        if not term:
            messagebox.showwarning("Input required", "Enter a street term to search")
            return
        rows = self.filtered.to_dict(orient="records") if hasattr(self.filtered, "to_dict") else self.filtered
        matches = [r for r in rows if term.lower() in (r.get("on_street_name") or "").lower()]
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, f"Found {len(matches)} matches\n")
        for m in matches[:100]:
            self.output.insert(tk.END, str(m) + "\n")


def main():
    root = tk.Tk()
    app = AccidentsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
