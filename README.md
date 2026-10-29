# Daman Pressure Intelligence — White Edition

A polished, white-background Streamlit/Plotly reservoir-pressure data-analysis workstation. Developed specifically around the layout of `Daman_Pressure_Data_Compiled.xlsx`, and works with similarly structured Excel/CSV inputs.

## Quick start (local)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local address printed by Streamlit (typically http://localhost:8501). **The app opens empty by default**, with a file-upload prompt. Upload your actual workbook using the left sidebar and choose the `All Pressure Data` worksheet. Only after an upload are the filters, metrics, interactive charts and Spotfire exports displayed. No demo or synthetic data is automatically loaded.

## GitHub and Streamlit Cloud deployment

1. Create a new GitHub repository.
2. Upload **at least** `app.py`, `data_engine.py`, and `requirements.txt` to the repository root. `.streamlit/config.toml`, `.gitignore`, the tests and this README are recommended. There is no sample-data directory or required data file.
3. **Do not upload your real field-pressure Excel to a public repository.**
4. In Streamlit Community Cloud, choose **New app**, select the repository, branch (`main`) and main file `app.py`.
5. Deploy. In the launched app, upload your real workbook at runtime.

Uploads are held in application session memory for processing and are not deliberately written to a disk or external server by this app. Hosting provider security, access controls, retention and applicable data-handling rules still apply. For sensitive corporate data, use an organization-approved private host instead of public hosting.

## Dashboard pages

| Page | Features |
|---|---|
| Overview | KPI cards, sample-size charts, pressure families, sand matrix, latest reported observations |
| Pressure & Depth | Depth-reversed pressure-depth scatter, family symbols, sand comparison, measured/approximate provenance, optional exploratory fits |
| Time Trends | Year/month/raw pressure-series medians, reported-date-only option, spud-date warnings, exploratory within-well slopes |
| Well Explorer | Up to 12 wells, depth and dated observations, same-well/sand/family comparison matrix |
| Analytics Lab | Violin, histogram, box, descriptive crossplot, grouped statistics, stratified IQR screening |
| Visualization Studio | Custom scatter/bubble, line, median bar, box, violin, histogram, ECDF, density heatmap and 3D scatter; optional unit-equivalent secondary Y-axis |
| Data Quality | QC counts, missing/approx depths, spud-date proxies, psi/ksc QC, duplicate checks, drill-down audit table |
| Spotfire / Export | Spotfire ZIP with 9 CSVs + notes, Excel workbook with 6 tabs, filtered long CSV, annual/monthly date-safe summaries |

## Customization and interaction

- Sidebar filters: field, formation, pay zone, measurement type, block/area, wells, date range, critical QC and depth coverage.
- Chart settings: 5 curated color palettes, 5 font stacks, marker size/opacity, grid, height, optional labels and Plotly native image exports.
- Save/load sidebar selections and chart theme from a JSON setup file.
- Zoom, pan, select and download PNG directly from the Plotly modebar. Optional downloadable interactive HTML under each chart.
- Run the same code with a new Excel file, provided minimum column names are preserved. Missing optional columns are filled and flagged.

## Input schema

Minimum: `Well Name`, plus `Pressure (psi)` and/or `Pressure (ksc)`.

Recommended source columns: `Field`, `Formation`, `Depth (m TVDSS)`, `Pressure Type / Measurement`, `Pay Zone (Sand)`, `Block / Area`, `Date`, `Depth Note`, `Tested Interval / Choke`, `Remarks`, `Source Tab`.

- Numeric Excel serial dates are converted using 1899-12-30. Datetime / ISO date cells are supported.
- If one pressure unit is absent, it is derived using **1 kgf/cm² = 14.223343307 psi**.
- Depth is represented as source *m TVDSS* positive downwards. Surface/wellhead measurements have no fabricated depth.
- Source fields and raw pressure values are not modified or deduplicated. Derived columns carry provenance.

## Technical guardrails (important)

- **Spud date is not a DST test date**: source remarks mark these records as `Spud date proxy`. Year/month trend exports exclude them by design.
- **Flowing THP, static THP, flowing BHP, static BHP, formation-tester pressures and interpreted reservoir pressures are not interchangeable.** The main plots show types using colors and symbols.
- Measurement families and well/sand/date must be controlled for any depletion interpretation.
- An interval-midpoint depth is marked `Approximate` and cannot be presumed equal to tool gauge depth.
- `Apparent P/depth (psi/ft)` is only a ratio of recorded pressure and positive TVDSS depth; it is NOT a measured fluid gradient or contact estimate.
- Exploratory trend slopes require at least 3 unique dates spanning at least a quarter year within one well+sand+family, but are still NOT forecasts.
- Spurious outliers, duplicate measurements and pressure-unit discrepancies are FLAGGED, not silently deleted.
- Pressure medians and averages exported across families are **descriptive**, not reservoir pressure maps/averages.

## Spotfire import

In Spotfire, open `Spotfire_Data_Long.csv` from the downloaded ZIP; type `date` as Date and use `well_name`, `pay_zone_sand`, `pressure_family` and `date_basis` to organize views. Import `Spotfire_Summary_Well_Sand.csv` or `Spotfire_Trends_Annual_Reliable.csv` for grouped analysis. The CSVs have underscored, ASCII-friendly headers and UTF-8 BOM where applicable.

The ZIP also contains `Spotfire_Summary_Custom.csv`, `Spotfire_Summary_Sand_Type.csv`, monthly and annual trend exports, exploratory observation slopes, QC counts and a data dictionary. Consult `README_Spotfire_Import.txt` in the ZIP.

## Limitations

The tool has no model-based pressure normalization to a common datum and no rigorous material-balance pressure reconstruction. Those would require PVT, datum, density, contacts, well status, pressure history and uncertainty context not present in the uploaded source. QC labels must be reviewed by an engineer before decisions.


## V3 — upload-only launch and native Streamlit icon fonts

The default launch is deliberately empty. No demo asset, auto-load or synthetic generator is needed. Once a valid file has been uploaded, all analytical pages work as before.

The global CSS font overrides that accidentally rendered Streamlit Material Symbols ligatures as text (`keyboard_double_arrow...`, `upload`) were removed. Typography overrides now apply only to custom Daman hero/empty-state elements. Streamlit's built-in widgets use the native theme typography; the background is white through `.streamlit/config.toml`.

To upgrade V2: replace `app.py` and `data_engine.py` with the V3 files, commit, and reboot/redeploy. The old `sample_data` directory can be deleted.
