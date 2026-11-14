# -*- coding: utf-8 -*-
"""Bot configuration, read from environment variables (or bot/.env)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        raise SystemExit(f"{name} must be an integer, got {raw!r}")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _gpu_present() -> bool:
    """True when an NVIDIA GPU is visible (nvidia-smi -L lists one)."""
    import shutil, subprocess
    exe = shutil.which("nvidia-smi")
    if not exe:
        return False
    try:
        out = subprocess.run([exe, "-L"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return False
    return "GPU" in out


def _use_gpu() -> bool:
    """USE_GPU=1/0 forces it; unset = auto-detect (it used to default to CPU-only)."""
    if os.environ.get("USE_GPU", "").strip():
        return _bool("USE_GPU")
    return _gpu_present()


def _csv(name: str, default: str = "") -> Tuple[str, ...]:
    raw = os.environ.get(name, default)
    return tuple(x.strip() for x in raw.split(",") if x.strip())


@dataclass(frozen=True)
class Config:
    discord_token: str = ""
    database_url: str = "postgresql://postgres@localhost/mangabot"

    # where manga.py lives and how to run it
    repo_root: Path = REPO_ROOT
    manga_script: Path = REPO_ROOT / "manga.py"
    python: str = sys.executable
    # translate (Arabic/Ollama) still runs on the previous engine; clean/extract/typer use manga.py
    legacy_script: Path = REPO_ROOT / "legacy" / "manga_ar.py"
    font: str = "fonts/Vazirmatn-Bold.ttf"
    use_gpu: bool = False

    # storage
    work_dir: Path = REPO_ROOT / "bot_work"
    file_ttl_minutes: int = 20          # results/inputs are deleted this long after a job ends

    # limits
    max_upload_mb: int = 100            # per input file (Discord itself caps non-Nitro users at 10MB)
    reply_limit_mb: int = 0             # 0 = use the server's own upload limit
    max_link_mb: int = 500              # max size of a chapter downloaded from a Drive/Gofile link
    google_token_file: str = ""         # file holding a fresh Google OAuth access token (Colab sign-in)
    google_api_key: str = ""           # enables public Google Drive *folder* links
    allow_links: bool = True            # accept `link:` (Google Drive / Gofile) instead of an attachment
    max_unzipped_mb: int = 600          # zip-bomb guard
    max_pages: int = 60                 # clean / extract / typer
    max_pages_translate: int = 30       # translate (Ollama is slow)
    max_active_per_user: int = 2        # pending + running jobs per user
    job_timeout_minutes: int = 120
    workers: int = 1                    # parallel manga.py processes

    # translation (Ollama)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    allowed_models: Tuple[str, ...] = ("qwen2.5:7b-instruct",)
    ollama_context: int = 8192

    # access control (empty = everyone)
    allowed_guild_ids: Tuple[int, ...] = ()
    admin_user_ids: Tuple[int, ...] = ()

    # external host for results that do not fit Discord ("" = off, "gofile")
    external_host: str = ""
    gofile_token: str = ""
    gofile_upload_url: str = "https://upload.gofile.io/uploadfile"
    purge_old_commands: bool = False    # drop stale per-server slash commands at startup
    poll_seconds: float = 5.0
    progress_interval: float = 8.0
    monitor_seconds: float = 30.0       # CPU/RAM/GPU line written to run.log this often
    heartbeat_seconds: float = 30.0     # refresh the status message even if manga.py printed nothing


def load_config() -> Config:
    try:  # optional dependency
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / "bot" / ".env")
    except Exception:
        pass

    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct").strip()
    allowed = _csv("OLLAMA_ALLOWED_MODELS") or (model,)
    if model not in allowed:
        allowed = (model,) + tuple(allowed)

    return Config(
        discord_token=os.environ.get("DISCORD_TOKEN", "").strip(),
        database_url=os.environ.get("DATABASE_URL", Config.database_url).strip(),
        manga_script=Path(os.environ.get("MANGA_SCRIPT", str(REPO_ROOT / "manga.py"))),
        python=os.environ.get("MANGA_PYTHON", sys.executable),
        legacy_script=Path(os.environ.get("LEGACY_SCRIPT", str(REPO_ROOT / "legacy" / "manga_ar.py"))),
        font=os.environ.get("MANGA_FONT", "fonts/Vazirmatn-Bold.ttf"),
        use_gpu=_use_gpu(),
        work_dir=Path(os.environ.get("BOT_WORK_DIR", str(REPO_ROOT / "bot_work"))),
        file_ttl_minutes=_int("FILE_TTL_MINUTES", 20),
        max_upload_mb=_int("MAX_UPLOAD_MB", 100),
        reply_limit_mb=_int("REPLY_LIMIT_MB", 0),
        max_link_mb=_int("MAX_LINK_MB", 500),
        google_token_file=os.environ.get("GOOGLE_TOKEN_FILE", "").strip(),
        google_api_key=os.environ.get("GOOGLE_API_KEY", "").strip(),
        allow_links=_bool("ALLOW_LINKS", True),
        max_unzipped_mb=_int("MAX_UNZIPPED_MB", 600),
        max_pages=_int("MAX_PAGES", 60),
        max_pages_translate=_int("MAX_PAGES_TRANSLATE", 30),
        max_active_per_user=_int("MAX_ACTIVE_PER_USER", 2),
        job_timeout_minutes=_int("JOB_TIMEOUT_MINUTES", 120),
        workers=max(1, _int("WORKERS", 1)),
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=model,
        allowed_models=allowed,
        ollama_context=_int("OLLAMA_CONTEXT_LENGTH", 8192),
        allowed_guild_ids=tuple(int(x) for x in _csv("ALLOWED_GUILD_IDS")),
        admin_user_ids=tuple(int(x) for x in _csv("ADMIN_USER_IDS")),
        purge_old_commands=_bool("PURGE_OLD_COMMANDS"),
        external_host=os.environ.get("EXTERNAL_HOST", "").strip().lower(),
        gofile_token=os.environ.get("GOFILE_TOKEN", "").strip(),
        gofile_upload_url=os.environ.get("GOFILE_UPLOAD_URL", "").strip() or Config.gofile_upload_url,
        monitor_seconds=float(os.environ.get("MONITOR_SECONDS", "30") or 30),
        heartbeat_seconds=float(os.environ.get("HEARTBEAT_SECONDS", "30") or 30),
    )
