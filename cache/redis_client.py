"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

# ─────────────────────────────────────────────────────────────────────────────
# Versão com suporte a REDIS_URL (Upstash / Railway / Render / Vercel KV).
#
# Prioridade de configuração:
#   1. REDIS_URL  → string de conexão completa  (ex.: rediss://default:xxx@host:port)
#   2. REDIS_HOST + REDIS_PORT + REDIS_DB       → variáveis individuais (comportamento original)
# ─────────────────────────────────────────────────────────────────────────────

import logging
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import redis
else:
    try:
        import redis
    except ImportError:
        redis = None  # type: ignore

from app.config import Config

logger = logging.getLogger(__name__)

_redis_client: Optional['redis.Redis'] = None
_last_warning_log = 0.0
_WARNING_LOG_COOLDOWN = 60


def _build_client() -> Optional['redis.Redis']:
    """Cria o cliente Redis a partir de REDIS_URL ou variáveis individuais."""
    if redis is None:
        return None

    import os
    redis_url = os.getenv('REDIS_URL', '').strip()

    if redis_url:
        # Upstash / serviços com URL completa (rediss:// ou redis://)
        return redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    # Comportamento original: REDIS_HOST + REDIS_PORT + REDIS_DB
    if not Config.REDIS_HOST or Config.REDIS_HOST.strip() == '':
        return None

    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        decode_responses=False,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def init_redis():
    global _redis_client, _last_warning_log

    if redis is None:
        _redis_client = None
        return

    try:
        client = _build_client()
        if client is None:
            _redis_client = None
            return
        client.ping()
        _redis_client = client
        _last_warning_log = 0.0
    except Exception:
        _redis_client = None


def get_redis_client() -> Optional['redis.Redis']:
    if redis is None:
        return None

    if _redis_client is None:
        try:
            init_redis()
        except Exception:
            pass
    return _redis_client
