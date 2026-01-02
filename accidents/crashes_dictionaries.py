# Authors: Marc Aaron Africano, Alexander John Balagso

"""Utilities to handle crash CSV field names and CSV row helpers."""

from typing import Dict, Iterable, List
import csv
from pathlib import Path

# Column names used in the NYC crashes dataset (commonly present)
FIELDS: List[str] = [
    "crash_date",
    "crash_time",
    "borough",
    "zip_code",
    "latitude",
    "longitude",
    "location",
    "on_street_name",
    "off_street_name",
    "cross_street_name",
    "number_of_persons_injured",
    "number_of_persons_killed",
    "number_of_pedestrians_injured",
    "number_of_pedestrians_killed",
    "number_of_cyclist_injured",
    "number_of_cyclist_killed",
    "number_of_motorist_injured",
    "number_of_motorist_killed",
    "contributing_factor_vehicle_1",
    "contributing_factor_vehicle_2",
    "contributing_factor_vehicle_3",
    "contributing_factor_vehicle_4",
    "contributing_factor_vehicle_5",
    "collision_id",
    "vehicle_type_code1",
    "vehicle_type_code2",
    "vehicle_type_code3",
    "vehicle_type_code4",
    "vehicle_type_code5",
]


def dict_to_csv_row(row: Dict[str, object]) -> List[object]:
    """Return a list of values in `FIELDS` order from a mapping `row`.

    Missing keys are returned as empty strings to ensure a stable CSV order.
    """
    return [row.get(k, "") for k in FIELDS]


def write_csv_header(path: str | Path):
    """Write CSV header to `path` using the canonical `FIELDS` order."""
    p = Path(path)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)


def append_rows_to_csv(path: str | Path, rows: Iterable[Dict[str, object]]):
    """Append multiple dict rows to a CSV file (writing header if missing)."""
    p = Path(path)
    write_header = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(FIELDS)
        for r in rows:
            w.writerow(dict_to_csv_row(r))


__all__ = ["FIELDS", "dict_to_csv_row", "write_csv_header", "append_rows_to_csv"] 