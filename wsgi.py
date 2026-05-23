"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

# ─────────────────────────────────────────────────────────────────────────────
# Ponto de entrada WSGI para a Vercel.
# A Vercel importa este arquivo e procura a variável `app`.
#
# IMPORTANTE: o diretório `api/` do projeto é um pacote Python interno
# (tem __init__.py), por isso a Vercel não o trata como funções serverless.
# Todo o tráfego é roteado para este arquivo via vercel.json.
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys

# Garante que o raiz do projeto está no sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importações adiadas para reduzir tempo de cold start
from app.config import Config
from app.bootstrap import Bootstrap
from utils.logging.logger import setup_logging

setup_logging(Config.LOG_LEVEL, Config.LOG_FORMAT)

# Variável `app` é o que a Vercel (@vercel/python) procura neste arquivo
app = Bootstrap.create_app()

# Permite rodar localmente: python app.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "7006")), debug=False)
