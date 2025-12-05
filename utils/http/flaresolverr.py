"""Copyright (c) 2025 DFlexy"""
"""https://github.com/DFlexy"""

import logging
import time
import uuid
import threading
from typing import Optional
import requests
from cache.redis_client import get_redis_client
from cache.redis_keys import flaresolverr_session_key, flaresolverr_created_key
from app.config import Config

logger = logging.getLogger(__name__)

# Cache em memória por requisição (apenas quando Redis não está disponível)
_request_cache = threading.local()


class FlareSolverrClient:
    def __init__(self, address: str):
        self.address = address.rstrip('/')
        self.api_url = f"{self.address}/v1"
        self.redis = get_redis_client()
    
    def _get_session_key(self, base_url: str) -> str:
        return flaresolverr_session_key(base_url)
    
    def _get_session_created_key(self, base_url: str) -> str:
        return flaresolverr_created_key(base_url)
    
    def _create_session(self, base_url: str, skip_redis: bool = False) -> Optional[str]:
        # Cria nova sessão FlareSolverr (Redis primeiro, memória se Redis não disponível)
        try:
            session_id = f"dfindexer_{uuid.uuid4().hex[:12]}"
            
            payload = {
                "cmd": "sessions.create",
                "session": session_id
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=150,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "ok":
                created_session_id = result.get("session")
                if created_session_id:
                    # Tenta Redis primeiro
                    if self.redis and not skip_redis:
                        try:
                            session_key = self._get_session_key(base_url)
                            created_key = self._get_session_created_key(base_url)
                            self.redis.setex(session_key, Config.FLARESOLVERR_SESSION_TTL, created_session_id)
                            self.redis.setex(created_key, Config.FLARESOLVERR_SESSION_TTL, str(int(time.time())))
                        except Exception:
                            pass
                    
                    logger.debug(f"Sessão FlareSolverr criada: {created_session_id} para {base_url}")
                    return created_session_id
            
            logger.warning(f"Falha ao criar sessão FlareSolverr: {result}")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(
                f"Timeout ao criar sessão FlareSolverr (FlareSolverr pode estar demorando para iniciar Chrome). "
                f"Tente novamente em alguns segundos."
            )
            return None
        except Exception as e:
            error_msg = str(e)
            is_connection_error = (
                "No route to host" in error_msg or
                "Connection refused" in error_msg or
                "Failed to establish" in error_msg or
                "Max retries exceeded" in error_msg
            )
            if is_connection_error:
                logger.warning(
                    f"FlareSolverr não está acessível em {self.api_url}. "
                    f"Verifique se o serviço está rodando e acessível."
                )
            else:
                logger.error(f"Erro ao criar sessão FlareSolverr: {e}")
            return None
    
    def _validate_session(self, session_id: str) -> bool:
        try:
            payload = {
                "cmd": "sessions.list"
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            sessions = result.get("sessions", [])
            return session_id in sessions
            
        except Exception:
            return True
    
    def get_or_create_session(self, base_url: str, skip_redis: bool = False) -> Optional[str]:
        # Obtém ou cria sessão FlareSolverr (Redis primeiro, memória se Redis não disponível)
        # Tenta Redis primeiro
        if self.redis and not skip_redis:
            try:
                session_key = self._get_session_key(base_url)
                cached = self.redis.get(session_key)
                if cached:
                    session_id = cached.decode('utf-8')
                    if self._validate_session(session_id):
                        logger.debug(f"Sessão FlareSolverr reutilizada: {session_id} para {base_url}")
                        return session_id
                    else:
                        self.redis.delete(session_key)
                        self.redis.delete(self._get_session_created_key(base_url))
            except Exception:
                pass
        
        # Usa memória apenas se Redis não está disponível desde o início
        if not self.redis or skip_redis:
            if not hasattr(_request_cache, 'flaresolverr_sessions'):
                _request_cache.flaresolverr_sessions = {}
            
            # Verifica cache em memória
            if base_url in _request_cache.flaresolverr_sessions:
                session_id, expire_at = _request_cache.flaresolverr_sessions[base_url]
                if time.time() < expire_at and self._validate_session(session_id):
                    return session_id
                else:
                    # Expirou ou inválida, remove
                    del _request_cache.flaresolverr_sessions[base_url]
        
        # Cria nova sessão
        session_id = self._create_session(base_url, skip_redis)
        
        # Salva em memória se Redis não disponível
        if (not self.redis or skip_redis) and session_id:
            if not hasattr(_request_cache, 'flaresolverr_sessions'):
                _request_cache.flaresolverr_sessions = {}
            expire_at = time.time() + Config.FLARESOLVERR_SESSION_TTL
            _request_cache.flaresolverr_sessions[base_url] = (session_id, expire_at)
        
        return session_id
    
    def solve(self, url: str, session_id: str, referer: str = '', base_url: str = '', skip_redis: bool = False) -> Optional[bytes]:
        try:
            payload = {
                "cmd": "request.get",
                "url": url,
                "session": session_id,
                "maxTimeout": 60000
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=90,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 500:
                error_detail = ""
                try:
                    error_json = response.json()
                    error_detail = error_json.get("message", "")
                except:
                    error_detail = response.text[:200] if response.text else ""
                
                logger.warning(
                    f"FlareSolverr retornou erro 500 para {url}. "
                    f"Sessão: {session_id}. Detalhes: {error_detail}"
                )
                if base_url:
                    self._invalidate_session(session_id, base_url, skip_redis)
                return None
            
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") == "ok":
                solution = result.get("solution", {})
                html_content = solution.get("response", "")
                
                if html_content:
                    return html_content.encode('utf-8')
                else:
                    logger.warning(f"FlareSolverr retornou resposta vazia para {url}")
                    return None
            else:
                error_msg = result.get("message", "Erro desconhecido")
                logger.warning(f"FlareSolverr retornou erro para {url}: {error_msg}")
                
                if "session" in error_msg.lower() or "not found" in error_msg.lower() or "500" in error_msg:
                    self._invalidate_session(session_id, base_url, skip_redis)
                
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout ao resolver {url} via FlareSolverr")
            return None
        except Exception as e:
            logger.error(f"Erro ao resolver {url} via FlareSolverr: {e}")
            return None
    
    def _invalidate_session(self, session_id: str, base_url: str, skip_redis: bool = False):
        # Invalida sessão (Redis primeiro, memória se Redis não disponível)
        # Remove do Redis
        if self.redis and not skip_redis:
            try:
                session_key = self._get_session_key(base_url)
                created_key = self._get_session_created_key(base_url)
                self.redis.delete(session_key)
                self.redis.delete(created_key)
            except Exception:
                pass
        
        # Remove da memória
        if hasattr(_request_cache, 'flaresolverr_sessions'):
            _request_cache.flaresolverr_sessions.pop(base_url, None)
    
    def destroy_session(self, session_id: str, base_url: str):
        # Destrói sessão FlareSolverr
        try:
            payload = {
                "cmd": "sessions.destroy",
                "session": session_id
            }
            
            requests.post(
                self.api_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
        except Exception:
            pass  # Ignora erros ao destruir
        
        # Remove do cache (Redis e memória)
        self._invalidate_session(session_id, base_url, skip_redis=False)

