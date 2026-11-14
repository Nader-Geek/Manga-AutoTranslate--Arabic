-- Manga bot schema. Applied automatically at startup (idempotent).

CREATE TABLE IF NOT EXISTS jobs (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT      NOT NULL,
    guild_id      BIGINT,
    channel_id    BIGINT      NOT NULL,
    message_id    BIGINT,                          -- status message we keep editing
    kind          TEXT        NOT NULL
                  CHECK (kind IN ('clean', 'extract', 'typer', 'translate', 'chapter')),
    status        TEXT        NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'running', 'done', 'failed', 'cancelled')),
    source_name   TEXT        NOT NULL,            -- original file name (display only)
    workdir       TEXT,                            -- per-job folder; NULL after cleanup
    input_path    TEXT        NOT NULL,
    total_pages   INTEGER,
    options       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    progress      TEXT        NOT NULL DEFAULT '',
    pages_done    INTEGER     NOT NULL DEFAULT 0,
    bubbles_seen  INTEGER     NOT NULL DEFAULT 0,
    stats         JSONB,
    result_files  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    error         TEXT,
    attempts      INTEGER     NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ
);

-- when manga.py last printed something (for the stuck/working indicator)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS jobs_queue_idx   ON jobs (id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS jobs_user_idx    ON jobs (user_id, id DESC);
CREATE INDEX IF NOT EXISTS jobs_expiry_idx  ON jobs (expires_at) WHERE workdir IS NOT NULL;

-- databases created before the 'chapter' kind existed: widen the CHECK (idempotent)
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check
    CHECK (kind IN ('clean', 'extract', 'typer', 'translate', 'chapter'));
