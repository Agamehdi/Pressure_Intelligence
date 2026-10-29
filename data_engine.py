"""Pure data-engine functions for Daman Pressure Intelligence.

No Streamlit dependencies: reusable for CLI validation, QC, and Spotfire exports.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any
import re
import zipfile

import numpy as np
import pandas as pd

PSI_PER_KSC = 14.223343307
MANDATORY = ("Well Name",)
OPTIONAL_SOURCE = [
    "Well Name", "Field", "Formation", "Depth (m TVDSS)", "Pressure (ksc)",
    "Pressure (psi)", "Pressure Type / Measurement", "Pay Zone (Sand)",
    "Block / Area", "Date", "Depth Note", "Tested Interval / Choke",
    "Remarks", "Source Tab",
]

FAMILY_DESCRIPTIONS = {
    "Static BHP": "Static downhole pressure: surveys or DST build-up; not necessarily stabilized reservoir pressure.",
    "Formation tester": "Wireline or drilling formation pressure: RFT/MDT/XPT/RCI/FPWD.",
    "Reservoir estimate": "Interpreted pressure P*, Pi or Pavg. Keep distinct from measured pressures.",
    "Build-up test": "Unclassified build-up pressure; interpretation needs checking.",
    "Flowing BHP": "Flowing bottom-hole pressure. Not reservoir static pressure.",
    "Static THP": "Static wellhead pressure. Do not merge with downhole pressure.",
    "Flowing THP": "Flowing wellhead pressure. Do not merge with downhole pressure.",
    "Unclassified": "Source does not provide sufficient pressure classification.",
}
RESERVOIR_FAMILIES = ["Static BHP", "Formation tester", "Reservoir estimate"]



def _clean_string(s: pd.Series, default: str = "Not specified") -> pd.Series:
    out = s.astype("string").str.strip()
    return out.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA}).fillna(default).astype(str)


def _dates(s: pd.Series) -> pd.Series:
    """Handle Excel serials and timestamp/text dates safely, with no silent day-first switch."""
    result = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    numeric = pd.to_numeric(s, errors="coerce")
    serial = numeric.notna() & numeric.between(20000, 90000)
    if serial.any():
        result.loc[serial] = pd.to_datetime(numeric.loc[serial], unit="D", origin="1899-12-30", errors="coerce")
    if (~serial).any():
        # Standard ISO and Excel-exported date strings, plus any datetime cells.
        raw = s.loc[~serial]
        try:
            result.loc[~serial] = pd.to_datetime(raw, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            result.loc[~serial] = pd.to_datetime(raw, errors="coerce")
    return result


def pressure_family(label: str) -> str:
    t = str(label).strip().upper()
    if t.startswith("FTHP"):
        return "Flowing THP"
    if t.startswith("STHP"):
        return "Static THP"
    if t.startswith("FBHP"):
        return "Flowing BHP"
    if t.startswith("SBHP"):
        return "Static BHP"
    if t.startswith(("MDT", "RFT", "XPT", "FPWD", "RCI")):
        return "Formation tester"
    if t.startswith(("P*", "PI ", "PAVG")) or "EXTRAPOLATED" in t or "INITIAL RESERVOIR PRESSURE" in t:
        return "Reservoir estimate"
    if t.startswith("BUILD-UP"):
        return "Build-up test"
    return "Unclassified"


def classify_depth(note: str, family: str, depth: float) -> str:
    text = str(note).lower()
    if "wellhead" in text or family in {"Static THP", "Flowing THP"}:
        return "Surface"
    if pd.isna(depth):
        return "Unavailable"
    if "approx" in text or "mid-point" in text:
        return "Approximate"
    if "measured" in text:
        return "Measured"
    return "Unspecified"


def prepare_data(raw: pd.DataFrame, source_name: str = "Uploaded file") -> pd.DataFrame:
    """Normalize the original workbook, retaining source fields and adding audit columns.

    QC flags are informational; no record is quietly removed or changed.
    """
    if raw is None or raw.empty:
        raise ValueError("Selected sheet/file is empty.")
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)
    # Avoid silent confusion if the source has duplicate headers.
    if len(df.columns) != len(set(df.columns)):
        raise ValueError("Duplicate column headers. Please make column names unique.")
    missing = [c for c in MANDATORY if c not in df.columns]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    if "Pressure (psi)" not in df and "Pressure (ksc)" not in df:
        raise ValueError("At least one pressure column (Pressure (psi) or Pressure (ksc)) is required.")
    for col in OPTIONAL_SOURCE:
        if col not in df:
            df[col] = pd.NA

    for col in ("Well Name", "Field", "Formation", "Pressure Type / Measurement", "Pay Zone (Sand)",
                "Block / Area", "Depth Note", "Remarks", "Source Tab"):
        df[col] = _clean_string(df[col])
    df["Pressure (psi)"] = pd.to_numeric(df["Pressure (psi)"], errors="coerce")
    df["Pressure (ksc)"] = pd.to_numeric(df["Pressure (ksc)"], errors="coerce")
    both = df["Pressure (psi)"].notna() & df["Pressure (ksc)"].notna()
    df["Pressure (psi)"] = df["Pressure (psi)"].fillna(df["Pressure (ksc)"] * PSI_PER_KSC)
    df["Pressure (ksc)"] = df["Pressure (ksc)"].fillna(df["Pressure (psi)"] / PSI_PER_KSC)
    df["Depth (m TVDSS)"] = pd.to_numeric(df["Depth (m TVDSS)"], errors="coerce")
    df["Date"] = _dates(df["Date"])
    df["Row ID"] = np.arange(2, len(df) + 2)
    df["Pressure Family"] = df["Pressure Type / Measurement"].map(pressure_family)
    df["Depth Quality"] = [classify_depth(note, fam, d) for note, fam, d in zip(
        df["Depth Note"], df["Pressure Family"], df["Depth (m TVDSS)"]
    )]
    df["Date Basis"] = np.where(
        df["Remarks"].str.contains(r"spud\s*date", case=False, regex=True, na=False),
        "Spud date proxy", np.where(df["Date"].isna(), "Missing date", "Reported date")
    )
    df["Date Reliable"] = df["Date Basis"].eq("Reported date")
    df["Pressure Context"] = np.where(df["Pressure Family"].isin(RESERVOIR_FAMILIES),
                                       "Reservoir-related", "Other / operational")
    df["Apparent P/depth (psi/ft)"] = np.where(
        df["Depth (m TVDSS)"].gt(0),
        df["Pressure (psi)"] / (df["Depth (m TVDSS)"] * 3.280839895), np.nan
    )
    # The P/depth ratio is NOT a measured fluid gradient. Retain clear naming.
    expected_psi = df["Pressure (ksc)"] * PSI_PER_KSC
    df["Unit Difference (%)"] = np.where(both & expected_psi.abs().gt(1),
        (df["Pressure (psi)"] - expected_psi).abs() / expected_psi.abs() * 100,
        np.nan
    )

    dupe_cols = ["Well Name", "Pay Zone (Sand)", "Pressure Type / Measurement", "Date", "Depth (m TVDSS)", "Pressure (psi)"]
    is_duplicate = df.duplicated(dupe_cols, keep=False)
    unit_issue = df["Unit Difference (%)"].gt(2).fillna(False)
    invalid_p = df["Pressure (psi)"].isna() | df["Pressure (psi)"].le(0)
    df["Flag · Missing depth"] = df["Depth (m TVDSS)"].isna()
    df["Flag · Approx depth"] = df["Depth Quality"].eq("Approximate")
    df["Flag · Spud date proxy"] = df["Date Basis"].eq("Spud date proxy")
    df["Flag · Missing date"] = df["Date"].isna()
    df["Flag · Missing sand"] = df["Pay Zone (Sand)"].eq("Not specified")
    df["Flag · Unit mismatch"] = unit_issue
    df["Flag · Nonpositive/missing P"] = invalid_p
    df["Flag · Duplicate"] = is_duplicate
    df["Flag · Unclassified type"] = df["Pressure Family"].eq("Unclassified")
    qflag = [c for c in df if c.startswith("Flag ·")]
    df["QC Flag Count"] = df[qflag].sum(axis=1).astype(int)
    df["QC Status"] = np.select([
        invalid_p | unit_issue,
        df["QC Flag Count"].ge(1),
    ], ["Critical review", "Review context"], default="No listed flags")
    df["Source File"] = source_name
    return df


def qc_summary(df: pd.DataFrame) -> pd.DataFrame:
    flags = [c for c in df.columns if c.startswith("Flag ·")]
    result = pd.DataFrame({"QC Check": [c.removeprefix("Flag · ") for c in flags],
                          "Affected Rows": [int(df[c].sum()) for c in flags]})
    result["Share (%)"] = (result["Affected Rows"] / max(len(df), 1) * 100).round(1)
    return result.sort_values("Affected Rows", ascending=False).reset_index(drop=True)


def spotfire_long(df: pd.DataFrame) -> pd.DataFrame:
    """Flat, Spotfire-friendly file: ISO date, raw & standardized values and QC flags."""
    cols = ["Row ID", "Well Name", "Field", "Formation", "Pay Zone (Sand)", "Block / Area",
        "Date", "Date Basis", "Date Reliable", "Pressure Type / Measurement", "Pressure Family",
        "Pressure Context", "Pressure (psi)", "Pressure (ksc)", "Depth (m TVDSS)",
        "Depth Quality", "Apparent P/depth (psi/ft)", "QC Status", "QC Flag Count",
        "Unit Difference (%)", "Depth Note", "Tested Interval / Choke", "Remarks", "Source Tab", "Source File"]
    cols += [c for c in df if c.startswith("Flag ·")]
    out = df.loc[:, [c for c in cols if c in df]].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    # CSV-safe ASCII column labels; string contents are left untouched.
    out.columns = [re.sub(r"[^a-zA-Z0-9]+", "_", c).strip("_").lower() for c in out.columns]
    return out


def group_summary(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Group pressure measurements without claiming the data form comparable reservoir pressure estimates."""
    keys = [k for k in keys if k in df.columns]
    if not keys:
        keys = ["Pressure Family"]
    clean = df.dropna(subset=["Pressure (psi)"]).copy()
    if clean.empty:
        return pd.DataFrame(columns=keys + ["Measurements"])
    g = clean.groupby(keys, dropna=False, observed=True)
    out = g.agg(Measurements=("Pressure (psi)", "size"),
        Wells=("Well Name", "nunique"), Pressure_Mean_psi=("Pressure (psi)", "mean"),
        Pressure_Median_psi=("Pressure (psi)", "median"),
        Pressure_Min_psi=("Pressure (psi)", "min"), Pressure_Max_psi=("Pressure (psi)", "max"),
        Pressure_Std_psi=("Pressure (psi)", "std"), Depth_Available=("Depth (m TVDSS)", "count"),
        Spud_Date_Proxies=("Flag · Spud date proxy", "sum"),
        Reliable_Date_Rows=("Date Reliable", "sum"),
        QC_Review_Rows=("QC Flag Count", lambda x: int((x > 0).sum()))).reset_index()
    num = out.select_dtypes(include="number").columns.difference([
        "Measurements", "Wells", "Depth_Available", "Spud_Date_Proxies", "Reliable_Date_Rows", "QC_Review_Rows"])
    out[num] = out[num].round(2)
    return out.sort_values("Measurements", ascending=False)


def trend_summary(df: pd.DataFrame, freq: str = "YS") -> pd.DataFrame:
    """Aggregate only actual/report-dated reservoir-related pressure points.

    Separate pressure measurement families so incompatible metrics are not combined.
    """
    t = df[df["Date Reliable"] & df["Pressure Family"].isin(RESERVOIR_FAMILIES)].copy()
    t = t.dropna(subset=["Date", "Pressure (psi)"])
    if t.empty:
        return pd.DataFrame(columns=["Period", "Pay Zone (Sand)", "Pressure Family", "N", "Median (psi)", "Mean (psi)"])
    t["Period"] = t["Date"].dt.to_period("M" if freq == "MS" else "Y").dt.to_timestamp()
    agg = t.groupby(["Period", "Pay Zone (Sand)", "Pressure Family"], dropna=False, observed=True).agg(
        N=("Pressure (psi)", "size"), **{"Median (psi)": ("Pressure (psi)", "median"),
                                     "Mean (psi)": ("Pressure (psi)", "mean")}).reset_index()
    return agg.sort_values("Period")


def calculate_trend_rates(df: pd.DataFrame, min_dates: int = 3) -> pd.DataFrame:
    """Exploratory rates only from reliable dates and same well/sand/pressure-family group.

    These are fitted observation slopes, NOT depletion forecasts or validated rates.
    """
    f = df[(df["Date Reliable"]) & (df["Pressure Family"].isin(RESERVOIR_FAMILIES))].dropna(subset=["Date", "Pressure (psi)"]).copy()
    rows = []
    for (well, sand, family), x in f.groupby(["Well Name", "Pay Zone (Sand)", "Pressure Family"], dropna=False):
        v = x.groupby("Date", as_index=False)["Pressure (psi)"].median().sort_values("Date")
        if len(v) < min_dates:
            continue
        t = (v["Date"] - v["Date"].min()).dt.total_seconds() / (365.25 * 86400)
        if float(t.max()) - float(t.min()) < 0.25:
            continue
        slope = float(np.polyfit(t, v["Pressure (psi)"], 1)[0])
        rows.append({"Well": well, "Sand": sand, "Pressure Family": family, "Unique Dates": len(v),
                     "First Date": v["Date"].min(), "Last Date": v["Date"].max(),
                     "Observation Slope (psi/year)": round(slope, 2),
                     "First Pressure (psi)": round(float(v["Pressure (psi)"].iloc[0]), 2),
                     "Last Pressure (psi)": round(float(v["Pressure (psi)"].iloc[-1]), 2)})
    return pd.DataFrame(rows)


def build_spotfire_zip(df: pd.DataFrame, group_keys: list[str]) -> bytes:
    if df.empty:
        raise ValueError("No filtered records to export.")
    dates = df.copy()
    dates["Date"] = pd.to_datetime(dates["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    dictionary = pd.DataFrame([
        ["date", "Reported date or spud proxy; consult date_basis", "YYYY-MM-DD"],
        ["date_basis", "Spud date proxy != actual pressure test date", "Text"],
        ["date_reliable", "True if a date exists and is not explicitly a spud proxy", "Boolean"],
        ["pressure_family", "Measurement taxonomy; do not combine WHP/BHP/RFT without justification", "Text"],
        ["pressure_psi", "Pressure in pounds per square inch", "psi"],
        ["pressure_ksc", "Pressure in kgf/cm²", "ksc"],
        ["depth_m_tvdss", "Depth below sea level, positive downward in source", "metre"],
        ["depth_quality", "Measured, Approximate, Surface, Unavailable, Unspecified", "Text"],
        ["apparent_p_depth_psi_ft", "P/depth ratio; NOT a fluid gradient", "psi/ft"],
        ["qc_flag_count", "Count of separate contextual and technical flags", "Count"],
    ], columns=["column", "meaning", "unit"])
    summary = group_summary(df, group_keys)
    annual = trend_summary(df, freq="YS")
    monthly = trend_summary(df, freq="MS")
    well = group_summary(df, ["Well Name", "Pay Zone (Sand)", "Pressure Family"])
    sand = group_summary(df, ["Formation", "Pay Zone (Sand)", "Pressure Family"])
    qc = qc_summary(df)
    slopes = calculate_trend_rates(df)
    files = {
        "Spotfire_Data_Long.csv": spotfire_long(df),
        "Spotfire_Summary_Custom.csv": summary,
        "Spotfire_Summary_Well_Sand.csv": well,
        "Spotfire_Summary_Sand_Type.csv": sand,
        "Spotfire_Trends_Annual_Reliable.csv": annual,
        "Spotfire_Trends_Monthly_Reliable.csv": monthly,
        "Spotfire_Observation_Slopes.csv": slopes,
        "Spotfire_QC_Summary.csv": qc,
        "Spotfire_Data_Dictionary.csv": dictionary,
    }
    guide = (
        "DAMAN PRESSURE INTELLIGENCE / SPOTFIRE EXPORT\n"
        "All exports reflect the current app filters, except that trend files deliberately exclude spud-date proxies.\n"
        "1) Import Spotfire_Data_Long.csv using Spotfire's text import; Date is ISO YYYY-MM-DD.\n"
        "2) Spotfire_Summary_*.csv = descriptive measurement summaries; do not assume family means are reservoir pressures.\n"
        "3) Use pressure_family as a mandatory grouping in comparisons.\n"
        "4) Spud-date proxy records have date_basis='Spud date proxy' and date_reliable=False.\n"
        "5) Depth is absent for surface measurements. Approx depths are interpreted interval midpoints.\n"
        "6) Observation slopes are exploratory unweighted linear fits, require >=3 dated events, and are NOT depletion forecasts.\n"
        "7) Apparent P/depth is NOT an actual fluid pressure gradient.\n"
        "8) QC status flags do NOT automatically imply invalid measurements.\n"
        "9) No deduplication or source value overwrite has been performed.\n"
        "10) Source File / Row ID allow trace-back to the uploaded dataset.\n"
    )
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, part in files.items():
            z.writestr(name, part.to_csv(index=False, encoding="utf-8-sig", date_format="%Y-%m-%d"))
        z.writestr("README_Spotfire_Import.txt", guide)
    return buf.getvalue()


def export_excel(df: pd.DataFrame, group_keys: list[str]) -> bytes:
    """Five worksheets for offline checks; not automatically persisted on the Streamlit host."""
    b = BytesIO()
    with pd.ExcelWriter(b, engine="xlsxwriter", datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as writer:
        sheets = {
            "Filtered_Data": df,
            "Spotfire_Long": spotfire_long(df),
            "Custom_Summary": group_summary(df, group_keys),
            "Well_Sand_Summary": group_summary(df, ["Well Name", "Pay Zone (Sand)", "Pressure Family"]),
            "QC_Summary": qc_summary(df),
            "Reliable_Trends": trend_summary(df),
        }
        for name, table in sheets.items():
            table.to_excel(writer, index=False, sheet_name=name)
            worksheet = writer.sheets[name]
            worksheet.freeze_panes(1, 0)
            worksheet.set_default_row(18)
            if len(table.columns):
                worksheet.autofilter(0, 0, max(1,len(table)), len(table.columns) - 1)
            worksheet.set_column(0, min(12, max(0, len(table.columns)-1)), 20)
    return b.getvalue()
