# -*- coding: utf-8 -*-
"""Google Drive access straight from the Colab sign-in (no API key).

    from bot.colab_auth import start_token_file
    path = start_token_file()      # shows Colab's "Sign in with Google" popup once

The access token is written to a file and refreshed every ~40 minutes by a background thread
in the notebook kernel; the bot reads it from GOOGLE_TOKEN_FILE when it downloads a link, so
it can open public AND private Drive files/folders of the account you signed in with.
Only works inside Google Colab (raises RuntimeError elsewhere). Stops when the kernel stops.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path


def start_token_file(path: str = "/tmp/google_access_token", every_s: int = 2400) -> str:
    try:
        from google.colab import auth
    except ImportError:
        raise RuntimeError("not running in Google Colab")
    auth.authenticate_user()
    import google.auth
    from google.auth.transport.requests import Request
    creds, _ = google.auth.default()

    def write() -> None:
        creds.refresh(Request())
        tmp = Path(path + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(creds.token or "")
        tmp.replace(path)

    write()

    def loop() -> None:
        while True:
            time.sleep(every_s)
            try:
                write()
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True).start()
    return path
