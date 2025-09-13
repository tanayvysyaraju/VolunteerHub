-- Enable UUID support
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- --------------------------
-- Types
-- --------------------------
CREATE TYPE event_mode AS ENUM ('in_person','virtual','hybrid');

-- --------------------------
-- Organization
-- --------------------------
CREATE TABLE IF NOT EXISTS organization (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  website       TEXT
);

-- --------------------------
-- Users
-- --------------------------
CREATE TABLE IF NOT EXISTS app_user (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email          TEXT UNIQUE NOT NULL,
  full_name      TEXT,
  organization_id INT REFERENCES organization(id) ON DELETE SET NULL,
  password_hash  TEXT,
  slack_id       TEXT,
  dept           TEXT,
  location_city  TEXT,
  location_state TEXT,
  tz             TEXT DEFAULT 'UTC',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------
-- Events
-- --------------------------
CREATE TABLE IF NOT EXISTS event (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id  INT REFERENCES organization(id) ON DELETE SET NULL,
  title            TEXT NOT NULL,
  description      TEXT NOT NULL,
  mode             event_mode NOT NULL,
  location_city    TEXT,
  location_state   TEXT,
  location_lat     DOUBLE PRECISION,
  location_lng     DOUBLE PRECISION,
  is_remote        BOOLEAN DEFAULT FALSE,
  causes           TEXT[] NOT NULL,
  skills_needed    TEXT[] NOT NULL,
  accessibility    TEXT[] DEFAULT '{}',
  tags             TEXT[] DEFAULT '{}',
  min_duration_min INT DEFAULT 60,
  rsvp_url         TEXT,
  contact_email    TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --------------------------
-- Event Sessions
-- --------------------------
CREATE TABLE IF NOT EXISTS event_session (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id     UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  start_ts     TIMESTAMPTZ NOT NULL,
  end_ts       TIMESTAMPTZ NOT NULL,
  capacity     INT,
  meet_url     TEXT,
  address_line TEXT
);

-- --------------------------
-- Matching Table (users ↔ events)
-- --------------------------
CREATE TABLE IF NOT EXISTS user_event_match (
  user_id   UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  event_id  UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  score     DOUBLE PRECISION NOT NULL,
  reasons   TEXT[] DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, event_id)
);

-- --------------------------
-- Indexes
-- --------------------------
CREATE INDEX IF NOT EXISTS idx_event_causes_gin     ON event USING GIN (causes);
CREATE INDEX IF NOT EXISTS idx_event_skills_gin     ON event USING GIN (skills_needed);
CREATE INDEX IF NOT EXISTS idx_event_tags_gin       ON event USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_session_time         ON event_session (start_ts, end_ts);
CREATE INDEX IF NOT EXISTS idx_app_user_org         ON app_user(organization_id);

-- --------------------------
-- Triggers
-- --------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_event_updated_at ON event;
CREATE TRIGGER trg_event_updated_at BEFORE UPDATE ON event
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;
CREATE TRIGGER trg_app_user_updated_at BEFORE UPDATE ON app_user
FOR EACH ROW EXECUTE FUNCTION set_updated_at();