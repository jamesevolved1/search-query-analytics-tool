
import io
import math
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(
    page_title="Brand Analytics • Query Opportunity Analyzer",
    page_icon="🧠",
    layout="wide",
)

# ---------- Styling ----------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; }
.big-title { font-size: 2.0rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: .25rem; }
.subtle { color: rgba(255,255,255,.75); }
.card {
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  border-radius: 18px;
  padding: 16px 16px 12px 16px;
}
.card h3 { margin: 0; font-size: 0.95rem; font-weight: 700; opacity: 0.9;}
.card .value { font-size: 1.6rem; font-weight: 800; margin-top: .35rem; letter-spacing: -0.02em;}
.card .hint { font-size: .85rem; opacity: .75; margin-top: .25rem; }
.pill {
  display:inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: .8rem;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.06);
  margin-right: 6px;
}
hr.soft { border: none; height:1px; background: rgba(255,255,255,0.08); margin: 10px 0 18px 0; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- Helpers ----------
PCT_COLS_CANON = [
    "Our Conversion Rate",
    "Market Conversion Rate",
    "Our Click Through Rate",
    "Market Click Through Rate",
]

NUM_COLS_CANON = [
    "Impressions: ASIN Count",
    "Impressions: Total Count",
    "Clicks: ASIN Count",
    "Clicks: Total Count",
    "Cart Adds: ASIN Count",
    "Cart Adds: Total Count",
    "Purchases: ASIN Count",
    "Purchases: Total Count",
]

SHARE_COLS_CANON = [
    "Impressions - ASIN Share",
    "Clicks - ASIN Share",
    "Add to Cart - ASIN Share",
    "Purchases - ASIN Share",
]

DELTA_COLS_CANON = [
    "Delta (CR)",
    "Delta (CTR)",
    "Delta - Impressions to Clicks",
    "Delta - Clicks to Add to Cart",
    "Delta - Add to Cart to Purchases",
]

def _clean_col(c: str) -> str:
    if c is None:
        return ""
    c = str(c).strip()
    c = c.replace("\n", " ")
    c = re.sub(r"\s+", " ", c)
    # normalize common typos / spacing
    c = c.replace("Our Conversion Rate ", "Our Conversion Rate")
    c = c.replace("Add to Cart - ASIN Share ", "Add to Cart - ASIN Share")
    c = c.replace("Impressions - ASIN Share", "Impressions - ASIN Share")
    c = c.replace("Clicks - ASIN Share", "Clicks - ASIN Share")
    c = c.replace("Purchases - ASIN Share", "Purchases - ASIN Share")
    c = c.replace("Delta - Impressions to Clicks", "Delta - Impressions to Clicks")
    c = c.replace("Delta - Clicks to Add to Cart", "Delta - Clicks to Add to Cart")
    c = c.replace("Delta - Add to Cart to Purchases", "Delta - Add to Cart to Purchases")
    return c

def _to_number(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if s == "":
        return np.nan
    # handle percents like "3.2%" or "0.032"
    if s.endswith("%"):
        try:
            return float(s[:-1].replace(",", "")) / 100.0
        except:
            return np.nan
    # handle commas
    s = s.replace(",", "")
    try:
        return float(s)
    except:
        return np.nan

def _coerce_percent(series: pd.Series) -> pd.Series:
    s = series.apply(_to_number)
    # if values look like 3.2 (already percent points), convert to fraction
    # heuristic: if median > 1, treat as percent points
    med = np.nanmedian(s.values) if np.isfinite(s.values).any() else np.nan
    if pd.notna(med) and med > 1.0:
        s = s / 100.0
    return s

def load_anything(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        # excel
        xls = pd.ExcelFile(io.BytesIO(content))
        # choose best sheet by column match
        best = None
        best_score = -1
        for sh in xls.sheet_names:
            temp = pd.read_excel(xls, sheet_name=sh)
            cols = [_clean_col(c) for c in temp.columns]
            score = 0
            for must in ["Keyword", "Purchases: Total Count", "Clicks: Total Count", "Impressions: Total Count"]:
                if must in cols:
                    score += 3
            for opt in ["Our Conversion Rate", "Market Conversion Rate", "Our Click Through Rate", "Market Click Through Rate"]:
                if opt in cols:
                    score += 1
            if score > best_score:
                best_score = score
                best = sh
        df = pd.read_excel(xls, sheet_name=best)
    df.columns = [_clean_col(c) for c in df.columns]
    return df

def prep_df(df: pd.DataFrame) -> pd.DataFrame:
    # rename legacy delta columns into canon
    # Some sheets call them just "Delta" twice; we disambiguate if needed.
    df = df.copy()

    # Fix duplicate "Delta" columns by positional expectations
    cols = list(df.columns)
    delta_idx = [i for i,c in enumerate(cols) if c == "Delta"]
    if len(delta_idx) >= 2:
        cols[delta_idx[0]] = "Delta (CR)"
        cols[delta_idx[1]] = "Delta (CTR)"
        df.columns = cols
    elif len(delta_idx) == 1:
        # guess it's CR delta
        cols[delta_idx[0]] = "Delta (CR)"
        df.columns = cols

    # Coerce numeric/percent columns
    for c in PCT_COLS_CANON + [d for d in ["Delta (CR)", "Delta (CTR)"] if d in df.columns]:
        if c in df.columns:
            df[c] = _coerce_percent(df[c])

    for c in SHARE_COLS_CANON:
        if c in df.columns:
            df[c] = _coerce_percent(df[c])

    for c in NUM_COLS_CANON:
        if c in df.columns:
            df[c] = df[c].apply(_to_number)

    for c in ["Delta - Impressions to Clicks", "Delta - Clicks to Add to Cart", "Delta - Add to Cart to Purchases"]:
        if c in df.columns:
            df[c] = _coerce_percent(df[c])

    # Drop empty keywords
    if "Keyword" in df.columns:
        df["Keyword"] = df["Keyword"].astype(str).str.strip()
        df = df[df["Keyword"].ne("") & df["Keyword"].ne("nan")]

    # Derived fields
    df["Market_Demand"] = df.get("Impressions: Total Count", np.nan)
    if df["Market_Demand"].isna().all():
        df["Market_Demand"] = df.get("Clicks: Total Count", np.nan)

    # Opportunity features
    df["ClickGap"] = (df.get("Market Click Through Rate", np.nan) - df.get("Our Click Through Rate", np.nan))
    df["ConvGap"]  = (df.get("Market Conversion Rate", np.nan) - df.get("Our Conversion Rate", np.nan))
    df["ShareGap_Clicks"] = (df.get("Clicks - ASIN Share", np.nan) - df.get("Impressions - ASIN Share", np.nan))
    df["ShareGap_Purchases"] = (df.get("Purchases - ASIN Share", np.nan) - df.get("Clicks - ASIN Share", np.nan))

    # Normalize demand (log scale to reduce outliers)
    d = df["Market_Demand"].fillna(0).clip(lower=0)
    df["DemandScore"] = np.log1p(d)
    if df["DemandScore"].max() > 0:
        df["DemandScore"] = df["DemandScore"] / df["DemandScore"].max()

    # Score: prioritize demand + (positive) gaps
    def pos(x): 
        return np.where(pd.isna(x), 0, np.maximum(x, 0))
    df["OpportunityScore"] = (
        0.55 * df["DemandScore"]
        + 0.20 * pos(df["ClickGap"])
        + 0.15 * pos(df["ConvGap"])
        + 0.10 * pos(df["ShareGap_Purchases"])
    )
    df["OpportunityScore"] = df["OpportunityScore"].fillna(0)

    # Buckets (simple, deterministic rules)
    imp_share = df.get("Impressions - ASIN Share", pd.Series(np.nan, index=df.index))
    clk_share = df.get("Clicks - ASIN Share", pd.Series(np.nan, index=df.index))
    pur_share = df.get("Purchases - ASIN Share", pd.Series(np.nan, index=df.index))

    df["Bucket"] = "Ignore / Low Signal"
    # Ranking opp: demand high, impressions share exists, clicks/purchases lag
    df.loc[(df["DemandScore"] > 0.55) & (imp_share > 0) & (clk_share < imp_share*0.85), "Bucket"] = "Ranking Opportunity"
    # Conversion issue: you get clicks but purchases lag
    df.loc[(df["DemandScore"] > 0.35) & (clk_share > 0) & (pur_share < clk_share*0.75), "Bucket"] = "Conversion Problem"
    # PPC scale: purchases share >= clicks share (good conversion) but low impression share
    df.loc[(df["DemandScore"] > 0.35) & (pur_share >= clk_share*0.95) & (imp_share < 0.06), "Bucket"] = "PPC Scaling Opportunity"
    # Defend: strong shares
    df.loc[(imp_share >= 0.08) & (pur_share >= 0.06), "Bucket"] = "Defend Position"

    # Suggested action text
    def action(row):
        b = row["Bucket"]
        if b == "Ranking Opportunity":
            return "Launch/expand Exact + POE rank; validate relevance; tighten top-of-search placements; add to PLO (title/bullets/back-end) if truly core."
        if b == "Conversion Problem":
            return "Fix listing first (main image/value props/price/reviews); then isolate query in Exact to measure; avoid brute-force spend."
        if b == "PPC Scaling Opportunity":
            return "Scale PPC deliberately: raise bids/budgets where CPS holds; broaden match types; add defense targets; watch TACoS."
        if b == "Defend Position":
            return "Defend: maintain Exact + defense; cap waste; monitor share drops weekly."
        return "Ignore for now, or investigate relevance if it keeps appearing."
    df["Suggested Action"] = df.apply(action, axis=1)

    return df

def fmt_pct(x):
    if pd.isna(x):
        return ""
    return f"{x*100:.2f}%"

# ---------- Sidebar ----------
st.sidebar.markdown("### ⚙️ Controls")
uploaded = st.sidebar.file_uploader(
    "Upload Brand Analytics export (CSV/XLSX).",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=False
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Demo data")
use_demo = st.sidebar.toggle("Load demo from Wynwood analyzer (local)", value=True)
st.sidebar.caption("Turn off if you want to upload your own export.")

# ---------- Load data ----------
df_raw = None
if uploaded:
    df_raw = load_anything(uploaded)
elif use_demo:
    try:
        df_raw = pd.read_excel("Wynwood Search Query Performance Analyzer.xlsx", sheet_name="Data - Final")
        df_raw.columns = [_clean_col(c) for c in df_raw.columns]
    except Exception as e:
        st.error(f"Could not load demo file. {e}")

if df_raw is None or df_raw.empty:
    st.markdown('<div class="big-title">Brand Analytics • Query Opportunity Analyzer</div>', unsafe_allow_html=True)
    st.markdown("Upload a Brand Analytics Search Query export to get a prioritized, action-ready list.")
    st.info("Tip: Export Search Query Performance (Brand Analytics) → upload here. The app will auto-detect columns.")
    st.stop()

df = prep_df(df_raw)

# ---------- Header ----------
colA, colB = st.columns([3, 2])
with colA:
    st.markdown('<div class="big-title">Brand Analytics • Query Opportunity Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<span class="pill">Deterministic scoring</span><span class="pill">Team-ready outputs</span><span class="pill">Exportable tasks</span>', unsafe_allow_html=True)
with colB:
    st.caption("Goal: stop eyeballing rows. Prioritize. Execute. Track results.")

st.markdown('<hr class="soft" />', unsafe_allow_html=True)

# ---------- Top KPIs ----------
total_terms = len(df)
top_score = df["OpportunityScore"].max()
rank_ct = int((df["Bucket"] == "Ranking Opportunity").sum())
conv_ct = int((df["Bucket"] == "Conversion Problem").sum())
scale_ct = int((df["Bucket"] == "PPC Scaling Opportunity").sum())

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="card"><h3>Total queries</h3><div class="value">{total_terms:,}</div><div class="hint">Rows analyzed</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="card"><h3>Ranking opps</h3><div class="value">{rank_ct:,}</div><div class="hint">High demand, under-captured clicks</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="card"><h3>Conversion issues</h3><div class="value">{conv_ct:,}</div><div class="hint">Traffic without purchases</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="card"><h3>PPC scale</h3><div class="value">{scale_ct:,}</div><div class="hint">Good efficiency, low coverage</div></div>', unsafe_allow_html=True)

st.markdown("")

# ---------- Filters ----------
with st.expander("🔎 Filters", expanded=True):
    c1, c2, c3, c4 = st.columns([1.4, 1.1, 1.1, 1.4])
    with c1:
        q = st.text_input("Search keyword contains", "")
    with c2:
        bucket = st.selectbox("Bucket", ["All"] + sorted(df["Bucket"].unique().tolist()))
    with c3:
        min_score = st.slider("Min opportunity score", 0.0, 1.0, 0.15, 0.01)
    with c4:
        max_rows = st.slider("Max rows to show", 25, 250, 75, 25)

df_f = df.copy()
if q:
    df_f = df_f[df_f["Keyword"].str.contains(q, case=False, na=False)]
if bucket != "All":
    df_f = df_f[df_f["Bucket"] == bucket]
df_f = df_f[df_f["OpportunityScore"] >= min_score].sort_values("OpportunityScore", ascending=False).head(max_rows)

# ---------- Main Table ----------
left, right = st.columns([2.2, 1])

with left:
    st.subheader("Prioritized opportunities")
    display_cols = [
        "Keyword", "Bucket", "OpportunityScore",
        "Impressions: Total Count", "Clicks: Total Count", "Purchases: Total Count",
        "Impressions - ASIN Share", "Clicks - ASIN Share", "Purchases - ASIN Share",
        "Our Click Through Rate", "Market Click Through Rate",
        "Our Conversion Rate", "Market Conversion Rate",
        "Suggested Action",
    ]
    show = df_f[[c for c in display_cols if c in df_f.columns]].copy()
    if "OpportunityScore" in show.columns:
        show["OpportunityScore"] = show["OpportunityScore"].round(3)
    for c in ["Impressions - ASIN Share", "Clicks - ASIN Share", "Purchases - ASIN Share",
              "Our Click Through Rate", "Market Click Through Rate", "Our Conversion Rate", "Market Conversion Rate"]:
        if c in show.columns:
            show[c] = show[c].apply(fmt_pct)

    st.dataframe(show, use_container_width=True, height=520)

    # Export
    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered results (CSV)", data=csv, file_name="brand_analytics_opportunities.csv", mime="text/csv")

with right:
    st.subheader("What you do next")
    top = df.sort_values("OpportunityScore", ascending=False).head(12)
    for _, r in top.iterrows():
        st.markdown(f"**{r['Keyword']}**  \n`{r['Bucket']}`  \n{r['Suggested Action']}")
        st.markdown("---")

st.markdown("")
st.caption("Note: This MVP uses deterministic scoring. Next step is adding your playbook + a GPT step that writes ClickUp-ready tasks and weekly summaries in your voice.")
