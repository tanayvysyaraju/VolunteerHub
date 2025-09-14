-- ===== Extensions =====
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===== Types =====
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_mode') THEN
    CREATE TYPE event_mode AS ENUM ('in_person','virtual','hybrid');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
    CREATE TYPE task_status AS ENUM ('open','claimed','in_progress','done','cancelled');
  END IF;
END$$;

-- ===== Org =====
CREATE TABLE IF NOT EXISTS organization (
  id        SERIAL PRIMARY KEY,
  name      TEXT NOT NULL,
  website   TEXT
);

-- ===== Departments =====
CREATE TABLE IF NOT EXISTS department (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_department_name ON department(name);

-- ===== Employee Resource Groups (ERGs) =====
CREATE TABLE IF NOT EXISTS erg (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_erg_name ON erg(name);

-- ===== Users (UUID id, merged fields) =====
CREATE TABLE IF NOT EXISTS app_user (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email            TEXT UNIQUE NOT NULL,
  full_name        TEXT,
  organization_id  INT REFERENCES organization(id) ON DELETE SET NULL,
  department_id    INT REFERENCES department(id) ON DELETE SET NULL,
  erg_id           INT REFERENCES erg(id) ON DELETE SET NULL,
  password_hash    TEXT,

  -- Slack / profile fields
  slack_id         TEXT,
  user_name        TEXT,
  company          TEXT,
  position         TEXT,
  dept             TEXT,
  erg              TEXT,
  location_city    TEXT,
  location_state   TEXT,
  tz               TEXT DEFAULT 'UTC',

  -- Free-form profiling data
  raw_conversations   TEXT,
  strengths           TEXT,
  interests           TEXT,
  expertise           TEXT,
  communication_style TEXT,

  -- Skills array for matching and profiles
  skills            TEXT[] DEFAULT '{}',

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_user_org ON app_user(organization_id);
CREATE INDEX IF NOT EXISTS idx_app_user_department ON app_user(department_id);
CREATE INDEX IF NOT EXISTS idx_app_user_erg ON app_user(erg_id);
CREATE INDEX IF NOT EXISTS idx_app_user_skills_gin ON app_user USING GIN (skills);
CREATE UNIQUE INDEX IF NOT EXISTS idx_app_user_email ON app_user(email);

-- ===== Events =====
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

CREATE INDEX IF NOT EXISTS idx_event_causes_gin  ON event USING GIN (causes);
CREATE INDEX IF NOT EXISTS idx_event_skills_gin  ON event USING GIN (skills_needed);
CREATE INDEX IF NOT EXISTS idx_event_tags_gin    ON event USING GIN (tags);

-- Event sessions (time slots per event)
CREATE TABLE IF NOT EXISTS event_session (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id     UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  start_ts     TIMESTAMPTZ NOT NULL,
  end_ts       TIMESTAMPTZ NOT NULL,
  capacity     INT,
  meet_url     TEXT,
  address_line TEXT
);
CREATE INDEX IF NOT EXISTS idx_session_time ON event_session (start_ts, end_ts);

-- User↔Event match (recommendation scores)
CREATE TABLE IF NOT EXISTS user_event_match (
  user_id     UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  event_id    UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  score       DOUBLE PRECISION NOT NULL,
  reasons     TEXT[] DEFAULT '{}',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, event_id)
);

-- ===== Event Tasks (tasks within events) =====
CREATE TABLE IF NOT EXISTS event_task (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  skills_required TEXT[] DEFAULT '{}',
  estimated_duration_min INT,
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'claimed', 'in_progress', 'completed', 'cancelled')),
  assigned_to UUID REFERENCES app_user(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_task_event_id ON event_task(event_id);
CREATE INDEX IF NOT EXISTS idx_event_task_assigned_to ON event_task(assigned_to);
CREATE INDEX IF NOT EXISTS idx_event_task_status ON event_task(status);
CREATE INDEX IF NOT EXISTS idx_event_task_skills ON event_task USING GIN (skills_required);

-- ===== Micro-Tasks (from new schema, with indices) =====
CREATE TABLE IF NOT EXISTS task (
  id           BIGSERIAL PRIMARY KEY,

  task         TEXT NOT NULL,
  task_slug    TEXT GENERATED ALWAYS AS (regexp_replace(lower(trim(task)), '\s+', '-', 'g')) STORED,

  start_ts     TIMESTAMPTZ NOT NULL,
  end_ts       TIMESTAMPTZ NOT NULL,
  CONSTRAINT chk_task_time_order CHECK (end_ts > start_ts),

  -- up to 3 skills + array for querying
  skill1       TEXT,
  skill2       TEXT,
  skill3       TEXT,
  skills_array TEXT[] GENERATED ALWAYS AS (ARRAY_REMOVE(ARRAY[skill1, skill2, skill3], NULL)) STORED,

  active       BOOLEAN NOT NULL DEFAULT TRUE,
  status       task_status NOT NULL DEFAULT 'open',

  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_task_slug_unique ON task(task_slug);
CREATE INDEX IF NOT EXISTS idx_task_time    ON task(start_ts, end_ts);
CREATE INDEX IF NOT EXISTS idx_task_active  ON task(active);
CREATE INDEX IF NOT EXISTS idx_task_status  ON task(status);
CREATE INDEX IF NOT EXISTS idx_task_trgm    ON task USING GIN (task gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_task_skills  ON task USING GIN (skills_array);

-- ===== Communities (users groupings) =====
CREATE TABLE IF NOT EXISTS community (
  id     SERIAL PRIMARY KEY,
  name   VARCHAR(100) UNIQUE NOT NULL,
  skill1 VARCHAR(100) NOT NULL,
  skill2 VARCHAR(100) NOT NULL,
  skill3 VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_community (
  user_id      UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  community_id INT  NOT NULL REFERENCES community(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, community_id)
);

-- ===== Triggers: updated_at maintenance =====
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_event_updated_at ON event;
CREATE TRIGGER trg_event_updated_at BEFORE UPDATE ON event
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;
CREATE TRIGGER trg_app_user_updated_at BEFORE UPDATE ON app_user
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_event_task_updated_at ON event_task;
CREATE TRIGGER trg_event_task_updated_at BEFORE UPDATE ON event_task
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_task_updated_at ON task;
CREATE TRIGGER trg_task_updated_at BEFORE UPDATE ON task
FOR EACH ROW EXECUTE FUNCTION set_updated_at();