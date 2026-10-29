"""No demo assets required: python -m unittest discover -s tests -v"""
from __future__ import annotations

import io
from pathlib import Path
import unittest
import zipfile

import pandas as pd

from data_engine import prepare_data, qc_summary, spotfire_long, trend_summary, build_spotfire_zip, export_excel

ROOT = Path(__file__).resolve().parents[1]


def input_fixture() -> pd.DataFrame:
    """Small in-memory test fixture; never loaded or presented by the app."""
    records = []
    for group_i, group in enumerate(("Unit-1", "Unit-2", "Unit-3")):
        for well_i in range(1, 5):
            for sample_i, year in enumerate((2018, 2019, 2020, 2021, 2022)):
                p = 2900 + 200 * group_i + well_i * 7 - 80 * sample_i
                records.append({
                    "Well Name": f"TEST-{group_i}-{well_i}",
                    "Field": "TEST-FIELD",
                    "Formation": "Test Formation",
                    "Pay Zone (Sand)": group,
                    "Pressure (psi)": p,
                    "Pressure (ksc)": p / 14.223343307,
                    "Pressure Type / Measurement": "RFT – Repeat Formation Tester",
                    "Depth (m TVDSS)": 2120 + group_i * 100 + well_i * 15,
                    "Depth Note": "Measured, TVDSS",
                    "Date": f"{year}-07-16",
                    "Remarks": "QA observation",
                })
            records.append({
                "Well Name": f"TEST-{group_i}-{well_i}",
                "Field": "TEST-FIELD",
                "Formation": "Test Formation",
                "Pay Zone (Sand)": group,
                "Pressure (psi)": 900,
                "Pressure (ksc)": 900 / 14.223343307,
                "Pressure Type / Measurement": "FTHP – Flowing tubing-head pressure (DST)",
                "Depth Note": "Wellhead (surface)",
                "Date": "2020-03-14",
                "Remarks": "Date shown = well spud date (DST date not in source)",
            })
    return pd.DataFrame(records)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = prepare_data(input_fixture(), "test_fixture.csv")

    def test_pressure_data(self):
        self.assertGreater(len(self.data), 50)
        self.assertTrue(self.data['Pressure Family'].isin(['Formation tester', 'Flowing THP']).all())
        self.assertEqual(self.data['Well Name'].nunique(), 12)

    def test_date_proxy_flags(self):
        self.assertGreater(self.data['Flag · Spud date proxy'].sum(), 0)
        self.assertTrue(self.data['Date Reliable'].any())
        self.assertFalse(trend_summary(self.data).empty)

    def test_spotfire_flat_headers(self):
        long = spotfire_long(self.data)
        self.assertIn('pressure_psi', long.columns)
        self.assertIn('date_reliable', long.columns)
        self.assertFalse(any(' ' in c for c in long.columns))

    def test_zip_and_excel(self):
        payload = build_spotfire_zip(self.data, ['Pay Zone (Sand)', 'Pressure Family'])
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            self.assertIn('Spotfire_Data_Long.csv', z.namelist())
            self.assertIn('README_Spotfire_Import.txt', z.namelist())
            self.assertGreaterEqual(len(z.namelist()), 10)
        book = pd.ExcelFile(io.BytesIO(export_excel(self.data, ['Pressure Family'])))
        self.assertIn('Spotfire_Long', book.sheet_names)
        self.assertIn('Filtered_Data', book.sheet_names)

    def test_qc_and_bad_input(self):
        self.assertFalse(qc_summary(self.data).empty)
        with self.assertRaises(ValueError):
            prepare_data(pd.DataFrame({'Unrecognized': [1]}))

    def test_upload_only_launch_and_icon_font(self):
        code = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('if uploaded is None:', code)
        self.assertIn('    st.stop()\n\nwith st.sidebar:', code)
        self.assertNotIn('make_synthetic_demo', code)
        self.assertNotIn('DEFAULT_PRIVATE_DATA', code)
        self.assertNotIn('DEMO_FILE', code)
        self.assertNotIn('[data-testid="stSidebar"] *', code)
        self.assertNotIn('html, body, p, h1, h2', code)
        self.assertNotIn('sample_data', code)


if __name__ == '__main__':
    unittest.main()
