# VolunteerHub

A modern, minimal volunteer portal that connects employees with micro‑volunteer opportunities and surfaces personalized insights from Slack activity. The system spans a React frontend, a Flask API backend backed by PostgreSQL, and a Slack bot that analyzes channel messages using Google Gemini and writes insights to the shared database creating personalized experiences and reccomendations.

## Idea in a nutshell
- Employees log in, browse/join micro‑volunteer tasks for philonthrophic initiatives based on skills that they relate to, and track impact.
- A Slack bot analyzes channel messages per user (opt‑in/command driven), extracts strengths/interests/expertise/communication style via Gemini, and writes/updates user profiles in the same Postgres database.
- The frontend displays personalized recommendations and analytics using unified backend APIs.

---

## Tech stack
- Frontend: React + Vite (ES modules), CSS (utility/layout components), smooth hover/focus interactions
- Backend: Flask (routing, auth, JSON APIs), Flask‑JWT‑Extended (cookie JWT), Flask‑CORS
- Database: PostgreSQL + SQLAlchemy (core), psycopg2-binary
- Slack Bot: slack_bolt (Socket Mode), slack_sdk, google‑generativeai (Gemini 1.5‑flash)
- Env/config: python‑dotenv for Python apps; .env files for secrets

---

## Repository structure
```
CompanyVolunteerPortal/
  backend/               # Flask API and data logic
    app.py              # Routes, auth, analytics, skills helper (Gemini-supported)
    requirements.txt    # Backend Python deps
    venv/               # Backend virtualenv (local)

  frontend/             # React + Vite app
    src/
      pages/            # Views like Landing.jsx, Home.jsx, Login.jsx, etc.
    package.json        # Frontend deps and scripts
    vite.config.js      # Vite config

  SlackBot/             # Slack Bolt bot (Socket Mode) + Gemini analyzer
    main_bot.py         # Entry point; commands; orchestration
    postgres_database.py# Postgres helper (create/update profiles)
    llm_analyzer.py     # Gemini API calls (gemini-1.5-flash)
    requirements.txt    # Bot Python deps
    venv/               # SlackBot virtualenv (local)

  db/
    schema.sql          # Reference SQL schema (PostgreSQL)

  scripts/
    seeds_events.py     # Example seeding utilities
```

---

## How the pieces work together

### Backend (Flask) — routing, auth, analytics
- Serves JSON APIs only; the React app is served by Vite dev server in development.
- Cookie‑based JWT auth using Flask‑JWT‑Extended; endpoints like `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me`.
- Event and task endpoints (create, list, recommend) backed by Postgres tables (e.g., `event`, `event_task`, `user_task_registration`).
- Analytics endpoints aggregate event/task/user data for the dashboard.
- Skill suggestion helpers can call Gemini (if `GEMINI_API_KEY` is set) or fall back to keyword heuristics.

Key patterns in `backend/app.py`:
- DB connection: `engine = create_engine(DATABASE_URL, pool_pre_ping=True)`
- Per‑request sessions via `SessionLocal()` context managers
- Conditional helpers to ensure required columns/tables exist at startup

### Database (PostgreSQL)
- Primary tables include `app_user`, `department`, `erg`, `event`, `event_task`, `user_task_registration`.
- The Slack bot writes to the shared `app_user` table, so Slack and the web app stay in sync.
- Connection string via `DATABASE_URL` (example: `postgresql://<user>@localhost:5432/volunteer_portal`).

### Slack Bot — Slack API + Gemini
- Built on `slack_bolt` in Socket Mode; listens for slash commands:
  - `/generate-insights`: scrape recent channel messages, group by user, run Gemini analysis, upsert to Postgres (`app_user`)
  - `/link-user <email>`: link current Slack user to an existing app user row by email
  - `/my-profile`: fetch and summarize the caller’s profile from Postgres
- Gemini model: `gemini-1.5-flash` via `google-generativeai`
- Writes structured JSON fields to `app_user` (e.g., `strengths`, `interests`, `expertise`, `communication_style`), and merges top 3 interests into `skills[]`.

### Frontend (React + Vite)
- Auth pages (Landing, Login/Signup) call backend auth endpoints and set JWT cookies.
- Home/dashboard pages render recommended tasks, trending events, registered tasks, and analytics via backend APIs.
- Styling uses CSS with modern effects (focus/hover/3D lift) while keeping the UI minimal and clean.

---

## Environment variables
Create `.env` files in `backend/` and `SlackBot/` (do not commit real secrets).

Common variables:
```
# Shared
DATABASE_URL=postgresql://<user>@localhost:5432/volunteer_portal

# Backend
JWT_SECRET_KEY=dev-secret-key-change-in-production
FRONTEND_ORIGIN=http://localhost:5173
GEMINI_API_KEY=<optional_for_backend_skill_suggestions>
PORT=8080

# SlackBot (required)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
GEMINI_API_KEY=...
DATABASE_URL=postgresql://<user>@localhost:5432/volunteer_portal
```

---

## Local setup

### Prerequisites
- Python 3.12+
- Node 18+ (Vite 4.x works well)
- PostgreSQL 14+

### 1) Database
```bash
createdb volunteer_portal || true
# Optionally apply/inspect schema
psql -d volunteer_portal -f db/schema.sql
```

### 2) Backend (Flask)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://<user>@localhost:5432/volunteer_portal"
export JWT_SECRET_KEY="dev-secret-key-change-in-production"
export PORT=8080
python app.py
```
The API will run on `http://localhost:8080` (check `/health`).

### 3) Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
The app will run on `http://localhost:5173`.

### 4) Slack Bot
```bash
cd SlackBot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# ensure .env has SLACK_BOT_TOKEN, SLACK_APP_TOKEN, GEMINI_API_KEY, DATABASE_URL
python main_bot.py
```
Commands to try in Slack (invite the bot to the channel first):
- `/generate-insights` — analyze recent channel messages
- `/link-user you@company.com` — link Slack user to an existing app user
- `/my-profile` — view your analyzed profile

---

## Common issues & fixes
- Missing Python deps (e.g., `ModuleNotFoundError: requests`):
  - Run `pip install -r backend/requirements.txt` or the SlackBot’s `requirements.txt` inside their respective venvs.
- Port conflicts (5000/8080/5173):
  - The backend uses 8080 by default; adjust `PORT` or kill other listeners.
- Postgres connection failures:
  - Verify `DATABASE_URL` and that the DB exists: `psql -d volunteer_portal -c "SELECT 1;"`
- Slack socket mode reconnect/stale messages:
  - Ensure correct tokens, stable internet, and that the bot is invited to the target channel.
- Node/Vite version mismatches:
  - This repo uses Vite 4.x; Node 18+ is recommended.

---

## Development workflow
- Work on a feature branch, commit changes, and open a PR into `main`.
- If you need to sync everything from `origin/main` but keep local SlackBot changes, consider:
```bash
git fetch origin
git checkout -b merge-slackbot main
git merge -X theirs GaganBranch
# keep your SlackBot exactly
git checkout GaganBranch -- SlackBot
git add -A && git commit -m "Merge; keep SlackBot"
```

