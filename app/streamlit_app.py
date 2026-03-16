# Fail-safe: if Altair isn't available, don't crash the app
try:
    import altair as alt  # noqa: F401
except Exception:
    import streamlit as st
    st.warning("Altair is not installed; charts will use Streamlit's basic charting.")

import io
import streamlit as st
import pandas as pd
from pathlib import Path

# ---------- Page Setup ----------
st.set_page_config(page_title='Claims Automation & Insights', layout='wide')
st.title('Claims Automation & Insights – Live Demo')

# ---------- Data Loading ----------
DATA_DEFAULT = Path(__file__).resolve().parents[1] / 'data' / 'claims_sample.csv'

uploaded = st.file_uploader('Upload a claims CSV (or use the sample dataset):', type=['csv'])
if uploaded:
    df = pd.read_csv(uploaded, parse_dates=['CreatedAt', 'ClosedAt'])
else:
    df = pd.read_csv(DATA_DEFAULT, parse_dates=['CreatedAt', 'ClosedAt'])

# ---------- Feature Engineering ----------
now = pd.Timestamp.utcnow()
df['Resolved'] = df['ClosedAt'].notna()
df['DurationHours'] = ((df['ClosedAt'].fillna(now) - df['CreatedAt']).dt.total_seconds() / 3600).round(2)

# KPIs
avg_processing = df.loc[df['Resolved'], 'DurationHours'].mean()
sla_compliance = 100 * (
    (df.loc[df['Resolved'], 'DurationHours'] <= df.loc[df['Resolved'], 'SLA_Hours']).mean()
)
open_claims = int((~df['Resolved']).sum())

# ---------- KPI Header ----------
c1, c2, c3 = st.columns(3)
c1.metric('Avg Processing (hrs)', f"{avg_processing:.2f}" if pd.notna(avg_processing) else '—')
c2.metric('SLA Compliance (%)', f"{sla_compliance:.2f}" if pd.notna(sla_compliance) else '—')
c3.metric('Open Claims', open_claims)

# ---------- Helper to build CSV for download ----------
def build_kpi_summary_csv(df_current: pd.DataFrame) -> bytes:
    """Return a CSV (bytes) with the KPIs currently shown in the app."""
    now_ = pd.Timestamp.utcnow()
    tmp = df_current.copy()
    tmp["Resolved"] = tmp["ClosedAt"].notna()
    tmp["DurationHours"] = ((tmp["ClosedAt"].fillna(now_) - tmp["CreatedAt"]).dt.total_seconds() / 3600).round(2)

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

# ---------- Download button (right under KPI metrics) ----------
st.download_button(
    label="⬇️ Download KPIs (CSV)",
    data=build_kpi_summary_csv(df),
    file_name="kpi_summary.csv",
    mime="text/csv",
    help="Exports AvgProcessingHours, SLACompliancePct, and OpenClaims as a CSV."
)

# ---------- Chart: Aging Buckets ----------
st.subheader('Aging Buckets (Open Claims)')
open_df = df[~df['Resolved']].copy()
open_df['AgingBucket'] = pd.cut(
    open_df['DurationHours'],
    bins=[0, 24, 48, 1e9],
    labels=['0-24h', '24-48h', '>48h'],
    include_lowest=True
)
st.bar_chart(open_df['AgingBucket'].value_counts().sort_index())

# ---------- Table ----------
st.subheader('Raw Data Preview')
st.dataframe(df.head(50))
