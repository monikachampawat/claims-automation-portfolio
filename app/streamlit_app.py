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

# ---------- Helpers (CSV builders) ----------
def build_kpi_summary_csv(df: pd.DataFrame) -> bytes:
    """Return a CSV (bytes) with the KPIs currently shown in the app."""
    now = pd.Timestamp.utcnow()
    tmp = df.copy()
    tmp["Resolved"] = tmp["ClosedAt"].notna()
    tmp["DurationHours"] = ((tmp["ClosedAt"].fillna(now) - tmp["CreatedAt"]).dt.total_seconds() / 3600).round(2)

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

    # Ensure datetime
    dfx = df.copy()
    dfx["CreatedAt"] = pd.to_datetime(dfx["CreatedAt"], utc=True, errors="coerce")
    dfx["ClosedAt"]  = pd.to_datetime(dfx["ClosedAt"],  utc=True, errors="coerce")

    # Build a continuous calendar from first create to "today" (UTC)
    start = dfx["CreatedAt"].min()
    end   = pd.Timestamp.utcnow().normalize()
    if pd.isna(start):
        return pd.DataFrame(columns=["Date", "Bucket", "Count"])

    days = pd.date_range(start=start.normalize(), end=end, freq="D", tz="UTC")

    # For each day, compute age (in hours) for OPEN claims (not yet closed by that day)
    out = []
    for day in days:
        # All claims created up to 'day' and not closed before 'day'
        open_mask = (dfx["CreatedAt"] <= day + pd.Timedelta(days=1)) & (
            (dfx["ClosedAt"].isna()) | (dfx["ClosedAt"] > day + pd.Timedelta(days=1))
        )
        open_claims = dfx.loc[open_mask].copy()
        if open_claims.empty:
            for b in ["0-24h", "24-48h", ">48h"]:
                out.append({"Date": day.date(), "Bucket": b, "Count": 0})
            continue

        # Age as of the end of 'day'
        asof = day + pd.Timedelta(days=1)
        open_claims["AgeHours"] = ((asof - open_claims["CreatedAt"])
                                   .dt.total_seconds() / 3600.0)

        open_claims["Bucket"] = pd.cut(
            open_claims["AgeHours"],
            bins=[0, 24, 48, np.inf],
            labels=["0-24h", "24-48h", ">48h"],
            include_lowest=True,
            right=True
        )

        counts = open_claims["Bucket"].value_counts().reindex(["0-24h","24-48h",">48h"], fill_value=0)
        for b, c in counts.items():
            out.append({"Date": day.date(), "Bucket": b, "Count": int(c)})

    ts = pd.DataFrame(out)
    ts["Date"] = pd.to_datetime(ts["Date"])
    return ts.sort_values(["Date", "Bucket"]).reset_index(drop=True)


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

# ---------- Download buttons (side-by-side under KPI metrics) ----------
b1, b2 = st.columns(2)
with b1:
    st.download_button(
        label="⬇️ Download KPIs (CSV)",
        data=build_kpi_summary_csv(df),
        file_name="kpi_summary.csv",
        mime="text/csv",
        help="Exports AvgProcessingHours, SLACompliancePct, and OpenClaims as a CSV."
    )
with b2:
    st.download_button(
        label="⬇️ Download Aging Buckets (CSV)",
        data=build_aging_buckets_csv(df),
        file_name="aging_buckets.csv",
        mime="text/csv",
        help="Exports the Open-Claims distribution by 0-24h, 24-48h, and >48h."
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

# ---------- Aging Trends (Time Series) ----------
st.subheader("Aging Trends (Daily Open Claims by Bucket)")

aging_ts = build_aging_trends(df)

if aging_ts.empty:
    st.info("No data available to build aging trends.")
else:
    # Use Altair if present; otherwise fall back to Streamlit line chart
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
        # Pivot for Streamlit's wide-format line_chart
        piv = aging_ts.pivot(index="Date", columns="Bucket", values="Count").fillna(0)
        st.line_chart(piv)

    # (Optional) Download the trend data as CSV
    import io
    buf = io.StringIO()
    aging_ts.to_csv(buf, index=False)
    st.download_button(
        "⬇️ Download Aging Trends (CSV)",
        data=buf.getvalue().encode("utf-8"),
        file_name="aging_trends_daily.csv",
        mime="text/csv",
        help="Daily counts of open claims by aging bucket."
    )


# ---------- Table ----------
st.subheader('Raw Data Preview')
st.dataframe(df.head(50))
