import os
from datetime import timedelta, datetime, timezone
from collections import Counter
import re
import requests
import json
from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt, get_jwt_identity,
    jwt_required, set_access_cookies, unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv, find_dotenv
import random

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -------------------------
# Config
# -------------------------
load_dotenv(find_dotenv())
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-change-me")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
PORT = int(os.getenv("PORT", "8080"))

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False          # set True in prod (https)
app.config["JWT_COOKIE_SAMESITE"] = "Lax"        # consider "None" + Secure for cross-site
app.config["JWT_ACCESS_COOKIE_NAME"] = "vol_jwt"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=6)
app.config["JWT_COOKIE_CSRF_PROTECT"] = False    # disable CSRF for development

CORS(
    app,
    resources={r"/*": {"origins": [FRONTEND_ORIGIN]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

jwt = JWTManager(app)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# -------------------------
# DB helpers
# -------------------------
def ensure_password_column():
    """Add password_hash column to app_user if missing."""
    with engine.begin() as conn:
        conn.execute(text("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='app_user' AND column_name='password_hash'
              ) THEN
                ALTER TABLE app_user ADD COLUMN password_hash TEXT;
              END IF;
            END$$;
        """))

def fetch_user_by_email(db, email):
    row = db.execute(text("""
        SELECT id, email, full_name, password_hash, organization_id,
               slack_id, user_name, company, position, dept,
               location_city, location_state, tz,
               raw_conversations, strengths, interests, expertise, communication_style,
               skills,
               created_at, updated_at
        FROM app_user WHERE email = :email
    """), {"email": email}).mappings().first()
    return row

def fetch_user_by_id(db, user_id):
    row = db.execute(text("""
        SELECT id, email, full_name, organization_id,
               slack_id, user_name, company, position, dept,
               location_city, location_state, tz,
               raw_conversations, strengths, interests, expertise, communication_style,
               skills,
               created_at, updated_at
        FROM app_user WHERE id = :id
    """), {"id": user_id}).mappings().first()
    return row

# Run once at startup
ensure_password_column()

# -------------------------
# Skill vocabulary (50 common skills)
# -------------------------
SKILL_VOCAB: list[str] = [
    "Leadership", "Communication", "Project Management", "Product Management", "UX Design",
    "UI Design", "Graphic Design", "Content Strategy", "Marketing", "SEO",
    "Social Media", "Data Analysis", "Statistics", "SQL", "Python",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Cloud Architecture",
    "AWS", "Azure", "GCP", "DevOps", "CI/CD",
    "Docker", "Kubernetes", "Cybersecurity", "Risk Assessment", "Networking",
    "Backend Development", "Frontend Development", "Full-Stack Development", "JavaScript", "React",
    "Node.js", "Java", "Spring Boot", "APIs", "Microservices",
    "PostgreSQL", "NoSQL", "Electrical Engineering", "Civil Engineering", "Biomedical Engineering",
    "Research", "Clinical Trials", "Healthcare", "Community Management", "Sustainability"
]

# Simple keyword→skill mapping used to pick top-3 from text
KEYWORD_TO_SKILL: dict[str, str] = {
    # tech stacks
    "javascript": "JavaScript", "react": "React", "node": "Node.js", "node.js": "Node.js",
    "java ": "Java", " spring ": "Spring Boot", "spring boot": "Spring Boot", "api": "APIs",
    "microservice": "Microservices", "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "nosql": "NoSQL", "sql": "SQL",
    # ml/ai
    "machine learning": "Machine Learning", "deep learning": "Deep Learning", "nlp": "NLP",
    "computer vision": "Computer Vision", "python": "Python", "statistics": "Statistics",
    # cloud/devops
    "aws": "AWS", "azure": "Azure", "gcp": "GCP", "cloud": "Cloud Architecture",
    "devops": "DevOps", "ci/cd": "CI/CD", "docker": "Docker", "kubernetes": "Kubernetes",
    # security/networking
    "cyber": "Cybersecurity", "security": "Cybersecurity", "risk": "Risk Assessment",
    "network": "Networking",
    # design/product/content/marketing
    "product": "Product Management", "project": "Project Management", "ux": "UX Design",
    "ui ": "UI Design", "graphic": "Graphic Design", "content": "Content Strategy",
    "marketing": "Marketing", "seo": "SEO", "social": "Social Media",
    # community/healthcare/engineering/sustainability
    "community": "Community Management", "health": "Healthcare", "clinical": "Clinical Trials",
    "research": "Research", "electrical": "Electrical Engineering", "civil": "Civil Engineering",
    "biomedical": "Biomedical Engineering", "sustain": "Sustainability",
}


# ERG → 3 canonical skills mapping (chosen from SKILL_VOCAB)
ERG_SKILLS_MAP: dict[str, list[str]] = {
    "Women in Leadership / Women@": ["Leadership", "Communication", "Project Management"],
    "Black Employee Network / Black Professionals ERG": ["Leadership", "Community Management", "Communication"],
    "Latinx / Hispanic Heritage Network": ["Community Management", "Marketing", "Social Media"],
    "Asian Pacific Islander Network": ["Community Management", "Content Strategy", "Marketing"],
    "South Asian Professionals Network": ["Community Management", "Data Analysis", "Communication"],
    "LGBTQ+ Pride Network": ["Community Management", "Communication", "Content Strategy"],
    "Veterans & Military Families Network": ["Leadership", "Project Management", "Networking"],
    "Disability & Neurodiversity Alliance": ["UX Design", "Content Strategy", "Community Management"],
    "Parents & Caregivers ERG": ["Community Management", "Communication", "Project Management"],
    "Young Professionals / NextGen ERG": ["Communication", "Project Management", "Data Analysis"],
    "Multifaith / Interfaith Network": ["Community Management", "Communication", "Leadership"],
    "Mental Health & Wellness Network": ["Data Analysis", "Community Management", "Communication"],
    "Environmental & Sustainability Group (Green Team)": ["Sustainability", "Project Management", "Data Analysis"],
    "International Employees Network / Global Cultures ERG": ["Community Management", "Communication", "Marketing"],
    "Native & Indigenous Peoples Network": ["Community Management", "Content Strategy", "Communication"],
    "African Diaspora Network": ["Community Management", "Leadership", "Marketing"],
    "Middle Eastern & North African (MENA) ERG": ["Community Management", "Communication", "Marketing"],
    "Men as Allies / Gender Equity Advocates": ["Leadership", "Communication", "Project Management"],
    "Volunteers & Community Impact Network": ["Community Management", "Project Management", "Marketing"],
    "Multicultural / Diversity & Inclusion Council": ["Leadership", "Community Management", "Data Analysis"],
}


# -------------------------
# Event helpers
# -------------------------
VALID_EVENT_MODES = {"in_person", "virtual", "hybrid"}

def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]

def _parse_ts(s):
    # Accept "...Z" or ISO with offset; store as UTC
    dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)

def _require_fields(d, required):
    missing = [k for k in required if not d.get(k)]
    if missing:
        return f"missing fields: {', '.join(missing)}"
    return None

# -------------------------
# Routes
# -------------------------
@app.get("/")
def root():
    return redirect(f"{FRONTEND_ORIGIN}/", code=302)

@app.get("/login")
def login_page():
    # If you serve a frontend separately, redirect there:
    return redirect(f"{FRONTEND_ORIGIN}/login", code=302)

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@app.post("/auth/signup")
def signup():
    """
    Body: { 
        "email": "...", 
        "password": "...", 
        "full_name": "Optional", 
        "organization_id": 1,
        "user_name": "Optional",
        "company": "Optional",
        "position": "Optional", 
        "dept": "Optional",
        "erg": "Optional",
        "location_city": "Optional",
        "location_state": "Optional",
        "tz": "Optional",
        "strengths": "Optional",
        "interests": "Optional",
        "expertise": "Optional",
        "communication_style": "Optional"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password") or ""
    full_name = data.get("full_name")
    org_id = data.get("organization_id")
    
    # Additional user fields
    user_name = data.get("user_name")
    company = data.get("company")
    position = data.get("position")
    dept = data.get("dept")
    erg = data.get("erg")
    location_city = data.get("location_city")
    location_state = data.get("location_state")
    tz = data.get("tz", "UTC")
    strengths = data.get("strengths")
    interests = data.get("interests")
    expertise = data.get("expertise")
    skills = data.get("skills")  # accept list or comma-separated
    communication_style = data.get("communication_style")
    
    if not email or not pwd:
        return jsonify({"error": "email and password are required"}), 400

    pw_hash = generate_password_hash(pwd)

    with SessionLocal() as db:
        # Look up department_id by department name
        department_id = None
        if dept:
            dept_row = db.execute(text("SELECT id FROM department WHERE name = :dept_name"), {"dept_name": dept}).mappings().first()
            if dept_row:
                department_id = dept_row["id"]
        
        # Look up erg_id by ERG name
        erg_id = None
        if erg:
            erg_row = db.execute(text("SELECT id FROM erg WHERE name = :erg_name"), {"erg_name": erg}).mappings().first()
            if erg_row:
                erg_id = erg_row["id"]
        existing = fetch_user_by_email(db, email)
        if existing:
            return jsonify({"error": "email already registered"}), 409

        # Compute final skills to store (merge provided + ERG implied)
        combined_skills = _as_list(skills)
        if erg:
            implied = ERG_SKILLS_MAP.get(erg, [])
            for s in implied:
                if s in SKILL_VOCAB and s not in combined_skills:
                    combined_skills.append(s)

        # Insert user with all fields
        row = db.execute(text("""
            INSERT INTO app_user (
                email, full_name, organization_id, department_id, erg_id, password_hash,
                user_name, company, position, dept, erg,
                location_city, location_state, tz,
                strengths, interests, expertise, communication_style, skills
            )
            VALUES (
                :email, :full_name, :org_id, :department_id, :erg_id, :pw,
                :user_name, :company, :position, :dept, :erg,
                :location_city, :location_state, :tz,
                :strengths, :interests, :expertise, :communication_style, :skills
            )
            RETURNING id, email, full_name, organization_id, department_id, erg_id,
                     user_name, company, position, dept, erg,
                     location_city, location_state, tz,
                     strengths, interests, expertise, communication_style, skills
        """), {
            "email": email, "full_name": full_name, "org_id": org_id, "department_id": department_id, "erg_id": erg_id, "pw": pw_hash,
            "user_name": user_name, "company": company, "position": position, "dept": dept, "erg": erg,
            "location_city": location_city, "location_state": location_state, "tz": tz,
            "strengths": strengths, "interests": interests, "expertise": expertise, "communication_style": communication_style,
            "skills": combined_skills
        }).mappings().first()
        db.commit()

        # Issue JWT
        access_token = create_access_token(identity=str(row["id"]))
        resp = make_response({
            "user": {
                "id": str(row["id"]),
                "email": row["email"],
                "full_name": row["full_name"],
                "organization_id": row["organization_id"],
                "user_name": row["user_name"],
                "company": row["company"],
                "position": row["position"],
                "dept": row["dept"],
                "location_city": row["location_city"],
                "location_state": row["location_state"],
                "tz": row["tz"],
                "strengths": row["strengths"],
                "interests": row["interests"],
                "expertise": row["expertise"],
                "communication_style": row["communication_style"],
                "skills": row.get("skills")
            }
        })
        set_access_cookies(resp, access_token)
        return resp, 201

@app.post("/auth/login")
def login():
    """
    Body: { "email": "...", "password": "..." }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password") or ""

    if not email or not pwd:
        return jsonify({"error": "email and password are required"}), 400

    with SessionLocal() as db:
        user = fetch_user_by_email(db, email)
        if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], pwd):
            return jsonify({"error": "invalid credentials"}), 401

        access_token = create_access_token(identity=str(user["id"]))
        resp = make_response({
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "organization_id": user["organization_id"],
                "user_name": user["user_name"],
                "company": user["company"],
                "position": user["position"],
                "dept": user["dept"],
                "location_city": user["location_city"],
                "location_state": user["location_state"],
                "tz": user["tz"],
                "strengths": user["strengths"],
                "interests": user["interests"],
                "expertise": user["expertise"],
                "communication_style": user["communication_style"],
                "skills": user.get("skills")
            }
        })
        set_access_cookies(resp, access_token)
        return resp, 200

@app.post("/auth/logout")
def logout():
    resp = make_response({"ok": True})
    unset_jwt_cookies(resp)
    return resp, 200

@app.get("/auth/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        user = fetch_user_by_id(db, user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404
        return {
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
                "organization_id": user["organization_id"],
                "user_name": user["user_name"],
                "company": user["company"],
                "position": user["position"],
                "dept": user["dept"],
                "location_city": user["location_city"],
                "location_state": user["location_state"],
                "tz": user["tz"],
                "strengths": user["strengths"],
                "interests": user["interests"],
                "expertise": user["expertise"],
                "communication_style": user["communication_style"],
                "skills": user.get("skills")
            }
        }, 200

# Optional: token freshness/expiry check endpoint
@app.get("/auth/token")
@jwt_required()
def token_info():
    return {"sub": get_jwt_identity(), "exp": get_jwt()["exp"]}, 200

# -------------------------
# Organizations (for event form dropdown)
# -------------------------
@app.get("/api/organizations")
@jwt_required()
def list_organizations():
    with SessionLocal() as db:
        rows = db.execute(text("SELECT id, name, website FROM organization ORDER BY name")).mappings().all()
    return jsonify({"organizations": [dict(r) for r in rows]}), 200

@app.post("/api/organizations")
@jwt_required()
def create_organization():
    """Create a new organization for testing"""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "Test Organization")
    website = data.get("website", "https://test.org")
    
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO organization (name, website)
            VALUES (:name, :website)
            RETURNING id, name, website
        """), {"name": name, "website": website}).mappings().first()
        db.commit()
    
    return jsonify({"organization": dict(result)}), 201


# -------------------------
# Create Event (+ optional sessions)
# -------------------------
@app.post("/api/events")
@jwt_required()
def create_event():
    """
    Body JSON (minimal):
    {
      "title": "...",
      "description": "...",
      "mode": "in_person" | "virtual" | "hybrid",
      "location_city": "City",
      "location_state": "ST",
      "rsvp_url": "https://...",
      "contact_email": "org@example.org"
    }
    """
    data = request.get_json(silent=True) or {}

    # Required
    err = _require_fields(data, ["title", "description", "mode"])
    if err:
        return jsonify({"error": err}), 400

    mode = str(data.get("mode")).strip().lower()
    if mode not in VALID_EVENT_MODES:
        return jsonify({"error": f"mode must be one of {sorted(VALID_EVENT_MODES)}"}), 400

    # Minimal fields only
    causes = []
    skills = []
    accessibility = []
    tags = []
    min_duration = 60
    is_remote = False
    sessions = []

    # Validate/normalize sessions
    norm_sessions = []
    try:
        for i, s in enumerate(sessions):
            st = _parse_ts(s["start_ts"])
            en = _parse_ts(s["end_ts"])
            if not (st < en):
                return jsonify({"error": f"sessions[{i}] end_ts must be after start_ts"}), 400
            norm_sessions.append({
                "start_ts": st,
                "end_ts": en,
                "capacity": s.get("capacity"),
                "meet_url": s.get("meet_url"),
                "address_line": s.get("address_line"),
            })
    except Exception as e:
        return jsonify({"error": f"invalid session timestamp format: {e}"}), 400

    with SessionLocal() as db:
        organization_id = None

        # Insert event
        ev = db.execute(text("""
            INSERT INTO event (
              organization_id, title, description, mode,
              location_city, location_state, location_lat, location_lng,
              is_remote, causes, skills_needed, accessibility, tags,
              min_duration_min, rsvp_url, contact_email
            )
            VALUES (
              :organization_id, :title, :description, :mode,
              :location_city, :location_state, :location_lat, :location_lng,
              :is_remote, :causes, :skills_needed, :accessibility, :tags,
              :min_duration_min, :rsvp_url, :contact_email
            )
            RETURNING id, organization_id, title, description, mode,
                      location_city, location_state, location_lat, location_lng,
                      is_remote, causes, skills_needed, accessibility, tags,
                      min_duration_min, rsvp_url, contact_email, created_at, updated_at
        """), {
            "organization_id": organization_id,
            "title": data["title"].strip(),
            "description": data["description"].strip(),
            "mode": mode,
            "location_city": data.get("location_city"),
            "location_state": data.get("location_state"),
            "location_lat": None,
            "location_lng": None,
            "is_remote": is_remote,
            "causes": causes,
            "skills_needed": skills,
            "accessibility": accessibility,
            "tags": tags,
            "min_duration_min": min_duration,
            "rsvp_url": data.get("rsvp_url"),
            "contact_email": data.get("contact_email"),
        }).mappings().first()

        # Sessions removed in minimal API
        created_sessions = []

        db.commit()

    # serialize timestamps
    for s in created_sessions:
        s["start_ts"] = s["start_ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        s["end_ts"]   = s["end_ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    # Optionally generate subtasks via Gemini
    if data.get("generate_tasks"):
        desc = data.get("description", "")
        base_text = f"{data.get('title','')}\n\n{desc}"
        subtasks = []
        try:
            subtasks = call_gemini_for_subtasks(base_text)
        except Exception:
            subtasks = []

        # Fallback: if no subtasks, create one default task from the main event
        if not subtasks:
            subtasks = [{
                "title": (data.get("title") or "Task")[:120],
                "description": (desc or "")[:280]
            }]

        with SessionLocal() as db:
            for st in subtasks:
                # infer 3 skills for each subtask
                inferred = []
                try:
                    inferred = call_gemini_for_skills(f"{st.get('title','')}. {st.get('description','')}") or []
                except Exception:
                    inferred = []
                if not inferred:
                    lc = f" {st.get('title','').lower()} {st.get('description','').lower()} "
                    counts = Counter()
                    for kw, skill in KEYWORD_TO_SKILL.items():
                        if kw in lc:
                            counts[skill] += lc.count(kw)
                    inferred = [s for s, _ in counts.most_common() if s in SKILL_VOCAB][:3]

                db.execute(text("""
                    INSERT INTO event_task (event_id, title, description, skills_required, priority, status, start_ts, end_ts)
                    VALUES (:event_id, :title, :description, :skills_required, 'medium', 'open', :start_ts, :end_ts)
                """), {
                    "event_id": ev["id"],
                    "title": st.get("title", "Task"),
                    "description": st.get("description", ""),
                    "skills_required": inferred,
                    "start_ts": None,
                    "end_ts": None
                })
            db.commit()

    return jsonify({"event": dict(ev), "sessions": created_sessions}), 201


# -------------------------
# List Departments
# -------------------------
@app.get("/api/departments")
def list_departments():
    """Get all available departments"""
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM department
            ORDER BY name
        """)).mappings().all()
    return jsonify({"departments": [dict(r) for r in rows]}), 200

# -------------------------
# List ERGs
# -------------------------
@app.get("/api/ergs")
def list_ergs():
    """Get all available Employee Resource Groups"""
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, name, description
            FROM erg
            ORDER BY name
        """)).mappings().all()
    return jsonify({"ergs": [dict(r) for r in rows]}), 200

# -------------------------
# Skills API
# -------------------------
@app.get("/api/skills/vocab")
def get_skill_vocab():
    return jsonify({"skills": SKILL_VOCAB}), 200


@app.post("/api/skills/suggest")
def suggest_skills():
    """Return up to 3 skills from SKILL_VOCAB inferred from provided text or latest Slack import.
    Body: { text?: string, slack_source?: "latest", use_gemini?: bool }
    """
    data = request.get_json(silent=True) or {}
    source_text = data.get("text") or ""
    use_gemini = bool(data.get("use_gemini") and GEMINI_API_KEY)
    if not source_text and data.get("slack_source") == "latest":
        with SessionLocal() as db:
            row = db.execute(text("""
                SELECT raw_json FROM slack_raw_import ORDER BY id DESC LIMIT 1
            """)).first()
            if row and row[0]:
                try:
                    payload = json.loads(row[0])
                    # Concatenate all message texts
                    chunks = []
                    for ch in payload:
                        for m in ch.get("messages", []):
                            t = m.get("text")
                            if t:
                                chunks.append(str(t))
                    source_text = "\n".join(chunks)
                except Exception:
                    source_text = ""

    if use_gemini and source_text:
        try:
            suggestions = call_gemini_for_skills(source_text)
            if suggestions:
                return jsonify({"suggested_skills": suggestions[:3]}), 200
        except Exception:
            # fall back to keyword matcher
            pass

    # Fallback keyword-based matcher
    lc = f" {source_text.lower()} "
    counts: Counter = Counter()
    for kw, skill in KEYWORD_TO_SKILL.items():
        if kw in lc:
            counts[skill] += lc.count(kw)
    ranked = [s for s, _ in counts.most_common() if s in SKILL_VOCAB][:3]
    return jsonify({"suggested_skills": ranked}), 200


def textwrap_sql(s: str) -> str:
    return s


def call_gemini_for_skills(source_text: str) -> list:
    """Call Gemini to map free text to top 3 skills from SKILL_VOCAB.
    Returns a list of skills (strings) present in SKILL_VOCAB.
    """
    if not GEMINI_API_KEY:
        return []

    # Build strict prompt
    vocab_list = "\n".join(f"- {s}" for s in SKILL_VOCAB)
    system_prompt = (
        "You are given internal Slack-like messages. From the content, infer the most relevant 3 skills "
        "STRICTLY chosen from the provided SKILL_VOCAB list. Respond ONLY with a compact JSON array of exactly 3 strings.\n\n"
        f"SKILL_VOCAB (canonical names):\n{vocab_list}\n\n"
        "Rules:\n"
        "- Only return skills from SKILL_VOCAB.\n"
        "- Return exactly 3 skills, best matching the text.\n"
        "- Prefer varied, specific skills that are clearly tied to the task context.\n"
        "- Avoid generic repeats (e.g., Leadership, Communication, Project Management) unless strongly justified by the text.\n"
        "- Diversify selections across similar tasks when reasonable.\n"
        "- Output must be valid JSON, no markdown, no extra commentary.\n"
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
    )
    payload = {
        "contents": [
            {"parts": [{"text": system_prompt}]},
            {"parts": [{"text": source_text[:20000]}]},  # safety limit
        ]
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    text_out = ""
    try:
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        text_out = ""

    # Extract JSON array from model output
    arr = []
    if text_out:
        m = re.search(r"\[(.*?)\]", text_out, re.S)
        if m:
            frag = "[" + m.group(1) + "]"
            try:
                parsed = json.loads(frag)
                if isinstance(parsed, list):
                    arr = [str(x) for x in parsed]
            except Exception:
                arr = []

    # Normalize and keep only known skills
    canon = {s.lower(): s for s in SKILL_VOCAB}
    out = []
    for x in arr:
        key = x.strip().lower()
        # try direct match; otherwise soft match by inclusion
        if key in canon:
            out.append(canon[key])
        else:
            # soft contain
            hit = next((canon[k] for k in canon.keys() if k in key), None)
            if hit:
                out.append(hit)
    # de-dupe and cap 3
    seen = set()
    dedup = []
    for s in out:
        if s not in seen and s in SKILL_VOCAB:
            seen.add(s)
            dedup.append(s)
    # Ensure exactly 3 skills, pad using text-based ranking then vocab
    chosen = dedup[:3]
    if len(chosen) < 3:
        lc = f" { (source_text or '').lower() } "
        counts = Counter()
        for kw, skill in KEYWORD_TO_SKILL.items():
            if kw in lc and skill in SKILL_VOCAB and skill not in chosen:
                counts[skill] += lc.count(kw)
        ranked = [s for s, _ in counts.most_common() if s not in chosen]
        for s in ranked:
            if len(chosen) >= 3:
                break
            chosen.append(s)
        if len(chosen) < 3:
            for s in SKILL_VOCAB:
                if s not in chosen:
                    chosen.append(s)
                if len(chosen) >= 3:
                    break
    return chosen[:3]


def call_gemini_for_subtasks(source_text: str) -> list[dict]:
    """Call Gemini to split an event description into up to 3 actionable, short tasks.
    Returns list of {title, description}.
    """
    if not GEMINI_API_KEY:
        return []

    system_prompt = (
        "You are given an event description. Create exactly 3 concise, actionable volunteer tasks.\n"
        "Each task should have:\n- title (<= 8 words)\n- description (1 short sentence).\n"
        "Respond ONLY with a JSON array of 3 objects with keys: title, description. No markdown."
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
    )
    payload = {
        "contents": [
            {"parts": [{"text": system_prompt}]},
            {"parts": [{"text": source_text[:20000]}]},
        ]
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    text_out = ""
    try:
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        text_out = ""

    tasks = []
    if text_out:
        m = re.search(r"\[(.*?)\]", text_out, re.S)
        if m:
            frag = "[" + m.group(1) + "]"
            try:
                parsed = json.loads(frag)
                if isinstance(parsed, list):
                    for obj in parsed[:3]:
                        if isinstance(obj, dict) and obj.get("title"):
                            tasks.append({
                                "title": str(obj.get("title"))[:120],
                                "description": str(obj.get("description", ""))[:280]
                            })
            except Exception:
                tasks = []
    return tasks[:3]


def call_gemini_rank_tasks(user_skills: list[str], tasks: list[dict]) -> list[str]:
    """Ask Gemini to pick up to 5 best task ids for a user based on skill fit.

    tasks: each item must contain {id, title, description, skills_required}
    Returns list of task ids (strings).
    """
    if not GEMINI_API_KEY or not tasks:
        return []

    # Build concise candidate list
    lines = []
    for t in tasks[:50]:  # cap prompt size
        sid = str(t.get("id"))
        title = str(t.get("title", ""))[:120]
        desc = str(t.get("description", ""))[:240]
        sk = ", ".join(t.get("skills_required") or [])
        lines.append(f"id={sid} | title={title} | skills=[{sk}] | desc={desc}")

    vocab_list = "\n".join(f"- {s}" for s in SKILL_VOCAB)
    sys_prompt = (
        "Given a user's skills and a set of candidate tasks (with skills), pick up to 5 tasks that best match.\n"
        "Respond ONLY with a JSON array of task ids (strings). No extra text.\n\n"
        f"USER_SKILLS: {', '.join(user_skills)}\n\n"
        f"SKILL_VOCAB (canonical):\n{vocab_list}\n\n"
        "CANDIDATES (one per line):\n" + "\n".join(lines)
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
    )
    payload = {"contents": [{"parts": [{"text": sys_prompt}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return []

    # Parse JSON array of ids
    out = []
    m = re.search(r"\[(.*?)\]", text_out or "", re.S)
    if m:
        frag = "[" + m.group(1) + "]"
        try:
            parsed = json.loads(frag)
            if isinstance(parsed, list):
                out = [str(x) for x in parsed][:5]
        except Exception:
            out = []
    return out

# -------------------------
# List Events (for admin/review)
# -------------------------
@app.get("/api/events")
@jwt_required()
def list_events():
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT 
              e.id, e.organization_id, e.title, e.description, e.mode,
              e.location_city, e.location_state, e.is_remote, e.causes,
              e.skills_needed, e.tags, e.min_duration_min, e.rsvp_url, e.contact_email,
              e.created_at, e.updated_at,
              (
                SELECT COALESCE(COUNT(DISTINCT utr.user_id), 0)
                FROM user_task_registration utr
                JOIN event_task et ON et.id = utr.task_id
                WHERE et.event_id = e.id
              ) AS total_registered_count,
              (SELECT MIN(start_ts) FROM event_task et WHERE et.event_id = e.id) AS event_start_ts,
              (SELECT MAX(end_ts)   FROM event_task et WHERE et.event_id = e.id) AS event_end_ts,
              COALESCE((
                SELECT ARRAY(
                  SELECT DISTINCT s
                  FROM event_task et, unnest(et.skills_required) AS s
                  WHERE et.event_id = e.id AND s IS NOT NULL
                )
              ), ARRAY[]::TEXT[]) AS event_skills,
              EXISTS (
                SELECT 1
                FROM user_task_registration utr
                JOIN event_task et2 ON et2.id = utr.task_id
                WHERE utr.user_id = :uid AND et2.event_id = e.id
              ) AS user_registered
            FROM event e
            ORDER BY e.created_at DESC
        """), {"uid": user_id}).mappings().all()
    return jsonify({"events": [dict(r) for r in rows]}), 200

# -------------------------
# Task Management Endpoints
# -------------------------
@app.post("/api/events/<uuid:event_id>/tasks")
@jwt_required()
def create_event_task(event_id):
    """Create a new task for an event"""
    data = request.get_json()
    _require_fields(data, ["title"])  # description optional
    
    with SessionLocal() as db:
        # Check if event exists
        event = db.execute(text("SELECT id FROM event WHERE id = :event_id"), {"event_id": event_id}).mappings().first()
        if not event:
            return jsonify({"error": "Event not found"}), 404
        
        # Decide skills_required
        provided_skills = _as_list(data.get("skills_required", ""))
        skills_required = provided_skills

        # Optionally infer using Gemini (or fallback keywords) from title+description
        if not skills_required or data.get("use_gemini"):
            td_text = f"{data.get('title','')}.\n{data.get('description','')}"
            inferred: list[str] = []
            try:
                if data.get("use_gemini") and GEMINI_API_KEY:
                    inferred = call_gemini_for_skills(td_text) or []
            except Exception:
                inferred = []
            # fallback keyword-based if still empty
            if not inferred:
                lc = f" {td_text.lower()} "
                counts = Counter()
                for kw, skill in KEYWORD_TO_SKILL.items():
                    if kw in lc:
                        counts[skill] += lc.count(kw)
                inferred = [s for s, _ in counts.most_common() if s in SKILL_VOCAB][:3]

            # merge with provided, cap 3
            merged = []
            for s in (provided_skills + inferred):
                if s and s in SKILL_VOCAB and s not in merged:
                    merged.append(s)
            skills_required = merged[:3]

        # Create task
        task = db.execute(text("""
            INSERT INTO event_task (event_id, title, description, skills_required, estimated_duration_min, priority, status, start_ts, end_ts)
            VALUES (:event_id, :title, :description, :skills_required, :estimated_duration_min, :priority, :status, :start_ts, :end_ts)
            RETURNING id, event_id, title, description, skills_required, estimated_duration_min, priority, status, assigned_to, start_ts, end_ts, registered_count, created_at, updated_at
        """), {
            "event_id": event_id,
            "title": data["title"],
            "description": data.get("description", ""),
            "skills_required": skills_required,
            "estimated_duration_min": data.get("estimated_duration_min"),
            "priority": data.get("priority", "medium"),
            "status": data.get("status", "open"),
            "start_ts": data.get("start_ts"),
            "end_ts": data.get("end_ts")
        }).mappings().first()
        
        db.commit()
        return jsonify({"task": dict(task)}), 201

@app.get("/api/events/<uuid:event_id>/tasks")
@jwt_required()
def get_event_tasks(event_id):
    """Get all tasks for an event"""
    with SessionLocal() as db:
        tasks = db.execute(text("""
            SELECT 
              et.id, et.event_id, et.title, et.description, et.skills_required, et.estimated_duration_min, 
              et.priority, et.status, et.assigned_to, et.start_ts, et.end_ts, et.registered_count,
              et.created_at, et.updated_at,
              EXISTS (
                SELECT 1 FROM user_task_registration utr
                WHERE utr.user_id = :uid AND utr.task_id = et.id
              ) AS user_registered
            FROM event_task et
            WHERE et.event_id = :event_id
            ORDER BY et.created_at DESC
        """), {"event_id": event_id, "uid": get_jwt_identity()}).mappings().all()
        
        return jsonify({"tasks": [dict(t) for t in tasks]}), 200

@app.get("/api/tasks/recommended")
@jwt_required()
def get_recommended_event_tasks():
    """Recommend up to 5 tasks for the user. If GEMINI_API_KEY is set and use_gemini=true in query,
    use Gemini to rank tasks, else use simple overlap scoring."""
    user_id = get_jwt_identity()

    with SessionLocal() as db:
        usr = db.execute(text("""
            SELECT skills FROM app_user WHERE id = :uid
        """), {"uid": user_id}).mappings().first()
        if not usr:
            return jsonify({"error": "User not found"}), 404
        user_skills = (usr.get("skills") or [])

        tasks = db.execute(text("""
            SELECT 
              et.id, et.event_id, et.title, et.description, et.skills_required, et.priority, et.status, 
              et.start_ts, et.end_ts, et.registered_count, et.created_at,
              COALESCE((
                SELECT ARRAY(
                  SELECT DISTINCT s
                  FROM event_task etx, unnest(etx.skills_required) AS s
                  WHERE etx.event_id = et.event_id AND s IS NOT NULL
                )
              ), ARRAY[]::TEXT[]) AS event_skills,
              EXISTS (
                SELECT 1 FROM user_task_registration utr1
                WHERE utr1.user_id = :uid AND utr1.task_id = et.id
              ) AS user_registered_task,
              EXISTS (
                SELECT 1 
                FROM user_task_registration utr2
                JOIN event_task et2 ON et2.id = utr2.task_id
                WHERE utr2.user_id = :uid AND et2.event_id = et.event_id
              ) AS user_registered_event
            FROM event_task et
            WHERE et.status = 'open'
              AND NOT EXISTS (
                SELECT 1 FROM user_task_registration utr
                WHERE utr.user_id = :uid AND utr.task_id = et.id
              )
            ORDER BY et.created_at DESC
        """), {"uid": user_id}).mappings().all()

        # Gemini-based ranking if requested
        from flask import request as _rq
        if _rq.args.get("use_gemini") == "true" and GEMINI_API_KEY:
            wanted_ids = set(call_gemini_rank_tasks(user_skills, [dict(t) for t in tasks]))
            if wanted_ids:
                ranked = [t for t in tasks if str(t["id"]) in wanted_ids]
                return jsonify({"tasks": [dict(t) for t in ranked]}), 200
            # fall back to overlap scoring if Gemini returned nothing

        # Fallback overlap scoring
        def score(t):
            ts = t.get("skills_required") or []
            return len({s for s in ts if s in user_skills})
        ranked = sorted(tasks, key=score, reverse=True)[:5]
        return jsonify({"tasks": [dict(t) for t in ranked]}), 200

@app.get("/api/tasks/registered")
@jwt_required()
def get_registered_tasks():
    """Return tasks the current user has registered for"""
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT 
              et.id, et.event_id, et.title, et.description, et.skills_required, et.priority, et.status,
              et.start_ts, et.end_ts, et.registered_count, et.created_at, et.updated_at,
              COALESCE((
                SELECT ARRAY(
                  SELECT DISTINCT s
                  FROM event_task etx, unnest(etx.skills_required) AS s
                  WHERE etx.event_id = et.event_id AND s IS NOT NULL
                )
              ), ARRAY[]::TEXT[]) AS event_skills,
              e.title AS event_title
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            JOIN event e ON e.id = et.event_id
            WHERE utr.user_id = :uid
            ORDER BY et.created_at DESC
        """), {"uid": user_id}).mappings().all()
    # mark as user_registered=true in response
    out = []
    for r in rows:
        d = dict(r)
        d["user_registered"] = True
        out.append(d)
    return jsonify({"tasks": out}), 200

@app.put("/api/tasks/<uuid:task_id>/assign")
@jwt_required()
def assign_task(task_id):
    """Assign a task to the current user"""
    user_id = get_jwt_identity()
    
    with SessionLocal() as db:
        # Check if task exists and is available
        task = db.execute(text("""
            SELECT id, status, assigned_to FROM event_task WHERE id = :task_id
        """), {"task_id": task_id}).mappings().first()
        
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        if task["status"] != "open":
            return jsonify({"error": "Task is not available for assignment"}), 400
        
        # Assign task to user
        db.execute(text("""
            UPDATE event_task 
            SET assigned_to = :user_id, status = 'claimed', updated_at = now()
            WHERE id = :task_id
        """), {"user_id": user_id, "task_id": task_id})
        
        db.commit()
        return jsonify({"message": "Task assigned successfully"}), 200

@app.get("/api/tasks/my-tasks")
@jwt_required()
def get_my_tasks():
    """Get tasks assigned to the current user"""
    user_id = get_jwt_identity()
    
    with SessionLocal() as db:
        tasks = db.execute(text("""
            SELECT et.id, et.event_id, et.title, et.description, et.skills_required, 
                   et.estimated_duration_min, et.priority, et.status, et.created_at, et.updated_at,
                   e.title as event_title
            FROM event_task et
            JOIN event e ON et.event_id = e.id
            WHERE et.assigned_to = :user_id
            ORDER BY et.created_at DESC
        """), {"user_id": user_id}).mappings().all()
        
        return jsonify({"tasks": [dict(t) for t in tasks]}), 200

@app.put("/api/tasks/<uuid:task_id>/complete")
@jwt_required()
def complete_task(task_id):
    """Mark a task as completed"""
    user_id = get_jwt_identity()
    
    with SessionLocal() as db:
        # Check if task is assigned to user
        task = db.execute(text("""
            SELECT id, assigned_to, status FROM event_task WHERE id = :task_id
        """), {"task_id": task_id}).mappings().first()
        
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        if str(task["assigned_to"]) != str(user_id):
            return jsonify({"error": "Task is not assigned to you"}), 403
        
        if task["status"] not in ["claimed", "in_progress"]:
            return jsonify({"error": "Task cannot be completed in current status"}), 400
        
        # Mark task as completed
        db.execute(text("""
            UPDATE event_task 
            SET status = 'completed', updated_at = now()
            WHERE id = :task_id
        """), {"task_id": task_id})
        
        db.commit()
        return jsonify({"message": "Task completed successfully"}), 200

@app.post("/api/tasks/<uuid:task_id>/register")
@jwt_required()
def register_for_task(task_id):
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        exists = db.execute(text("""
            SELECT 1 FROM user_task_registration WHERE user_id=:uid AND task_id=:tid
        """), {"uid": user_id, "tid": task_id}).first()
        if exists:
            return jsonify({"message": "Already registered"}), 200

        ok = db.execute(text("""
            INSERT INTO user_task_registration (user_id, task_id)
            VALUES (:uid, :tid)
            RETURNING user_id
        """), {"uid": user_id, "tid": task_id}).first()
        if not ok:
            return jsonify({"error": "Unable to register"}), 400

        db.execute(text("""
            UPDATE event_task 
            SET registered_count = COALESCE(registered_count,0) + 1, updated_at=now()
            WHERE id = :tid
        """), {"tid": task_id})
        db.commit()
        return jsonify({"message": "Registered"}), 200

@app.delete("/api/tasks/<uuid:task_id>/register")
@jwt_required()
def unregister_for_task(task_id):
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        existed = db.execute(text("""
            DELETE FROM user_task_registration 
            WHERE user_id=:uid AND task_id=:tid
            RETURNING 1
        """), {"uid": user_id, "tid": task_id}).first()

        if not existed:
            return jsonify({"message": "Not registered"}), 200

        db.execute(text("""
            UPDATE event_task 
            SET registered_count = GREATEST(COALESCE(registered_count,0) - 1, 0), updated_at=now()
            WHERE id = :tid
        """), {"tid": task_id})
        db.commit()
        return jsonify({"message": "Unregistered"}), 200

# -------------------------
# Home Page Endpoints
# -------------------------
@app.get("/api/home/recommended-tasks")
@jwt_required()
def get_recommended_tasks():
    """Get 5 recommended tasks for the user"""
    user_id = get_jwt_identity()
    
    # For now, return empty data structure
    # Later this will be populated with actual recommendations
    return {
        "tasks": [],
        "message": "No recommended tasks available yet. Data will be populated soon."
    }, 200

@app.get("/api/home/trending-events")
@jwt_required()
def get_trending_events():
    """Top 5 events ranked by total registrations across their tasks"""
    user_id = get_jwt_identity()
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT 
              e.id, e.organization_id, e.title, e.description, e.mode,
              e.location_city, e.location_state, e.is_remote, e.causes,
              e.skills_needed, e.tags, e.min_duration_min, e.rsvp_url, e.contact_email,
              e.created_at, e.updated_at,
              COALESCE((SELECT SUM(registered_count)::int FROM event_task et WHERE et.event_id = e.id), 0) AS total_registered_count,
              (SELECT MIN(start_ts) FROM event_task et WHERE et.event_id = e.id) AS event_start_ts,
              (SELECT MAX(end_ts)   FROM event_task et WHERE et.event_id = e.id) AS event_end_ts,
              EXISTS (
                SELECT 1
                FROM user_task_registration utr
                JOIN event_task et2 ON et2.id = utr.task_id
                WHERE utr.user_id = :uid AND et2.event_id = e.id
              ) AS user_registered
            FROM event e
            ORDER BY total_registered_count DESC NULLS LAST, e.created_at DESC
            LIMIT 5
        """), {"uid": user_id}).mappings().all()
    return jsonify({"events": [dict(r) for r in rows]}), 200

@app.get("/api/home/analytics")
@jwt_required()
def get_analytics():
    """Get user analytics dashboard data (computed)"""
    user_id = get_jwt_identity()
    now = datetime.now(timezone.utc)
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Compute first day of last month
    last_month_year = first_day_this_month.year if first_day_this_month.month > 1 else first_day_this_month.year - 1
    last_month_month = first_day_this_month.month - 1 if first_day_this_month.month > 1 else 12
    first_day_last_month = first_day_this_month.replace(year=last_month_year, month=last_month_month)

    with SessionLocal() as db:
        # User skills
        user_row = db.execute(text("""
            SELECT skills FROM app_user WHERE id = :uid
        """), {"uid": user_id}).mappings().first()
        user_skills = list(user_row.get("skills") or []) if user_row else []

        # Registrations with timestamps, event titles, task start_ts and skills
        regs = db.execute(text("""
            SELECT 
              utr.registered_at,
              et.event_id,
              e.title AS event_title,
              et.start_ts AS task_start_ts,
              et.skills_required
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            JOIN event e ON e.id = et.event_id
            WHERE utr.user_id = :uid
        """), {"uid": user_id}).mappings().all()

    # Distinct registered events overall
    distinct_events_all = {r["event_id"] for r in regs if r.get("event_id")}

    # This month and last month using registration time
    this_month_events = set()
    last_month_events = set()
    for r in regs:
        rat = r.get("registered_at")
        ev_id = r.get("event_id")
        tstart = r.get("task_start_ts")
        if not ev_id:
            continue
        # Prefer task/event start time window to bucket by month; fallback to registration time
        ref_time = tstart or rat
        if not ref_time:
            continue
        if ref_time >= first_day_this_month:
            this_month_events.add(ev_id)
        elif first_day_last_month <= ref_time < first_day_this_month:
            last_month_events.add(ev_id)

    # Top interests derived from registered task skills (aggregate)
    skill_counts = Counter()
    for r in regs:
        skills = r.get("skills_required") or []
        for s in skills:
            if s:
                skill_counts[s] += 1
    top_interests = [s for s, _ in skill_counts.most_common(5)]

    # Simple monthly goal (static 5) and progress
    goal = 5
    current = len(this_month_events)
    percentage = int(round(100 * current / goal)) if goal > 0 else 0

    # Build distinct registered event names sorted by most recent relevant time
    ev_latest: dict[str, tuple[datetime, str]] = {}
    for r in regs:
        ev_id = r.get("event_id")
        title = r.get("event_title") or "Event"
        ref_time = r.get("task_start_ts") or r.get("registered_at") or now
        if ev_id and (ev_id not in ev_latest or ref_time > ev_latest[ev_id][0]):
            ev_latest[ev_id] = (ref_time, title)
    registered_event_names = [t for _, t in sorted(ev_latest.values(), key=lambda x: x[0], reverse=True)]

    payload = {
        "registered_events": {
            "total": len(distinct_events_all),
            "this_month": len(this_month_events),
            "last_month": len(last_month_events),
            "trend": "no_data" if not regs else ("up" if len(this_month_events) >= len(last_month_events) else "down"),
            "names": registered_event_names
        },
        "top_skills": user_skills[:5],
        "top_interests": top_interests,
        "progress": {
            "goal": goal,
            "current": current,
            "percentage": percentage,
            "message": "Keep going!"
        },
        "communities": {
            "registered": [],
            "leaderboard": []
        }
    }
    return payload, 200

@app.get("/api/home/communities")
@jwt_required()
def get_communities():
    """Get user's communities and leaderboard ranked by registrations."""
    user_id = get_jwt_identity()

    with SessionLocal() as db:
        me = db.execute(text("""
            SELECT department_id, erg_id FROM app_user WHERE id = :uid
        """), {"uid": user_id}).mappings().first()

        # Department leaderboard
        dept_rows = db.execute(text("""
            SELECT d.id AS id, 'department'::text AS kind, d.name AS name,
                   COALESCE(COUNT(utr.user_id), 0) AS score
            FROM department d
            LEFT JOIN app_user au ON au.department_id = d.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY d.id, d.name
        """)).mappings().all()

        # ERG leaderboard
        erg_rows = db.execute(text("""
            SELECT e.id AS id, 'erg'::text AS kind, e.name AS name,
                   COALESCE(COUNT(utr.user_id), 0) AS score
            FROM erg e
            LEFT JOIN app_user au ON au.erg_id = e.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY e.id, e.name
        """)).mappings().all()

    combined = []
    for r in dept_rows:
        combined.append({
            "id": r["id"],
            "kind": r["kind"],
            "name": f"Dept: {r['name']}",
            "score": int(r["score"] or 0),
        })
    for r in erg_rows:
        combined.append({
            "id": r["id"],
            "kind": r["kind"],
            "name": f"ERG: {r['name']}",
            "score": int(r["score"] or 0),
        })

    # Rank by score desc (dense ranking)
    combined.sort(key=lambda x: (-x["score"], x["name"]))
    last_score = None
    rank = 0
    for i, item in enumerate(combined):
        if item["score"] != last_score:
            rank = i + 1
            last_score = item["score"]
        item["rank"] = rank

    # User communities with ranks
    user_communities = []
    if me:
        if me.get("department_id") is not None:
            for c in combined:
                if c["kind"] == "department" and c["id"] == me["department_id"]:
                    user_communities.append({"name": c["name"], "rank": c["rank"]})
                    break
        if me.get("erg_id") is not None:
            for c in combined:
                if c["kind"] == "erg" and c["id"] == me["erg_id"]:
                    user_communities.append({"name": c["name"], "rank": c["rank"]})
                    break

    # Only show top 10 entries on the user view
    combined_top = combined[:10]
    return jsonify({
        "user_communities": user_communities,
        "leaderboard": [{"name": c["name"], "score": c["score"]} for c in combined_top]
    }), 200

# -------------------------
# Admin: Backfill/normalize task skills to exactly three per task
# -------------------------
@app.post("/api/admin/backfill-task-skills")
@jwt_required()
def backfill_task_skills():
    """Ensure every event_task has exactly three skills_required.

    Optional query param: rerun_all=true to recompute for all tasks; otherwise
    only tasks with < 3 skills are processed.
    """
    from flask import request as _rq
    rerun_all = (_rq.args.get("rerun_all") == "true")

    with SessionLocal() as db:
        if rerun_all:
            rows = db.execute(text(
                """
                SELECT id, title, description FROM event_task
                """
            )).mappings().all()
        else:
            rows = db.execute(text(
                """
                SELECT id, title, description, COALESCE(array_length(skills_required,1),0) AS n
                FROM event_task
                WHERE COALESCE(array_length(skills_required,1),0) < 3
                """
            )).mappings().all()

        updated = 0
        for r in rows:
            text_src = f"{r.get('title') or ''}. {r.get('description') or ''}"
            skills: list[str] = []
            try:
                if GEMINI_API_KEY:
                    skills = call_gemini_for_skills(text_src) or []
            except Exception:
                skills = []
            if not skills:
                # fallback keyword matcher
                lc = f" {text_src.lower()} "
                counts = Counter()
                for kw, skill in KEYWORD_TO_SKILL.items():
                    if kw in lc and skill in SKILL_VOCAB:
                        counts[skill] += lc.count(kw)
                skills = [s for s, _ in counts.most_common() if s in SKILL_VOCAB][:3]
            # enforce exactly three
            if len(skills) < 3:
                lc = f" {text_src.lower()} "
                counts = Counter()
                for kw, skill in KEYWORD_TO_SKILL.items():
                    if kw in lc and skill in SKILL_VOCAB and skill not in skills:
                        counts[skill] += lc.count(kw)
                ranked = [s for s, _ in counts.most_common() if s not in skills]
                for s in ranked:
                    if len(skills) >= 3:
                        break
                    skills.append(s)
                if len(skills) < 3:
                    for s in SKILL_VOCAB:
                        if s not in skills:
                            skills.append(s)
                        if len(skills) >= 3:
                            break
            skills = skills[:3]

            db.execute(text(
                "UPDATE event_task SET skills_required=:skills, updated_at=now() WHERE id=:id"
            ), {"skills": skills, "id": r["id"]})
            updated += 1

        db.commit()
    return jsonify({"updated": updated}), 200
# -------------------------
# Admin: Reset and seed events and LLM subtasks
# -------------------------
@app.post("/api/admin/reset_and_seed_events")
@jwt_required()
def reset_and_seed_events():
    """Deletes all existing event_task rows, creates events from payload, and
    generates LLM subtasks for each event.

    Body: { events: [ { task, description, skill1, skill2, skill3, start_ts, end_ts, mode } ] }
    """
    data = request.get_json(silent=True) or {}
    items = data.get("events") or []
    if not isinstance(items, list):
        return jsonify({"error": "events must be an array"}), 400

    def map_mode(m):
        if not m:
            return "virtual"
        m = str(m).lower()
        return "virtual" if m in ("remote", "virtual") else ("in_person" if m == "in_person" else "hybrid")

    created = []
    with SessionLocal() as db:
        # Delete all existing subtasks only
        db.execute(text("DELETE FROM event_task"))
        db.commit()

        for it in items:
            title = (it.get("task") or "Event").strip()
            desc = it.get("description") or ""
            s1, s2, s3 = it.get("skill1"), it.get("skill2"), it.get("skill3")
            start_ts = it.get("start_ts")
            end_ts = it.get("end_ts")
            mode = map_mode(it.get("mode"))
            skills_seed = [s for s in [s1, s2, s3] if s]

            # Insert event (with minimal required arrays)
            ev = db.execute(text("""
                INSERT INTO event (organization_id, title, description, mode,
                                   location_city, location_state, is_remote,
                                   causes, skills_needed, tags, min_duration_min, rsvp_url, contact_email)
                VALUES (NULL, :title, :description, :mode,
                        NULL, NULL, :is_remote,
                        :causes, :skills_needed, '{}', 60, NULL, NULL)
                RETURNING id, title
            """), {
                "title": title,
                "description": desc,
                "mode": mode,
                "is_remote": True if mode == "virtual" else False,
                "causes": [],
                "skills_needed": skills_seed or []
            }).mappings().first()

            # Generate LLM subtasks
            try:
                subtasks = call_gemini_for_subtasks(f"{title}\n\n{desc}") or []
            except Exception:
                subtasks = []
            if not subtasks:
                subtasks = [{"title": title[:120], "description": desc[:280]}]

            for st in subtasks:
                # infer skills per subtask
                inferred = []
                try:
                    inferred = call_gemini_for_skills(f"{st.get('title','')}. {st.get('description','')}") or []
                except Exception:
                    inferred = []
                if not inferred:
                    lc = f" {st.get('title','').lower()} {st.get('description','').lower()} "
                    counts = Counter()
                    for kw, skill in KEYWORD_TO_SKILL.items():
                        if kw in lc:
                            counts[skill] += lc.count(kw)
                    inferred = [s for s, _ in counts.most_common() if s in SKILL_VOCAB][:3]

                db.execute(text("""
                    INSERT INTO event_task (event_id, title, description, skills_required, priority, status, start_ts, end_ts)
                    VALUES (:event_id, :title, :description, :skills_required, 'medium', 'open', :start_ts, :end_ts)
                """), {
                    "event_id": ev["id"],
                    "title": st.get("title") or "Task",
                    "description": st.get("description") or "",
                    "skills_required": inferred,
                    "start_ts": start_ts,
                    "end_ts": end_ts
                })
            db.commit()
            created.append({"event_id": str(ev["id"]), "title": ev["title"], "subtasks": len(subtasks)})

    return jsonify({"seeded": len(created), "events": created}), 200


# -------------------------
# Admin: Seed leaderboard with fake users/registrations (for demo)
# -------------------------
@app.post("/api/admin/seed_leaderboard")
@jwt_required()
def seed_leaderboard():
    """Create a synthetic event/task and add fake users with registrations
    to generate leaderboard points for departments and ERGs. Only shows top 10
    in the user view.

    Body (optional): { per_group_min?: int, per_group_max?: int }
    """
    data = request.get_json(silent=True) or {}
    per_min = int(data.get("per_group_min", 3))
    per_max = int(data.get("per_group_max", 12))
    if per_min < 1: per_min = 1
    if per_max < per_min: per_max = per_min

    with SessionLocal() as db:
        # Ensure synthetic event/task exists
        ev = db.execute(text(
            "SELECT id FROM event WHERE title = :t"
        ), {"t": "Synthetic Leaderboard Seed Event"}).mappings().first()
        if not ev:
            ev = db.execute(text(
                """
                INSERT INTO event (organization_id, title, description, mode, causes, skills_needed, tags)
                VALUES (NULL, :title, :desc, 'virtual', '{}', '{demo}', '{}')
                RETURNING id
                """
            ), {"title": "Synthetic Leaderboard Seed Event", "desc": "Synthetic event for leaderboard seeding"}).mappings().first()
        task = db.execute(text(
            "SELECT id FROM event_task WHERE event_id = :eid AND title = :tt"
        ), {"eid": ev["id"], "tt": "Synthetic Leaderboard Seed Task"}).mappings().first()
        if not task:
            task = db.execute(text(
                """
                INSERT INTO event_task (event_id, title, description, skills_required, priority, status)
                VALUES (:eid, :title, 'Synthetic task for seeding', '{seed,points,demo}', 'medium', 'open')
                RETURNING id
                """
            ), {"eid": ev["id"], "title": "Synthetic Leaderboard Seed Task"}).mappings().first()

        # Helper to create a fake user and register once
        def create_user_and_register(dept_id=None, dept_name=None, erg_id=None, erg_name=None):
            email = f"seed_{random.randint(10_000_000,99_999_999)}@example.com"
            full_name = f"Seed User {random.randint(1000,9999)}"
            row = db.execute(text(
                """
                INSERT INTO app_user (email, full_name, department_id, dept, erg_id, erg)
                VALUES (:email, :full_name, :department_id, :dept, :erg_id, :erg)
                RETURNING id
                """
            ), {
                "email": email,
                "full_name": full_name,
                "department_id": dept_id,
                "dept": dept_name,
                "erg_id": erg_id,
                "erg": erg_name
            }).first()
            if row and row[0]:
                db.execute(text(
                    "INSERT INTO user_task_registration (user_id, task_id) VALUES (:uid, :tid) ON CONFLICT DO NOTHING"
                ), {"uid": row[0], "tid": task["id"]})

        # Departments
        depts = db.execute(text("SELECT id, name FROM department ORDER BY name" )).mappings().all()
        for d in depts:
            count = random.randint(per_min, per_max)
            for _ in range(count):
                create_user_and_register(dept_id=d["id"], dept_name=d["name"], erg_id=None, erg_name=None)

        # ERGs
        ergs = db.execute(text("SELECT id, name FROM erg ORDER BY name" )).mappings().all()
        for e in ergs:
            count = random.randint(per_min, per_max)
            for _ in range(count):
                create_user_and_register(dept_id=None, dept_name=None, erg_id=e["id"], erg_name=e["name"]) 

        db.commit()

        # Return top 10 combined snapshot
        rows = db.execute(text(
            """
            SELECT 'Dept: '||d.name AS name, COALESCE(COUNT(utr.user_id),0) AS score
            FROM department d
            LEFT JOIN app_user au ON au.department_id = d.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY d.name
            UNION ALL
            SELECT 'ERG: '||e.name AS name, COALESCE(COUNT(utr.user_id),0) AS score
            FROM erg e
            LEFT JOIN app_user au ON au.erg_id = e.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY e.name
            ORDER BY score DESC, name ASC
            LIMIT 10
            """
        )).mappings().all()

    return jsonify({"seeded_departments": len(depts), "seeded_ergs": len(ergs), "top10": [{"name": r["name"], "score": int(r["score"] or 0)} for r in rows]}), 200
# -------------------------
# Company Analytics Endpoints
# -------------------------
@app.get("/api/company/overview")
@jwt_required()
def get_company_overview():
    """Company-wide overview statistics from live data"""
    now = datetime.now(timezone.utc)
    start_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_year = start_this_month.year if start_this_month.month > 1 else start_this_month.year - 1
    prev_month_month = start_this_month.month - 1 if start_this_month.month > 1 else 12
    start_prev_month = start_this_month.replace(year=prev_month_year, month=prev_month_month)

    with SessionLocal() as db:
        total_employees = db.execute(text("SELECT COUNT(*) FROM app_user")).scalar() or 0
        active_volunteers = db.execute(text("SELECT COUNT(DISTINCT user_id) FROM user_task_registration")).scalar() or 0
        total_minutes = db.execute(text(
            """
            SELECT COALESCE(SUM(et.estimated_duration_min),0)
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            """
        )).scalar() or 0
        total_hours = int(round(total_minutes / 60))
        total_events_completed = db.execute(text("SELECT COUNT(*) FROM event_task WHERE status='completed'" )).scalar() or 0
        avg_hours_per_volunteer = (total_hours / active_volunteers) if active_volunteers else 0

        current_month_regs = db.execute(text(
            "SELECT COUNT(*) FROM user_task_registration WHERE registered_at >= :t"
        ), {"t": start_this_month}).scalar() or 0
        prev_month_regs = db.execute(text(
            "SELECT COUNT(*) FROM user_task_registration WHERE registered_at >= :a AND registered_at < :b"
        ), {"a": start_prev_month, "b": start_this_month}).scalar() or 0
        growth_percentage = 0
        if prev_month_regs:
            growth_percentage = int(round((current_month_regs - prev_month_regs) * 100 / prev_month_regs))

        top_departments = db.execute(text(
            """
            SELECT d.name AS name, COALESCE(COUNT(utr.user_id),0) AS score
            FROM department d
            LEFT JOIN app_user au ON au.department_id = d.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY d.name
            ORDER BY score DESC, d.name ASC
            LIMIT 5
            """
        )).mappings().all()

    return {
        "total_employees": total_employees,
        "active_volunteers": active_volunteers,
        "participation_rate": int(round((active_volunteers * 100) / total_employees)) if total_employees else 0,
        "total_hours_volunteered": total_hours,
        "total_events_completed": total_events_completed,
        "average_hours_per_volunteer": int(round(avg_hours_per_volunteer)),
        "top_departments": [{"name": r["name"], "score": int(r["score"] or 0)} for r in top_departments],
        "monthly_trends": {
            "current_month": current_month_regs,
            "previous_month": prev_month_regs,
            "growth_percentage": growth_percentage
        }
    }, 200

@app.get("/api/company/engagement")
@jwt_required()
def get_engagement_metrics():
    """Employee engagement and participation metrics"""
    now = datetime.now(timezone.utc)
    last_90 = now - timedelta(days=90)
    last_60 = now - timedelta(days=60)

    with SessionLocal() as db:
        total_users = db.execute(text("SELECT COUNT(*) FROM app_user")).scalar() or 0
        rows = db.execute(text(
            """
            SELECT au.id AS user_id, COALESCE(COUNT(utr.user_id),0) AS cnt
            FROM app_user au
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY au.id
            """
        )).mappings().all()
        cnts = [int(r["cnt"] or 0) for r in rows]
        highly = sum(1 for c in cnts if c >= 5)
        moderate = sum(1 for c in cnts if 2 <= c <= 4)
        low = sum(1 for c in cnts if c == 1)
        none = sum(1 for c in cnts if c == 0)

        skills90 = db.execute(text(
            """
            SELECT DISTINCT s
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            CROSS JOIN LATERAL UNNEST(et.skills_required) AS s
            WHERE utr.registered_at >= :t
            """
        ), {"t": last_90}).scalars().all()
        new_skills = len([s for s in skills90 if s])
        minutes90 = db.execute(text(
            """
            SELECT COALESCE(SUM(et.estimated_duration_min),0)
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            WHERE utr.registered_at >= :t
            """
        ), {"t": last_90}).scalar() or 0
        learning_hours = int(round(minutes90 / 60))
        skill_counts = db.execute(text(
            """
            SELECT s AS skill, COUNT(*) AS c
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            CROSS JOIN LATERAL UNNEST(et.skills_required) AS s
            GROUP BY s
            ORDER BY c DESC
            LIMIT 5
            """
        )).mappings().all()

        active_volunteers = db.execute(text("SELECT COUNT(DISTINCT user_id) FROM user_task_registration")).scalar() or 0
        recent_active = db.execute(text(
            "SELECT COUNT(DISTINCT user_id) FROM user_task_registration WHERE registered_at >= :t"
        ), {"t": last_60}).scalar() or 0
        retention_rate = int(round((recent_active * 100) / active_volunteers)) if active_volunteers else 0

    return {
        "participation_breakdown": {
            "highly_engaged": int(round(highly * 100 / total_users)) if total_users else 0,
            "moderately_engaged": int(round(moderate * 100 / total_users)) if total_users else 0,
            "low_engagement": int(round(low * 100 / total_users)) if total_users else 0,
            "not_participated": int(round(none * 100 / total_users)) if total_users else 0
        },
        "department_participation": [],
        "skill_development": {
            "new_skills_learned": new_skills,
            "skill_categories": [r["skill"] for r in skill_counts],
            "learning_hours": learning_hours
        },
        "retention_impact": {
            "volunteer_retention_rate": retention_rate,
            "satisfaction_score": 0,
            "recommendation_rate": 0
        }
    }, 200

@app.get("/api/company/impact")
@jwt_required()
def get_impact_analytics():
    """Community impact and social value metrics"""
    with SessionLocal() as db:
        communities_served = db.execute(text(
            "SELECT COUNT(DISTINCT department_id) FROM app_user au JOIN user_task_registration utr ON utr.user_id = au.id"
        )).scalar() or 0
        projects_completed = db.execute(text("SELECT COUNT(*) FROM event_task WHERE status='completed'" )).scalar() or 0
    return {
        "community_impact": {
            "communities_served": communities_served,
            "people_helped": 0,
            "projects_completed": projects_completed,
            "social_value_created": 0
        },
        "cause_areas": {},
        "geographic_reach": {
            "cities_served": 0,
            "states_covered": 0,
            "international_projects": 0
        },
        "sustainability_metrics": {
            "carbon_footprint_reduced": 0,
            "waste_diverted": 0,
            "renewable_energy_hours": 0
        }
    }, 200

@app.get("/api/company/progress")
@jwt_required()
def get_progress_tracking():
    """Get progress tracking for goals and milestones (events-based)"""
    now = datetime.now(timezone.utc)
    start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_year = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)
    with SessionLocal() as db:
        events_ytd = db.execute(text(
            """
            SELECT COALESCE(COUNT(DISTINCT et.event_id),0)
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            WHERE utr.registered_at >= :start
            """
        ), {"start": start_year}).scalar() or 0
    target = 100
    pct = int(round((events_ytd * 100) / target)) if target else 0
    days_remaining = (end_year.date() - now.date()).days
    milestones = {
        "first_10_events": {"achieved": events_ytd >= 10, "date": None},
        "first_50_events": {"achieved": events_ytd >= 50, "date": None},
        "first_100_events": {"achieved": events_ytd >= 100, "date": None}
    }
    return {
        "annual_goals": {
            "events_target": target,
            "current_events": events_ytd,
            "percentage_complete": pct,
            "days_remaining": days_remaining
        },
        "department_goals": [],
        "milestones": milestones,
        "quarterly_progress": {
            "q1": {"hours": 0, "events": 0, "participants": 0},
            "q2": {"hours": 0, "events": 0, "participants": 0},
            "q3": {"hours": 0, "events": 0, "participants": 0},
            "q4": {"hours": 0, "events": 0, "participants": 0}
        }
    }, 200

@app.get("/api/company/leaderboard")
@jwt_required()
def get_company_leaderboard():
    """Get company-wide leaderboard"""
    with SessionLocal() as db:
        top_vol = db.execute(text(
            """
            SELECT au.full_name, COALESCE(SUM(et.estimated_duration_min),0) AS minutes
            FROM app_user au
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            LEFT JOIN event_task et ON et.id = utr.task_id
            GROUP BY au.full_name
            ORDER BY minutes DESC, au.full_name ASC
            LIMIT 10
            """
        )).mappings().all()

        dept = db.execute(text(
            """
            SELECT d.name, COALESCE(COUNT(utr.user_id),0) AS score
            FROM department d
            LEFT JOIN app_user au ON au.department_id = d.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY d.name
            ORDER BY score DESC, d.name ASC
            LIMIT 10
            """
        )).mappings().all()

        erg = db.execute(text(
            """
            SELECT e.name, COALESCE(COUNT(utr.user_id),0) AS score
            FROM erg e
            LEFT JOIN app_user au ON au.erg_id = e.id
            LEFT JOIN user_task_registration utr ON utr.user_id = au.id
            GROUP BY e.name
            ORDER BY score DESC, e.name ASC
            LIMIT 10
            """
        )).mappings().all()

    return {
        "top_volunteers": [{"name": r["full_name"] or "User", "score": int(round((r["minutes"] or 0) / 60))} for r in top_vol],
        "department_rankings": [{"name": r["name"], "score": int(r["score"] or 0)} for r in dept],
        "erg_rankings": [{"name": r["name"], "score": int(r["score"] or 0)} for r in erg]
    }, 200

@app.get("/api/company/trends")
@jwt_required()
def get_company_trends():
    """Get trending data and predictive analytics"""
    now = datetime.now(timezone.utc)
    last_30 = now - timedelta(days=30)
    with SessionLocal() as db:
        last30_regs = db.execute(text(
            "SELECT COUNT(*) FROM user_task_registration WHERE registered_at >= :t"
        ), {"t": last_30}).scalar() or 0
        daily_avg = round(last30_regs / 30, 2)

        last7 = db.execute(text("SELECT COUNT(*) FROM user_task_registration WHERE registered_at >= :t"), {"t": now - timedelta(days=7)}).scalar() or 0
        prev7 = db.execute(text("SELECT COUNT(*) FROM user_task_registration WHERE registered_at >= :a AND registered_at < :b"), {"a": now - timedelta(days=14), "b": now - timedelta(days=7)}).scalar() or 0
        forecast = "stable"
        if prev7:
            delta = (last7 - prev7) / prev7
            forecast = "rising" if delta > 0.1 else ("falling" if delta < -0.1 else "stable")

        minutes_month = db.execute(text(
            """
            SELECT COALESCE(SUM(et.estimated_duration_min),0)
            FROM user_task_registration utr
            JOIN event_task et ON et.id = utr.task_id
            WHERE utr.registered_at >= :t
            """
        ), {"t": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)}).scalar() or 0

    return {
        "participation_trends": {"daily_average": daily_avg},
        "predictive_insights": {"projected_hours": int(round(minutes_month / 60)), "engagement_forecast": forecast}
    }, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)