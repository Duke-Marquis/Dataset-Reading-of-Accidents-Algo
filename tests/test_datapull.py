import unittest
from pathlib import Path
from Datapull import read_accidents_csv, filter_by_date_range, compute_stats
from datetime import date

HERE = Path(__file__).parent.parent
SAMPLE = HERE / "data" / "sample_2024.csv"

class TestDatapull(unittest.TestCase):
    def test_read_csv_list(self):
        rows = read_accidents_csv(str(SAMPLE), use_pandas=False)
        self.assertIsInstance(rows, list)
        self.assertGreaterEqual(len(rows), 4)

    def test_filter_2024(self):
        rows = read_accidents_csv(str(SAMPLE), use_pandas=False)
        start = date(2024,1,1)
        end = date(2024,12,31)
        filtered = filter_by_date_range(rows, start, end)
        # sample has 4 rows in 2024
        self.assertEqual(len(filtered), 4)

    def test_compute_stats_list(self):
        rows = read_accidents_csv(str(SAMPLE), use_pandas=False)
        start = date(2024,1,1)
        end = date(2024,12,31)
        filtered = filter_by_date_range(rows, start, end)
        stats = compute_stats(filtered)
        self.assertEqual(stats["total_accidents"], 4)
        self.assertEqual(stats["number_of_persons_killed"], 1)
        # Ensure FULTON ST is top street
        self.assertIn("FULTON ST", stats["top_streets"])


if __name__ == "__main__":
    unittest.main()
