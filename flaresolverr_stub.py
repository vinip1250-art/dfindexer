"""
flaresolverr_stub.py
====================
Substituto no-op do FlareSolverr para deploy no Vercel.

Se o projeto importa algo como `from core.flaresolverr import FlareSolverrClient`,
aponte esse import para este módulo ou copie este conteúdo para o arquivo original.

Qualquer chamada ao FlareSolverr retornará None silenciosamente, e o código
de fallback existente (scraping normal) assumirá o controle.
"""
import logging

logger = logging.getLogger(__name__)


class FlareSolverrClient:
    """Drop-in stub que não faz nada."""

    def __init__(self, *args, **kwargs):
        logger.debug("FlareSolverr stub ativo — nenhuma requisição será enviada.")

    def get(self, url: str, session_id: str | None = None, **kwargs) -> str | None:
        logger.debug(f"FlareSolverr stub: get({url}) → None")
        return None

    def create_session(self, session_id: str | None = None) -> str | None:
        return None

    def destroy_session(self, session_id: str) -> None:
        pass

    def is_available(self) -> bool:
        return False


def get_flaresolverr_client() -> FlareSolverrClient:
    return _stub


_stub = FlareSolverrClient()
