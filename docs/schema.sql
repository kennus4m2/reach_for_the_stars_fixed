-- Reach for the Stars: PostgreSQL schema
-- The Hub Contract gives each team its own schema named after its slug.
-- Run this in pgAdmin (Query Tool) inside your reach_for_the_stars database.

CREATE SCHEMA IF NOT EXISTS reach_for_the_stars;
SET search_path TO reach_for_the_stars;

-- ---------- Hosts (only hosts have accounts) ----------
CREATE TABLE IF NOT EXISTS hosts (
  id            INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,            -- bcrypt hash, never plain text
  display_name  VARCHAR(100) NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------- Question sets (Hub Contract Rule 3) ----------
-- "subject" is the category (Science, History, General Knowledge, Programming)
CREATE TABLE IF NOT EXISTS question_sets (
  id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  host_id     INT          NOT NULL REFERENCES hosts(id),
  title       VARCHAR(80)  NOT NULL CHECK (CHAR_LENGTH(title) BETWEEN 3 AND 80),
  description VARCHAR(255),
  subject     VARCHAR(50),
  grade_level VARCHAR(50),
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
  id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  question_set_id INT NOT NULL REFERENCES question_sets(id) ON DELETE CASCADE,
  position        INT NOT NULL,                    -- order inside the set
  text            VARCHAR(500) NOT NULL,
  type            VARCHAR(20)  NOT NULL CHECK (type IN ('multiple_choice', 'true_false')),
  time_limit_sec  INT NOT NULL DEFAULT 20 CHECK (time_limit_sec BETWEEN 5 AND 60),
  UNIQUE (question_set_id, position)
);

-- is_correct stays on the server. The API converts it to correct_index
-- only when a host exports a set. Players never receive it.
CREATE TABLE IF NOT EXISTS choices (
  id           INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  question_id  INT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  choice_index INT NOT NULL,                       -- counts from 0
  text         VARCHAR(120) NOT NULL,
  is_correct   BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (question_id, choice_index)
);

-- ---------- Sessions (one round) ----------
CREATE TABLE IF NOT EXISTS sessions (
  id              INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  host_id         INT NOT NULL REFERENCES hosts(id),
  question_set_id INT NOT NULL REFERENCES question_sets(id),
  join_code       CHAR(6) NOT NULL UNIQUE CHECK (join_code ~ '^[1-9][0-9]{5}$'),
  status          VARCHAR(10) NOT NULL DEFAULT 'waiting'
                  CHECK (status IN ('waiting', 'playing', 'ended')),
  starting_lives  INT NOT NULL DEFAULT 3,          -- proposed default, team to confirm
  duration_sec    INT NOT NULL DEFAULT 300,        -- proposed round time limit
  started_at      TIMESTAMPTZ,
  ends_at         TIMESTAMPTZ,                     -- server compares NOW() to this
  ended_at        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Players (nickname only, no personal data) ----------
CREATE TABLE IF NOT EXISTS session_players (
  id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id        INT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  nickname          VARCHAR(20) NOT NULL CHECK (CHAR_LENGTH(nickname) BETWEEN 2 AND 20),
  stars             INT NOT NULL DEFAULT 0 CHECK (stars >= 0),
  lives             INT NOT NULL DEFAULT 3,
  current_streak    INT NOT NULL DEFAULT 0,        -- resets on a wrong answer
  best_streak       INT NOT NULL DEFAULT 0,
  correct_count     INT NOT NULL DEFAULT 0,
  answer_count      INT NOT NULL DEFAULT 0,
  total_answer_ms   BIGINT NOT NULL DEFAULT 0,     -- for the average-time tie-break
  double_star_ready BOOLEAN NOT NULL DEFAULT FALSE,   -- from a Double Star chest
  protection_ready  BOOLEAN NOT NULL DEFAULT FALSE,   -- from a Protection Card chest
  current_question_id INT REFERENCES questions(id),   -- question being answered now
  question_served_at  TIMESTAMPTZ,                    -- when it was served (server timer)
  joined_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, nickname)                    -- 409 NICKNAME_TAKEN
);

-- ---------- Answers ----------
CREATE TABLE IF NOT EXISTS answers (
  id                  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  player_id           INT NOT NULL REFERENCES session_players(id) ON DELETE CASCADE,
  question_id         INT NOT NULL REFERENCES questions(id),
  choice_id           INT REFERENCES choices(id),  -- NULL = timeout
  is_correct          BOOLEAN NOT NULL,
  answer_time_ms      INT NOT NULL,                -- measured by the server
  stars_earned        INT NOT NULL DEFAULT 0,
  streak_after        INT NOT NULL DEFAULT 0,
  double_star_used    BOOLEAN NOT NULL DEFAULT FALSE,
  protection_used     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (player_id, question_id)                  -- one answer per question
);

-- ---------- 5-streak mystery chests ----------
-- A 5th correct answer in a row creates one offer with 3 slots. The server
-- fills the slots BEFORE the player picks. Contents are never sent early.
CREATE TABLE IF NOT EXISTS chest_offers (
  id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  answer_id   INT NOT NULL UNIQUE REFERENCES answers(id) ON DELETE CASCADE,
  player_id   INT NOT NULL REFERENCES session_players(id) ON DELETE CASCADE,
  status      VARCHAR(10) NOT NULL DEFAULT 'offered'
              CHECK (status IN ('offered', 'opened', 'expired')),
  picked_slot INT CHECK (picked_slot BETWEEN 1 AND 3),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  opened_at   TIMESTAMPTZ
);

-- reward_type: double_star, protection_card, or empty ("Better Luck Next Time")
CREATE TABLE IF NOT EXISTS chest_slots (
  id             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chest_offer_id INT NOT NULL REFERENCES chest_offers(id) ON DELETE CASCADE,
  slot_number    INT NOT NULL CHECK (slot_number BETWEEN 1 AND 3),
  reward_type    VARCHAR(20) NOT NULL
                 CHECK (reward_type IN ('double_star', 'protection_card', 'empty')),
  UNIQUE (chest_offer_id, slot_number)
);

-- ---------- Upgrades (safe to run again) ----------
-- If you ran an older version of this file, these add what is missing.
ALTER TABLE session_players ADD COLUMN IF NOT EXISTS current_question_id INT REFERENCES questions(id);
ALTER TABLE session_players ADD COLUMN IF NOT EXISTS question_served_at TIMESTAMPTZ;

-- "Star" and "star" count as the same nickname (409 NICKNAME_TAKEN)
CREATE UNIQUE INDEX IF NOT EXISTS uq_player_nickname_ci
  ON session_players (session_id, LOWER(nickname));

CREATE INDEX IF NOT EXISTS idx_sessions_host ON sessions (host_id);
CREATE INDEX IF NOT EXISTS idx_answers_player ON answers (player_id);