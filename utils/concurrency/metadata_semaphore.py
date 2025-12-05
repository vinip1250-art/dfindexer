"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import threading
import logging
from app.config import Config

logger = logging.getLogger(__name__)

# Semáforo global para limitar requisições de metadata simultâneas
# Evita rate limiting da API quando múltiplos scrapers processam simultaneamente
_metadata_semaphore = None
_semaphore_lock = threading.Lock()


# Retorna o semáforo global para requisições de metadata
# Cria o semáforo na primeira chamada com limite configurável
def get_metadata_semaphore():
    global _metadata_semaphore
    
    if _metadata_semaphore is None:
        with _semaphore_lock:
            # Double-check locking pattern
            if _metadata_semaphore is None:
                max_concurrent = Config.METADATA_MAX_CONCURRENT if hasattr(Config, 'METADATA_MAX_CONCURRENT') else 32
                _metadata_semaphore = threading.Semaphore(max_concurrent)
                logger.info(f"Semáforo de metadata criado com limite de {max_concurrent} requisições simultâneas")
    
    return _metadata_semaphore


# Adquire um slot para fazer requisição de metadata
# Bloqueia se o limite de requisições simultâneas foi atingido
def acquire_metadata_slot():
    semaphore = get_metadata_semaphore()
    semaphore.acquire()


# Libera um slot após completar requisição de metadata
def release_metadata_slot():
    semaphore = get_metadata_semaphore()
    semaphore.release()

