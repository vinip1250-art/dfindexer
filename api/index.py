import sys
import os
import types

# Raiz do projeto no path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Variáveis de ambiente
os.environ.setdefault("FLARESOLVERR_ADDRESS", "")
os.environ.setdefault("REDIS_HOST", "")

# ---- Mocks de módulos de servidor (não usados no Vercel) ----
for _mod in ("waitress", "gunicorn", "gevent"):
    if _mod not in sys.modules:
        _m = types.ModuleType(_mod)
        _m.serve = lambda *a, **kw: None
        sys.modules[_mod] = _m

# ---- Import do app Flask ----
from app.main import app
