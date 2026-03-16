
# Claims Automation & Insights System

An end-to-end **hybrid** project that demonstrates Business Analysis + .NET context + **SQL/Data modeling** + **Power BI analytics** + **Python automation**. Use this repo as a live portfolio when reaching out to hiring managers and senior leaders.

## What this shows
- Requirements & System Design (docs)
- SQL schema + KPI queries (sql/)
- **Python automation** to validate data and export KPIs (python/)
- A **live demo web app** using Streamlit (app/)
- Sample data you can demo immediately (data/)

## Repo Structure
```
Monika_Claims_Automation_Portfolio_Repo/
  app/                 # Streamlit web app for live demo
  python/              # Python automation (data validation + KPI export)
  sql/                 # SQL Server schema + KPI queries
  data/                # Sample claims dataset (CSV)
  docs/                # BRD, System Design, User Stories
  outputs/             # Generated KPI CSVs & charts after running scripts
```

## Quick Start (Local)
1) Create a virtual environment and install deps
```bash
python -m venv .venv
# Windows
. .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

2) Generate KPIs & charts
```bash
python python/automate_kpis.py
```
Outputs will appear in the `outputs/` directory.

3) Run the **live demo** web app (optional but recommended)
```bash
streamlit run app/streamlit_app.py
```
Open the URL Streamlit prints (usually http://localhost:8501) and interact with the demo.

## Suggested Live Hosting (free)
- **Streamlit Community Cloud** → Deploy `app/streamlit_app.py`
- **GitHub** → Host the code; include the repo link in LinkedIn Featured

## Screenshots (optional)
Add screenshots of your Power BI dashboard or the Streamlit app to this README after you run it.

## License
MIT
