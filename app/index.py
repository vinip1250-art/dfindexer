"""Vercel entrypoint for the Flask application."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from app.bootstrap import Bootstrap
from app.config import Config
from utils.logging.logger import print_support_banner, setup_logging

setup_logging(Config.LOG_LEVEL, Config.LOG_FORMAT)
print_support_banner(Config.LOG_FORMAT)

app = Bootstrap.create_app()
