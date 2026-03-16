# Fail-safe: if Altair isn't available, don't crash the app
try:
    import altair as alt  # noqa: F401
except Exception:
    import streamlit as st
    st.warning("Altair is not installed; charts will use Streamlit's basic charting.")

import io
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date

# =========================
# Helpers (CSV builders)
# =========================
def build_kpi_summary_csv(df: pd.DataFrame) -> bytes:
    """Return a CSV (bytes) with the KPIs currently shown in the app."""
    now = pd.Timestamp.utcnow()
    tmp = df.copy()
    tmp["Resolved"] = tmp["ClosedAt"].notna()
    tmp["DurationHours"] = ((tmp["ClosedAt"].fillna(now) - tmp["CreatedAt"])
                            .dt.total_seconds() / 3600).round(2)

    avg_proc = tmp.loc[tmp["Resolved"], "DurationHours"].mean()
    sla_pct  = 100 * ((tmp.loc[tmp["Resolved"], "DurationHours"]
                       <= tmp.loc[tmp["Resolved"], "SLA_Hours"]).mean())
    open_cnt = int((~tmp["Resolved"]).sum())

    summary = pd.DataFrame([{
        "AvgProcessingHours": round(float(avg_proc), 2) if pd.notna(avg_proc) else None,
        "SLACompliancePct":   round(float(sla_pct),  2) if pd.notna(sla_pct)  else None,
        "OpenClaims":         open_cnt
    }])

    buf = io.StringIO()
    summary.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def build_aging_buckets_csv(df: pd.DataFrame) -> bytes:
    """Return a CSV (bytes) with the Open-Claims Aging Buckets distribution."""
    now = pd.Timestamp.utcnow()
    tmp = df.copy()
    tmp["Resolved"] = tmp["ClosedAt"].notna()
    tmp["DurationHours"] = ((tmp["ClosedAt"].fillna(now) - tmp["CreatedAt"])
                            .dt.total_seconds() / 3600).round(2)

    open_df = tmp[~tmp["Resolved"]].copy()
    open_df["AgingBucket"] = pd.cut(
        open_df["DurationHours"],
        bins=[0, 24, 48, 1e9],
        labels=["0-24h", "24-48h", ">48h"],
        include_lowest=True
    )

    aging = (open_df["AgingBucket"]
             .value_counts()
             .sort_index()
             .rename_axis("Bucket")
             .reset_index(name="Count"))

    buf = io.StringIO()
    aging.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def build_aging_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a daily time series of counts of OPEN claims by aging bucket.
    Buckets: 0–24h, 24–48h, >48h.
    """
    if df.empty:
        return pd.DataFrame(columns=["Date", "Bucket", "Count"])

    dfx = df.copy()
    dfx["CreatedAt"] = pd.to_datetime(dfx["CreatedAt"], utc=True, errors="coerce")
    dfx["ClosedAt"]  = pd.to_datetime(dfx["ClosedAt"],  utc=True, errors="coerce")

    start = dfx["CreatedAt"].min()
    end   = pd.Timestamp.utcnow().normalize()
    if pd.isna(start):
        return pd.DataFrame(columns=["Date", "Bucket", "Count"])

    days = pd.date_range(start=start.normalize(), end=end, freq="D", tz="UTC")

    out = []
    for day in days:
        # Open as of the end of 'day'
        cutoff = day + pd.Timedelta(days=1)
        open_mask = (dfx["CreatedAt"] <= cutoff) & ((dfx["ClosedAt"].isna()) | (dfx["ClosedAt"] > cutoff))
        open_claims = dfx.loc[open_mask].copy()

        if open_claims.empty:
            for b in ["0-24h", "24-48h", ">48h"]:
                out.append({"Date": day.date(), "Bucket": b, "Count": 0})
            continue

        open_claims["AgeHours"] = ((cutoff - open_claims["CreatedAt"]).dt.total_seconds() / 3600.0)
        open_claims["Bucket"] = pd.cut(
            open_claims["AgeHours"],
            bins=[0, 24, 48, np.inf],  # or float('inf') if you prefer to avoid numpy
            labels=["0-24h", "24-48h", ">48h"],
            include_lowest=True,
            right=True
        )

        counts = open_claims["Bucket"].value_counts().reindex(["0-24h", "24-48h", ">48h"], fill_value=0)
        for b, c in counts.items():
            out.append({"Date": day.date(), "Bucket": b, "Count": int(c)})

    ts = pd.DataFrame(out)
    ts["Date"] = pd.to_datetime(ts["Date"])
    return ts.sort_values(["Date", "Bucket"]).reset_index(drop=True)


# =========================
# Page Setup
# =========================
st.set_page_config(page_title="Claims Automation & Insights", layout="wide")
st.title("Claims Automation & Insights – Live Demo")

# =========================
# Data Loading
# =========================
DATA_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "claims_sample.csv"

uploaded = st.file_uploader("Upload a claims CSV (or use the sample dataset):", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded, parse_dates=["CreatedAt", "ClosedAt"])
else:
    df = pd.read_csv(DATA_DEFAULT, parse_dates=["CreatedAt", "ClosedAt"])

# Basic hygiene
for col in ["Priority", "Status"]:
    if col not in df.columns:
        df[col] = "Unknown"

# =========================
# Sidebar Filters (Date / Priority / Status)
# =========================
st.sidebar.header("Filters")

min_dt = pd.to_datetime(df["CreatedAt"]).min().date() if not df.empty else date.today()
max_dt = pd.to_datetime(df["CreatedAt"]).max().date() if not df.empty else date.today()

date_range = st.sidebar.date_input(
    "Date range (CreatedAt)",
    value=(min_dt, max_dt),
    min_value=min_dt,
    max_value=max_dt
)

all_priorities = sorted(pd.Series(df["Priority"]).fillna("Unknown").unique().tolist())
all_statuses   = sorted(pd.Series(df["Status"]).fillna("Unknown").unique().tolist())

sel_priorities = st.sidebar.multiselect("Priority", all_priorities, default=all_priorities)
sel_statuses   = st.sidebar.multiselect("Status",   all_statuses,   default=all_statuses)

# Normalize empty selections → include all
if not sel_priorities:
    sel_priorities = all_priorities
if not sel_statuses:
    sel_statuses = all_statuses

# Apply filters
start_dt, end_dt = date_range if isinstance(date_range, tuple) else (min_dt, max_dt)
mask_date     = (df["CreatedAt"].dt.date >= start_dt) & (df["CreatedAt"].dt.date <= end_dt)
mask_priority = df["Priority"].fillna("Unknown").isin(sel_priorities)
mask_status   = df["Status"].fillna("Unknown").isin(sel_statuses)

df_f = df.loc[mask_date & mask_priority & mask_status].copy()

# =========================
# Feature Engineering (filtered)
# =========================
now = pd.Timestamp.utcnow()
df_f["Resolved"] = df_f["ClosedAt"].notna()
df_f["DurationHours"] = ((df_f["ClosedAt"].fillna(now) - df_f["CreatedAt"]).dt.total_seconds() / 3600).round(2)

# =========================
# KPIs (filtered)
# =========================
avg_processing = df_f.loc[df_f["Resolved"], "DurationHours"].mean()
sla_compliance = 100 * ((df_f.loc[df_f["Resolved"], "DurationHours"] <= df_f.loc[df_f["Resolved"], "SLA_Hours"]).mean())
open_claims    = int((~df_f["Resolved"]).sum())

c1, c2, c3 = st.columns(3)
c1.metric("Avg Processing (hrs)", f"{avg_processing:.2f}" if pd.notna(avg_processing) else "—")
c2.metric("SLA Compliance (%)",  f"{sla_compliance:.2f}" if pd.notna(sla_compliance) else "—")
c3.metric("Open Claims", open_claims)

# Download buttons respond to current filters (use df_f)
b1, b2 = st.columns(2)
with b1:
    st.download_button(
        label="⬇️ Download KPIs (CSV)",
        data=build_kpi_summary_csv(df_f),
        file_name="kpi_summary.csv",
        mime="text/csv",
        help="Exports AvgProcessingHours, SLACompliancePct, and OpenClaims as a CSV."
    )
with b2:
    st.download_button(
        label="⬇️ Download Aging Buckets (CSV)",
        data=build_aging_buckets_csv(df_f),
        file_name="aging_buckets.csv",
        mime="text/csv",
        help="Exports the Open-Claims distribution by 0-24h, 24-48h, and >48h."
    )

# =========================
# Aging Buckets (filtered)
# =========================
st.subheader("Aging Buckets (Open Claims)")
open_df = df_f[~df_f["Resolved"]].copy()
if open_df.empty:
    st.info("No open claims in the current filter selection.")
else:
    open_df["AgingBucket"] = pd.cut(
        open_df["DurationHours"],
        bins=[0, 24, 48, 1e9],
        labels=["0-24h", "24-48h", ">48h"],
        include_lowest=True
    )
    st.bar_chart(open_df["AgingBucket"].value_counts().sort_index())

# =========================
# Aging Trends (filtered)
# =========================
st.subheader("Aging Trends (Daily Open Claims by Bucket)")
aging_ts = build_aging_trends(df_f)
if aging_ts.empty:
    st.info("No data available to build aging trends for the current selection.")
else:
    try:
        import altair as alt
        line = (
            alt.Chart(aging_ts)
            .mark_line(point=True)
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Count:Q", title="Open Claims"),
                color=alt.Color("Bucket:N", title="Aging Bucket"),
                tooltip=["Date:T", "Bucket:N", "Count:Q"]
            )
            .properties(height=320)
            .interactive()
        )
        st.altair_chart(line, use_container_width=True)
    except Exception:
        piv = aging_ts.pivot(index="Date", columns="Bucket", values="Count").fillna(0)
        st.line_chart(piv)

    # Download Aging Trends CSV
    buf = io.StringIO()
    aging_ts.to_csv(buf, index=False)
    st.download_button(
        "⬇️ Download Aging Trends (CSV)",
        data=buf.getvalue().encode("utf-8"),
        file_name="aging_trends_daily.csv",
        mime="text/csv",
        help="Daily counts of open claims by aging bucket for the current filters."
    )

# =========================
# Table (filtered)
# =========================
st.subheader("Raw Data Preview (Filtered)")
if df_f.empty:
    st.info("No rows match the current filters.")
else:
    st.dataframe(df_f.head(50))
