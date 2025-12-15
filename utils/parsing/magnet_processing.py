"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def process_magnet_links(
    magnet_links: List[str],
    page_data: Dict,
    scraper_instance,
    sizes: Optional[List[str]] = None
) -> List[Dict]:
    """
    Processa uma lista de magnet links e retorna torrents formatados.
    
    Centraliza a lógica comum de processamento de magnets que estava duplicada
    em todos os scrapers.
    
    Args:
        magnet_links: Lista de magnet links resolvidos
        page_data: Dicionário com dados extraídos da página:
            - original_title: Título original
            - translated_title: Título traduzido
            - page_title: Título da página (fallback)
            - year: Ano
            - imdb: ID do IMDB
            - date: Data (datetime ou None)
            - absolute_link: URL da página
            - audio_info: Informação de áudio detectada do HTML
            - audio_html_content: HTML para detecção adicional de áudio
        scraper_instance: Instância do scraper (para acessar _skip_metadata)
        sizes: Lista de tamanhos extraídos (opcional)
    
    Returns:
        Lista de dicionários de torrents formatados
    """
    from magnet.parser import MagnetParser
    from utils.parsing.magnet_utils import process_trackers
    from utils.text.title_builder import create_standardized_title, prepare_release_title
    from utils.parsing.audio_extraction import add_audio_tag_if_needed
    from utils.text.cross_data import get_cross_data_from_redis, save_cross_data_to_redis
    from utils.text.storage import save_release_title_to_redis
    from utils.logging import format_error, format_link_preview
    
    torrents = []
    sizes = sizes or []
    
    # Extrai dados da página
    original_title = page_data.get('original_title', '')
    translated_title = page_data.get('translated_title', '')
    page_title = page_data.get('page_title', '')
    year = page_data.get('year', '')
    imdb = page_data.get('imdb', '')
    date = page_data.get('date')
    absolute_link = page_data.get('absolute_link', '')
    audio_info = page_data.get('audio_info')
    audio_html_content = page_data.get('audio_html_content', '')
    
    # Acessa flags do scraper
    skip_metadata = getattr(scraper_instance, '_skip_metadata', False)
    
    for idx, magnet_link in enumerate(magnet_links):
        try:
            magnet_data = MagnetParser.parse(magnet_link)
            info_hash = magnet_data['info_hash']
            
            # Busca dados cruzados no Redis por info_hash (fallback principal)
            cross_data = None
            try:
                cross_data = get_cross_data_from_redis(info_hash)
            except Exception:
                pass
            
            # Cria cópias locais para não modificar os originais
            local_original_title = original_title
            local_translated_title = translated_title
            local_imdb = imdb
            
            # Preenche campos faltantes com dados cruzados do Redis
            if cross_data:
                if not local_original_title and cross_data.get('original_title_html'):
                    local_original_title = cross_data['original_title_html']
                
                if not local_translated_title and cross_data.get('translated_title_html'):
                    local_translated_title = cross_data['translated_title_html']
                
                if not local_imdb and cross_data.get('imdb'):
                    local_imdb = cross_data['imdb']
            
            # Extrai raw_release_title diretamente do display_name do magnet resolvido
            raw_release_title = magnet_data.get('display_name', '')
            missing_dn = not raw_release_title or len(raw_release_title.strip()) < 3
            
            # Se ainda está missing_dn, tenta buscar do cross_data
            if missing_dn and cross_data and cross_data.get('release_title_magnet'):
                raw_release_title = cross_data['release_title_magnet']
                missing_dn = False
            
            # Salva release_title_magnet no Redis se encontrado
            if not missing_dn and raw_release_title:
                try:
                    save_release_title_to_redis(info_hash, raw_release_title)
                except Exception:
                    pass
            
            # Prepara fallback_title
            fallback_title = local_original_title or local_translated_title or page_title or ''
            
            # Prepara release_title
            original_release_title = prepare_release_title(
                raw_release_title,
                fallback_title,
                year,
                missing_dn=missing_dn,
                info_hash=info_hash if missing_dn else None,
                skip_metadata=skip_metadata
            )
            
            # Garante que translated_title seja string
            translated_title_str = str(local_translated_title) if local_translated_title else None
            if translated_title_str and not isinstance(translated_title_str, str):
                translated_title_str = None
            
            # Cria título padronizado
            standardized_title = create_standardized_title(
                str(local_original_title) if local_original_title else '',
                year,
                original_release_title,
                translated_title_html=translated_title_str,
                raw_release_title_magnet=raw_release_title
            )
            
            # Adiciona tags de áudio
            final_title = add_audio_tag_if_needed(
                standardized_title,
                original_release_title,
                info_hash=info_hash,
                skip_metadata=skip_metadata,
                audio_info_from_html=audio_info,
                audio_html_content=audio_html_content
            )
            
            # Determina origem_audio_tag
            origem_audio_tag = 'N/A'
            if raw_release_title and ('dual' in raw_release_title.lower() or 'dublado' in raw_release_title.lower() or 'legendado' in raw_release_title.lower()):
                origem_audio_tag = 'release_title_magnet'
            elif missing_dn and info_hash:
                origem_audio_tag = 'metadata (iTorrents.org) - usado durante processamento'
            
            # Extrai tamanho
            size = ''
            if sizes and idx < len(sizes):
                size = sizes[idx]
            
            # Processa trackers
            trackers = process_trackers(magnet_data)
            
            # Salva dados cruzados no Redis
            try:
                cross_data_to_save = {
                    'original_title_html': str(local_original_title) if local_original_title else None,
                    'release_title_magnet': raw_release_title if not missing_dn else None,
                    'translated_title_html': str(local_translated_title) if local_translated_title else None,
                    'imdb': local_imdb if local_imdb else None,
                    'missing_dn': missing_dn,
                    'origem_audio_tag': origem_audio_tag if origem_audio_tag != 'N/A' else None,
                    'size': size if size and size.strip() else None
                }
                save_cross_data_to_redis(info_hash, cross_data_to_save)
            except Exception:
                pass
            
            # Cria torrent dict
            torrent = {
                'title': final_title,
                'original_title': local_original_title if local_original_title else (local_translated_title if local_translated_title else page_title),
                'translated_title': local_translated_title if local_translated_title else None,
                'details': absolute_link,
                'year': year,
                'imdb': local_imdb if local_imdb else '',
                'audio': [],
                'magnet_link': magnet_link,
                'date': date.strftime('%Y-%m-%dT%H:%M:%SZ') if date else '',
                'info_hash': info_hash,
                'trackers': trackers,
                'size': size,
                'leech_count': 0,
                'seed_count': 0,
                'similarity': 1.0
            }
            torrents.append(torrent)
        
        except Exception as e:
            logger.error(f"Magnet error: {format_error(e)} (link: {format_link_preview(magnet_link)})")
            continue
    
    return torrents

