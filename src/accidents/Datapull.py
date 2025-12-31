"""Simple data-pull utilities for the accidents CSV.

Expected CSV header (example):
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import json
import socket
import ssl
import urllib.request
import urllib.error
import io
import urllib.parse


def _pandas_available() -> bool:
	try:
		import pandas as _pd  # type: ignore

		return True
	except Exception:
		return False


# NYC API Configuration
# Use the Socrata resource CSV endpoint for programmatic access
# Use the v3 query CSV by default; resource CSV supports SoQL params
NYC_CRASHES_URL = "https://data.cityofnewyork.us/api/v3/views/h9gi-nx95/query.csv"
NYC_RESOURCE_CSV = "https://data.cityofnewyork.us/resource/h9gi-nx95.csv"
CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "nyc_crashes_cached.csv"
CACHE_META_FILE = CACHE_DIR / "nyc_crashes_meta.json"


def _is_online() -> bool:
	"""Check if internet connection is available."""
	try:
		socket.create_connection(("8.8.8.8", 53), timeout=3)
		return True
	except (socket.timeout, socket.error):
		return False


def _disable_ssl_verification():
	"""Disable SSL verification for macOS certificate issues."""
	try:
		ssl._create_default_https_context = ssl._create_unverified_context
	except Exception:
		pass


def _download_nyc_crashes(url: str) -> str:
	"""Download CSV data from NYC open data API, handling SSL issues."""
	_disable_ssl_verification()
	try:
		# Use a browser-like User-Agent to avoid HTTP 403 from some endpoints
		req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DataPull/1.0)"})
		with urllib.request.urlopen(req, timeout=30) as resp:
			text = resp.read().decode("utf-8-sig")
		return text
	except urllib.error.URLError as e:
		raise Exception(f"Failed to download from {url}: {e}")


def pull_and_cache_nyc_crashes(force_update: bool = False, start_date: str | None = None, end_date: str | None = None) -> tuple[str | list, dict]:
	"""
	Pull NYC crashes data from the official API and cache it locally.
	
	When online and data is stale (> 7 days), automatically updates cache.
	When offline, uses cached data if available.
	
	Args:
		force_update: Force update from URL even if cache is recent
		
	Returns:
		tuple of (data, metadata) where:
		- data is the CSV content or parsed rows
		- metadata includes cache_timestamp, source, last_updated_from_api
	"""
	CACHE_DIR.mkdir(parents=True, exist_ok=True)
	
	metadata = {
		"cache_timestamp": None,
		"source": "cache",
		"last_updated_from_api": None,
		"url": NYC_CRASHES_URL,
	}
	
	# Load existing metadata
	if CACHE_META_FILE.exists():
		try:
			with CACHE_META_FILE.open("r") as f:
				metadata.update(json.load(f))
		except Exception:
			pass
	
	is_online = _is_online()
	cache_exists = CACHE_FILE.exists()
	
	print(f"[NYC Crashes Data] Online: {is_online}, Cache exists: {cache_exists}")
	
	# Determine if we should update from API
	should_update = False
	if force_update and is_online:
		should_update = True
		print("Force update requested...")
	elif is_online and cache_exists:
		# Check cache age (update if > 7 days old)
		try:
			import time
			cache_age_seconds = time.time() - CACHE_FILE.stat().st_mtime
			cache_age_days = cache_age_seconds / (60 * 60 * 24)
			if cache_age_days > 7:
				should_update = True
				print(f"Cache is {cache_age_days:.1f} days old, updating...")
		except Exception:
			pass
	elif is_online and not cache_exists:
		should_update = True
		print("No cache found, downloading from API...")

	# If a date range is requested, prefer fetching from API to honor it
	if (start_date or end_date) and is_online:
		should_update = True
		print("Date range requested — fetching from API to apply filter...")
	
	# Update from API if needed
	if should_update:
		try:
			# If a date range is provided, use the Socrata resource endpoint with a SoQL $where clause
			if start_date and end_date:
				where = f"crash_date between '{start_date}T00:00:00' and '{end_date}T23:59:59'"
				params = {"$where": where, "$limit": "500000"}
				url = NYC_RESOURCE_CSV + "?" + urllib.parse.urlencode(params)
			else:
				# No date filter: request the resource CSV (may be large)
				params = {"$limit": "500000"}
				url = NYC_RESOURCE_CSV + "?" + urllib.parse.urlencode(params)

			print(f"Downloading from {url}...")
			csv_text = _download_nyc_crashes(url)
			# Write the downloaded CSV to the cache file
			with CACHE_FILE.open("w", encoding="utf-8") as f:
				f.write(csv_text)
			metadata["cache_timestamp"] = datetime.now().isoformat()
			metadata["source"] = "api"
			metadata["last_updated_from_api"] = datetime.now().isoformat()
			# Save metadata
			with CACHE_META_FILE.open("w") as f:
				json.dump(metadata, f, indent=2)
			print(f"✓ Cache updated: {CACHE_FILE}")
			# Socrata limits responses to 50,000 rows by default; if the API returned the limit, warn the user
			if "$limit" in url and "500000" not in url:
				print("⚠ Note: API response may be truncated to 50,000 rows due to Socrata limits.")
			return CACHE_FILE, metadata
		except Exception as e:
			print(f"⚠ Failed to update from API: {e}")
			if cache_exists:
				print("Using cached data instead...")
			else:
				raise
	
	# Use cached data
	if cache_exists:
		metadata["source"] = "cache"
		print(f"✓ Using cached data from {CACHE_FILE}")
		return CACHE_FILE, metadata
	else:
		raise FileNotFoundError(
			f"No internet connection and no cached data. "
			f"Please connect to the internet or provide {CACHE_FILE}"
		)


def read_accidents_csv(path: str, use_pandas: Optional[bool] = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False):
	"""Read accidents CSV and return a DataFrame when pandas is available.

	If pandas is not installed or use_pandas=False, returns a list of dict rows.
	It will attempt to combine `crash_date` and `crash_time` into `crash_datetime` when possible.
	
	Special paths:
	  - "nyc" or "nyc:latest" — pulls from NYC API with automatic caching & updates
	  - "nyc:cached" — uses cached data only (no internet required)
	  - "nyc:update" — forces update from API
	"""
	# Handle special NYC API shortcuts
	if path.lower() in ("nyc", "nyc:latest"):
		cache_path, meta = pull_and_cache_nyc_crashes(force_update=force_update, start_date=start_date, end_date=end_date)
		path = str(cache_path)
		print(f"[Cache Info] {meta}")
	elif path.lower() == "nyc:cached":
		if not CACHE_FILE.exists():
			raise FileNotFoundError(f"No cached data available at {CACHE_FILE}")
		path = str(CACHE_FILE)
		print(f"[Using Cache] {CACHE_FILE}")
	elif path.lower() == "nyc:update":
		cache_path, meta = pull_and_cache_nyc_crashes(force_update=True, start_date=start_date, end_date=end_date)
		path = str(cache_path)
		print(f"[Cache Info] {meta}")
	
	# If a URL is provided, allow pandas to read it, or download and parse without pandas.
	if isinstance(path, str) and path.lower().startswith(("http://", "https://")):
		pandas_ok = _pandas_available()
		if use_pandas is False:
			pandas_ok = False
		if pandas_ok:
			# let pandas handle URL reads (handles compression and formats)
			import pandas as pd  # type: ignore

			df = pd.read_csv(path, low_memory=False)
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
		# fall back to simple download and csv reader
		import urllib.request
		import io
		with urllib.request.urlopen(path) as resp:
			text = resp.read().decode("utf-8-sig")
		reader = csv.DictReader(io.StringIO(text))
		rows = [row for row in reader]
		# Try to add combined datetime string if fields exist
		if rows and "crash_date" in rows[0]:
			for r in rows:
				date = r.get("crash_date") or ""
				time = r.get("crash_time") or ""
				r["crash_datetime"] = (date + " " + time).strip()
		return rows

	path_obj = Path(path)
	if not path_obj.exists():
		raise FileNotFoundError(f"File not found: {path}")

	# Decide whether to use pandas; but if pandas is absent we gracefully fall back to csv
	pandas_ok = _pandas_available()
	will_use_pandas = False
	if use_pandas is not False and pandas_ok:
		# attempt to import pandas (guard against ImportError after detection)
		try:
			import pandas as pd  # type: ignore
			will_use_pandas = True
		except Exception:
			# pandas detected earlier but import failed; fall back to csv reader
			will_use_pandas = False

	if not will_use_pandas:
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

	# Prefer pandas (import succeeded above)
	import pandas as pd  # type: ignore

	# Try the default C engine first; if it fails due to irregular quoting or unexpected
	# field counts, retry with the python engine and skip bad lines. If that still fails,
	# fall back to a simple csv.DictReader.
	try:
		df = pd.read_csv(path_obj, low_memory=False)
	except Exception as exc:
		# try a more permissive parser
		try:
			df = pd.read_csv(path_obj, low_memory=False, engine="python", on_bad_lines="skip")
			print("Warning: Some CSV lines were malformed and were skipped during parsing.")
		except Exception:
			# Final fallback to csv reader
			with path_obj.open("r", encoding="utf-8-sig", newline="") as fh:
				reader = csv.DictReader(fh)
				rows = [row for row in reader]
				if rows and "crash_date" in rows[0]:
					for r in rows:
						date = r.get("crash_date") or ""
						time = r.get("crash_time") or ""
						r["crash_datetime"] = (date + " " + time).strip()
				return rows

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
def load_and_preview(path: str, preview: int = 5, use_pandas: Optional[bool] = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False):
		"""Load the CSV and return a tuple (data, summary) where `summary['preview']`
		contains up to `preview` rows for display.

		- `data` is a pandas.DataFrame when pandas is available (and used) or a list[dict] when
			falling back to the csv module.
		- `summary` is the same structure returned by `summarize` with an added `preview` key.
		"""
		data = read_accidents_csv(path, use_pandas=use_pandas, start_date=start_date, end_date=end_date, force_update=force_update)
		summary = summarize(data)
		summary["preview"] = summary.get("head", [])[:preview]
		return data, summary


# Helper utilities for filtering and reporting
from datetime import datetime, date
from typing import List, Tuple


def _ensure_crash_datetime(data: Any):
	"""Ensure `crash_datetime` exists on data (pandas.DataFrame or list[dict]).

	Attempts to parse crash date/time robustly using dateutil when present, otherwise
	falls back to a handful of common formats.
	"""
	if _pandas_available() and hasattr(data, "shape"):
		import pandas as pd  # type: ignore
		df = data
		if "crash_datetime" not in df.columns and "crash_date" in df.columns:
			time_col = "crash_time" if "crash_time" in df.columns else None
			if time_col:
				df["crash_datetime"] = pd.to_datetime(
					df["crash_date"].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip(),
					errors="coerce",
				)
			else:
				df["crash_datetime"] = pd.to_datetime(df["crash_date"], errors="coerce")
		return df

	# list-of-dicts fallback
	rows = data if isinstance(data, list) else []
	# try dateutil parser if available
	try:
		from dateutil.parser import parse as _parse_date  # type: ignore
	except Exception:
		_parse_date = None

	formats = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y-%m-%d")
	for r in rows:
		# if crash_datetime is present but is a string, try to parse it
		cdval = r.get("crash_datetime")
		if cdval and not isinstance(cdval, (datetime,)):
			# attempt to parse existing string
			try:
				if _parse_date:
					r["crash_datetime"] = _parse_date(str(cdval))
					continue
			except Exception:
				pass
		# if no crash_datetime or still not parsed, try combine date/time
		date_s = (r.get("crash_date") or "").strip()
		time_s = (r.get("crash_time") or "").strip()
		joined = (date_s + " " + time_s).strip()
		if not joined:
			continue
		# try dateutil
		if _parse_date:
			try:
				r["crash_datetime"] = _parse_date(joined)
				continue
			except Exception:
				pass
		# try isoformat
		try:
			r["crash_datetime"] = datetime.fromisoformat(joined)
		except Exception:
			for fmt in formats:
				try:
					r["crash_datetime"] = datetime.strptime(joined, fmt)
					break
				except Exception:
					continue
	return rows


def filter_by_date_range(data: Any, start: date, end: date):
	"""Return a subset of `data` where crash_datetime is between `start` and `end` (inclusive).

	Works with pandas.DataFrame or list[dict]. `start` and `end` should be `datetime.date` objects.
	"""
	if _pandas_available() and hasattr(data, "shape"):
		df = _ensure_crash_datetime(data)
		mask = df["crash_datetime"].dt.date.between(start, end)
		return df.loc[mask].copy()
	else:
		rows = _ensure_crash_datetime(data)
		out = [r for r in rows if isinstance(r.get("crash_datetime"), (datetime,)) and start <= r["crash_datetime"].date() <= end]
		return out

def compute_stats(data: Any) -> dict:
	"""Compute simple stats required by the assignment:

	- total accidents
	- total injured and killed counts
	- top streets by number of accidents (on_street_name)
	- month with greatest number of accidents
	"""
	stats = {}
	if _pandas_available() and hasattr(data, "shape"):
		import pandas as pd  # type: ignore
		df = _ensure_crash_datetime(data)
		stats["total_accidents"] = int(df.shape[0])
		# numeric sums (handle missing / non-numeric)
		for col in ["number_of_persons_injured", "number_of_persons_killed"]:
			if col in df.columns:
				stats[col] = int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
			else:
				stats[col] = 0
		# top streets
		if "on_street_name" in df.columns:
			stats["top_streets"] = df["on_street_name"].value_counts(dropna=True).head(10).to_dict()
		else:
			stats["top_streets"] = {}
		# top month
		if "crash_datetime" in df.columns:
			df = df.copy()
			df["_month"] = df["crash_datetime"].dt.to_period("M")
			stats["top_months"] = df["_month"].value_counts().head(6).to_dict()
	else:
		rows = data if isinstance(data, list) else []
		stats["total_accidents"] = len(rows)
		inj = 0
		killed = 0
		street_counts: Dict[str, int] = {}
		month_counts: Dict[str, int] = {}
		for r in rows:
			try:
				inj += int(r.get("number_of_persons_injured") or 0)
			except Exception:
				pass
			try:
				killed += int(r.get("number_of_persons_killed") or 0)
			except Exception:
				pass
			sn = r.get("on_street_name") or ""
			if sn:
				street_counts[sn] = street_counts.get(sn, 0) + 1
			dt = r.get("crash_datetime")
			if isinstance(dt, datetime):
				m = dt.strftime("%Y-%m")
				month_counts[m] = month_counts.get(m, 0) + 1
		stats["number_of_persons_injured"] = inj
		stats["number_of_persons_killed"] = killed
		stats["top_streets"] = dict(sorted(street_counts.items(), key=lambda kv: kv[1], reverse=True)[:10])
		stats["top_months"] = dict(sorted(month_counts.items(), key=lambda kv: kv[1], reverse=True)[:6])
	return stats


def export_report_csv(stats: dict, outpath: str):
	"""Write a simple CSV report of `stats` to `outpath`.

	The CSV will contain rows "metric, value". For dict-like values such as `top_streets`
	we serialize as semicolon-separated key:value pairs.
	"""
	p = Path(outpath)
	with p.open("w", encoding="utf-8", newline="") as fh:
		w = csv.writer(fh)
		w.writerow(["metric", "value"])
		for k, v in stats.items():
			if isinstance(v, dict):
				val = "; ".join([f"{kk}:{vv}" for kk, vv in v.items()])
			else:
				val = str(v)
			w.writerow([k, val])


__all__ = ["read_accidents_csv", "summarize", "load_and_preview", "filter_by_date_range", "compute_stats", "export_report_csv", "pull_and_cache_nyc_crashes"]

