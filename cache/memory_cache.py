"""
Cache em memória substituindo Redis para deploy no Vercel.
Thread-safe com TTL automático usando cachetools.
"""
import threading
import time
from typing import Any, Optional

# ---------------------------------------------------------------------------
# TTL Cache simples (sem dependência extra)
# ---------------------------------------------------------------------------

class TTLCache:
    """Dict com TTL por entrada. Thread-safe."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float = 60) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def expire(self, key: str, ttl_seconds: float) -> None:
        with self._lock:
            item = self._store.get(key)
            if item is not None:
                value, _ = item
                self._store[key] = (value, time.monotonic() + ttl_seconds)

    def keys(self, pattern: str = "*") -> list[str]:
        """Retorna chaves (sem suporte real a glob, só para compatibilidade)."""
        now = time.monotonic()
        with self._lock:
            # Remove expirados
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
            if pattern == "*":
                return list(self._store.keys())
            # Suporte básico a prefixo tipo "html:*"
            prefix = pattern.rstrip("*")
            return [k for k in self._store if k.startswith(prefix)]

    def flush(self) -> None:
        with self._lock:
            self._store.clear()


# Instância global (compartilhada dentro do mesmo processo/worker)
_global_cache = TTLCache()


# ---------------------------------------------------------------------------
# Interface compatível com o uso de Redis no projeto original
# ---------------------------------------------------------------------------

class MemoryRedis:
    """
    Substituto drop-in para redis.Redis usando TTLCache em memória.
    Implementa apenas os métodos usados pelo dfindexer.
    """

    def __init__(self):
        self._cache = _global_cache

    # --- Strings ---
    def get(self, key: str) -> Optional[bytes]:
        val = self._cache.get(key)
        if val is None:
            return None
        if isinstance(val, str):
            return val.encode()
        if isinstance(val, bytes):
            return val
        return str(val).encode()

    def set(self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None) -> bool:
        ttl = 3600  # padrão 1h
        if ex is not None:
            ttl = ex
        elif px is not None:
            ttl = px / 1000
        self._cache.set(key, value, ttl_seconds=ttl)
        return True

    def setex(self, key: str, time_seconds: int, value: Any) -> bool:
        self._cache.set(key, value, ttl_seconds=time_seconds)
        return True

    def delete(self, *keys) -> int:
        count = 0
        for key in keys:
            existed = self._cache.exists(key)
            self._cache.delete(key)
            count += int(existed)
        return count

    def exists(self, key: str) -> int:
        return 1 if self._cache.exists(key) else 0

    def expire(self, key: str, seconds: int) -> bool:
        self._cache.expire(key, seconds)
        return True

    def ttl(self, key: str) -> int:
        with self._cache._lock:
            item = self._cache._store.get(key)
            if item is None:
                return -2
            _, expires_at = item
            remaining = expires_at - time.monotonic()
            return int(remaining) if remaining > 0 else -2

    def keys(self, pattern: str = "*") -> list[bytes]:
        return [k.encode() for k in self._cache.keys(pattern)]

    # --- Hashes ---
    def hget(self, name: str, key: str) -> Optional[bytes]:
        d = self._cache.get(name)
        if not isinstance(d, dict):
            return None
        val = d.get(key)
        if val is None:
            return None
        return val.encode() if isinstance(val, str) else val

    def hset(self, name: str, key: str = None, value: Any = None, mapping: dict = None) -> int:
        d = self._cache.get(name) or {}
        if not isinstance(d, dict):
            d = {}
        if mapping:
            d.update(mapping)
        elif key is not None:
            d[key] = value
        self._cache.set(name, d, ttl_seconds=3600)
        return 1

    def hgetall(self, name: str) -> dict:
        d = self._cache.get(name)
        if not isinstance(d, dict):
            return {}
        return {k.encode() if isinstance(k, str) else k:
                v.encode() if isinstance(v, str) else v
                for k, v in d.items()}

    def hmset(self, name: str, mapping: dict) -> bool:
        return bool(self.hset(name, mapping=mapping))

    def hdel(self, name: str, *keys) -> int:
        d = self._cache.get(name)
        if not isinstance(d, dict):
            return 0
        count = 0
        for k in keys:
            if k in d:
                del d[k]
                count += 1
        self._cache.set(name, d, ttl_seconds=3600)
        return count

    # --- Listas ---
    def rpush(self, key: str, *values) -> int:
        lst = self._cache.get(key) or []
        if not isinstance(lst, list):
            lst = []
        lst.extend(values)
        self._cache.set(key, lst, ttl_seconds=3600)
        return len(lst)

    def lrange(self, key: str, start: int, end: int) -> list:
        lst = self._cache.get(key) or []
        if not isinstance(lst, list):
            return []
        end = None if end == -1 else end + 1
        return [v.encode() if isinstance(v, str) else v for v in lst[start:end]]

    # --- Ping ---
    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass


def get_memory_redis() -> MemoryRedis:
    """Retorna instância singleton do MemoryRedis."""
    return _instance


_instance = MemoryRedis()
