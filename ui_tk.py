# Authors: Alexander John Balagso, Marc Aaron Africano

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
import os
from pathlib import Path

def _ensure_project_path():
    """Try to add the project root (where Datapull.py or crashes_dictionaries.py live)
    to sys.path so local imports work when running this file from elsewhere."""
    here = Path(__file__).resolve().parent
    # search upward for known project files
    for parent in [here] + list(here.parents):
        if (parent / "crashes_dictionaries.py").exists() or (parent / "Datapull.py").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return
    # fallback: ensure current working directory is in sys.path
    cwd = Path.cwd()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))

_ensure_project_path()

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
        # default: use local sample CSV for offline demo
        self.path_var = tk.StringVar(value=os.path.join("data", "sample_2024.csv"))
        self.path_entry = ttk.Entry(frm, textvariable=self.path_var, width=60)
        self.path_entry.grid(column=0, row=1, columnspan=3, sticky="w")
        ttk.Button(frm, text="Browse", command=self.browse_file).grid(column=3, row=1, sticky="e")
        # Auto-load toggle (default disabled to avoid accidental heavy loads). User can enable if desired.
        self.autoload_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Auto-load on startup", variable=self.autoload_var).grid(column=4, row=1, sticky="w")

        # Try auto-loading after short delay (safe, runs in background) only if enabled
        try:
            if self.autoload_var.get():
                # call after UI settles
                self.master.after(250, lambda: self.load_data(suppress_error=True))
        except Exception:
            # ignore if window not fully initialized in some test contexts
            pass

        # Date range
        ttk.Label(frm, text="Start (YYYY-MM-DD):").grid(column=0, row=2, sticky="w")
        self.start_var = tk.StringVar(value="2024-01-01")
        ttk.Entry(frm, textvariable=self.start_var, width=12).grid(column=1, row=2, sticky="w")
        ttk.Label(frm, text="End (YYYY-MM-DD):").grid(column=2, row=2, sticky="w")
        self.end_var = tk.StringVar(value="2024-12-31")
        ttk.Entry(frm, textvariable=self.end_var, width=12).grid(column=3, row=2, sticky="w")

        # Actions
        self.load_btn = ttk.Button(frm, text="Load", command=self.load_data, style="Accent.TButton")
        self.load_btn.grid(column=0, row=3, sticky="w")
        self.filter_btn = ttk.Button(frm, text="Filter & Show Stats", command=self.filter_and_show)
        self.filter_btn.grid(column=1, row=3)
        self.export_report_btn = ttk.Button(frm, text="Export Report", command=self.export_report_dialog)
        self.export_report_btn.grid(column=2, row=3)
        self.export_filtered_btn = ttk.Button(frm, text="Export Filtered CSV", command=self.export_filtered_dialog)
        self.export_filtered_btn.grid(column=3, row=3)
        ttk.Button(frm, text="Check Dependencies", command=self.check_dependencies).grid(column=6, row=3, sticky="e")

        # Visuals
        style = ttk.Style(master)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Accent.TButton", foreground="white", background="#0078d4")

        ttk.Separator(frm).grid(column=0, row=4, columnspan=4, sticky="ew", pady=8)
        ttk.Button(frm, text="Show Monthly Chart", command=self.show_monthly_chart, style="Accent.TButton").grid(column=0, row=5, sticky="w")
        ttk.Button(frm, text="Show Top Streets Chart", command=self.show_top_streets_chart, style="Accent.TButton").grid(column=1, row=5)

        # Search (street or vehicle)
        ttk.Label(frm, text="Search:").grid(column=0, row=6, sticky="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(frm, textvariable=self.search_var, width=40)
        self.search_entry.grid(column=1, row=6, columnspan=2, sticky="w")
        # Search type selector
        self.search_type_var = tk.StringVar(value="Street")
        ttk.Combobox(frm, textvariable=self.search_type_var, values=["Street", "Vehicle type"], width=18, state="readonly").grid(column=3, row=6, sticky="w")
        # Search mode (AND/OR)
        self.search_mode_var = tk.StringVar(value="AND")
        ttk.Combobox(frm, textvariable=self.search_mode_var, values=["AND", "OR"], width=6, state="readonly").grid(column=4, row=6, sticky="w")
        # Fuzzy match checkbox
        self.fuzzy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Fuzzy", variable=self.fuzzy_var).grid(column=5, row=6, sticky="w")
        # Buttons: Search / Clear / Export
        self.search_btn = ttk.Button(frm, text="Search", command=self.search_street, style="Accent.TButton")
        self.search_btn.grid(column=6, row=6, sticky="w")
        self.clear_btn = ttk.Button(frm, text="Clear", command=self.clear_output)
        self.clear_btn.grid(column=7, row=6, sticky="w")
        self.export_search_btn = ttk.Button(frm, text="Export Results", command=self.export_search_results)
        self.export_search_btn.grid(column=8, row=6, sticky="w")

        # Small hint
        ttk.Label(frm, text="Tip: choose 'Vehicle type' for cars (supports partial/token search)", foreground="#555").grid(column=0, row=7, columnspan=9, sticky="w", pady=(4,0))

        # Output area (styled)
        self.output = tk.Text(frm, width=100, height=20, bg="#f8f9fb", fg="#111")
        self.output.grid(column=0, row=8, columnspan=9, pady=8)
        # color tags
        self.output.tag_config("header", foreground="#0b6efd", font=("Helvetica", 10, "bold"))
        self.output.tag_config("muted", foreground="#666")
        self.output.tag_config("danger", foreground="#c82333")

        # Status (colored)
        self.status = ttk.Label(frm, text="Ready", foreground="#2b7a0b")
        self.status.grid(column=0, row=9, columnspan=9, sticky="w")

        # internal indices for fast search
        import re
        self._re_split = re.compile(r"\W+")
        self._rows = []
        self._street_index = {}
        self._vehicle_index = {}
        self._last_search_matches = []
        # indexing state flags
        self._index_ready = False
        self._indexing_in_progress = False

    def browse_file(self):
        path = filedialog.askopenfilename(title="Open CSV file", filetypes=[("CSV files", "*.csv"), ("All files", "*")])
        if path:
            self.path_var.set(path)

    def load_data(self, suppress_error: bool = False):
        """Load dataset (runs in a background thread). If `suppress_error` is True the
        method will not show modal error dialogs (useful for auto-load on startup)."""
        path = self.path_var.get().strip()
        if not path:
            if not suppress_error:
                messagebox.showwarning("Input required", "Please provide a CSV path or URL")
            return
        # capture date-range to pass to loader (Datapull honors these for 'nyc' shortcuts)
        start_date = self.start_var.get().strip() or None
        end_date = self.end_var.get().strip() or None

        def worker():
            try:
                data, summary = load_and_preview(path, preview=0, start_date=start_date, end_date=end_date)
            except Exception as e:
                if suppress_error:
                    # update status non-modally
                    self.master.after(0, lambda: self._set_busy(False, f"Load failed: {e}"))
                else:
                    self.master.after(0, lambda: (messagebox.showerror("Load failed", str(e)), self._set_busy(False, "Load failed")))
                return
            def done():
                self.data = data
                self.filtered = data
                self._build_search_indices()
                self.output.insert(tk.END, f"Loaded: rows={summary.get('rows')}\n")
                self._set_busy(False, "Loaded data")
            self.master.after(0, done)
        self._set_busy(True, "Loading...")
        threading.Thread(target=worker, daemon=True).start()

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
        def worker():
            try:
                filtered = filter_by_date_range(self.data, start, end)
                stats = compute_stats(filtered)
            except Exception as e:
                self.master.after(0, lambda: (messagebox.showerror("Filter failed", str(e)), self._set_busy(False, "Filter failed")))
                return
            def done():
                self.filtered = filtered
                self._build_search_indices()
                self.output.delete("1.0", tk.END)
                self.output.insert(tk.END, "=== Stats ===\n", "header")
                for k, v in stats.items():
                    self.output.insert(tk.END, f"{k}: {v}\n", "muted")
                self._set_busy(False, "Filtered and displayed stats")
            self.master.after(0, done)
        self._set_busy(True, "Filtering...")
        threading.Thread(target=worker, daemon=True).start()

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



    def _build_search_indices(self):
        """Asynchronously build simple inverted indices for streets and vehicle types to avoid blocking the UI."""
        if getattr(self, '_indexing_in_progress', False):
            return
        self._indexing_in_progress = True
        self._index_ready = False
        rows = self.filtered.to_dict(orient="records") if hasattr(self.filtered, "to_dict") else (self.filtered or [])

        def worker():
            street_index = {}
            vehicle_index = {}
            re_split = self._re_split
            vehicle_cols = ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]
            for i, r in enumerate(rows):
                # street tokens
                s = (r.get("on_street_name") or "").lower().strip()
                if s:
                    toks = {t for t in re_split.split(s) if t}
                    for tok in toks:
                        street_index.setdefault(tok, set()).add(i)
                    street_index.setdefault(s, set()).add(i)
                # vehicle tokens
                for col in vehicle_cols:
                    v = (r.get(col) or "").lower().strip()
                    if v:
                        toks = {t for t in re_split.split(v) if t}
                        for tok in toks:
                            vehicle_index.setdefault(tok, set()).add(i)
                        vehicle_index.setdefault(v, set()).add(i)
            # done building, update UI state on main thread
            def done():
                self._rows = rows
                self._street_index = street_index
                self._vehicle_index = vehicle_index
                self._index_ready = True
                self._indexing_in_progress = False
                self._set_busy(False, f"Indexing complete (rows={len(rows)})")
                try:
                    self.output.insert(tk.END, f"Indexed: rows={len(rows)}\n")
                except Exception:
                    pass
            self.master.after(0, done)

        # run worker in background
        self._set_busy(True, "Indexing...")
        th = threading.Thread(target=worker, daemon=True)
        th.start()
    def _set_busy(self, busy: bool, status_text: str | None = None):
        """Disable/enable UI controls and update status/cursor."""
        state = "disabled" if busy else "normal"
        for btn in [getattr(self, "load_btn", None), getattr(self, "filter_btn", None), getattr(self, "search_btn", None), getattr(self, "export_report_btn", None), getattr(self, "export_filtered_btn", None), getattr(self, "export_search_btn", None), getattr(self, "clear_btn", None)]:
            if btn is not None:
                try:
                    btn.config(state=state)
                except Exception:
                    pass
        if busy:
            self.status.config(text=status_text or "Busy...")
            try:
                self.master.config(cursor="watch")
            except Exception:
                pass
        else:
            self.status.config(text=status_text or "Ready")
            try:
                self.master.config(cursor="")
            except Exception:
                pass

    def clear_output(self):
        self.output.delete("1.0", tk.END)
        self._last_search_matches = []

    def export_search_results(self):
        if not getattr(self, "_last_search_matches", None):
            messagebox.showinfo("No results", "Nothing to export. Please run a search first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Save search results as", initialfile="search_results.csv")
        if not path:
            return
        try:
            cd.write_csv_header(path)
            cd.append_rows_to_csv(path, self._last_search_matches)
            messagebox.showinfo("Saved", f"Search results saved to {path}")
        except Exception as e:
            messagebox.showerror("Failed", str(e))

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
            messagebox.showwarning("Input required", "Enter a search term")
            return
        stype = getattr(self, "search_type_var", tk.StringVar(value="Street")).get()

        t = term.lower().strip()
        matches = []
        import difflib
        fuzzy = bool(getattr(self, 'fuzzy_var', tk.BooleanVar(value=False)).get())
        mode = getattr(self, 'search_mode_var', tk.StringVar(value='AND')).get()

        # Prepare rows to scan
        rows = self._rows or (self.filtered.to_dict(orient="records") if hasattr(self.filtered, "to_dict") else list(self.filtered or []))

        use_index = getattr(self, '_index_ready', False)

        # If indices are ready use them (fast). Otherwise do an immediate synchronous scan (functional, may be slower).
        if use_index:
            if stype == "Street":
                tokens = [tok for tok in self._re_split.split(t) if tok]
                if tokens:
                    token_sets = []
                    for tok in tokens:
                        s = self._street_index.get(tok, set())
                        if not s and fuzzy:
                            # try fuzzy match against known tokens
                            close = difflib.get_close_matches(tok, list(self._street_index.keys()), n=5, cutoff=0.6)
                            for c in close:
                                s = s.union(self._street_index.get(c, set()))
                        token_sets.append(s)
                    if mode == 'AND':
                        cand = set.intersection(*[ss for ss in token_sets if ss]) if any(token_sets) else set()
                    else:
                        cand = set.union(*[ss for ss in token_sets if ss]) if any(token_sets) else set()
                    if not cand:
                        # fallback to substring scan
                        cand = {i for i, r in enumerate(rows) if t in (r.get("on_street_name") or "").lower()}
                    matches = [rows[i] for i in sorted(cand)]
                else:
                    matches = []
            else:
                tokens = [tok for tok in self._re_split.split(t) if tok]
                if tokens:
                    token_sets = []
                    for tok in tokens:
                        s = self._vehicle_index.get(tok, set())
                        if not s and fuzzy:
                            close = difflib.get_close_matches(tok, list(self._vehicle_index.keys()), n=5, cutoff=0.6)
                            for c in close:
                                s = s.union(self._vehicle_index.get(c, set()))
                        token_sets.append(s)
                    if mode == 'AND':
                        cand = set.intersection(*[ss for ss in token_sets if ss]) if any(token_sets) else set()
                    else:
                        cand = set.union(*[ss for ss in token_sets if ss]) if any(token_sets) else set()
                    if not cand:
                        # fallback to broader scan
                        cand = {i for i, r in enumerate(rows) if any(t in (str(r.get(c, "")).lower()) for c in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]) }
                    matches = [rows[i] for i in sorted(cand)]
                else:
                    matches = []
        else:
            # Synchronous scan fallback: always functional but may be slower for very large datasets
            if stype == "Street":
                tokens = [tok for tok in self._re_split.split(t) if tok]
                if tokens:
                    if mode == 'AND':
                        matches = [r for r in rows if all(tok in ((r.get("on_street_name") or "").lower()) for tok in tokens)]
                    else:
                        matches = [r for r in rows if any(tok in ((r.get("on_street_name") or "").lower()) for tok in tokens)]
                else:
                    matches = []
                # fuzzy fallback if enabled and no matches
                if fuzzy and not matches:
                    names = [((r.get("on_street_name") or "").lower()) for r in rows if r.get("on_street_name")]
                    close = difflib.get_close_matches(t, names, n=20, cutoff=0.6)
                    if close:
                        matches = [r for r in rows if (r.get("on_street_name") or "").lower() in close]
            else:
                tokens = [tok for tok in self._re_split.split(t) if tok]
                veh_cols = ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]
                if tokens:
                    if mode == 'AND':
                        matches = [r for r in rows if all(any(tok in (str(r.get(c, "")).lower()) for c in veh_cols) for tok in tokens)]
                    else:
                        matches = [r for r in rows if any(any(tok in (str(r.get(c, "")).lower()) for c in veh_cols) for tok in tokens)]
                else:
                    matches = []
                if fuzzy and not matches:
                    # try fuzzy match on vehicle strings
                    all_veh = list({str(r.get(c, "") or "").lower() for r in rows for c in veh_cols if r.get(c)})
                    close = difflib.get_close_matches(t, all_veh, n=20, cutoff=0.6)
                    if close:
                        matches = [r for r in rows if any((str(r.get(c, "") or "").lower() in close) for c in veh_cols)]

        # Display results with styling
        self.output.delete("1.0", tk.END)
        self._last_search_matches = matches
        # note whether we used a prebuilt index or a direct scan
        header_note = "" if getattr(self, '_index_ready', False) else " (scanned)"
        self.output.insert(tk.END, f"Found {len(matches)} matches ({stype}){header_note}\n", "header")
        for m in matches[:200]:
            date = m.get("crash_date") or m.get("crash_datetime") or ""
            street = m.get("on_street_name", "")
            vehicle = ", ".join([str(m.get(c, "")) for c in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"] if m.get(c)])
            inj = m.get("number_of_persons_injured", "")
            killed = m.get("number_of_persons_killed", "")
            line = f"{date} | {street} | vehicles: {vehicle} | inj:{inj} killed:{killed}\n"
            self.output.insert(tk.END, line)

        # Highlight all occurrences of the search term in the output (case-insensitive)
        try:
            i = self.output.search(term, "1.0", nocase=True, stopindex=tk.END)
            while i:
                end_i = f"{i}+{len(term)}c"
                self.output.tag_add('danger', i, end_i)
                i = self.output.search(term, end_i, nocase=True, stopindex=tk.END)
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = AccidentsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
