import os
from datetime import timedelta, datetime, timezone

from flask import Flask, request, jsonify, make_response
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
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5174")
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
        SELECT id, email, full_name, password_hash, organization_id
        FROM app_user WHERE email = :email
    """), {"email": email}).mappings().first()
    return row

def fetch_user_by_id(db, user_id):
    row = db.execute(text("""
        SELECT id, email, full_name, organization_id
        FROM app_user WHERE id = :id
    """), {"id": user_id}).mappings().first()
    return row

# Run once at startup
ensure_password_column()

# -------------------------
# Routes
# -------------------------
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

@app.post("/auth/signup")
def signup():
    """
    Body: { "email": "...", "password": "...", "full_name": "Optional", "organization_id": 1 }
    """
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password") or ""
    full_name = data.get("full_name")
    org_id = data.get("organization_id")

    if not email or not pwd:
        return jsonify({"error": "email and password are required"}), 400

    pw_hash = generate_password_hash(pwd)

    with SessionLocal() as db:
        existing = fetch_user_by_email(db, email)
        if existing:
            return jsonify({"error": "email already registered"}), 409

        # Insert user
        row = db.execute(text("""
            INSERT INTO app_user (email, full_name, organization_id, password_hash)
            VALUES (:email, :full_name, :org_id, :pw)
            RETURNING id, email, full_name, organization_id
        """), {"email": email, "full_name": full_name, "org_id": org_id, "pw": pw_hash}).mappings().first()
        db.commit()

        # Issue JWT
        access_token = create_access_token(identity=str(row["id"]))
        resp = make_response({
            "user": {
                "id": str(row["id"]),
                "email": row["email"],
                "full_name": row["full_name"],
                "organization_id": row["organization_id"],
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
            }
        }, 200

# Optional: token freshness/expiry check endpoint
@app.get("/auth/token")
@jwt_required()
def token_info():
    return {"sub": get_jwt_identity(), "exp": get_jwt()["exp"]}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)