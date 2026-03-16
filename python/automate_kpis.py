
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / 'data' / 'claims_sample.csv'
OUT = Path(__file__).resolve().parents[1] / 'outputs'
OUT.mkdir(exist_ok=True)

claims = pd.read_csv(DATA, parse_dates=['CreatedAt','ClosedAt'], keep_default_na=False)

# Basic validation
required = ['ClaimID','CustomerID','CreatedAt','Status','SLA_Hours']
missing = [c for c in required if c not in claims.columns]
if missing:
    raise SystemExit(f'Missing columns: {missing}')

now = pd.Timestamp.utcnow()
claims['Resolved'] = claims['ClosedAt'].notna() & (claims['ClosedAt'].astype(str) != '')
claims['ClosedAt'] = pd.to_datetime(claims['ClosedAt'].replace({'': pd.NaT}))
claims['DurationHours'] = ((claims['ClosedAt'].fillna(now) - claims['CreatedAt']).dt.total_seconds() / 3600).round(2)

avg_processing = claims.loc[claims['Resolved'], 'DurationHours'].mean()
sla_ok = (claims.loc[claims['Resolved'], 'DurationHours'] <= claims.loc[claims['Resolved'], 'SLA_Hours']).mean()
sla_compliance = round(100 * float(sla_ok), 2) if pd.notna(sla_ok) else 0.0

# Aging buckets
bins = [0, 24, 48, 1e9]
labels = ['0-24h','24-48h','>48h']
open_mask = ~claims['Resolved']
claims.loc[open_mask, 'AgingBucket'] = pd.cut(claims.loc[open_mask, 'DurationHours'], bins=bins, labels=labels, right=True, include_lowest=True)
aging = claims.loc[open_mask, 'AgingBucket'].value_counts().reindex(labels, fill_value=0)

# Export CSVs
pd.DataFrame({
    'AvgProcessingHours':[round(avg_processing,2)],
    'SLACompliancePct':[sla_compliance]
}).to_csv(OUT / 'kpi_summary.csv', index=False)

aging.rename_axis('Bucket').reset_index(name='Count').to_csv(OUT / 'aging_buckets.csv', index=False)

# Chart
plt.figure(figsize=(5,3))
aging.plot(kind='bar', color=['#4C78A8','#F58518','#E45756'])
plt.title('Open Claims by Aging Bucket')
plt.ylabel('Count')
plt.tight_layout()
plt.savefig(OUT / 'aging_buckets.png', dpi=160)
print('Exported outputs: kpi_summary.csv, aging_buckets.csv, aging_buckets.png')
