# -*- coding: utf-8 -*-
"""Throw-away PostgreSQL for notebooks (Kaggle / molab / local) — no root, no apt.

Uses the `pixeltable-pgserver` wheel (PostgreSQL bundled inside pip). Keep the returned
handle alive for as long as you need the database; call .stop() when done.

    srv = start("/tmp/mangabot_pg")
    os.environ["DATABASE_URL"] = srv.dsn
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class EmbeddedPostgres:
    dsn: str
    _server: Any

    def stop(self) -> None:
        try:
            self._server.cleanup()
        except Exception:
            pass


def ensure_installed() -> None:
    try:
        import pixeltable_pgserver  # noqa: F401
        return
    except ImportError:
        pass
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pixeltable-pgserver"])


def start(data_dir: str = "/tmp/mangabot_pg") -> EmbeddedPostgres:
    ensure_installed()
    import pixeltable_pgserver as pgserver
    os.makedirs(data_dir, exist_ok=True)
    srv = pgserver.get_server(data_dir, cleanup_mode="stop")
    return EmbeddedPostgres(dsn=srv.get_uri(), _server=srv)
