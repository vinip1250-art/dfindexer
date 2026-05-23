"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

# ─────────────────────────────────────────────────────────────────────────────
# Ponto de entrada para a Vercel (e outros hosts WSGI como Gunicorn/uWSGI).
# A Vercel importa este módulo e procura uma variável chamada `app`.
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys

# Garante que o diretório raiz do projeto está no sys.path,
# independente do diretório de trabalho da Vercel.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.config import Config
from app.bootstrap import Bootstrap
from utils.logging.logger import setup_logging

setup_logging(Config.LOG_LEVEL, Config.LOG_FORMAT)

# `app` é a variável que a Vercel (e Gunicorn) procura automaticamente.
app = Bootstrap.create_app()
