"""Rotas públicas de saúde da API."""

from fastapi import APIRouter, Depends

from app.core.config import Configuracoes, obter_configuracoes
from app.schemas.health import HealthResponse

router = APIRouter(tags=["saúde"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica a saúde da API",
)
def health_check(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> HealthResponse:
    """Retorna o status básico da aplicação.

    A dependência de configuração é carregada aqui para validar que o bootstrap
    da aplicação consegue resolver variáveis de ambiente mesmo em rota pública.
    """
    _ = configuracoes
    return HealthResponse(status="ok")
