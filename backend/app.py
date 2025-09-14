import os
from datetime import timedelta, datetime, timezone
from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt, get_jwt_identity,
    jwt_required, set_access_cookies, unset_jwt_cookies
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -------------------------
# Config
# -------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-change-me")
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
               created_at, updated_at
        FROM app_user WHERE id = :id
    """), {"id": user_id}).mappings().first()
    return row

# Run once at startup
ensure_password_column()

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

        # Insert user with all fields
        row = db.execute(text("""
            INSERT INTO app_user (
                email, full_name, organization_id, department_id, erg_id, password_hash,
                user_name, company, position, dept, erg,
                location_city, location_state, tz,
                strengths, interests, expertise, communication_style
            )
            VALUES (
                :email, :full_name, :org_id, :department_id, :erg_id, :pw,
                :user_name, :company, :position, :dept, :erg,
                :location_city, :location_state, :tz,
                :strengths, :interests, :expertise, :communication_style
            )
            RETURNING id, email, full_name, organization_id, department_id, erg_id,
                     user_name, company, position, dept, erg,
                     location_city, location_state, tz,
                     strengths, interests, expertise, communication_style
        """), {
            "email": email, "full_name": full_name, "org_id": org_id, "department_id": department_id, "erg_id": erg_id, "pw": pw_hash,
            "user_name": user_name, "company": company, "position": position, "dept": dept, "erg": erg,
            "location_city": location_city, "location_state": location_state, "tz": tz,
            "strengths": strengths, "interests": interests, "expertise": expertise, "communication_style": communication_style
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
                "communication_style": row["communication_style"]
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
                "communication_style": user["communication_style"]
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
                "communication_style": user["communication_style"]
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
    Body JSON:
    {
      "organization_id": 1,
      "title": "...",
      "description": "...",
      "mode": "in_person" | "virtual" | "hybrid",
      "location_city": "City", "location_state": "ST",
      "location_lat": 40.7, "location_lng": -74.0,
      "is_remote": false,
      "causes": ["hunger","community"],         # or "hunger, community"
      "skills_needed": ["logistics","outreach"],
      "accessibility": ["wheelchair"],          # optional
      "tags": ["weekend","family"],             # optional
      "min_duration_min": 120,                  # optional
      "rsvp_url": "https://...",
      "contact_email": "org@example.org",
      "sessions": [                             # optional
        {"start_ts": "2025-10-01T09:00:00Z", "end_ts": "2025-10-01T12:00:00Z",
         "capacity": 25, "meet_url": null, "address_line": "123 Main St"}
      ]
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

    causes = _as_list(data.get("causes"))
    skills = _as_list(data.get("skills_needed"))
    accessibility = _as_list(data.get("accessibility"))
    tags = _as_list(data.get("tags"))
    min_duration = data.get("min_duration_min", 60)
    is_remote = bool(data.get("is_remote", False))
    sessions = data.get("sessions") or []

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
        # Check org if provided
        organization_id = data.get("organization_id")
        if organization_id:
            org = db.execute(text("SELECT id FROM organization WHERE id = :id"), {"id": organization_id}).first()
            if not org:
                return jsonify({"error": "organization_id not found"}), 400

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
            "location_lat": data.get("location_lat"),
            "location_lng": data.get("location_lng"),
            "is_remote": is_remote,
            "causes": causes,
            "skills_needed": skills,
            "accessibility": accessibility,
            "tags": tags,
            "min_duration_min": min_duration,
            "rsvp_url": data.get("rsvp_url"),
            "contact_email": data.get("contact_email"),
        }).mappings().first()

        # Insert sessions
        created_sessions = []
        for s in norm_sessions:
            # Convert empty capacity to None
            capacity = s.get("capacity")
            if capacity == "" or capacity is None:
                capacity = None
            else:
                try:
                    capacity = int(capacity)
                except (ValueError, TypeError):
                    capacity = None
            
            row = db.execute(text("""
                INSERT INTO event_session (event_id, start_ts, end_ts, capacity, meet_url, address_line)
                VALUES (:event_id, :start_ts, :end_ts, :capacity, :meet_url, :address_line)
                RETURNING id, event_id, start_ts, end_ts, capacity, meet_url, address_line
            """), {
                "event_id": ev["id"], 
                "start_ts": s["start_ts"],
                "end_ts": s["end_ts"],
                "capacity": capacity,
                "meet_url": s.get("meet_url") or None,
                "address_line": s.get("address_line") or None
            }).mappings().first()
            created_sessions.append(dict(row))

        db.commit()

    # serialize timestamps
    for s in created_sessions:
        s["start_ts"] = s["start_ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        s["end_ts"]   = s["end_ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

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
# List Events (for admin/review)
# -------------------------
@app.get("/api/events")
@jwt_required()
def list_events():
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, organization_id, title, description, mode,
                   location_city, location_state, is_remote, causes,
                   skills_needed, tags, min_duration_min, rsvp_url, contact_email,
                   created_at, updated_at
            FROM event
            ORDER BY created_at DESC
        """)).mappings().all()
    return jsonify({"events": [dict(r) for r in rows]}), 200

# -------------------------
# Task Management Endpoints
# -------------------------
@app.post("/api/events/<uuid:event_id>/tasks")
@jwt_required()
def create_event_task(event_id):
    """Create a new task for an event"""
    data = request.get_json()
    _require_fields(data, ["title"])
    
    with SessionLocal() as db:
        # Check if event exists
        event = db.execute(text("SELECT id FROM event WHERE id = :event_id"), {"event_id": event_id}).mappings().first()
        if not event:
            return jsonify({"error": "Event not found"}), 404
        
        # Create task
        task = db.execute(text("""
            INSERT INTO event_task (event_id, title, description, skills_required, estimated_duration_min, priority, status)
            VALUES (:event_id, :title, :description, :skills_required, :estimated_duration_min, :priority, :status)
            RETURNING id, event_id, title, description, skills_required, estimated_duration_min, priority, status, assigned_to, created_at, updated_at
        """), {
            "event_id": event_id,
            "title": data["title"],
            "description": data.get("description", ""),
            "skills_required": _as_list(data.get("skills_required", "")),
            "estimated_duration_min": data.get("estimated_duration_min"),
            "priority": data.get("priority", "medium"),
            "status": data.get("status", "open")
        }).mappings().first()
        
        db.commit()
        return jsonify({"task": dict(task)}), 201

@app.get("/api/events/<uuid:event_id>/tasks")
@jwt_required()
def get_event_tasks(event_id):
    """Get all tasks for an event"""
    with SessionLocal() as db:
        tasks = db.execute(text("""
            SELECT id, event_id, title, description, skills_required, estimated_duration_min, 
                   priority, status, assigned_to, created_at, updated_at
            FROM event_task 
            WHERE event_id = :event_id
            ORDER BY created_at DESC
        """), {"event_id": event_id}).mappings().all()
        
        return jsonify({"tasks": [dict(t) for t in tasks]}), 200

@app.get("/api/tasks/recommended")
@jwt_required()
def get_recommended_event_tasks():
    """Get recommended tasks for the user based on their skills and interests"""
    user_id = get_jwt_identity()
    
    with SessionLocal() as db:
        # Get user's skills and interests
        user = db.execute(text("""
            SELECT interests, strengths, expertise
            FROM app_user 
            WHERE id = :user_id
        """), {"user_id": user_id}).mappings().first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # For now, return empty data - later this will use AI matching
        return jsonify({
            "tasks": [],
            "message": "No recommended tasks available yet. AI matching will be implemented soon."
        }), 200

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
    """Get trending events"""
    user_id = get_jwt_identity()
    
    # For now, return empty data structure
    return {
        "events": [],
        "message": "No trending events available yet. Data will be populated soon."
    }, 200

@app.get("/api/home/analytics")
@jwt_required()
def get_analytics():
    """Get user analytics dashboard data"""
    user_id = get_jwt_identity()
    
    # For now, return empty data structure
    return {
        "registered_events": {
            "total": 0,
            "this_month": 0,
            "last_month": 0,
            "trend": "no_data"
        },
        "top_skills": [],
        "top_interests": [],
        "progress": {
            "goal": 0,
            "current": 0,
            "percentage": 0,
            "message": "Set your monthly goal to track progress"
        },
        "communities": {
            "registered": [],
            "leaderboard": []
        }
    }, 200

@app.get("/api/home/communities")
@jwt_required()
def get_communities():
    """Get user's communities and leaderboard"""
    user_id = get_jwt_identity()
    
    # For now, return empty data structure
    return {
        "user_communities": [],
        "leaderboard": [],
        "message": "No communities available yet. Join communities to see leaderboard."
    }, 200

# -------------------------
# Company Analytics Endpoints
# -------------------------
@app.get("/api/company/overview")
@jwt_required()
def get_company_overview():
    """Get company-wide overview statistics"""
    user_id = get_jwt_identity()
    
    # For now, return empty data structure with comprehensive metrics
    return {
        "total_employees": 0,
        "active_volunteers": 0,
        "participation_rate": 0,
        "total_hours_volunteered": 0,
        "total_events_completed": 0,
        "average_hours_per_volunteer": 0,
        "top_departments": [],
        "monthly_trends": {
            "current_month": 0,
            "previous_month": 0,
            "growth_percentage": 0
        },
        "message": "Company analytics will be populated when data is available."
    }, 200

@app.get("/api/company/engagement")
@jwt_required()
def get_engagement_metrics():
    """Get employee engagement and participation metrics"""
    user_id = get_jwt_identity()
    
    return {
        "participation_breakdown": {
            "highly_engaged": 0,
            "moderately_engaged": 0,
            "low_engagement": 0,
            "not_participated": 0
        },
        "department_participation": [],
        "skill_development": {
            "new_skills_learned": 0,
            "skill_categories": [],
            "learning_hours": 0
        },
        "retention_impact": {
            "volunteer_retention_rate": 0,
            "satisfaction_score": 0,
            "recommendation_rate": 0
        },
        "message": "Engagement metrics will be calculated from volunteer data."
    }, 200

@app.get("/api/company/impact")
@jwt_required()
def get_impact_analytics():
    """Get community impact and social value metrics"""
    user_id = get_jwt_identity()
    
    return {
        "community_impact": {
            "communities_served": 0,
            "people_helped": 0,
            "projects_completed": 0,
            "social_value_created": 0
        },
        "cause_areas": {
            "education": 0,
            "environment": 0,
            "healthcare": 0,
            "poverty_alleviation": 0,
            "community_development": 0,
            "other": 0
        },
        "geographic_reach": {
            "cities_served": 0,
            "states_covered": 0,
            "international_projects": 0
        },
        "sustainability_metrics": {
            "carbon_footprint_reduced": 0,
            "waste_diverted": 0,
            "renewable_energy_hours": 0
        },
        "message": "Impact analytics will be tracked from completed volunteer activities."
    }, 200

@app.get("/api/company/progress")
@jwt_required()
def get_progress_tracking():
    """Get progress tracking for goals and milestones"""
    user_id = get_jwt_identity()
    
    return {
        "annual_goals": {
            "volunteer_hours_target": 10000,
            "current_hours": 0,
            "percentage_complete": 0,
            "days_remaining": 365
        },
        "department_goals": [],
        "milestones": {
            "first_100_hours": {"achieved": False, "date": None},
            "first_500_hours": {"achieved": False, "date": None},
            "first_1000_hours": {"achieved": False, "date": None},
            "first_volunteer_month": {"achieved": False, "date": None}
        },
        "quarterly_progress": {
            "q1": {"hours": 0, "events": 0, "participants": 0},
            "q2": {"hours": 0, "events": 0, "participants": 0},
            "q3": {"hours": 0, "events": 0, "participants": 0},
            "q4": {"hours": 0, "events": 0, "participants": 0}
        },
        "message": "Progress tracking will be updated as volunteers log activities."
    }, 200

@app.get("/api/company/leaderboard")
@jwt_required()
def get_company_leaderboard():
    """Get company-wide leaderboard and recognition"""
    user_id = get_jwt_identity()
    
    return {
        "top_volunteers": [],
        "department_rankings": [],
        "monthly_winners": {
            "volunteer_of_month": None,
            "department_of_month": None,
            "most_improved": None
        },
        "achievements": {
            "total_achievements_unlocked": 0,
            "recent_achievements": [],
            "upcoming_milestones": []
        },
        "recognition_program": {
            "badges_earned": 0,
            "certificates_issued": 0,
            "awards_given": 0
        },
        "message": "Leaderboard will be populated as volunteer activities are tracked."
    }, 200

@app.get("/api/company/trends")
@jwt_required()
def get_company_trends():
    """Get trending data and predictive analytics"""
    user_id = get_jwt_identity()
    
    return {
        "participation_trends": {
            "daily_average": 0,
            "weekly_patterns": [],
            "seasonal_variations": []
        },
        "popular_activities": [],
        "emerging_causes": [],
        "predictive_insights": {
            "projected_hours": 0,
            "engagement_forecast": "stable",
            "recommended_actions": []
        },
        "benchmarking": {
            "industry_average": 0,
            "peer_comparison": "above_average",
            "best_practices": []
        },
        "message": "Trend analysis will be available as more data is collected."
    }, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)