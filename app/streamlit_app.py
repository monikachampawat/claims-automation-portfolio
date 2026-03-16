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

# ---------- Helpers (CSV builders) ----------
def build_kpi_summary_csv(df: pd.DataFrame) -> bytes:
    """Return a CSV (bytes) with the KPIs currently shown in the app."""
    now = pd.Timestamp.utcnow()
    tmp = df.copy()
    tmp["Resolved"] = tmp["ClosedAt"].notna()
    tmp["DurationHours"] = ((tmp["ClosedAt"].fillna(now) - tmp["CreatedAt"])
                            .dt.total_seconds() / 3600).round(2)

    avg_proc = tmp.loc[tmp["Resolved"], "DurationHours"].mean()
    sla_pct = 100 * (
        (tmp.loc[tmp["Resolved"], "DurationHours"] <= tmp.loc[tmp["Resolved"], "SLA_Hours"]).mean()
    )
    open_cnt = int((~tmp["Resolved"]).sum())

    summary = pd.DataFrame([{
        "AvgProcessingHours": round(float(avg_proc), 2) if pd.notna(avg_proc) else None,
        "SLACompliancePct": round(float(sla_pct), 2) if pd.notna(sla_pct) else None,
        "OpenClaims": open_cnt
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
    Return a daily time series of counts of OPEN claims by aging bucket.
    Buckets: 0–24h, 24–48h, >48h.
    """
    if df.empty:
        return pd.DataFrame(columns=["Date", "Bucket", "Count"])

    dfx = df.copy()
    dfx["CreatedAt"] = pd.to_datetime(dfx["CreatedAt"], utc=True, errors="coerce")
