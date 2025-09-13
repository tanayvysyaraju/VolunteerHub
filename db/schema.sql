-- Enable UUIDs if needed
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE event_mode AS ENUM ('in_person','virtual','hybrid');

CREATE TABLE organization (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  website       TEXT
);

CREATE TABLE event (
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

CREATE TABLE event_session (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id     UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  start_ts     TIMESTAMPTZ NOT NULL,
  end_ts       TIMESTAMPTZ NOT NULL,
  capacity     INT,
  meet_url     TEXT,
  address_line TEXT
);

-- Indexes
CREATE INDEX idx_event_causes_gin     ON event USING GIN (causes);
CREATE INDEX idx_event_skills_gin     ON event USING GIN (skills_needed);
CREATE INDEX idx_event_tags_gin       ON event USING GIN (tags);
CREATE INDEX idx_session_time         ON event_session (start_ts, end_ts);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_event_updated_at BEFORE UPDATE ON event
FOR EACH ROW EXECUTE FUNCTION set_updated_at();