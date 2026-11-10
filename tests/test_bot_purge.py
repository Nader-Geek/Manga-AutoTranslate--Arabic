"""Stale-command purge with a fake Discord client. Run: python3 tests/test_bot_purge.py"""
import asyncio, os, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.purge_commands import purge_commands
from bot.config import load_config

class FakeHTTP:
    def __init__(self, glob, guilds): self.glob, self.guilds, self.calls = glob, guilds, []
    async def get_global_commands(self, app): return list(self.glob)
    async def bulk_upsert_global_commands(self, app, payload): self.calls.append(("global", payload)); self.glob = payload
    async def get_guild_commands(self, app, gid):
        if gid == 666: raise RuntimeError("Missing Access")
        return list(self.guilds.get(gid, []))
    async def bulk_upsert_guild_commands(self, app, gid, payload): self.calls.append((gid, payload)); self.guilds[gid] = payload

class FakeClient:
    def __init__(self, http, guild_ids): self.http, self._g = http, guild_ids
    async def application_info(self): return NS(id=42)
    async def fetch_guilds(self, limit=None):
        for g in self._g: yield NS(id=g)

async def main():
    http = FakeHTTP(["old1", "old2"], {1: ["a", "b", "c"], 2: [], 3: ["x"]})
    logs = []
    res = await purge_commands(FakeClient(http, [1, 2, 3, 666]), log=logs.append)
    assert res == {"global": 2, "guilds": {1: 3, 3: 1}}, res
    assert http.glob == [] and http.guilds[1] == [] and http.guilds[3] == []
    assert not any(c[0] == 2 for c in http.calls), "empty server must not be touched"
    assert any("666" in l and "skipped" in l for l in logs), "a failing server must not abort the purge"
    # idempotent + guild-only mode leaves global commands alone
    http2 = FakeHTTP(["keep"], {1: ["a"]})
    res = await purge_commands(FakeClient(http2, [1]), include_global=False, log=lambda *_: None)
    assert res["global"] == 0 and http2.glob == ["keep"] and http2.guilds[1] == []
    res = await purge_commands(FakeClient(http2, [1]), include_global=False, log=lambda *_: None)
    assert res["guilds"] == {}
asyncio.run(main())

for k in ("PURGE_OLD_COMMANDS", "MAX_UPLOAD_MB"): os.environ.pop(k, None)
c = load_config(); assert c.purge_old_commands is False and c.max_upload_mb == 100
os.environ["PURGE_OLD_COMMANDS"] = "1"; os.environ["MAX_UPLOAD_MB"] = "250"
c = load_config(); assert c.purge_old_commands is True and c.max_upload_mb == 250
print("test_bot_purge OK")
