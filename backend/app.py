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

CORS(
    app,
    resources={r"/*": {"origins": [FRONTEND_ORIGIN]}},
    supports_credentials=True,
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
        existing = fetch_user_by_email(db, email)
        if existing:
            return jsonify({"error": "email already registered"}), 409

        # Insert user with all fields
        row = db.execute(text("""
            INSERT INTO app_user (
                email, full_name, organization_id, password_hash,
                user_name, company, position, dept,
                location_city, location_state, tz,
                strengths, interests, expertise, communication_style
            )
            VALUES (
                :email, :full_name, :org_id, :pw,
                :user_name, :company, :position, :dept,
                :location_city, :location_state, :tz,
                :strengths, :interests, :expertise, :communication_style
            )
            RETURNING id, email, full_name, organization_id,
                     user_name, company, position, dept,
                     location_city, location_state, tz,
                     strengths, interests, expertise, communication_style
        """), {
            "email": email, "full_name": full_name, "org_id": org_id, "pw": pw_hash,
            "user_name": user_name, "company": company, "position": position, "dept": dept,
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)