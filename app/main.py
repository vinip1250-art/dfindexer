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

import app.main as _main
import inspect

# Tenta encontrar o app Flask automaticamente
from flask import Flask
app = None
for _name, _obj in inspect.getmembers(_main):
    if isinstance(_obj, Flask):
        app = _obj
        break

if app is None:
    raise RuntimeError(f"Flask app não encontrado em app.main. Membros: {dir(_main)}")
