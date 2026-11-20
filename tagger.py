"""LLM tagging (Groq, llama-3.1-8b-instant) with a rule-based fallback so the pipeline never breaks."""
import os, re, json, requests

ROLES = ["Software Engineer", "Backend", "Frontend", "Full Stack", "Data Analyst", "Data Scientist",
         "ML/AI Engineer", "DevOps/Cloud", "QA/Testing", "Mobile", "Product/Design", "Support/Ops", "Other"]
CITIES = ["Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi NCR", "Chennai", "Kolkata",
          "Ahmedabad", "Remote", "Other"]

CITY_RULES = {"Bengaluru": r"bengaluru|bangalore", "Hyderabad": r"hyderabad|secunderabad",
  "Pune": r"pune", "Mumbai": r"mumbai|navi mumbai|thane", "Delhi NCR": r"delhi|gurgaon|gurugram|noida|ghaziabad|faridabad",
  "Chennai": r"chennai", "Kolkata": r"kolkata", "Ahmedabad": r"ahmedabad|gandhinagar", "Remote": r"remote|work from home|wfh"}
ROLE_RULES = [("ML/AI Engineer", r"machine learning|\bml\b|\bai\b|genai|llm|deep learning|nlp"),
  ("Data Scientist", r"data scien"), ("Data Analyst", r"data analy|business analy|\bbi\b|analytics"),
  ("DevOps/Cloud", r"devops|cloud|sre|site reliability|infrastructure"),
  ("QA/Testing", r"\bqa\b|quality|test|sdet"), ("Mobile", r"android|ios|mobile|flutter|react native"),
  ("Full Stack", r"full.?stack"), ("Frontend", r"front.?end|react|angular|ui developer"),
  ("Backend", r"back.?end|java\b|python|node|golang|\.net"),
  ("Product/Design", r"product|design|ux"), ("Support/Ops", r"support|operations|customer"),
  ("Software Engineer", r"software|developer|engineer|sde|programmer|trainee")]

def rule_tag(j):
    blob = f"{j['title']} {j['location'] or ''}".lower()
    city = next((c for c, p in CITY_RULES.items() if re.search(p, blob)), "Other")
    role = next((r for r, p in ROLE_RULES if re.search(p, j["title"].lower())), "Other")
    return role, city

def llm_tag(batch, key):
    items = [{"id": j["id"], "title": j["title"], "location": j["location"],
              "snippet": (j["description"] or "")[:200]} for j in batch]
    prompt = (f"Tag each job. role must be one of {ROLES}. city must be one of {CITIES} "
              "(map suburbs to the main city, use Remote for remote/WFH). "
              'Return JSON {"results":[{"id":"..","role":"..","city":".."}]}.\n' + json.dumps(items))
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"}, timeout=60,
        json={"model": "llama-3.1-8b-instant", "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    return {x["id"]: x for x in json.loads(r.json()["choices"][0]["message"]["content"])["results"]}

def tag_all(jobs):
    """jobs: list of dicts. Mutates with role, city, tagged_by."""
    key = os.getenv("GROQ_API_KEY")
    for i in range(0, len(jobs), 20):
        batch, out = jobs[i:i+20], {}
        if key:
            try: out = llm_tag(batch, key)
            except Exception as e: print("LLM tag failed, using rules:", e)
        for j in batch:
            o = out.get(j["id"])
            if o and o.get("role") in ROLES and o.get("city") in CITIES:
                j["role"], j["city"], j["tagged_by"] = o["role"], o["city"], "llm"
            else:
                j["role"], j["city"] = rule_tag(j); j["tagged_by"] = "rules"
    return jobs
