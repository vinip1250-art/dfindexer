"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import threading
import logging
import time
from contextlib import contextmanager
from app.config import Config

logger = logging.getLogger(__name__)

# Semáforo global para limitar requisições de metadata simultâneas
# Evita rate limiting da API quando múltiplos scrapers processam simultaneamente
_metadata_semaphore = None
_semaphore_lock = threading.Lock()
_current_limit = None
_debug_enabled = True  # Habilita logs de debug para diagnóstico

# Coleta de tempos para cálculo da média
_times_list = []
_times_lock = threading.Lock()


# Retorna o semáforo global para requisições de metadata
# Recria o semáforo se o limite mudou
def get_metadata_semaphore():
    global _metadata_semaphore, _current_limit
    
    max_concurrent = Config.METADATA_MAX_CONCURRENT if hasattr(Config, 'METADATA_MAX_CONCURRENT') else 128
    
    # Se o semáforo não existe ou o limite mudou, recria
    if _metadata_semaphore is None or _current_limit != max_concurrent:
        with _semaphore_lock:
            # Double-check locking pattern
            if _metadata_semaphore is None or _current_limit != max_concurrent:
                if _metadata_semaphore is not None:
                    logger.info(f"Semáforo de metadata recriado: {_current_limit} → {max_concurrent} requisições simultâneas")
                else:
                    logger.info(f"Semáforo de metadata criado com limite de {max_concurrent} requisições simultâneas")
                _metadata_semaphore = threading.Semaphore(max_concurrent)
                _current_limit = max_concurrent
    
    return _metadata_semaphore


# Context manager para garantir que o slot sempre seja liberado
@contextmanager
def metadata_slot(timeout=None):
    """
    Context manager para adquirir e liberar slot de metadata automaticamente.
    
    Args:
        timeout: Timeout em segundos para adquirir o slot (None = sem timeout)
    
    Usage:
        with metadata_slot():
            # código que usa metadata
            pass
    """
    semaphore = get_metadata_semaphore()
    acquired = False
    start_time = time.time()  # Sempre mede o tempo para o log final
    
    try:
        if timeout is not None:
            acquired = semaphore.acquire(timeout=timeout)
            if not acquired:
                raise TimeoutError(f"Timeout ao adquirir slot de metadata após {timeout}s")
        else:
            semaphore.acquire()
            acquired = True
        yield
    finally:
        if acquired:
            semaphore.release()
            elapsed = time.time() - start_time
            available_after = semaphore._value
            in_use_after = _current_limit - available_after
            
            # Coleta o tempo para cálculo da média
            with _times_lock:
                _times_list.append(elapsed)
                
                # Quando todos os slots estiverem livres, calcula e mostra a média
                if in_use_after == 0 and len(_times_list) > 0:
                    avg_time = sum(_times_list) / len(_times_list)
                    min_time = min(_times_list)
                    max_time = max(_times_list)
                    total_requests = len(_times_list)
                    logger.debug(f"[SEMÁFORO] Batch concluído: {total_requests} requisições | Tempo médio: {avg_time:.2f}s | Mín: {min_time:.2f}s | Máx: {max_time:.2f}s")
                    _times_list.clear()  # Limpa para o próximo batch


# Adquire um slot para fazer requisição de metadata
# Bloqueia se o limite de requisições simultâneas foi atingido
def acquire_metadata_slot(timeout=None):
    """
    Adquire um slot no semáforo.
    
    Args:
        timeout: Timeout em segundos (None = bloqueia indefinidamente)
    
    Returns:
        True se adquiriu, False se timeout
    """
    semaphore = get_metadata_semaphore()
    if timeout is not None:
        return semaphore.acquire(timeout=timeout)
    else:
        semaphore.acquire()
        return True


# Libera um slot após completar requisição de metadata
def release_metadata_slot():
    semaphore = get_metadata_semaphore()
    semaphore.release()

