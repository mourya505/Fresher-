"""Public, API-based sources only (no HTML scraping, so site terms are respected).
Adzuna India API, Greenhouse + Lever public job-board APIs, Remotive public API."""
import os, re, html, datetime as dt, requests

UA = {"User-Agent": "fresher-jobs-india/1.0 (student project)"}
T = 20

def _clean(t):
    t = html.unescape(t or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()

def adzuna():
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("Adzuna keys missing - skipping (free key: developer.adzuna.com)")
        return
    queries = ["fresher software developer", "graduate engineer trainee", "intern software",
               "entry level python", "junior data analyst", "machine learning intern",
               "fresher java", "fresher web developer", "ai engineer fresher", "qa fresher"]
    for q in queries:
        for page in (1, 2, 3):
            try:
                r = requests.get(f"https://api.adzuna.com/v1/api/jobs/in/search/{page}",
                    params={"app_id": app_id, "app_key": app_key, "results_per_page": 50,
                            "what": q, "max_days_old": 30, "content-type": "application/json"},
                    headers=UA, timeout=T)
                r.raise_for_status()
            except Exception as e:
                print("adzuna", q, page, e); break
            for j in r.json().get("results", []):
                yield dict(title=j.get("title"), company=(j.get("company") or {}).get("display_name"),
                           location=(j.get("location") or {}).get("display_name"),
                           url=j.get("redirect_url"), posted=(j.get("created") or "")[:10],
                           description=_clean(j.get("description")), source="Adzuna")

# Public job-board tokens. Companies that use Greenhouse/Lever. Wrong tokens just 404 and are skipped.
GREENHOUSE = ["groww", "phonepe", "postman", "razorpaysoftwareprivatelimited", "databricks",
              "stripe", "cloudflare", "airbnb", "twilio", "elastic", "mongodb", "okta", "gitlab"]
LEVER = ["cred", "meesho", "paytm", "dream11", "upgrad", "zeta"]

def greenhouse():
    for t in GREENHOUSE:
        try:
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs",
                             params={"content": "true"}, headers=UA, timeout=T)
            if r.status_code != 200: continue
            for j in r.json().get("jobs", []):
                yield dict(title=j.get("title"), company=j.get("company_name") or t.title(),
                           location=(j.get("location") or {}).get("name"), url=j.get("absolute_url"),
                           posted=(j.get("updated_at") or "")[:10],
                           description=_clean(j.get("content")), source="Greenhouse")
        except Exception as e:
            print("greenhouse", t, e)

def lever():
    for t in LEVER:
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{t}", params={"mode": "json"},
                             headers=UA, timeout=T)
            if r.status_code != 200: continue
            for j in r.json():
                ts = j.get("createdAt")
                posted = dt.datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d") if ts else ""
                yield dict(title=j.get("text"), company=t.title(),
                           location=(j.get("categories") or {}).get("location"),
                           url=j.get("hostedUrl"), posted=posted,
                           description=_clean(j.get("descriptionPlain")), source="Lever")
        except Exception as e:
            print("lever", t, e)

def remotive():  # attribution required by Remotive; called once per day only
    try:
        r = requests.get("https://remotive.com/api/remote-jobs", params={"category": "software-dev"},
                         headers=UA, timeout=T)
        for j in r.json().get("jobs", []):
            loc = j.get("candidate_required_location") or ""
            if re.search(r"india|worldwide|anywhere|apac|asia", loc, re.I):
                yield dict(title=j.get("title"), company=j.get("company_name"), location="Remote - " + loc,
                           url=j.get("url"), posted=(j.get("publication_date") or "")[:10],
                           description=_clean(j.get("description")), source="Remotive")
    except Exception as e:
        print("remotive", e)

ALL = [adzuna, greenhouse, lever, remotive]
