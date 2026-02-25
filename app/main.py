import sys
import os
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("FLARESOLVERR_ADDRESS", "")
os.environ.setdefault("REDIS_HOST", "")

for _mod in ("waitress", "gunicorn", "gevent"):
    if _mod not in sys.modules:
        _m = types.ModuleType(_mod)
        _m.serve = lambda *a, **kw: None
        sys.modules[_mod] = _m

from app.main import create_app

app = create_app()
