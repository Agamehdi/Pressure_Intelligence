"""Daman Pressure Intelligence — interactive Streamlit reservoir pressure workstation.

Run: streamlit run app.py
Public GitHub tip: do not commit private pressure datasets. Upload at runtime instead.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from data_engine import (
    FAMILY_DESCRIPTIONS, RESERVOIR_FAMILIES, PSI_PER_KSC,
    prepare_data, qc_summary, group_summary, trend_summary,
    calculate_trend_rates, spotfire_long, build_spotfire_zip, export_excel,
    make_synthetic_demo,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_PRIVATE_DATA = ROOT / "data" / "Daman_Pressure_Data_Compiled.xlsx"
DEMO_FILE = ROOT / "sample_data" / "synthetic_pressure_demo.csv"

PALETTES = {
    "Vibrant / Signature": ["#126BFF", "#FF623B", "#7F44F1", "#00BFA5", "#F63F81", "#F0A202", "#12A6DE", "#75C91C", "#445FDC", "#E85EED"],
    "Electric": ["#0051F9", "#FF3B7C", "#11D3C6", "#9F44F7", "#FFA31A", "#3B82F6", "#10B981", "#F75555"],
    "Ocean & Energy": ["#006CB8", "#20C5A7", "#F77F00", "#5E60CE", "#47B8E0", "#D81159", "#2A9D8F"],
    "Colorblind friendly": ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"],
    "Elegant / Corporate": ["#2446A6", "#23A6A6", "#E57A44", "#7854A8", "#94B43C", "#C84D7A", "#737F8B"],
}
GROUP_OPTIONS = ["Pay Zone (Sand)", "Pressure Family", "Well Name", "Formation", "Block / Area", "Field", "Depth Quality", "Date Basis", "QC Status"]
PLOT_FIELDS = ["Pressure (psi)", "Pressure (ksc)", "Depth (m TVDSS)", "Date", "Well Name", "Pay Zone (Sand)",
               "Pressure Family", "Pressure Type / Measurement", "Formation", "Block / Area", "Field",
               "Depth Quality", "QC Flag Count", "Unit Difference (%)", "Apparent P/depth (psi/ft)"]

st.set_page_config(
    page_title="Daman Pressure Intelligence | Reservoir Analytics",
    page_icon="💠", layout="wide", initial_sidebar_state="expanded"
)

CSS = """
<style>
:root {--ink:#13233C;--muted:#62748B;--blue:#126BFF;--line:#E5ECF5;--soft:#F5F8FD;}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {background:#FFFFFF !important;}
[data-testid="stHeader"] {background:rgba(255,255,255,.90) !important;}
[data-testid="stSidebar"] {background:#F8FAFF !important; border-right:1px solid #E5EDF7;}
[data-testid="stSidebar"] * {font-family:Inter, Aptos, 'Segoe UI', Arial, sans-serif;}
html, body, p, h1, h2, h3, h4, label, div, button {font-family:Inter, Aptos, 'Segoe UI', Arial, sans-serif;}
.block-container {padding-top:1.25rem; padding-bottom:3rem; max-width:1600px;}
.daman-hero {padding:23px 29px 21px;background:linear-gradient(110deg,#FFFFFF 0%,#F4F8FF 73%,#EDFAFF 100%);
  border:1px solid #E1ECFA;border-radius:20px;margin:0 0 19px;position:relative;overflow:hidden;}
.daman-hero::after {content:'';position:absolute;right:-90px;top:-120px;width:330px;height:330px;
  border-radius:50%;background:radial-gradient(circle,rgba(18,107,255,.11),rgba(18,107,255,0) 67%);}
.daman-kicker {font-size:11px;font-weight:900;letter-spacing:2.5px;color:#126BFF;margin-bottom:7px;}
.daman-title {font-size:34px;line-height:1.12;color:#152540;font-weight:900;letter-spacing:-.9px;}
.daman-sub {font-size:13px;color:#62748B;margin-top:9px;max-width:850px;line-height:1.65;}
.daman-chip {display:inline-flex;align-items:center;border-radius:99px;background:white;border:1px solid #DBE8F6;
   padding:5px 10px;font-size:10px;font-weight:800;color:#415873;margin-right:7px;margin-top:11px;}
.stTabs [data-baseweb="tab-list"] {gap:6px; padding:9px 2px 7px;overflow-x:auto;border-bottom:1px solid #E6EBF4;}
.stTabs [data-baseweb="tab"] {border:1px solid #E6EDF7;border-radius:12px 12px 9px 9px;background:#F7FAFE;
  padding:8px 14px;color:#53657A;white-space:nowrap;font-size:12px;font-weight:750;}
.stTabs [aria-selected="true"] {background:#EAF2FF !important;border-color:#BCD3FF !important;color:#0858CB !important;}
[data-testid="stMetric"] {padding:14px 17px 12px;border:1px solid #E7ECF4;border-radius:15px;
 background:linear-gradient(135deg,#FFFFFF,#F9FBFF);box-shadow:0 2px 8px rgba(30,65,113,.035);}
[data-testid="stMetricLabel"] {font-size:11px;color:#6B7F99;font-weight:700;letter-spacing:.3px;}
[data-testid="stMetricValue"] {font-size:27px;font-weight:900;color:#19345D;}
[data-testid="stMetricDelta"] {font-size:10px;}
[data-testid="stDataFrame"], [data-testid="stTable"] {border:1px solid #E8EDF5;border-radius:11px;}
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {
 background:linear-gradient(100deg,#126BFF,#4357D8);color:white;border:none;font-weight:800;border-radius:10px;}
div[data-testid="stExpander"] {border:1px solid #E7EDF5;border-radius:12px;background:#FCFDFF;}
.section-eyebrow {font-size:10px;letter-spacing:2px;font-weight:900;color:#1760D7;margin-top:17px;margin-bottom:6px;}
.section-title {font-size:21px;letter-spacing:-.4px;font-weight:850;color:#182D4D;margin-bottom:7px;}
.info-note {border-left:3px solid #3B88FF;background:#F2F7FF;padding:10px 13px;color:#415C7A;
 font-size:12px;line-height:1.6;border-radius:0 9px 9px 0;margin:11px 0 15px;}
.info-note.warn {border-left-color:#EA9715;background:#FFF9ED;color:#77552C;}
.small-label {color:#71839A;font-weight:700;font-size:11px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def section(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section-eyebrow">{kicker.upper()}</div><div class="section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


def note(text: str, warning: bool = False) -> None:
    st.markdown(f'<div class="info-note {"warn" if warning else ""}">{text}</div>', unsafe_allow_html=True)


def ensure_multiselect(key: str, options: list[str], default: list[str] | None = None) -> None:
    if key not in st.session_state:
        st.session_state[key] = [x for x in (default or []) if x in options]
    else:
        st.session_state[key] = [x for x in st.session_state[key] if x in options]


def ensure_select(key: str, options: list[str], default: str) -> None:
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]


def shorten_series_counts(data: pd.DataFrame, col: str, n: int = 16) -> pd.DataFrame:
    x = data.groupby(col, dropna=False, observed=True).size().nlargest(n).reset_index(name="Count")
    return x


@st.cache_data(show_spinner=False)
def read_bytes(raw: bytes, ext: str, selected_sheet: str | None) -> pd.DataFrame:
    if ext.lower().endswith("csv"):
        return pd.read_csv(BytesIO(raw), low_memory=False)
    return pd.read_excel(BytesIO(raw), sheet_name=selected_sheet or 0, engine="openpyxl")


@st.cache_data(show_spinner=False)
def read_sheetnames(raw: bytes) -> list[str]:
    with pd.ExcelFile(BytesIO(raw), engine="openpyxl") as f:
        return f.sheet_names


@st.cache_data(show_spinner=False)
def cleaned(raw: bytes, extension: str, sheetname: str | None, filename: str) -> pd.DataFrame:
    return prepare_data(read_bytes(raw, extension, sheetname), filename)


def style_fig(fig: go.Figure, cfg: dict, title: str = "", x_title: str | None = None,
              y_title: str | None = None, height: int | None = None) -> go.Figure:
    font = cfg["font"]
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(family=font, size=18, color="#1A2B48")),
        font=dict(family=font, size=cfg["font_size"], color="#364B68"),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        colorway=PALETTES[cfg["palette"]],
        height=height or cfg["height"],
        hovermode="closest", margin=dict(l=55, r=55, t=66 if title else 30, b=68),
        legend=dict(orientation="h", yanchor="top", y=-0.23, x=0, title_text="",
                    font=dict(size=max(10, cfg["font_size"] - 1)), bgcolor="rgba(255,255,255,0)"),
        transition_duration=150,
    )
    fig.update_xaxes(showgrid=cfg["grid"], gridcolor="#EBF0F7", zeroline=False,
                     linecolor="#D3DDE9", title_text=x_title)
    fig.update_yaxes(showgrid=cfg["grid"], gridcolor="#EBF0F7", zeroline=False,
                     linecolor="#D3DDE9", title_text=y_title)
    return fig


def showfig(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, key=f"fig_{key}", config={
        "displaylogo": False, "scrollZoom": True, "responsive": True,
        "toImageButtonOptions": {"format": "png", "filename": f"Daman_{key}", "scale": 2},
        "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
    })
    if st.session_state.get("enable_html", False):
        st.download_button("⇩ Export interactive HTML", fig.to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8"),
                           file_name=f"Daman_{key}.html", mime="text/html", key=f"html_{key}")


def render_dataframe(data: pd.DataFrame, key: str, height: int = 310, search: bool = False) -> None:
    if search:
        q = st.text_input("Search table (any visible column)", key=f"search_{key}")
        if q:
            mask = data.astype(str).apply(lambda c: c.str.contains(q, case=False, na=False, regex=False)).any(axis=1)
            data = data.loc[mask]
    st.dataframe(data, width="stretch", height=height, hide_index=True, key=f"table_{key}")


# ================ DATA & SIDEBAR ================
with st.sidebar:
    st.markdown("### 💠 Daman Intelligence")
    st.caption("Pressure analytics · technical QC · Spotfire-ready exports")
    st.markdown("#### 📂 Data source")
    uploaded = st.file_uploader("Upload pressure measurements", type=["xlsx", "xlsm", "csv"],
                                help="Excel and CSV with Well Name and pressure column(s).")
    using_demo = False
    if uploaded is not None:
        payload = uploaded.getvalue()
        suffix = Path(uploaded.name).suffix.lower()
        filename = uploaded.name
    elif DEFAULT_PRIVATE_DATA.exists():
        payload = DEFAULT_PRIVATE_DATA.read_bytes()
        filename, suffix = DEFAULT_PRIVATE_DATA.name, ".xlsx"
    else:
        # GitHub's web uploader can omit sample_data/ (or users may choose to
        # upload only app.py + data_engine.py). Never require a local demo file.
        # Keep the app usable by generating a deterministic demo in memory.
        try:
            if not DEMO_FILE.is_file():
                raise FileNotFoundError(f"Optional demo file absent: {DEMO_FILE}")
            payload = DEMO_FILE.read_bytes()
            filename = DEMO_FILE.name
        except OSError:
            payload = make_synthetic_demo().to_csv(index=False).encode("utf-8")
            filename = "built_in_synthetic_demo.csv"
        suffix = ".csv"
        using_demo = True
    sheet = None
    if suffix in (".xlsx", ".xlsm"):
        sheetnames = read_sheetnames(payload)
        sheet = st.selectbox("Worksheet", sheetnames)
    try:
        all_df = cleaned(payload, suffix, sheet, filename)
    except Exception as exc:
        st.error(f"Cannot load dataset: {exc}")
        st.info("Expected columns: Well Name, Pressure (psi) and/or Pressure (ksc); other Daman columns are optional.")
        st.stop()
    if using_demo:
        st.warning("SYNTHETIC DEMO data in use. Upload your actual workbook to analyze Daman measurements.")
    else:
        st.success(f"Loaded {len(all_df):,} measurements")

    st.divider()
    st.markdown("#### 🎛 Global filters")
    filters = {}
    for k, col in [("filter_field", "Field"), ("filter_formation", "Formation"),
                   ("filter_sand", "Pay Zone (Sand)"), ("filter_family", "Pressure Family"),
                   ("filter_area", "Block / Area"), ("filter_well", "Well Name")]:
        opts = sorted(all_df[col].dropna().astype(str).unique().tolist())
        ensure_multiselect(k, opts)
        st.multiselect(col, opts, key=k, placeholder="All (no restriction)")
        filters[col] = st.session_state[k]
    reliable_only = st.checkbox("Reliable dates only", value=False, help="Excludes spud-date proxies and missing date records from all charts and exports.")
    hide_critical = st.checkbox("Exclude critical QC records", value=False, help="Excludes pressure<=0 and unit mismatches >2%, no other QC flags.")
    depth_only = st.checkbox("Only rows with depth", value=False)

    min_dt = all_df["Date"].min()
    max_dt = all_df["Date"].max()
    if pd.notna(min_dt) and pd.notna(max_dt):
        lo, hi = min_dt.date(), max_dt.date()
        v = st.date_input("Measurement date window", value=(lo, hi), min_value=lo, max_value=hi,
                          help="For spud-date proxy rows, this limits the proxy year, NOT the actual test date.")
        if isinstance(v, (list, tuple)) and len(v) == 2:
            date_start, date_end = v
        else:
            date_start, date_end = lo, hi
    else:
        date_start, date_end = None, None

    st.divider()
    st.markdown("#### 🎨 Visualization studio settings")
    ensure_select("palette", list(PALETTES), "Vibrant / Signature")
    palette = st.selectbox("Palette", list(PALETTES), key="palette")
    ensure_select("color_group", GROUP_OPTIONS, "Pay Zone (Sand)")
    color_group = st.selectbox("Global color by", GROUP_OPTIONS, key="color_group")
    ensure_select("font_family", ["Inter", "Aptos", "Segoe UI", "Arial", "Calibri"], "Inter")
    font = st.selectbox("Chart font", ["Inter", "Aptos", "Segoe UI", "Arial", "Calibri"], key="font_family")
    fontsize = st.slider("Chart font size", 10, 18, 12, key="font_size")
    height = st.slider("Chart height (px)", 380, 760, 490, 10, key="plot_height")
    point_size = st.slider("Marker size", 5, 17, 9, key="marker_size")
    opacity = st.slider("Marker opacity", .25, 1.0, .86, .05, key="marker_opacity")
    grid = st.checkbox("Show plot grid", value=True, key="plot_grid")
    labels = st.checkbox("Show point labels", value=False, key="show_point_labels")
    st.checkbox("Enable HTML exports below plots", value=False, key="enable_html")

    st.divider()
    st.markdown("#### 💾 Save / load setup")
    config_upload = st.file_uploader("Load dashboard JSON", type=["json"], key="config_upload")
    if config_upload and st.button("Apply saved setup", width="stretch"):
        try:
            cfg_json = json.loads(config_upload.getvalue().decode("utf-8"))
            allowed = ["palette", "color_group", "font_family", "font_size", "plot_height", "marker_size",
                       "marker_opacity", "plot_grid", "show_point_labels", "enable_html", "filter_field",
                       "filter_formation", "filter_sand", "filter_family", "filter_area", "filter_well"]
            for key in allowed:
                if key in cfg_json:
                    st.session_state[key] = cfg_json[key]
            st.rerun()
        except (OSError, json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
            st.error(f"Invalid setup file: {exc}")
    cfg_keys = ["palette", "color_group", "font_family", "font_size", "plot_height", "marker_size",
                "marker_opacity", "plot_grid", "show_point_labels", "enable_html", "filter_field",
                "filter_formation", "filter_sand", "filter_family", "filter_area", "filter_well"]
    saved_settings = {k: st.session_state.get(k) for k in cfg_keys}
    st.download_button("Download dashboard setup.json", json.dumps(saved_settings, indent=2).encode("utf-8"),
                       file_name="Daman_Dashboard_Settings.json", mime="application/json", width="stretch")

cfg = dict(palette=palette, color=color_group, font=font, font_size=fontsize, height=height,
           size=point_size, opacity=opacity, grid=grid, labels=labels)
palette_colors = PALETTES[palette]

df = all_df.copy()
for col, selected in filters.items():
    if selected:
        df = df[df[col].isin(selected)]
if reliable_only:
    df = df[df["Date Reliable"]]
if hide_critical:
    df = df[df["QC Status"] != "Critical review"]
if depth_only:
    df = df[df["Depth (m TVDSS)"].notna()]
if date_start is not None and date_end is not None:
    is_full_window = pd.notna(min_dt) and pd.notna(max_dt) and date_start == min_dt.date() and date_end == max_dt.date()
    in_window = df["Date"].between(pd.Timestamp(date_start), pd.Timestamp(date_end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))
    df = df[in_window | (df["Date"].isna() if is_full_window else False)]
df = df.copy()

st.markdown('''<div class="daman-hero">
<div class="daman-kicker">RESERVOIR DATA INTELLIGENCE / ANALYTICS WORKSTATION</div>
<div class="daman-title">Daman Pressure Intelligence <span style="color:#126BFF">✦</span></div>
<div class="daman-sub">Explore pressure architecture, vertical distribution, time behaviour, well-level diagnostics, quality assurance and Spotfire-ready exports — with a clean white canvas and vibrant interactive visualization.</div>
<div><span class="daman-chip">✦ Pressure × Depth</span><span class="daman-chip">✦ Well & Sand Explorer</span><span class="daman-chip">✦ Time-Series Intelligence</span><span class="daman-chip">✦ Spotfire Integration</span></div>
</div>''', unsafe_allow_html=True)
if using_demo:
    st.warning("🧪 **Synthetic demonstration mode.** Metrics and plots shown here are artificial. Upload `Daman_Pressure_Data_Compiled.xlsx` in the sidebar to view real values.")
else:
    st.caption(f"Data source: **{filename}** · Rows in active filter: **{len(df):,}** / {len(all_df):,} · Source measurements are preserved and contextual QC flags are additive.")

if df.empty:
    st.warning("No records match the active filters. Relax one or more filters in the sidebar.")
    st.stop()

cols = st.columns(6)
all_press = df["Pressure (psi)"].dropna()
cardvals = [
    ("MEASUREMENTS", f"{len(df):,}"), ("WELLS", f"{df['Well Name'].nunique():,}"),
    ("SAND INTERVALS", f"{df.loc[df['Pay Zone (Sand)']!='Not specified', 'Pay Zone (Sand)'].nunique():,}"),
    ("MEDIAN PRESSURE", f"{all_press.median():,.0f} psi" if len(all_press) else "—"),
    ("DEPTH COVERAGE", f"{df['Depth (m TVDSS)'].notna().mean():.0%}"),
    ("DATE PROXIES", f"{df['Flag · Spud date proxy'].sum():,}"),
]
for i, (label, value) in enumerate(cardvals):
    cols[i].metric(label, value)

st.markdown(" ")
main_tabs = st.tabs([
    "📍 Overview", "📐 Pressure & Depth", "📈 Time Trends", "🛢️ Well Explorer",
    "📊 Analytics Lab", "🎛 Visualization Studio", "🧪 Data Quality", "📤 Spotfire / Export",
])

# ================ OVERVIEW ================
with main_tabs[0]:
    section("Field intelligence", "Data portfolio at a glance", "Pressure measurements and their contexts, based on the currently filtered dataset.")
    c1, c2 = st.columns([1.06, .94])
    with c1:
        d = shorten_series_counts(df, "Pay Zone (Sand)")
        f = px.bar(d, x="Pay Zone (Sand)", y="Count", color="Pay Zone (Sand)",
                   color_discrete_sequence=palette_colors, text="Count")
        f.update_traces(textposition="outside", cliponaxis=False)
        showfig(style_fig(f, cfg, "Measurements by pay sand", "Pay zone", "Count"), "overview_sand")
    with c2:
        d = shorten_series_counts(df, "Pressure Family")
        f = px.pie(d, values="Count", names="Pressure Family", hole=.63,
                   color_discrete_sequence=palette_colors)
        f.update_traces(textposition="outside", textinfo="percent", textfont_size=11,
                        marker=dict(line=dict(color="white", width=2)))
        showfig(style_fig(f, cfg, "Pressure measurement taxonomy"), "overview_family")
    c1, c2 = st.columns([1, 1])
    with c1:
        d = df.dropna(subset=["Pressure (psi)"])
        fig = px.box(d, x="Pressure Family", y="Pressure (psi)", color="Pressure Family",
                     points="outliers", color_discrete_sequence=palette_colors)
        fig.update_xaxes(tickangle=-35)
        showfig(style_fig(fig, cfg, "Pressure distributions by measurement family", "Measurement family", "Pressure (psi)"), "overview_box")
    with c2:
        y = df.groupby(["Pay Zone (Sand)", "Pressure Family"], observed=True).size().unstack(fill_value=0)
        fig = px.imshow(y, color_continuous_scale="Turbo", text_auto=True, aspect="auto",
                        labels={"x": "Pressure family", "y": "Pay zone", "color": "Count"})
        fig.update_xaxes(tickangle=-25)
        showfig(style_fig(fig, cfg, "Sand × pressure-type coverage", "Pressure family", "Pay zone"), "overview_heat")
    note("<b>Interpretation:</b> The global median above is descriptive across mixed pressure types. It is <b>not</b> a field reservoir-pressure estimate. Separate wellhead, flowing and static/formation pressures for interpretation.", warning=True)
    section("Latest measurements", "Observation register")
    latest = df[df["Date Reliable"]].dropna(subset=["Date"]).sort_values("Date", ascending=False)
    fields = ["Date", "Well Name", "Pay Zone (Sand)", "Pressure Family", "Pressure (psi)",
              "Depth (m TVDSS)", "Depth Quality", "QC Status"]
    render_dataframe(latest[fields].head(30), "latest", height=280)

# ================ PRESSURE-DEPTH ================
with main_tabs[1]:
    section("Reservoir geometry", "Pressure vs vertical depth", "Depth is positive TVDSS below sea level; vertical axis increases downwards.")
    p1, p2, p3, p4 = st.columns([1.5, 1, 1, 1])
    with p1:
        fams = sorted(df["Pressure Family"].unique())
        defaults = [x for x in RESERVOIR_FAMILIES if x in fams]
        ensure_multiselect("depth_families", fams, defaults)
        selected_families = st.multiselect("Pressure families", fams, key="depth_families")
    with p2:
        x_unit = st.selectbox("X-axis unit", ["Pressure (psi)", "Pressure (ksc)"], key="depth_punit")
    with p3:
        overlay_fit = st.checkbox("Exploratory fit by sand", value=False)
    with p4:
        only_measured = st.checkbox("Measured-depth only", value=False)
    d = df[df["Pressure Family"].isin(selected_families)].dropna(subset=["Depth (m TVDSS)", x_unit]).copy()
    if only_measured:
        d = d[d["Depth Quality"] == "Measured"]
    if len(d):
        fig = px.scatter(d, x=x_unit, y="Depth (m TVDSS)", color=color_group,
                         symbol="Pressure Family", color_discrete_sequence=palette_colors,
                         text="Well Name" if labels else None,
                         hover_name="Well Name",
                         hover_data={"Pay Zone (Sand)": True, "Date": True,
                                     "Pressure Family": True, "Depth Quality": True,
                                     "Date Basis": True, "Pressure Type / Measurement": True,
                                     "Remarks": False, "Row ID": True})
        fig.update_traces(marker=dict(size=cfg["size"], opacity=cfg["opacity"], line=dict(width=.75, color="#FFFFFF")),
                          mode="markers+text" if labels else "markers", textposition="top center")
        if overlay_fit:
            lines = []
            for sand, g in d.groupby("Pay Zone (Sand)"):
                g = g.dropna(subset=["Depth (m TVDSS)", x_unit])
                if len(g) < 4 or g["Depth (m TVDSS)"].nunique() < 3:
                    continue
                xx = g["Depth (m TVDSS)"].to_numpy(float)
                yy = g[x_unit].to_numpy(float)
                slope, intercept = np.polyfit(xx, yy, 1)
                grid_depth = np.linspace(xx.min(), xx.max(), 35)
                fig.add_trace(go.Scatter(x=slope*grid_depth+intercept, y=grid_depth,
                              mode="lines", name=f"{sand} exploratory fit", line=dict(width=2, dash="dash")))
                lines.append({"Sand": sand, "Points": len(g), "Slope (psi/m)" if x_unit.endswith("psi)") else "Slope (ksc/m)": round(slope, 3)})
            if lines:
                with st.expander("See exploratory regressions and limitations"):
                    st.dataframe(pd.DataFrame(lines), hide_index=True, width="stretch")
                    st.warning("Cross-sectional depth fits combine wells and potentially different years/types. They are not validated pressure gradients or water contacts.")
        fig.update_yaxes(autorange="reversed")
        showfig(style_fig(fig, cfg, "Daman | Vertical pressure architecture", x_unit, "Depth (m TVDSS) — increasing downward", height=max(540, height)), "depth_scatter")
        d2 = d.copy()
        d2["Approx. P/depth (psi/ft)"] = d2["Apparent P/depth (psi/ft)"]
        c1, c2 = st.columns(2)
        with c1:
            f2 = px.box(d2, x="Pay Zone (Sand)", y=x_unit, color="Pay Zone (Sand)",
                        color_discrete_sequence=palette_colors, points="outliers")
            showfig(style_fig(f2, cfg, "Pressure spread across sand intervals", "Pay zone", x_unit), "depth_sand_box")
        with c2:
            q = d2.groupby("Depth Quality", observed=True).size().reset_index(name="Count")
            f3 = px.bar(q, x="Depth Quality", y="Count", color="Depth Quality",
                        color_discrete_sequence=palette_colors, text="Count")
            showfig(style_fig(f3, cfg, "Depth provenance", "Depth quality", "Count"), "depth_quality")
    else:
        st.info("No downhole points match these filters. Adjust the pressure-family or depth-quality options.")
    note("Measured depth and interval-midpoint estimates are distinguished by <b>Depth Quality</b>. Surface pressure points are not assigned fabricated downhole depths. The displayed P/depth proxy is <b>not</b> a fluid pressure gradient.", warning=True)

# ================ TIME SERIES ================
with main_tabs[2]:
    section("Chronology", "Pressure evolution through time", "Reliable-date points are preferred; an actual pressure-test date is required for defensible depletion analysis.")
    t1, t2, t3, t4 = st.columns([1.4, 1, 1, 1])
    with t1:
        allfam = sorted(df["Pressure Family"].unique())
        ensure_multiselect("trend_fam", allfam, [x for x in RESERVOIR_FAMILIES if x in allfam])
        fam = st.multiselect("Pressure families", allfam, key="trend_fam")
    with t2:
        use_proxies = st.checkbox("Allow spud-date proxies", value=False, help="Enable only for illustrative context, not for chronological interpretation.")
    with t3:
        period = st.selectbox("Summary period", ["Year", "Month", "Raw observations"], key="trend_period")
    with t4:
        show_raw = st.checkbox("Show individual events", value=True)
    td = df[df["Pressure Family"].isin(fam)].dropna(subset=["Date", "Pressure (psi)"]).copy()
    if not use_proxies:
        td = td[td["Date Reliable"]]
    if td.empty:
        st.info("No dated observations are available in the selected pressure families.")
    else:
        td["Series"] = td["Pay Zone (Sand)"].astype(str) + " · " + td["Pressure Family"].astype(str)
        fig = go.Figure()
        groups = sorted(td["Series"].unique())
        for i, group in enumerate(groups):
            chunk = td[td["Series"] == group].sort_values("Date")
            color = palette_colors[i % len(palette_colors)]
            if period == "Raw observations":
                agg = chunk.groupby("Date", as_index=False)["Pressure (psi)"].median()
                agg["Count"] = chunk.groupby("Date").size().values
            else:
                freq = "M" if period == "Month" else "Y"
                chunk = chunk.copy()
                chunk["Period"] = chunk["Date"].dt.to_period(freq).dt.to_timestamp()
                agg = chunk.groupby("Period", as_index=False).agg(**{
                    "Pressure (psi)": ("Pressure (psi)", "median"), "Count": ("Pressure (psi)", "size")})
                agg = agg.rename(columns={"Period": "Date"})
            fig.add_trace(go.Scatter(x=agg["Date"], y=agg["Pressure (psi)"], mode="lines+markers",
                name=group, line=dict(color=color, width=2.5), marker=dict(size=7),
                customdata=np.column_stack([agg["Count"]]),
                hovertemplate="%{x|%Y-%m-%d}<br>Median: %{y:,.1f} psi<br>N: %{customdata[0]}<extra>%{fullData.name}</extra>"))
            if show_raw and period != "Raw observations":
                fig.add_trace(go.Scatter(x=chunk["Date"], y=chunk["Pressure (psi)"], mode="markers",
                    marker=dict(color=color, size=7, opacity=.33), showlegend=False,
                    name=group + " raw", hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.1f} psi<extra></extra>"))
        showfig(style_fig(fig, cfg, "Pressure observations | Sand + measurement family", "Date / year", "Pressure (psi)", height=max(540, height)), "time_pressure")
        if use_proxies:
            note("<b>Spud-date proxies are enabled.</b> They represent a well spud date, not necessarily a DST test date. Apparent trends can be misleading.", warning=True)
        else:
            note("Rows explicitly marked as spud-date proxies have been excluded from this chart. Summary lines are medians of individual measurements, not validated average reservoir pressures.")
        c1, c2 = st.columns([1.06, .94])
        with c1:
            st.markdown("**Observations by year and source-date quality**")
            cy = df.dropna(subset=["Date"]).copy()
            cy["Year"] = cy["Date"].dt.year.astype(str)
            counts = cy.groupby(["Year", "Date Basis"], observed=True).size().reset_index(name="Count")
            fig = px.bar(counts, x="Year", y="Count", color="Date Basis", barmode="stack",
                          color_discrete_sequence=palette_colors)
            showfig(style_fig(fig, cfg, "Dating confidence overview", "Year assigned in source", "Measurements"), "time_confidence")
        with c2:
            st.markdown("**Exploratory within-well rates (if eligible)**")
            rates = calculate_trend_rates(td)
            if not rates.empty:
                render_dataframe(rates.sort_values("Observation Slope (psi/year)"), "trend_rates", height=340)
            else:
                st.info("Insufficient measurements: need ≥3 distinct reliable dates spanning ≥0.25 years within each well + sand + pressure family.")
        note("A slope calculated from sparse historical observations is a descriptive regression, <b>not a depletion forecast</b>. Interpret only after checking gauge type, test conditions, completion and sand consistency.", warning=True)

# ================ WELL EXPLORER ================
with main_tabs[3]:
    section("Well diagnostics", "Well-by-well intelligence", "Compare several wells while keeping sand intervals and pressure-measurement contexts visible.")
    wellcounts = df["Well Name"].value_counts()
    well_options = wellcounts.index.tolist()
    ensure_multiselect("selected_wells_detail", well_options, well_options[:3])
    selected_wells = st.multiselect("Select wells to compare", well_options,
                                    key="selected_wells_detail", max_selections=12)
    if selected_wells:
        wd = df[df["Well Name"].isin(selected_wells)].copy()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Selected wells", str(len(selected_wells)))
        c2.metric("Measurements", str(len(wd)))
        c3.metric("Downhole depths", str(wd["Depth (m TVDSS)"].notna().sum()))
        c4.metric("Reported dates", str(wd["Date Reliable"].sum()))
        c1, c2 = st.columns(2)
        with c1:
            vd = wd.dropna(subset=["Depth (m TVDSS)", "Pressure (psi)"])
            if not vd.empty:
                fig = px.scatter(vd, x="Pressure (psi)", y="Depth (m TVDSS)", color="Well Name",
                                 symbol="Pressure Family", color_discrete_sequence=palette_colors,
                                 hover_data=["Pay Zone (Sand)", "Depth Quality", "Date Basis"])
                fig.update_traces(marker=dict(size=cfg["size"], opacity=cfg["opacity"]))
                fig.update_yaxes(autorange="reversed")
                showfig(style_fig(fig, cfg, "Selected wells | Pressure vs depth", "Pressure (psi)", "Depth (m TVDSS)"), "wells_depth")
            else:
                st.info("No depth values for the selected wells.")
        with c2:
            ts = wd.dropna(subset=["Date", "Pressure (psi)"])
            ts = ts[ts["Date Reliable"]]
            if not ts.empty:
                fig = px.scatter(ts.sort_values("Date"), x="Date", y="Pressure (psi)", color="Well Name",
                                 symbol="Pressure Family", color_discrete_sequence=palette_colors,
                                 hover_data=["Pay Zone (Sand)", "Pressure Type / Measurement"])
                fig.update_traces(marker=dict(size=cfg["size"]+1, opacity=cfg["opacity"]))
                showfig(style_fig(fig, cfg, "Dated pressure observations by well", "Reported date", "Pressure (psi)"), "wells_time")
            else:
                st.info("No reliable dated observations for these wells.")
        section("Quick comparison", "Well × sand measurement matrix")
        tbl = wd.groupby(["Well Name", "Pay Zone (Sand)", "Pressure Family"], observed=True).agg(
            N=("Pressure (psi)", "count"), Median_psi=("Pressure (psi)", "median"),
            Depth_n=("Depth (m TVDSS)", "count"), Reliable_dates=("Date Reliable", "sum")
        ).reset_index().sort_values(["Well Name", "Pay Zone (Sand)"])
        render_dataframe(tbl.round(2), "wellsummary", height=320)
        with st.expander("View all original measurements for selected wells"):
            render_dataframe(wd[["Well Name", "Date", "Pay Zone (Sand)", "Pressure Family",
                                 "Pressure (psi)", "Depth (m TVDSS)", "Depth Quality", "Date Basis",
                                 "QC Status", "Remarks"]], "wellraw", height=410, search=True)
    else:
        st.info("Select at least one well above.")

# ================ ANALYTICS LAB ================
with main_tabs[4]:
    section("Descriptive analytics", "Pressure statistics and exploration", "Use comparable categories and review group sample sizes before interpreting differences.")
    a1, a2, a3 = st.columns(3)
    with a1:
        stat_group = st.selectbox("Group statistics by", ["Pay Zone (Sand)", "Pressure Family", "Well Name", "Formation", "Block / Area"])
    with a2:
        stat_family = st.multiselect("Limit statistical sample", sorted(df["Pressure Family"].unique()),
                                    default=[x for x in RESERVOIR_FAMILIES if x in df["Pressure Family"].unique()],
                                    key="stats_family")
    with a3:
        pmetric = st.selectbox("Pressure unit", ["Pressure (psi)", "Pressure (ksc)"], key="stats_metric")
    subset = df[df["Pressure Family"].isin(stat_family)].dropna(subset=[pmetric]).copy()
    if subset.empty:
        st.info("No measurements in the chosen pressure families.")
    else:
        q1, q2 = st.columns(2)
        with q1:
            fig = px.violin(subset, x=stat_group, y=pmetric, color=stat_group, box=True, points="outliers",
                            color_discrete_sequence=palette_colors)
            if subset[stat_group].nunique() > 15:
                fig.update_xaxes(categoryorder="total descending")
            fig.update_xaxes(tickangle=-35)
            showfig(style_fig(fig, cfg, "Distribution and variability", stat_group, pmetric), "analytics_violin")
        with q2:
            fig = px.histogram(subset, x=pmetric, color="Pressure Family", nbins=30, marginal="box",
                               color_discrete_sequence=palette_colors, opacity=.75, barmode="overlay")
            showfig(style_fig(fig, cfg, "Pressure frequency distribution", pmetric, "Count"), "analytics_hist")
        q1, q2 = st.columns([1, 1])
        with q1:
            if subset["Depth (m TVDSS)"].notna().sum() >= 3:
                fig = px.scatter(subset.dropna(subset=["Depth (m TVDSS)"]), x="Depth (m TVDSS)", y=pmetric,
                                 color=stat_group, color_discrete_sequence=palette_colors,
                                 hover_name="Well Name", opacity=cfg["opacity"])
                fig.update_traces(marker=dict(size=cfg["size"]))
                showfig(style_fig(fig, cfg, "Pressure × depth correlation (descriptive)", "Depth (m TVDSS)", pmetric), "analytics_cross")
            else:
                st.info("At least 3 depth/pressure pairs needed for crossplot.")
        with q2:
            pivot = subset.groupby(stat_group, observed=True)[pmetric].agg(["count", "median", "mean", "std", "min", "max"]).round(2).reset_index()
            pivot = pivot.sort_values("count", ascending=False)
            st.markdown("**Statistics by selected grouping**")
            render_dataframe(pivot, "analytics_stats", height=380)
        section("Distribution quality", "Within-group outlier screening")
        st.caption("IQR rule (1.5 × interquartile range) only for groups with at least 5 values; screening is not a reason for automatic deletion.")
        out_rows = []
        for (sand, family), g in subset.groupby(["Pay Zone (Sand)", "Pressure Family"], observed=True):
            if len(g) < 5:
                continue
            q25, q75 = g[pmetric].quantile([.25, .75])
            iqr = q75 - q25
            if iqr == 0:
                continue
            x = g[(g[pmetric] < q25 - 1.5*iqr) | (g[pmetric] > q75 + 1.5*iqr)]
            for _, r in x.iterrows():
                out_rows.append({"Well": r["Well Name"], "Sand": sand, "Family": family,
                                 "Value": round(float(r[pmetric]), 2), "Date": r["Date"],
                                 "Row ID": r["Row ID"]})
        if out_rows:
            render_dataframe(pd.DataFrame(out_rows), "iqr_outliers", height=265)
        else:
            st.success("No IQR screen hits among groups with ≥5 measurements in the active sample.")

# ================ VISUALIZATION STUDIO ================
with main_tabs[5]:
    section("Build your own chart", "Interactive Visualization Studio", "Choose dimensions, plot types, fonts, colours, labels and a second pressure-unit axis.")
    choices = [x for x in PLOT_FIELDS if x in df.columns]
    r1, r2, r3, r4 = st.columns([1, 1, 1, 1])
    with r1:
        kind = st.selectbox("Chart type", ["Scatter / Bubble", "Line", "Bar (median)", "Box", "Violin", "Histogram", "ECDF", "2D density heatmap", "3D scatter"])
    with r2:
        ensure_select("studio_x", choices, "Depth (m TVDSS)")
        sx = st.selectbox("X-axis", choices, key="studio_x")
    with r3:
        ensure_select("studio_y", choices, "Pressure (psi)")
        sy = st.selectbox("Y-axis", choices, key="studio_y")
    with r4:
        ensure_select("studio_color", GROUP_OPTIONS, "Pay Zone (Sand)")
        sc = st.selectbox("Color by", GROUP_OPTIONS, key="studio_color")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        custom_title = st.text_input("Chart title", value="Custom Daman pressure visualization")
    with b2:
        facet = st.selectbox("Facet by", ["None", "Pressure Family", "Pay Zone (Sand)", "Formation", "Field"])
    with b3:
        show_2axis = st.checkbox("Secondary pressure-unit axis", value=False,
                                 help="Adds a right-side equivalent ksc/psi scale without plotting additional data.")
    with b4:
        invert_depth = st.checkbox("Depth axis positive down", value=True)
    k = df.dropna(subset=[sx] + ([sy] if kind not in ["Histogram", "ECDF"] else [])).copy()
    if len(k):
        kwargs = dict(color=sc, color_discrete_sequence=palette_colors)
        fac = None if facet == "None" else facet
        if fac and k[fac].nunique() > 8:
            st.warning("More than 8 facet categories: only the 8 most frequent will be displayed.")
            k = k[k[fac].isin(k[fac].value_counts().head(8).index)]
        if fac:
            kwargs["facet_col"] = fac
            kwargs["facet_col_wrap"] = 3
        y_has_numeric = sy in k.columns and pd.api.types.is_numeric_dtype(k[sy])
        if kind in ["Scatter / Bubble", "Line", "3D scatter", "2D density heatmap", "Bar (median)"] and not y_has_numeric:
            st.warning("Choose a numeric Y-axis for this chart type.")
        else:
            if kind == "Scatter / Bubble":
                valid_sizes = ["None", "Pressure (psi)", "Pressure (ksc)", "Depth (m TVDSS)", "QC Flag Count"]
                bubble_size = st.selectbox("Bubble size", valid_sizes, key="studio_bubble")
                if bubble_size != "None":
                    # Plotly Express requires size >=0 and numeric.
                    k["Bubble radius"] = pd.to_numeric(k[bubble_size], errors="coerce").clip(lower=0).fillna(0) + 1
                fig = px.scatter(k, x=sx, y=sy, size="Bubble radius" if bubble_size != "None" else None,
                                 hover_name="Well Name", text="Well Name" if labels and len(k) <= 120 else None,
                                 hover_data=["Pressure Family", "Date Basis", "QC Status"],
                                 **kwargs)
                fig.update_traces(marker=dict(opacity=cfg["opacity"], line=dict(width=.5, color="white")))
            elif kind == "Line":
                k = k.sort_values(sx)
                fig = px.line(k, x=sx, y=sy, markers=True, **kwargs)
            elif kind == "Bar (median)":
                grouping = [sx, sc] + ([fac] if fac and fac not in [sx, sc] else [])
                kagg = k.groupby(grouping, dropna=False, observed=True)[sy].median().reset_index()
                fig = px.bar(kagg, x=sx, y=sy, barmode="group", **kwargs)
            elif kind == "Box":
                fig = px.box(k, x=sx, y=sy, points="outliers", **kwargs)
            elif kind == "Violin":
                fig = px.violin(k, x=sx, y=sy, box=True, points="outliers", **kwargs)
            elif kind == "Histogram":
                bins = st.slider("Histogram bins", min_value=8, max_value=90, value=25)
                fig = px.histogram(k, x=sx, nbins=bins, barmode="overlay", opacity=.75, **kwargs)
            elif kind == "ECDF":
                fig = px.ecdf(k, x=sx, **kwargs)
            elif kind == "2D density heatmap":
                fig = px.density_heatmap(k, x=sx, y=sy, nbinsx=35, nbinsy=35,
                                         color_continuous_scale="Turbo")
            else:
                zopts = [c for c in ["Depth (m TVDSS)", "Pressure (psi)", "Pressure (ksc)",
                                         "QC Flag Count", "Unit Difference (%)"] if c not in [sx, sy]]
                zfield = st.selectbox("3D Z-axis", zopts) if zopts else sy
                k = k.dropna(subset=[zfield])
                fig = px.scatter_3d(k, x=sx, y=sy, z=zfield, hover_name="Well Name",
                                    color=sc, color_discrete_sequence=palette_colors)
                fig.update_traces(marker=dict(size=5, opacity=cfg["opacity"]))
            fig = style_fig(fig, cfg, custom_title, sx, sy, height=max(570, height))
            if invert_depth and kind not in ["3D scatter"]:
                if sx == "Depth (m TVDSS)":
                    fig.update_xaxes(autorange="reversed")
                if sy == "Depth (m TVDSS)":
                    fig.update_yaxes(autorange="reversed")
            if labels and kind == "Scatter / Bubble":
                if len(k) <= 120:
                    fig.update_traces(mode="markers+text", textposition="top center")
                else:
                    st.caption("Point labels are hidden for >120 marks to avoid overcrowding; hover to see the well name.")
            if show_2axis:
                if kind in ["Scatter / Bubble", "Line", "Bar (median)", "Box", "Violin", "2D density heatmap"] and sy in ["Pressure (psi)", "Pressure (ksc)"]:
                    equivalence = 1 / PSI_PER_KSC if sy == "Pressure (psi)" else PSI_PER_KSC
                    yy = pd.to_numeric(k[sy], errors="coerce").dropna()
                    if not yy.empty:
                        v0, v1 = float(yy.min()), float(yy.max())
                        extra = max((v1 - v0) * .06, abs(v1) * .015, 1)
                        fig.update_yaxes(range=[v0-extra, v1+extra])
                        fig.update_layout(yaxis2=dict(
                            title=dict(text="Pressure (ksc)" if sy == "Pressure (psi)" else "Pressure (psi)",
                                       font=dict(color="#7057C8")),
                            overlaying="y", side="right", showgrid=False, zeroline=False,
                            range=[(v0-extra)*equivalence, (v1+extra)*equivalence],
                            tickfont=dict(color="#7057C8")))
                else:
                    st.info("Equivalent right-axis scale is available only if Y is pressure (psi) or ksc for 2D charts.")
            showfig(fig, "studio_custom")
            if kind == "Line":
                note("Connecting mixed-well, mixed-family or spud-date observations can create artificial trajectories. For true pressure decline, filter to one well + sand + comparable family and reliable dates.", warning=True)
    else:
        st.info("The chosen X/Y combination has no non-null observations.")

# ================ DATA QUALITY ================
with main_tabs[6]:
    section("Quality assurance", "Transparent QC and provenance", "Flags document limitations. A flag is not automatic evidence that a measurement is incorrect.")
    q = qc_summary(df)
    a, b, c, d = st.columns(4)
    a.metric("Missing depths", f"{df['Flag · Missing depth'].sum():,}")
    b.metric("Approximate depths", f"{df['Flag · Approx depth'].sum():,}")
    c.metric("Spud-date proxies", f"{df['Flag · Spud date proxy'].sum():,}")
    d.metric("Unit mismatches >2%", f"{df['Flag · Unit mismatch'].sum():,}")
    c1, c2 = st.columns([1.06, .94])
    with c1:
        f = px.bar(q.sort_values("Affected Rows"), x="Affected Rows", y="QC Check", orientation="h",
                   text="Affected Rows", color="Share (%)", color_continuous_scale="Turbo")
        f.update_traces(textposition="outside", cliponaxis=False)
        showfig(style_fig(f, cfg, "QC coverage | Filtered data", "Flagged rows", "QC rule", height=max(520, height)), "qc_flags")
    with c2:
        quality = df.groupby("QC Status", observed=True).size().reset_index(name="Count")
        f = px.pie(quality, values="Count", names="QC Status", hole=.64,
                   color_discrete_sequence=palette_colors)
        f.update_traces(marker=dict(line=dict(color="white", width=2)))
        showfig(style_fig(f, cfg, "QC status distribution"), "qc_status")
    st.markdown("**QC rules and affected rows**")
    render_dataframe(q, "qc_rules", height=330)
    flags = [col for col in df if col.startswith("Flag ·")]
    fl = st.selectbox("Inspect flagged records", flags)
    n = df[df[fl]].copy()
    st.caption(f"**{len(n)}** rows match this rule.")
    show_fields = ["Row ID", "Well Name", "Pay Zone (Sand)", "Date", "Date Basis", "Pressure Family",
                   "Pressure (psi)", "Pressure (ksc)", "Unit Difference (%)", "Depth (m TVDSS)",
                   "Depth Quality", "Depth Note", "Remarks", "QC Status"]
    render_dataframe(n[show_fields], "qc_records", height=370, search=True)
    note("<b>Unit check:</b> ksc is kgf/cm², 1 ksc ≈ 14.223343 psi; a discrepancy beyond 2% is flagged. <b>Date check:</b> records explicitly described as using well spud date are not treated as dated pressure tests.")

# ================ EXPORT ================
with main_tabs[7]:
    section("Interoperability", "Spotfire / Excel data packages", "Flat, analysis-ready CSV data; separate descriptive summary tables; transparent audit fields.")
    e1, e2, e3 = st.columns(3)
    with e1:
        export_groups = st.multiselect("Summary dimensions", ["Field", "Formation", "Pay Zone (Sand)", "Pressure Family",
                                                      "Well Name", "Block / Area", "Depth Quality", "Date Basis"],
                                      default=["Pay Zone (Sand)", "Pressure Family"], key="spotfire_group")
    with e2:
        include_source = st.checkbox("Include original source columns", value=True)
    with e3:
        st.metric("Rows included in export", f"{len(df):,}")
    summary = group_summary(df, export_groups)
    section("Preview", "Spotfire summary — active groups")
    render_dataframe(summary, "export_summary", height=390)
    data_to_export = df if include_source else df.drop(columns=["Depth Note", "Tested Interval / Choke", "Remarks", "Source Tab"], errors="ignore")
    st.markdown(" ")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇ Download Spotfire ZIP", build_spotfire_zip(data_to_export, export_groups),
                           file_name="Daman_Spotfire_Export.zip", mime="application/zip",
                           type="primary", width="stretch")
        st.caption("9 CSV outputs + import notes; includes annual/monthly reliable-date trends.")
    with c2:
        st.download_button("⬇ Download formatted Excel", export_excel(data_to_export, export_groups),
                           file_name="Daman_Analysis_Export.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        st.caption("6 worksheets: filtered data, Spotfire long, summary, wells, QC, reliable trends.")
    with c3:
        st.download_button("⬇ Download filtered CSV", spotfire_long(data_to_export).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                           file_name="Daman_Filtered_Long.csv", mime="text/csv", width="stretch")
        st.caption("One flat table with clean Spotfire headers, ISO dates and contextual flags.")
    st.markdown(" ")
    section("Pre-built summaries", "Ready for Spotfire import")
    rr1, rr2 = st.columns(2)
    with rr1:
        st.markdown("**Well × Sand × Pressure Family**")
        render_dataframe(group_summary(df, ["Well Name", "Pay Zone (Sand)", "Pressure Family"]).head(60), "export_well_sand", height=370)
    with rr2:
        st.markdown("**Year × Sand × Pressure Family (reliable-date only)**")
        render_dataframe(trend_summary(df).head(80), "export_period", height=370)
    note("<b>Export semantics:</b> All outputs respect the sidebar filters. Trend CSVs always exclude spud-date proxies, irrespective of whether a proxy date is visible elsewhere. Summaries are descriptive aggregations of heterogeneous test types; they are not field-average reservoir pressure estimates.", warning=True)

st.markdown("---")
st.caption("Daman Pressure Intelligence · Streamlit + Plotly · White edition · Source values are not overwritten · Made for engineering interpretation, QC, and Spotfire handoff")
