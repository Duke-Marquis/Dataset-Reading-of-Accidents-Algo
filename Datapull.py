"""Simple data-pull utilities for the accidents CSV.

Expected CSV header (example):
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, Optional


def _pandas_available() -> bool:
	try:
		import pandas as _pd  # type: ignore

		return True
	except Exception:
		return False


def read_accidents_csv(path: str, use_pandas: Optional[bool] = None):
	"""Read accidents CSV and return a DataFrame when pandas is available.

	If pandas is not installed or use_pandas=False, returns a list of dict rows.
	It will attempt to combine `crash_date` and `crash_time` into `crash_datetime` when possible.
	"""
	path_obj = Path(path)
	if not path_obj.exists():
		raise FileNotFoundError(f"File not found: {path}")

	pandas_ok = _pandas_available()
	if use_pandas is False or (use_pandas is None and not pandas_ok):
		# Fallback to csv.DictReader
		with path_obj.open("r", encoding="utf-8-sig", newline="") as fh:
			reader = csv.DictReader(fh)
			rows = [row for row in reader]
		# Try to add combined datetime string if fields exist
		if rows and "crash_date" in rows[0]:
			for r in rows:
				date = r.get("crash_date") or ""
				time = r.get("crash_time") or ""
				r["crash_datetime"] = (date + " " + time).strip()
		return rows

	# Prefer pandas
	import pandas as pd  # type: ignore

	df = pd.read_csv(path_obj, low_memory=False)
	# combine date/time when possible
	if "crash_date" in df.columns:
		time_col = "crash_time" if "crash_time" in df.columns else None
		if time_col:
			df["crash_datetime"] = pd.to_datetime(
				df["crash_date"].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip(),
				errors="coerce",
			)
		else:
			df["crash_datetime"] = pd.to_datetime(df["crash_date"], errors="coerce")
	return df


def summarize(data: Any) -> Dict[str, Any]:
	"""Return a compact summary for a DataFrame or list-of-dicts.

	Summary includes number of rows, columns (when available), and a few top counts for
	the `contributing_factor_vehicle_1` column if present.
	"""
	summary: Dict[str, Any] = {}
	if _pandas_available() and hasattr(data, "shape"):
		# pandas DataFrame
		import pandas as pd  # type: ignore

		df = data
		summary["rows"] = int(df.shape[0])
		summary["columns"] = int(df.shape[1])
		summary["head"] = df.head(5).to_dict(orient="records")
		if "contributing_factor_vehicle_1" in df.columns:
			summary["top_contributing_factors"] = (
				df["contributing_factor_vehicle_1"].value_counts(dropna=True).head(10).to_dict()
			)
		# missing counts for a few important numeric columns if present
		for col in [
			"number_of_persons_injured",
			"number_of_persons_killed",
			"number_of_pedestrians_injured",
		]:
			if col in df.columns:
				summary[f"missing_{col}"] = int(df[col].isna().sum())
	else:
		# assume list of dicts
		rows = data if isinstance(data, list) else []
		summary["rows"] = len(rows)
		summary["columns"] = len(rows[0].keys()) if rows else 0
		summary["head"] = rows[:5]
		# top contributing factor
		counts: Dict[str, int] = {}
		for r in rows:
			k = r.get("contributing_factor_vehicle_1")
			if k:
				counts[k] = counts.get(k, 0) + 1
		summary["top_contributing_factors"] = dict(
			sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
		)

	return summary


def _cli() -> None:
	parser = argparse.ArgumentParser(description="Basic CSV data pull and summary for accidents file")
	parser.add_argument("file", help="Path to the accidents CSV file")
	parser.add_argument("--no-pandas", action="store_true", help="Force fallback to csv reader instead of pandas")
	parser.add_argument("--preview", "-n", type=int, default=5, help="Number of preview rows to show")
	args = parser.parse_args()

	data = read_accidents_csv(args.file, use_pandas=not args.no_pandas)
	s = summarize(data)

	# print brief summary
	print("=== Summary ===")
	print(f"Rows: {s.get('rows')}")
	print(f"Columns: {s.get('columns')}")
	print("\nTop contributing factors:")
	for k, v in (s.get("top_contributing_factors") or {}).items():
		print(f"  {k}: {v}")

	print("\nPreview:")
	head = s.get("head", [])
	for r in head[: args.preview]:
		print(r)


if __name__ == "__main__":
	_cli()


# Convenience wrapper for programmatic use from other modules (e.g. `main.py`)
def load_and_preview(path: str, preview: int = 5, use_pandas: Optional[bool] = None):
		"""Load the CSV and return a tuple (data, summary) where `summary['preview']`
		contains up to `preview` rows for display.

		- `data` is a pandas.DataFrame when pandas is available (and used) or a list[dict] when
			falling back to the csv module.
		- `summary` is the same structure returned by `summarize` with an added `preview` key.
		"""
		data = read_accidents_csv(path, use_pandas=use_pandas)
		summary = summarize(data)
		summary["preview"] = summary.get("head", [])[:preview]
		return data, summary


__all__ = ["read_accidents_csv", "summarize", "load_and_preview"]

