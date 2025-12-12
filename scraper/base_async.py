"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
import asyncio
import html
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from bs4 import BeautifulSoup
import aiohttp
from cache.redis_client import get_redis_client
from cache.redis_keys import html_long_key, html_short_key
from app.config import Config
from tracker import get_tracker_service
from magnet.parser import MagnetParser
from utils.text.utils import format_bytes

logger = logging.getLogger(__name__)


# Classe base async para scrapers
class BaseScraperAsync(ABC):
    SCRAPER_TYPE: str = ''
    DEFAULT_BASE_URL: str = ''
    DISPLAY_NAME: str = ''
    
    def __init__(self, base_url: Optional[str] = None, use_flaresolverr: bool = False):
        resolved_url = (base_url or self.DEFAULT_BASE_URL or '').strip()
        if resolved_url and not resolved_url.endswith('/'):
            resolved_url = f"{resolved_url}/"
        if not resolved_url:
            raise ValueError(
                f"{self.__class__.__name__} requer DEFAULT_BASE_URL definido ou um base_url explícito"
            )
        self.base_url = resolved_url
        self.redis = get_redis_client()
        self._session: Optional[aiohttp.ClientSession] = None
        self.tracker_service = get_tracker_service()
        self._skip_metadata = False
        self._is_test = False
        
        # Estatísticas de cache
        self._cache_stats = {
            'html': {'hits': 0, 'misses': 0},
            'metadata': {'hits': 0, 'misses': 0},
            'trackers': {'hits': 0, 'misses': 0}
        }
        
        self.use_flaresolverr = use_flaresolverr and Config.FLARESOLVERR_ADDRESS is not None
        
        if use_flaresolverr and Config.FLARESOLVERR_ADDRESS is None:
            logger.warning("[[ FlareSolverr Não Conectado ]] - FLARESOLVERR_ADDRESS não configurado")
            self.use_flaresolverr = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém ou cria sessão aiohttp reutilizável com connection pooling otimizado."""
        if self._session is None or self._session.closed:
            # Timeout otimizado para balancear velocidade e confiabilidade
            timeout = aiohttp.ClientTimeout(
                total=Config.HTTP_REQUEST_TIMEOUT if hasattr(Config, 'HTTP_REQUEST_TIMEOUT') else 45,
                connect=5,
                sock_read=30
            )
            
            # Connection pooling otimizado - aumentado significativamente
            connector = aiohttp.TCPConnector(
                limit=200,  # Aumentado de 100 para 200 (total connections)
                limit_per_host=50,  # Aumentado de 20 para 50 (connections por host)
                ttl_dns_cache=300,  # Cache DNS por 5 minutos
                enable_cleanup_closed=True,  # Limpa conexões fechadas automaticamente
                force_close=False  # Reutiliza conexões quando possível
            )
            
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                },
                # Compressão automática para economizar banda
                auto_decompress=True
            )
        return self._session
    
    async def close(self):
        """Fecha a sessão aiohttp."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_document(self, url: str, referer: str = '') -> Optional[BeautifulSoup]:
        """Obtém documento HTML (async) com cache em múltiplas camadas."""
        # Verifica cache local primeiro (mais rápido que Redis)
        from cache.http_cache import get_http_cache
        http_cache = get_http_cache()
        
        if not self._is_test:
            cached_local = http_cache.get(url)
            if cached_local:
                self._cache_stats['html']['hits'] += 1
                return BeautifulSoup(cached_local, 'html.parser')
        
        # Verifica cache Redis
        if self.redis and not self._is_test:
            try:
                cache_key = html_long_key(url)
                cached = self.redis.get(cache_key)
                if cached:
                    self._cache_stats['html']['hits'] += 1
                    return BeautifulSoup(cached, 'html.parser')
            except:
                pass
            
            try:
                short_cache_key = html_short_key(url)
                cached = self.redis.get(short_cache_key)
                if cached:
                    self._cache_stats['html']['hits'] += 1
                    return BeautifulSoup(cached, 'html.parser')
            except:
                pass
        
        # Cache miss - será buscado do site
        self._cache_stats['html']['misses'] += 1
        
        # Por enquanto, FlareSolverr ainda é síncrono
        # TODO: Migrar FlareSolverr para async
        if self.use_flaresolverr and "%3A" not in url and "%3a" not in url.lower():
            # Tenta FlareSolverr primeiro (síncrono por enquanto)
            try:
                from utils.http.flaresolverr import FlareSolverrClient
                flaresolverr_client = FlareSolverrClient(Config.FLARESOLVERR_ADDRESS)
                session_id = flaresolverr_client.get_or_create_session(
                    self.base_url,
                    skip_redis=self._is_test
                )
                if session_id:
                    html_content = flaresolverr_client.solve(
                        url,
                        session_id,
                        referer if referer else self.base_url,
                        self.base_url,
                        skip_redis=self._is_test
                    )
                    if html_content:
                        # Salva no cache local primeiro (mais rápido)
                        if not self._is_test:
                            try:
                                http_cache.set(url, html_content)
                            except:
                                pass
                        
                        # Salva no Redis
                        if self.redis and not self._is_test:
                            try:
                                short_cache_key = html_short_key(url)
                                self.redis.setex(
                                    short_cache_key,
                                    Config.HTML_CACHE_TTL_SHORT,
                                    html_content
                                )
                                
                                cache_key = html_long_key(url)
                                self.redis.setex(
                                    cache_key,
                                    Config.HTML_CACHE_TTL_LONG,
                                    html_content
                                )
                            except:
                                pass
                        
                        return BeautifulSoup(html_content, 'html.parser')
            except Exception as e:
                logger.debug(f"FlareSolverr error: {type(e).__name__} - tentando requisição direta")
        
        # Requisição HTTP direta (async)
        session = await self._get_session()
        headers = {'Referer': referer if referer else self.base_url}
        
        try:
            import time as time_module
            start_time = time_module.time()
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                html_content = await response.read()
                elapsed_time = time_module.time() - start_time
                
                logger.debug(f"[BaseScraperAsync] HTTP GET: {url[:60]}... | Status: {response.status} | Tempo: {elapsed_time:.2f}s | Tamanho: {len(html_content)} bytes")
                
                # Salva no cache local primeiro (mais rápido)
                if not self._is_test:
                    try:
                        from cache.http_cache import get_http_cache
                        http_cache_inst = get_http_cache()
                        http_cache_inst.set(url, html_content)
                    except:
                        pass
                
                # Salva no Redis
                if self.redis and not self._is_test:
                    try:
                        short_cache_key = html_short_key(url)
                        self.redis.setex(
                            short_cache_key,
                            Config.HTML_CACHE_TTL_SHORT,
                            html_content
                        )
                        
                        cache_key = html_long_key(url)
                        self.redis.setex(
                            cache_key,
                            Config.HTML_CACHE_TTL_LONG,
                            html_content
                        )
                    except:
                        pass
                
                return BeautifulSoup(html_content, 'html.parser')
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e).split('\n')[0][:100] if str(e) else str(e)
            url_preview = url[:50] if url else 'N/A'
            logger.error(f"Document error: {error_type} - {error_msg} (url: {url_preview}...)")
            return None
    
    @abstractmethod
    async def search(self, query: str, filter_func: Optional[Callable[[Dict], bool]] = None) -> List[Dict]:
        """Busca torrents por query (async)."""
        pass
    
    @abstractmethod
    async def get_page(self, page: str = '1', max_items: Optional[int] = None) -> List[Dict]:
        """Obtém torrents de uma página específica (async)."""
        pass
    
    @abstractmethod
    async def _get_torrents_from_page(self, link: str) -> List[Dict]:
        """Extrai torrents de uma página individual de torrent (async)."""
        pass
    
    def _resolve_link(self, href: str) -> Optional[str]:
        """Resolve automaticamente qualquer link (magnet direto ou protegido)."""
        if not href:
            return None
        
        if href.startswith('magnet:'):
            href = href.replace('&amp;', '&').replace('&#038;', '&')
            return html.unescape(href)
        
        # Link protegido ainda é resolvido de forma síncrona
        # TODO: Migrar para async
        try:
            from utils.parsing.link_resolver import is_protected_link, resolve_protected_link
            if is_protected_link(href):
                # Por enquanto usa requests síncrono
                import requests
                session = requests.Session()
                resolved = resolve_protected_link(href, session, self.base_url, redis=self.redis)
                return resolved
        except Exception as e:
            logger.debug(f"Link resolver error: {type(e).__name__}")
        
        return None
    
    async def enrich_torrents(
        self,
        torrents: List[Dict],
        skip_metadata: bool = False,
        skip_trackers: bool = False,
        filter_func: Optional[Callable[[Dict], bool]] = None
    ) -> List[Dict]:
        """Enriquece torrents (async)."""
        from core.enrichers.torrent_enricher_async import TorrentEnricherAsync
        from scraper import available_scraper_types
        
        if not hasattr(self, '_enricher'):
            self._enricher = TorrentEnricherAsync()
        
        scraper_name = None
        if hasattr(self, 'SCRAPER_TYPE'):
            scraper_type = getattr(self, 'SCRAPER_TYPE', '')
            types_info = available_scraper_types()
            normalized_type = scraper_type.lower().strip()
            if normalized_type in types_info:
                scraper_name = types_info[normalized_type].get('display_name', scraper_type)
            else:
                scraper_name = getattr(self, 'DISPLAY_NAME', '') or scraper_type
        
        return await self._enricher.enrich(
            torrents,
            skip_metadata,
            skip_trackers,
            filter_func,
            scraper_name=scraper_name
        )

