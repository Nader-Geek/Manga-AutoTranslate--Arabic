"""bot/colab_auth with faked google.colab / google.auth modules (the real ones only exist in Colab)."""
import os, stat, sys, tempfile, time, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import colab_auth

# outside Colab -> clean RuntimeError (the notebook catches it and continues without Drive)
try: colab_auth.start_token_file(); raise SystemExit("expected RuntimeError")
except RuntimeError as e: assert "Colab" in str(e)

calls = {"auth": 0, "n": 0}
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m
class Creds:
    token = None
    def refresh(self, req): calls["n"] += 1; self.token = f"tok{calls['n']}"
google = mod("google")
colab = mod("google.colab"); colab.auth = mod("google.colab.auth", authenticate_user=lambda: calls.__setitem__("auth", calls["auth"] + 1))
gauth = mod("google.auth", default=lambda: (Creds(), "proj")); google.auth = gauth; google.colab = colab
tr = mod("google.auth.transport"); trr = mod("google.auth.transport.requests", Request=object); tr.requests = trr; gauth.transport = tr

path = os.path.join(tempfile.mkdtemp(), "tok")
assert colab_auth.start_token_file(path, every_s=1) == path
assert Path(path).read_text() == "tok1" and calls["auth"] == 1
assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
time.sleep(2.3); assert Path(path).read_text() in ("tok2", "tok3"), Path(path).read_text()
print("test_colab_auth OK")
