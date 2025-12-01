"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
import json
import time
from typing import Optional, Dict, Any
from cache.redis_client import get_redis_client
from cache.redis_keys import metadata_key

logger = logging.getLogger(__name__)


# Cache para metadata de torrents
class MetadataCache:
    def __init__(self):
        self.redis = get_redis_client()
    
    def get(self, info_hash: str) -> Optional[Dict[str, Any]]:
        """Obtém metadata do cache"""
        if not self.redis:
            return None
        
        try:
            key = metadata_key(info_hash)
            # Chave separada para metadata principal
            data_str = self.redis.get(key)
            if data_str:
                data = json.loads(data_str.decode('utf-8'))
                return data
        except Exception:
            pass
        
        return None
    
    def set(self, info_hash: str, metadata: Dict[str, Any]) -> None:
        """Salva metadata no cache"""
        if not self.redis:
            return
        
        try:
            key = metadata_key(info_hash)
            # Verifica se já existe no cache antes de salvar
            exists = self.redis.exists(key)
            # Chave separada para metadata principal - armazena JSON diretamente
            metadata_json = json.dumps(metadata, separators=(',', ':'))
            self.redis.setex(key, 7 * 24 * 3600, metadata_json)  # 7 dias
            if not exists:
                size_info = f"size={metadata.get('size', 'N/A')}"
                name_info = f"name={metadata.get('name', 'N/A')[:50]}" if metadata.get('name') else ""
                info_parts = [size_info]
                if name_info:
                    info_parts.append(name_info)
                info_str = " | ".join(info_parts)
                logger.debug(f"[CACHE REDIS SAVE] Metadata salvo: {info_hash[:16]}... (TTL: 604800s | {info_str})")
            else:
                logger.debug(f"[CACHE REDIS UPDATE] Metadata atualizado: {info_hash[:16]}...")
        except Exception:
            pass  # Ignora erros de cache
    
    def set_failure(self, info_hash: str, ttl: int = 60) -> None:
        """Marca metadata como falha no cache"""
        if not self.redis:
            return
        
        try:
            from cache.redis_keys import metadata_failure_key, metadata_failure503_key
            # Usa chave específica conforme o tipo de falha
            if ttl == 300:  # Falha 503
                key = metadata_failure503_key(info_hash)
            else:  # Falha normal
                key = metadata_failure_key(info_hash)
            self.redis.setex(key, ttl, str(int(time.time())))
        except Exception:
            pass  # Ignora erros de cache

