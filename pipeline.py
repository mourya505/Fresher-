"""Run: python pipeline.py   (fetch -> fresher filter -> India filter -> dedupe -> tag -> SQLite)"""
import re, hashlib, datetime as dt
from collections import defaultdict
from rapidfuzz import fuzz
import db, sources, tagger

FRESHER = re.compile(r"fresher|graduate|intern\b|internship|entry.?level|trainee|junior|apprentice|"
                     r"campus|new grad|associate|0\s*-\s*[12]\s*(years|yrs)|\b(sde|software engineer)\s*(i|1)\b", re.I)
SENIOR = re.compile(r"senior|\bsr\.?\b|lead|principal|staff|manager|director|head of|architect|"
                    r"\b([3-9]|1\d)\s*\+?\s*(years|yrs)", re.I)
INDIA = re.compile(r"india|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|gurgaon|gurugram|noida|chennai|"
                   r"kolkata|ahmedabad|kochi|jaipur|indore|remote", re.I)

def norm(s): return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

def is_fresher(j):
    title, desc = j["title"] or "", (j["description"] or "")[:1500]
    if SENIOR.search(title): return False
    return bool(FRESHER.search(title) or FRESHER.search(desc)) and not re.search(r"\b([3-9]|1\d)\s*\+\s*(years|yrs)", desc, re.I)

def dedupe(jobs):
    seen_url, groups, out = set(), defaultdict(list), []
    for j in jobs:
        u = (j["url"] or "").split("?")[0]
        if not u or u in seen_url: continue
        seen_url.add(u)
        comp = norm(j["company"]); t = norm(j["title"])
        if any(fuzz.token_set_ratio(t, o) > 92 and norm(x["location"]) == norm(j["location"])
               for x in groups[comp] for o in [norm(x["title"])]):
            continue  # same company + near-identical title + same place = duplicate
        groups[comp].append(j); out.append(j)
    return out

def run():
    raw = []
    for src in sources.ALL:
        before = len(raw)
        raw.extend(src())
        print(f"{src.__name__}: {len(raw)-before} fetched")
    raw = [j for j in raw if j.get("title") and j.get("company")]
    jobs = [j for j in raw if INDIA.search(j["location"] or "") and is_fresher(j)]
    print(f"{len(raw)} raw -> {len(jobs)} fresher/India")
    jobs = dedupe(jobs)
    print(f"{len(jobs)} after dedupe")
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    for j in jobs:
        j["id"] = hashlib.sha1(f"{norm(j['title'])}|{norm(j['company'])}|{norm(j['location'])}".encode()).hexdigest()[:16]
    with db.conn() as c:
        known = {r["id"] for r in c.execute("SELECT id FROM jobs")}
        new = [j for j in jobs if j["id"] not in known]
        tagger.tag_all(new)
        for j in new:
            c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (j["id"], j["title"], j["company"], j["location"], j["city"], j["role"], j["source"],
                 j["url"], j["posted"], (j["description"] or "")[:3000], now, now, j["tagged_by"]))
        c.executemany("UPDATE jobs SET last_seen=? WHERE id=?", [(now, j["id"]) for j in jobs if j["id"] in known])
        c.execute("DELETE FROM jobs WHERE last_seen < datetime('now','-14 days')")  # drop expired posts
        db.set_meta(c, "last_run", now)
        total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        db.set_meta(c, "last_new", len(new))
    print(f"added {len(new)} new, {total} total in DB")

if __name__ == "__main__":
    run()
