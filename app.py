"""Vercel entrypoint for the Flask application.

Vercel may prefer a root app.py entrypoint for Flask projects. This file is
also imported as the "app" module, so it exposes __path__ to keep imports like
app.config and app.bootstrap resolving to the existing app/ package directory.
"""

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
__path__ = [os.path.join(ROOT_DIR, "app")]

from app.bootstrap import Bootstrap
from app.config import Config
from utils.logging.logger import print_support_banner, setup_logging

setup_logging(Config.LOG_LEVEL, Config.LOG_FORMAT)
print_support_banner(Config.LOG_FORMAT)

app = Bootstrap.create_app()
