"""Composição principal da aplicação FastAPI."""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import Configuracoes, obter_configuracoes
from app.core.middleware import LimitePayloadMiddleware
from app.integrations.vector_store import BancoVetorialChromaDB
from app.services.persistencia_embeddings import ServicoPersistenciaEmbeddings

logger = logging.getLogger(__name__)


def _registrar_evento_inicializacao(nivel: int, evento: str, **metadados: object) -> None:
    """Registra evento estruturado de inicialização da aplicação."""
    logger.log(
        nivel,
        json.dumps(
            {"event": evento, "metadata": metadados},
            ensure_ascii=False,
            default=str,
        ),
    )


def carregar_embeddings_na_inicializacao(config: Configuracoes) -> None:
    """Carrega embeddings do disco para o ChromaDB ao iniciar a aplicação.

    A carga só ocorre quando habilitada e quando a coleção está vazia, tornando
    a operação idempotente. Falhas de conexão ou arquivos ausentes não impedem a
    subida da API: o RAG apenas ficará sem resultados até a indexação ou carga.
    """
    if not config.embeddings_autoload_enabled:
        return
    if config.app_env.lower() == "test":
        return

    try:
        banco_vetorial = BancoVetorialChromaDB(
            url=config.vector_db_url,
            colecao=config.vector_db_collection,
        )
        servico = ServicoPersistenciaEmbeddings(
            banco_vetorial=banco_vetorial,
            diretorio_embeddings=config.embeddings_export_dir,
            colecao=config.vector_db_collection,
        )
        servico.importar(somente_se_vazio=True)
    except Exception as erro:  # noqa: BLE001 - inicialização não pode derrubar a API
        _registrar_evento_inicializacao(
            logging.WARNING,
            "embeddings_autoload_falhou",
            erro=erro.__class__.__name__,
        )


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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Executa carga automática de embeddings ao iniciar a aplicação."""
        carregar_embeddings_na_inicializacao(config)
        yield

    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        lifespan=lifespan,
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
