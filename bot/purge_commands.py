# -*- coding: utf-8 -*-
"""Remove stale slash commands left by an older bot using the same Discord application.

Why: `tree.sync()` already replaces this application's *global* commands, but commands
registered *per server* (guild commands) by an old bot stay and show up as duplicates.

Standalone (removes global + all server commands, then exits):
    DISCORD_TOKEN=... python -m bot.purge_commands
Inside the bot: set PURGE_OLD_COMMANDS=1 (removes server commands only; the normal sync
then re-registers the current global commands).

This only touches the application whose token you pass. Commands of a *different* old bot
application can't be removed with this token — kick that bot or use its own token.
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Callable, Dict


async def purge_commands(client: Any, *, include_global: bool = True,
                         log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Overwrite command lists with [] (idempotent). `client` must already be logged in."""
    app = await client.application_info()
    removed: Dict[str, Any] = {"global": 0, "guilds": {}}
    if include_global:
        old = await client.http.get_global_commands(app.id)
        if old:
            await client.http.bulk_upsert_global_commands(app.id, [])
        removed["global"] = len(old)
        log(f"global commands removed: {len(old)}")
    async for guild in client.fetch_guilds(limit=None):
        try:
            old = await client.http.get_guild_commands(app.id, guild.id)
            if old:
                await client.http.bulk_upsert_guild_commands(app.id, guild.id, [])
                removed["guilds"][guild.id] = len(old)
                log(f"server {guild.id}: removed {len(old)} command(s)")
        except Exception as e:  # e.g. missing access in one server — keep going
            log(f"server {guild.id}: skipped ({e})")
    return removed


def main() -> None:
    import discord
    from .config import load_config

    token = load_config().discord_token
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set")

    class _Purger(discord.Client):
        async def setup_hook(self) -> None:
            res = await purge_commands(self)
            total = res["global"] + sum(res["guilds"].values())
            print(f"done: {total} command(s) removed. Start the bot to register the new ones.")
            await self.close()

    _Purger(intents=discord.Intents.none()).run(token, log_handler=None)


if __name__ == "__main__":
    main()
