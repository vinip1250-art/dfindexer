import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("FLARESOLVERR_ADDRESS", "")
os.environ.setdefault("REDIS_HOST", "")

from app.main import app  # Flask app — Vercel usa diretamente como WSGI
