"""
api/index.py — Entry point para o Vercel.

Este arquivo importa a aplicação existente e a expõe via handler ASGI/WSGI.
Ajuste o import conforme o framework usado no projeto:
  - FastAPI  → use Mangum (ASGI)
  - Flask    → use o app diretamente (WSGI)
"""
import sys
import os

# Adiciona a raiz do projeto ao path para que os módulos internos sejam encontrados
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# -----------------------------------------------------------------------
# Patch de compatibilidade: desabilita Redis/FlareSolverr antes de qualquer
# import do projeto, garantindo que o módulo cache/ em memória seja usado.
# -----------------------------------------------------------------------
os.environ.setdefault("REDIS_HOST", "")          # sem Redis
os.environ.setdefault("FLARESOLVERR_ADDRESS", "")  # sem FlareSolverr

# -----------------------------------------------------------------------
# Import da aplicação principal
# Tente primeiro FastAPI com Mangum, depois Flask puro
# -----------------------------------------------------------------------
try:
    # --- FastAPI + Mangum ---
    from mangum import Mangum  # pip install mangum

    # Importa o app FastAPI do projeto original.
    # Ajuste o caminho conforme necessário (ex: "app.main", "core.app", etc.)
    try:
        from app.main import app as fastapi_app
    except ImportError:
        from core.app import app as fastapi_app

    handler = Mangum(fastapi_app, lifespan="off")

    # Vercel chama a função `handler` para requests ASGI
    app = handler

except ImportError:
    # --- Flask / WSGI ---
    try:
        from app.main import app
    except ImportError:
        from core.app import app

    # Para Flask, Vercel chama `app` diretamente (WSGI)
    # Nada adicional necessário
