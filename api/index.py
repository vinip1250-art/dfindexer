# api/index.py
import sys, os, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("FLARESOLVERR_ADDRESS", "")
os.environ.setdefault("REDIS_HOST", "")

# Mock waitress — não é necessário no Vercel
mock_waitress = types.ModuleType("waitress")
mock_waitress.serve = lambda *a, **kw: None
sys.modules["waitress"] = mock_waitress

from app.main import app  # Flask app
