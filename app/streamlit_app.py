
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title='Claims Automation & Insights', layout='wide')
st.title('Claims Automation & Insights – Live Demo')

DATA_DEFAULT = Path(__file__).resolve().parents[1] / 'data' / 'claims_sample.csv'

uploaded = st.file_uploader('Upload a claims CSV (or use the sample dataset):', type=['csv'])
if uploaded:
    df = pd.read_csv(uploaded, parse_dates=['CreatedAt','ClosedAt'])
else:
    df = pd.read_csv(DATA_DEFAULT, parse_dates=['CreatedAt','ClosedAt'])

now = pd.Timestamp.utcnow()
df['Resolved'] = df['ClosedAt'].notna()
df['DurationHours'] = ((df['ClosedAt'].fillna(now) - df['CreatedAt']).dt.total_seconds()/3600).round(2)

avg_processing = df.loc[df['Resolved'], 'DurationHours'].mean()
sla_compliance = 100 * (df.loc[df['Resolved'], 'DurationHours'] <= df.loc[df['Resolved'], 'SLA_Hours']).mean()

c1, c2, c3 = st.columns(3)
c1.metric('Avg Processing (hrs)', f"{avg_processing:.2f}" if pd.notna(avg_processing) else '—')
c2.metric('SLA Compliance (%)', f"{sla_compliance:.2f}" if pd.notna(sla_compliance) else '—')
c3.metric('Open Claims', int((~df['Resolved']).sum()))

st.subheader('Aging Buckets (Open Claims)')
open_df = df[~df['Resolved']].copy()
open_df['AgingBucket'] = pd.cut(open_df['DurationHours'], bins=[0,24,48,1e9], labels=['0-24h','24-48h','>48h'], include_lowest=True)
st.bar_chart(open_df['AgingBucket'].value_counts().sort_index())

st.subheader('Raw Data Preview')
st.dataframe(df.head(50))
