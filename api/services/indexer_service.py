"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import re
import logging
import requests as _requests
from typing import List, Dict, Optional
from app.config import Config
from scraper import (
    create_scraper,
    available_scraper_types,
    normalize_scraper_type,
)
from cache import cleanup_request_caches
from core.enrichers.torrent_enricher import TorrentEnricher
from core.filters.query_filter import QueryFilter
from core.processors.torrent_processor import TorrentProcessor

logger = logging.getLogger(__name__)

_IMDB_ID_RE = re.compile(r'^tt\d+$', re.IGNORECASE)

SCRAPER_NUMBER_MAP = {
    "1": "starck",
    "2": "rede",
    "3": "xfilmes",
    "4": "tfilme",
    "5": None,  # Removido (vaca)
    "6": "comand",
    "7": "bludv",
    "8": "portal",
}


def get_valid_scraper_ids() -> Dict[str, str]:
    return {k: v for k, v in SCRAPER_NUMBER_MAP.items() if v is not None}


def _resolve_imdb_to_title(imdb_id: str) -> Optional[str]:
    """
    Resolve IMDB ID → título original via scraping direto do IMDB.
    Não depende de chave de API.
    """
    # Tentativa 1: endpoint JSON do IMDB (não requer chave)
    try:
        resp = _requests.get(
            f"https://www.imdb.com/title/{imdb_id}/",
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=8,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            # Tenta extrair do JSON-LD (mais confiável que regex no <title>)
            json_ld_match = re.search(
                r'"@type"\s*:\s*"(?:Movie|TVSeries|TVMiniSeries)"[^}]*"name"\s*:\s*"([^"]+)"',
                resp.text
            )
            if json_ld_match:
                title = json_ld_match.group(1).strip()
                if title:
                    logger.info(f"[IMDB] {imdb_id} → '{title}' (JSON-LD)")
                    return title

            # Fallback: og:title meta tag
            og_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"(]+)', resp.text)
            if og_match:
                title = og_match.group(1).strip()
                if title:
                    logger.info(f"[IMDB] {imdb_id} → '{title}' (og:title)")
                    return title

            # Fallback: tag <title>
            title_match = re.search(r'<title>([^<(]+)', resp.text)
            if title_match:
                title = title_match.group(1).strip().rstrip(" -")
                if title and title.lower() not in ("imdb", ""):
                    logger.info(f"[IMDB] {imdb_id} → '{title}' (<title>)")
                    return title

    except Exception as e:
        logger.debug(f"[IMDB] Erro ao resolver {imdb_id}: {type(e).__name__}: {e}")

    logger.warning(f"[IMDB] Não foi possível resolver: {imdb_id}")
    return None


class IndexerService:
    def __init__(self):
        self.enricher = TorrentEnricher()
        self.processor = TorrentProcessor()

    # Busca torrents por query
    def search(self, scraper_type: str, query: str, use_flaresolverr: bool = False, filter_results: bool = False, max_results: Optional[int] = None) -> tuple[List[Dict], Optional[Dict]]:

        # Se a query é um IMDB ID, resolve para título antes de buscar
        imdb_filter_func = None
        effective_query = query
        if query and _IMDB_ID_RE.match(query.strip()):
            imdb_id = query.strip().lower()
            resolved_title = _resolve_imdb_to_title(imdb_id)
            if resolved_title:
                effective_query = resolved_title
                logger.info(f"[IMDB] Buscando por título resolvido: '{effective_query}' (id={imdb_id})")
                # Filtro secundário por IMDB ID — só aplica se o campo imdb estiver preenchido
                def _make_imdb_filter(target_id):
                    def _f(torrent: Dict) -> bool:
                        torrent_imdb = (torrent.get('imdb') or '').strip().lower()
                        if torrent_imdb:
                            return torrent_imdb == target_id
                        return True  # campo vazio → aceita (pode não ter sido extraído)
                    return _f
                imdb_filter_func = _make_imdb_filter(imdb_id)
            else:
                logger.warning(f"[IMDB] Busca abortada — não foi possível resolver: {imdb_id}")
                return [], None

        scraper = create_scraper(scraper_type, use_flaresolverr=use_flaresolverr)

        try:
            filter_func = None
            if effective_query:
                filter_func = QueryFilter.create_filter(effective_query)

            # Combina filtro de título com filtro de IMDB ID (quando aplicável)
            if imdb_filter_func:
                title_filter = filter_func
                def combined_filter(torrent: Dict) -> bool:
                    if title_filter and not title_filter(torrent):
                        return False
                    return imdb_filter_func(torrent)
                filter_func = combined_filter

            torrents = scraper.search(effective_query, filter_func=filter_func)

            filter_stats = None
            if hasattr(scraper, '_enricher') and scraper._enricher:
                if hasattr(scraper._enricher, '_last_filter_stats'):
                    stats = scraper._enricher._last_filter_stats
                    if stats and isinstance(stats, dict):
                        filter_stats = {
                            'total': stats.get('total', 0),
                            'filtered': stats.get('filtered', 0),
                            'approved': stats.get('approved', 0),
                            'scraper_name': stats.get('scraper_name', '')
                        }

            if max_results and max_results > 0:
                torrents = torrents[:max_results]

            self.processor.sanitize_torrents(torrents)
            self.processor.remove_internal_fields(torrents)
            self.processor.sort_by_date(torrents)

            return torrents, filter_stats
        finally:
            scraper.close()
            cleanup_request_caches()

    # Retorna as estatísticas do último filtro aplicado
    def get_last_filter_stats(self):
        return self.enricher._last_filter_stats if hasattr(self.enricher, '_last_filter_stats') else None

    # Obtém torrents de uma página
    def get_page(self, scraper_type: str, page: str = '1', use_flaresolverr: bool = False, is_test: bool = False, max_results: Optional[int] = None) -> tuple[List[Dict], Optional[Dict]]:
        scraper = create_scraper(scraper_type, use_flaresolverr=use_flaresolverr)

        try:
            max_links = None
            if is_test:
                max_links = Config.EMPTY_QUERY_MAX_LINKS if Config.EMPTY_QUERY_MAX_LINKS > 0 else None

            torrents = scraper.get_page(page, max_items=max_links, is_test=is_test)

            if max_results and max_results > 0:
                torrents = torrents[:max_results]

            filter_stats = None
            if hasattr(scraper, '_enricher') and hasattr(scraper._enricher, '_last_filter_stats'):
                stats = scraper._enricher._last_filter_stats
                if stats:
                    filter_stats = {
                        'total': stats.get('total', 0),
                        'filtered': stats.get('filtered', 0),
                        'approved': stats.get('approved', 0),
                        'scraper_name': stats.get('scraper_name', '')
                    }

            self.processor.sanitize_torrents(torrents)
            self.processor.remove_internal_fields(torrents)

            if not (is_test and Config.EMPTY_QUERY_MAX_LINKS > 0):
                self.processor.sort_by_date(torrents)

            return torrents, filter_stats
        finally:
            scraper.close()
            cleanup_request_caches()

    # Obtém informações dos scrapers disponíveis
    def get_scraper_info(self) -> Dict:
        types_info = available_scraper_types()
        sites_dict = {
            scraper_type: meta.get('default_url')
            for scraper_type, meta in types_info.items()
            if meta.get('default_url')
        }

        return {
            'configured_sites': sites_dict,
            'available_types': list(types_info.keys()),
            'types_info': types_info
        }

    # Valida tipo de scraper e retorna tipo normalizado
    def validate_scraper_type(self, scraper_type: str) -> tuple[bool, Optional[str]]:
        if scraper_type in SCRAPER_NUMBER_MAP:
            mapped_type = SCRAPER_NUMBER_MAP[scraper_type]
            if mapped_type is None:
                return False, None
            scraper_type = mapped_type

        types_info = available_scraper_types()
        normalized_type = normalize_scraper_type(scraper_type)

        if normalized_type not in types_info:
            return False, None

        return True, normalized_type
