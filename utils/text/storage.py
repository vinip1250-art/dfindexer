"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

from typing import Optional


# Busca o nome do torrent via metadata API quando falta display_name no magnet
def get_release_title_from_redis(info_hash: str) -> Optional[str]:
    """
    Busca release_title_magnet no Redis por info_hash.
    Retorna o release_title_magnet se encontrado, None caso contrário.
    """
    from app.config import Config
    if not info_hash or len(info_hash) != Config.INFO_HASH_LENGTH:
        return None
    
    try:
        from cache.redis_client import get_redis_client
        from cache.redis_keys import release_title_key
        
        redis = get_redis_client()
        if not redis:
            return None
        
        key = release_title_key(info_hash)
        cached = redis.get(key)
        if cached:
            release_title = cached.decode('utf-8').strip()
            if release_title and len(release_title) >= 3:
                return release_title
    except Exception:
        pass
    
    return None


def save_release_title_to_redis(info_hash: str, release_title: str) -> None:
    """
    Salva release_title_magnet no Redis por info_hash.
    """
    if not info_hash or len(info_hash) != 40:
        return
    
    if not release_title or len(release_title.strip()) < 3:
        return
    
    try:
        from cache.redis_client import get_redis_client
        from cache.redis_keys import release_title_key
        
        redis = get_redis_client()
        if not redis:
            return
        
        key = release_title_key(info_hash)
        # Salva por 7 dias (mesmo TTL do metadata)
        from app.config import Config
        redis.setex(key, Config.RELEASE_TITLE_CACHE_TTL, release_title.strip())
    except Exception:
        pass


def get_metadata_name(info_hash: str, skip_metadata: bool = False) -> Optional[str]:
    if skip_metadata:
        return None
    
    # Primeiro tenta buscar do cross_data (evita consulta desnecessária ao metadata)
    try:
        from utils.text.cross_data import get_cross_data_from_redis
        cross_data = get_cross_data_from_redis(info_hash)
        if cross_data and cross_data.get('release_title_magnet'):
            release_title = cross_data.get('release_title_magnet')
            if release_title and release_title != 'N/A' and len(str(release_title).strip()) >= 3:
                return str(release_title).strip()
    except Exception:
        pass
    
    # Se não encontrou no cross_data, busca do metadata
    try:
        from magnet.metadata import fetch_metadata_from_itorrents
        metadata = fetch_metadata_from_itorrents(info_hash)
        if metadata and metadata.get('name'):
            name = metadata.get('name', '').strip()
            if name and len(name) >= 3:
                return name
    except Exception:
        pass
    
    return None

