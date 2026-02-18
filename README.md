# Brand Analytics • Query Opportunity Analyzer (MVP)

## What this is
A simple Streamlit app that ingests a Brand Analytics Search Query export (CSV/XLSX),
computes an opportunity score, buckets each query into action categories, and exports results.

## Run locally
1) Install Python 3.10+
2) From this folder:
   pip install -r requirements.txt
3) Start:
   streamlit run streamlit_app.py

## Demo mode
If `Wynwood Search Query Performance Analyzer.xlsx` is in the same folder,
toggle "Load demo..." in the sidebar to see the UI instantly.

## Deploy (Cloud Run or similar)
- Build a container with Streamlit
- Expose port 8080 and set Streamlit server port accordingly
- Or deploy to Streamlit Community Cloud

Next iteration:
- Add OpenAI API integration to auto-generate ClickUp tasks + weekly summaries
- Add history tracking (weekly runs) + share trend charts
