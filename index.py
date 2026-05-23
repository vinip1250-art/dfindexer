"""Vercel entrypoint for the Flask application."""

from app.bootstrap import Bootstrap
from app.config import Config
from utils.logging.logger import print_support_banner, setup_logging

setup_logging(Config.LOG_LEVEL, Config.LOG_FORMAT)
print_support_banner(Config.LOG_FORMAT)

app = Bootstrap.create_app()
