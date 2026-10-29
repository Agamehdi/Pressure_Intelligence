"""Smoke tests: python -m unittest discover -s tests -v"""
import io
from pathlib import Path
import unittest
import zipfile

import pandas as pd

from data_engine import prepare_data, qc_summary, spotfire_long, trend_summary, build_spotfire_zip, export_excel

ROOT = Path(__file__).resolve().parents[1]


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = prepare_data(pd.read_csv(ROOT / 'sample_data' / 'synthetic_pressure_demo.csv'), 'Synthetic demo')

    def test_demo_values(self):
        self.assertGreater(len(self.demo), 50)
        self.assertGreater(self.demo['Date'].notna().sum(), 50)
        self.assertTrue(self.demo['Pressure Family'].isin(['Formation tester', 'Static BHP', 'Flowing THP']).all())

    def test_time_proxy_flags(self):
        self.assertGreater(self.demo['Flag · Spud date proxy'].sum(), 0)
        summary = trend_summary(self.demo)
        self.assertFalse(summary.empty)
        self.assertTrue((summary['N'] > 0).all())

    def test_flat_csv_headers(self):
        flattened = spotfire_long(self.demo)
        self.assertIn('pressure_psi', flattened.columns)
        self.assertIn('date_reliable', flattened.columns)
        self.assertFalse(any(' ' in c for c in flattened.columns))

    def test_zip_and_excel(self):
        payload = build_spotfire_zip(self.demo, ['Pay Zone (Sand)', 'Pressure Family'])
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            self.assertIn('Spotfire_Data_Long.csv', z.namelist())
            self.assertIn('README_Spotfire_Import.txt', z.namelist())
        book = pd.ExcelFile(io.BytesIO(export_excel(self.demo, ['Pressure Family'])))
        self.assertIn('Spotfire_Long', book.sheet_names)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            prepare_data(pd.DataFrame({'Unrecognized': [1]}))


if __name__ == '__main__':
    unittest.main()
