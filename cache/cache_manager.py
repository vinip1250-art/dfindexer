"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
import threading
import time
from typing import Optional, List, Dict, Any
from cache.redis_client import get_redis_client
from cache.http_cache import get_http_cache

logger = logging.getLogger(__name__)


class CacheInvalidationManager:
    """
    Gerenciador de invalidação inteligente de cache.
    Monitora padrões de acesso e invalida cache quando necessário.
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.http_cache = get_http_cache()
        self._lock = threading.Lock()
        self._invalidation_log: Dict[str, float] = {}  # URL -> timestamp última invalidação
        self._min_invalidation_interval = 300  # 5 minutos mínimo entre invalidações da mesma URL
    
    def invalidate_url(self, url: str, reason: str = "manual") -> bool:
        """
        Invalida cache de uma URL específica em todas as camadas.
        
        Args:
            url: URL para invalidar
            reason: Razão da invalidação (para logging)
            
        Returns:
            True se invalidou, False se não foi necessário (recente)
        """
        with self._lock:
            now = time.time()
            last_invalidation = self._invalidation_log.get(url, 0)
            
            # Evita invalidações muito frequentes da mesma URL
            if now - last_invalidation < self._min_invalidation_interval:
                return False
            
            # Invalida cache local
            try:
                # HTTP cache usa dict interno, precisamos remover manualmente
                with self.http_cache._lock:
                    if url in self.http_cache._cache:
                        del self.http_cache._cache[url]
                        logger.debug(f"Cache local invalidado: {url[:50]}... (razão: {reason})")
            except Exception as e:
                logger.debug(f"Erro ao invalidar cache local: {type(e).__name__}")
            
            # Invalida Redis
            if self.redis:
                try:
                    from cache.redis_keys import html_long_key, html_short_key
                    long_key = html_long_key(url)
                    short_key = html_short_key(url)
                    
                    deleted = 0
                    if self.redis.exists(long_key):
                        self.redis.delete(long_key)
                        deleted += 1
                    if self.redis.exists(short_key):
                        self.redis.delete(short_key)
                        deleted += 1
                    
                    if deleted > 0:
                        logger.debug(f"Cache Redis invalidado: {url[:50]}... ({deleted} chaves, razão: {reason})")
                except Exception as e:
                    logger.debug(f"Erro ao invalidar cache Redis: {type(e).__name__}")
            
            # Registra invalidação
            self._invalidation_log[url] = now
            
            # Limpa log antigo (mais de 1 hora)
            old_urls = [u for u, t in self._invalidation_log.items() if now - t > 3600]
            for old_url in old_urls:
                del self._invalidation_log[old_url]
            
            return True
    
    def invalidate_pattern(self, base_url: str, pattern: str = "*") -> int:
        """
        Invalida cache de URLs que correspondem a um padrão.
        
        Args:
            base_url: URL base do site (ex: 'https://example.com/')
            pattern: Padrão para matching (suporta * wildcard)
            
        Returns:
            Número de URLs invalidadas
        """
        invalidated = 0
        
        # Invalida cache local
        with self.http_cache._lock:
            urls_to_remove = []
            for url in list(self.http_cache._cache.keys()):
                if url.startswith(base_url):
                    if pattern == "*" or pattern in url:
                        urls_to_remove.append(url)
            
            for url in urls_to_remove:
                del self.http_cache._cache[url]
                invalidated += 1
        
        if invalidated > 0:
            logger.info(f"Cache invalidado: {invalidated} URLs de {base_url} (padrão: {pattern})")
        
        return invalidated
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas consolidadas de todas as camadas de cache.
        
        Returns:
            Dict com estatísticas
        """
        stats = {
            'http_cache': self.http_cache.stats() if self.http_cache else {},
            'redis_available': self.redis is not None,
            'invalidations_logged': len(self._invalidation_log)
        }
        
        # Estatísticas do Redis (se disponível)
        if self.redis:
            try:
                info = self.redis.info('memory')
                stats['redis_memory'] = {
                    'used_memory_human': info.get('used_memory_human', 'N/A'),
                    'used_memory_peak_human': info.get('used_memory_peak_human', 'N/A'),
                }
            except Exception:
                stats['redis_memory'] = {'error': 'unable to fetch'}
        
        return stats
    
    def warm_cache(self, urls: List[str], fetch_func) -> int:
        """
        Pre-aquece o cache com uma lista de URLs.
        Útil para preparar o cache antes de uma carga pesada.
        
        Args:
            urls: Lista de URLs para pre-aquecer
            fetch_func: Função para buscar conteúdo (recebe URL, retorna bytes)
            
        Returns:
            Número de URLs cacheadas com sucesso
        """
        cached = 0
        
        for url in urls:
            try:
                # Verifica se já está em cache
                if self.http_cache.get(url):
                    continue
                
                # Busca e cacheia
                content = fetch_func(url)
                if content:
                    self.http_cache.set(url, content)
                    cached += 1
            except Exception as e:
                logger.debug(f"Erro ao aquecer cache para {url[:50]}: {type(e).__name__}")
        
        if cached > 0:
            logger.info(f"Cache aquecido: {cached}/{len(urls)} URLs")
        
        return cached


# Singleton global
_cache_manager = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheInvalidationManager:
    """
    Obtém instância global do gerenciador de cache.
    Thread-safe singleton pattern.
    
    Returns:
        Instância de CacheInvalidationManager
    """
    global _cache_manager
    
    if _cache_manager is None:
        with _cache_manager_lock:
            if _cache_manager is None:
                _cache_manager = CacheInvalidationManager()
    
    return _cache_manager

