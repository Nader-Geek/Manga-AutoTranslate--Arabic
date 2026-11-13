# -*- coding: utf-8 -*-
"""PostgreSQL access layer (asyncpg) and the job queue."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

Job = Dict[str, Any]


async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


class Database:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def connect(cls, dsn: str, min_size: int = 1, max_size: int = 6) -> "Database":
        pool = await asyncpg.create_pool(
            dsn, min_size=min_size, max_size=max_size, init=_init_conn)
        db = cls(pool)
        await db.apply_schema()
        return db

    async def close(self) -> None:
        await self.pool.close()

    async def apply_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        async with self.pool.acquire() as conn:
            await conn.execute(sql)

    # ------------------------------------------------------------------ queue
    async def create_job(self, *, user_id: int, guild_id: Optional[int], channel_id: int,
                         kind: str, source_name: str, workdir: str, input_path: str,
                         total_pages: Optional[int], options: Dict[str, Any]) -> Job:
        row = await self.pool.fetchrow(
            """INSERT INTO jobs (user_id, guild_id, channel_id, kind, source_name,
                                 workdir, input_path, total_pages, options)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *""",
            user_id, guild_id, channel_id, kind, source_name, workdir, input_path,
            total_pages, options)
        return dict(row)

    async def count_active(self, user_id: int) -> int:
        return await self.pool.fetchval(
            "SELECT count(*) FROM jobs WHERE user_id=$1 AND status IN ('pending','running')",
            user_id)

    async def queue_position(self, job_id: int) -> int:
        """1-based position among pending jobs (0 if not pending)."""
        return await self.pool.fetchval(
            """SELECT CASE WHEN EXISTS (SELECT 1 FROM jobs WHERE id=$1 AND status='pending')
                      THEN (SELECT count(*) FROM jobs WHERE status='pending' AND id <= $1)
                      ELSE 0 END""", job_id)

    async def queue_summary(self) -> Dict[str, int]:
        rows = await self.pool.fetch(
            "SELECT status, count(*) AS n FROM jobs WHERE status IN ('pending','running') "
            "GROUP BY status")
        out = {"pending": 0, "running": 0}
        for r in rows:
            out[r["status"]] = int(r["n"])
        return out

    async def claim_job(self) -> Optional[Job]:
        """Atomically take the oldest pending job (safe with several workers)."""
        row = await self.pool.fetchrow(
            """UPDATE jobs SET status='running', started_at=now(), attempts=attempts+1, last_activity_at=now(),
                              progress='', pages_done=0, bubbles_seen=0
               WHERE id = (SELECT id FROM jobs WHERE status='pending'
                           ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
               RETURNING *""")
        return dict(row) if row else None

    async def requeue_stale(self, max_attempts: int = 2) -> int:
        """After a crash: running jobs go back to the queue, or fail if retried enough."""
        await self.pool.execute(
            """UPDATE jobs SET status='failed', finished_at=now(),
                   error='interrupted by a bot restart (too many attempts)'
               WHERE status='running' AND attempts >= $1""", max_attempts)
        r = await self.pool.execute(
            "UPDATE jobs SET status='pending' WHERE status='running' AND attempts < $1",
            max_attempts)
        return int(r.split()[-1])

    async def set_message(self, job_id: int, message_id: int) -> None:
        await self.pool.execute("UPDATE jobs SET message_id=$2 WHERE id=$1", job_id, message_id)

    async def update_progress(self, job_id: int, *, text: str, pages_done: int,
                              bubbles_seen: int, idle_s: float = 0.0) -> None:
        """idle_s = seconds since manga.py last printed a line (stored as last_activity_at)."""
        await self.pool.execute(
            "UPDATE jobs SET progress=$2, pages_done=$3, bubbles_seen=$4, "
            "last_activity_at = now() - make_interval(secs => $5) "
            "WHERE id=$1 AND status='running'", job_id, text, pages_done, bubbles_seen,
            float(max(0.0, idle_s)))

    async def finish_job(self, job_id: int, *, stats: Dict[str, Any],
                         result_files: List[str], ttl_minutes: int) -> bool:
        r = await self.pool.execute(
            """UPDATE jobs SET status='done', finished_at=now(), stats=$2, result_files=$3,
                   expires_at = now() + make_interval(mins => $4)
               WHERE id=$1 AND status='running'""",
            job_id, stats, result_files, ttl_minutes)
        return r.endswith("1")

    async def fail_job(self, job_id: int, error: str, ttl_minutes: int,
                       stats: Optional[Dict[str, Any]] = None) -> None:
        await self.pool.execute(
            """UPDATE jobs SET status='failed', finished_at=now(), error=$2, stats=$3,
                   expires_at = now() + make_interval(mins => $4)
               WHERE id=$1 AND status IN ('running','pending')""",
            job_id, error[:3500], stats, ttl_minutes)

    async def cancel_job(self, job_id: int, user_id: int, ttl_minutes: int,
                         is_admin: bool = False) -> Optional[str]:
        """Cancel a pending/running job. Returns the previous status, or None."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT status, user_id FROM jobs WHERE id=$1 FOR UPDATE", job_id)
                if row is None or row["status"] not in ("pending", "running"):
                    return None
                if row["user_id"] != user_id and not is_admin:
                    return None
                await conn.execute(
                    """UPDATE jobs SET status='cancelled', finished_at=now(),
                           expires_at = now() + make_interval(mins => $2) WHERE id=$1""",
                    job_id, ttl_minutes)
                return row["status"]

    # ---------------------------------------------------------------- queries
    async def get_job(self, job_id: int) -> Optional[Job]:
        row = await self.pool.fetchrow("SELECT * FROM jobs WHERE id=$1", job_id)
        return dict(row) if row else None

    async def user_history(self, user_id: int, limit: int = 10) -> List[Job]:
        rows = await self.pool.fetch(
            "SELECT * FROM jobs WHERE user_id=$1 ORDER BY id DESC LIMIT $2", user_id, limit)
        return [dict(r) for r in rows]

    async def user_totals(self, user_id: int) -> Dict[str, Any]:
        """Lifetime counters for /history (pages and bubbles from finished jobs)."""
        row = await self.pool.fetchrow(
            """SELECT count(*) FILTER (WHERE status='done')                       AS jobs_done,
                      count(*) FILTER (WHERE status='failed')                     AS jobs_failed,
                      coalesce(sum((stats->>'pages')::int)   FILTER (WHERE status='done'), 0) AS pages,
                      coalesce(sum((stats->>'bubbles')::int) FILTER (WHERE status='done'), 0) AS bubbles
               FROM jobs WHERE user_id=$1""", user_id)
        return dict(row)

    # ---------------------------------------------------------------- cleanup
    async def take_expired_workdirs(self) -> List[Job]:
        """Jobs that finished long enough ago for their files to be deleted."""
        rows = await self.pool.fetch(
            """SELECT id, workdir FROM jobs
               WHERE workdir IS NOT NULL AND expires_at IS NOT NULL AND expires_at < now()""")
        return [dict(r) for r in rows]

    async def mark_workdir_removed(self, job_id: int) -> None:
        await self.pool.execute(
            "UPDATE jobs SET workdir=NULL, result_files='[]'::jsonb WHERE id=$1", job_id)
