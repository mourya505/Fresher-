import datetime as dt, pandas as pd, streamlit as st
import db, pipeline

st.set_page_config(page_title="FresherRadar India", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.5rem;max-width:1250px}
.hero{background:linear-gradient(120deg,#4F46E5,#7C3AED);color:#fff;padding:28px 32px;border-radius:18px;margin-bottom:18px}
.hero h1{margin:0;font-size:2rem;color:#fff} .hero p{margin:6px 0 0;opacity:.9}
.kpi{background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:14px 18px}
.kpi b{font-size:1.6rem;color:#4F46E5;display:block} .kpi span{color:#64748B;font-size:.85rem}
.card{background:#fff;border:1px solid #E2E8F0;border-radius:14px;padding:16px 18px;margin-bottom:12px;transition:.15s}
.card:hover{box-shadow:0 6px 20px rgba(79,70,229,.12);border-color:#C7D2FE}
.card h4{margin:0 0 2px;font-size:1.05rem;color:#0F172A} .co{color:#475569;font-size:.92rem}
.tag{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.75rem;margin:8px 6px 0 0;font-weight:500}
.t-role{background:#EEF2FF;color:#4338CA} .t-city{background:#ECFDF5;color:#047857} .t-src{background:#F1F5F9;color:#475569}
.apply{float:right;background:#4F46E5;color:#fff!important;padding:6px 16px;border-radius:8px;text-decoration:none;font-size:.85rem}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load():
    with db.conn() as c:
        return pd.read_sql("SELECT * FROM jobs ORDER BY posted DESC, first_seen DESC", c)

df = load()
last = db.get_meta("last_run")
stale = (not last) or (dt.datetime.utcnow() - dt.datetime.fromisoformat(last)) > dt.timedelta(hours=24)

# Self-refresh fallback: if the daily GitHub Action hasn't run, refresh on first visit after 24h.
if stale:
    with st.spinner("Refreshing job feed (daily update)…"):
        try: pipeline.run(); st.cache_data.clear(); df = load(); last = db.get_meta("last_run")
        except Exception as e: st.warning(f"Auto-refresh failed: {e}")

st.markdown(f"""<div class="hero"><h1>🎯 FresherRadar India</h1>
<p>Fresher &amp; internship openings from public sources · de-duplicated · AI-tagged by role and city ·
updated daily{f" · last update {last[:16].replace('T',' ')} UTC" if last else ""}</p></div>""", unsafe_allow_html=True)

if df.empty:
    st.info("No jobs yet. Run `python pipeline.py` (set ADZUNA_APP_ID / ADZUNA_APP_KEY / GROQ_API_KEY first)."); st.stop()

with st.sidebar:
    st.header("Filters")
    q = st.text_input("🔎 Search", placeholder="python, intern, Infosys…")
    roles = st.multiselect("Role", sorted(df.role.unique()))
    cities = st.multiselect("City", sorted(df.city.unique()))
    srcs = st.multiselect("Source", sorted(df.source.unique()))
    days = st.slider("Posted within (days)", 1, 30, 30)
    sort = st.radio("Sort by", ["Newest", "Company A–Z"], horizontal=True)

f = df.copy()
if q:
    m = pd.Series(False, index=f.index)
    for t in q.lower().split():
        m |= f[["title", "company", "description", "role", "city"]].fillna("").agg(" ".join, axis=1).str.lower().str.contains(t, regex=False)
    f = f[m]
if roles: f = f[f.role.isin(roles)]
if cities: f = f[f.city.isin(cities)]
if srcs: f = f[f.source.isin(srcs)]
cut = (dt.date.today() - dt.timedelta(days=days)).isoformat()
f = f[(f.posted.fillna("") >= cut) | (f.posted.fillna("") == "")]
if sort == "Company A–Z": f = f.sort_values("company")

k = st.columns(4)
for col, (n, l) in zip(k, [(len(f), "Matching jobs"), (len(df), "Total tracked"), (f.company.nunique(), "Companies"),
                           (int(db.get_meta("last_new", 0)), "New in last refresh")]):
    col.markdown(f'<div class="kpi"><b>{n}</b><span>{l}</span></div>', unsafe_allow_html=True)
st.write("")

tab1, tab2, tab3 = st.tabs(["📋 Jobs", "📊 Insights", "🗂 Table & Export"])
with tab1:
    per = 20; pages = max(1, -(-len(f) // per))
    p = st.number_input("Page", 1, pages, 1) if pages > 1 else 1
    for _, r in f.iloc[(p-1)*per:p*per].iterrows():
        st.markdown(f"""<div class="card"><a class="apply" href="{r.url}" target="_blank">Apply ↗</a>
<h4>{r.title}</h4><div class="co">🏢 {r.company} · 📍 {r.location or r.city} · 🗓 {r.posted or '—'}</div>
<span class="tag t-role">{r.role}</span><span class="tag t-city">{r.city}</span><span class="tag t-src">{r.source}</span></div>""",
            unsafe_allow_html=True)
    if f.empty: st.info("No jobs match these filters.")
    else: st.caption(f"Showing page {p} of {pages}")
with tab2:
    a, b = st.columns(2)
    a.subheader("Jobs by role"); a.bar_chart(f.role.value_counts())
    b.subheader("Jobs by city"); b.bar_chart(f.city.value_counts())
    a.subheader("Top hiring companies"); a.bar_chart(f.company.value_counts().head(10))
    b.subheader("By source"); b.bar_chart(f.source.value_counts())
with tab3:
    show = f[["title", "company", "role", "city", "location", "posted", "source", "url"]]
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={"url": st.column_config.LinkColumn("Apply", display_text="Open")})
    st.download_button("⬇ Download CSV", show.to_csv(index=False), "fresher_jobs_india.csv", "text/csv")

st.caption("Data via Adzuna, Greenhouse, Lever and Remotive public APIs (attribution: remotive.com). "
           "Always verify details on the employer's page before applying.")
