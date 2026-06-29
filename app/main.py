"""Composição principal da aplicação FastAPI."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import Configuracoes, obter_configuracoes


def criar_app(configuracoes: Configuracoes | None = None) -> FastAPI:
    """Cria a aplicação FastAPI com routers e configurações centrais.

    Args:
        configuracoes: Configurações opcionais para facilitar testes sem
            depender diretamente das variáveis de ambiente.

    Returns:
        Instância configurada da aplicação FastAPI.
    """
    config = configuracoes or obter_configuracoes()

    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
    )
    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = criar_app()
