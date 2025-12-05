"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
import threading
import time
from typing import Optional
from cache.redis_client import get_redis_client
from cache.redis_keys import html_long_key, html_short_key
from app.config import Config

logger = logging.getLogger(__name__)

# Cache em memória por requisição (apenas quando Redis não está disponível)
_request_cache = threading.local()


# Cache para documentos HTML
class HTMLCache:
    def __init__(self):
        self.redis = get_redis_client()
    
    def get(self, url: str) -> Optional[bytes]:
        # Obtém HTML do cache (Redis primeiro, memória se Redis não disponível)
        # Tenta Redis primeiro
        if self.redis:
            try:
                # Tenta cache de longa duração primeiro
                cache_key = html_long_key(url)
                cached = self.redis.get(cache_key)
                if cached:
                    return cached
                
                # Tenta cache de curta duração
                short_cache_key = html_short_key(url)
                cached = self.redis.get(short_cache_key)
                if cached:
                    return cached
            except Exception:
                # Se Redis falhou durante operação, não usa memória
                return None
        
        # Usa memória apenas se Redis não está disponível desde o início
        if not self.redis:
            if not hasattr(_request_cache, 'html_cache'):
                _request_cache.html_cache = {}
            
            cache_entry = _request_cache.html_cache.get(url)
            if cache_entry:
                cached_content, expire_at = cache_entry
                if time.time() < expire_at:
                    return cached_content
                else:
                    # Expirou, remove
                    del _request_cache.html_cache[url]
        
        return None
    
    def set(self, url: str, html_content: bytes, skip_cache: bool = False) -> None:
        # Salva HTML no cache (Redis primeiro, memória se Redis não disponível)
        if skip_cache:
            return
        
        # Tenta Redis primeiro
        if self.redis:
            try:
                # Cache de curta duração
                short_cache_key = html_short_key(url)
                self.redis.setex(
                    short_cache_key,
                    Config.HTML_CACHE_TTL_SHORT,
                    html_content
                )
                
                # Cache de longa duração
                cache_key = html_long_key(url)
                self.redis.setex(
                    cache_key,
                    Config.HTML_CACHE_TTL_LONG,
                    html_content
                )
                return
            except Exception:
                # Se Redis falhou durante operação, não salva em memória
                return
        
        # Salva em memória apenas se Redis não está disponível desde o início
        if not self.redis:
            if not hasattr(_request_cache, 'html_cache'):
                _request_cache.html_cache = {}
            
            # Usa TTL curto para memória (10 minutos)
            expire_at = time.time() + Config.HTML_CACHE_TTL_SHORT
            _request_cache.html_cache[url] = (html_content, expire_at)

