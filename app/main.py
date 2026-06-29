"""Composição principal da aplicação FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import Configuracoes, obter_configuracoes
from app.core.middleware import LimitePayloadMiddleware


def _validar_configuracao_seguranca(configuracoes: Configuracoes) -> None:
    """Valida configurações de segurança que dependem do ambiente."""
    if configuracoes.app_env.lower() == "production" and "*" in configuracoes.cors_allowed_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS não pode usar '*' em produção.")


def criar_app(configuracoes: Configuracoes | None = None) -> FastAPI:
    """Cria a aplicação FastAPI com routers e configurações centrais.

    Args:
        configuracoes: Configurações opcionais para facilitar testes sem
            depender diretamente das variáveis de ambiente.

    Returns:
        Instância configurada da aplicação FastAPI.
    """
    config = configuracoes or obter_configuracoes()
    _validar_configuracao_seguranca(config)

    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
    )
    app.add_middleware(LimitePayloadMiddleware, max_payload_bytes=config.max_payload_bytes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    if configuracoes is not None:
        app.dependency_overrides[obter_configuracoes] = lambda: config

    app.include_router(health_router)
    app.include_router(v1_router)

    return app


app = criar_app()
