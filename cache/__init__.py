"""
Cache adapter para Vercel — usa apenas memória, sem Redis.

Substitua o __init__.py original do diretório cache/ por este arquivo.
Mantém a mesma interface pública que o código original espera.
"""
import os
import logging
from .memory_cache import MemoryRedis, TTLCache, get_memory_redis

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Compatibilidade: o projeto original expõe get_redis_client() e variáveis
# de TTL lidas de env vars.
# -----------------------------------------------------------------------

HTML_CACHE_TTL_SHORT = int(
    os.getenv("HTML_CACHE_TTL_SHORT", str(10 * 60))   # 10 min
)
HTML_CACHE_TTL_LONG = int(
    os.getenv("HTML_CACHE_TTL_LONG", str(12 * 60 * 60))  # 12h
)

# Cache local em memória de 30s (já existia no projeto original, mantido)
_local_html_cache = TTLCache()
LOCAL_CACHE_TTL = 30  # segundos


def get_redis_client() -> MemoryRedis:
    """
    Retorna o cliente de cache em memória.
    Drop-in replacement para o cliente Redis original.
    """
    return get_memory_redis()


def is_redis_available() -> bool:
    """Sempre True — memória nunca falha."""
    return True


# -----------------------------------------------------------------------
# HTML Cache helpers (replicam o comportamento do projeto original)
# -----------------------------------------------------------------------

def get_html_cache(url: str) -> str | None:
    """Busca HTML cacheado. Primeiro local (30s), depois memória-redis."""
    # Camada 1: cache local 30s
    local_val = _local_html_cache.get(f"local:{url}")
    if local_val:
        return local_val

    # Camada 2: cache principal em memória
    redis = get_memory_redis()
    val = redis.get(f"html:{url}")
    if val:
        html = val.decode() if isinstance(val, bytes) else val
        # popula o local para as próximas chamadas imediatas
        _local_html_cache.set(f"local:{url}", html, ttl_seconds=LOCAL_CACHE_TTL)
        return html

    return None


def set_html_cache(url: str, html: str, is_large: bool = False) -> None:
    """Salva HTML no cache. TTL varia pelo tamanho da página."""
    redis = get_memory_redis()
    ttl = HTML_CACHE_TTL_LONG if is_large else HTML_CACHE_TTL_SHORT
    redis.setex(f"html:{url}", ttl, html)
    _local_html_cache.set(f"local:{url}", html, ttl_seconds=LOCAL_CACHE_TTL)


def delete_html_cache(url: str) -> None:
    redis = get_memory_redis()
    redis.delete(f"html:{url}")
    _local_html_cache.delete(f"local:{url}")


__all__ = [
    "get_redis_client",
    "is_redis_available",
    "get_html_cache",
    "set_html_cache",
    "delete_html_cache",
    "HTML_CACHE_TTL_SHORT",
    "HTML_CACHE_TTL_LONG",
    "LOCAL_CACHE_TTL",
    "MemoryRedis",
    "TTLCache",
]
