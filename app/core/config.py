"""Configuração central da aplicação carregada por variáveis de ambiente."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Configuracoes(BaseModel):
    """Configurações da API validadas por Pydantic.

    Segredos não recebem valores padrão reais. Quando ausentes, permanecem como
    `None` para que as camadas funcionais decidam se a configuração é exigida.
    """

    model_config = ConfigDict(extra="forbid")

    app_env: str = Field(default="development", min_length=1)
    app_name: str = Field(default="api-sprints-ia", min_length=1)
    app_version: str = Field(default="0.1.0", min_length=1)
    log_level: str = Field(default="INFO", min_length=1)
    log_file_path: Path = Field(default=Path("logs/api.json"))

    auth_enabled: bool = True
    auth_token: str | None = None

    cors_allowed_origins: tuple[str, ...] = Field(default_factory=tuple)
    max_payload_bytes: int = Field(default=1_048_576, ge=1, le=10_485_760)

    data_dir: Path = Field(default=Path("data"))
    max_rag_rank: int = Field(default=10, ge=1, le=100)
    max_fragment_size: int = Field(default=3000, ge=1, le=100_000)
    max_message_length: int = Field(default=4000, ge=1, le=100_000)
    max_sprints_per_request: int = Field(default=20, ge=1, le=1000)

    openai_api_key: str | None = None
    openai_llm_model: str | None = None
    openai_embedding_model: str | None = None
    openai_timeout_seconds: float = Field(default=30.0, gt=0)

    vector_db_url: str = Field(default="http://localhost:8001", min_length=1)
    vector_db_collection: str = Field(default="sprints", min_length=1)
    embeddings_enabled: bool = True

    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    cache_enabled: bool = True
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86_400)
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = Field(default=60, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86_400)
    rate_limit_fail_open: bool = True

    @field_validator("auth_token", "openai_api_key", mode="before")
    @classmethod
    def normalizar_segredo_vazio(cls, valor: Any) -> Any:
        """Converte segredos vazios em ausentes para evitar falsos positivos."""
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalizar_origens_cors(cls, valor: Any) -> tuple[str, ...]:
        """Normaliza a lista de origens CORS a partir de string ou coleção."""
        if valor is None:
            return ()

        if isinstance(valor, str):
            return tuple(origem.strip() for origem in valor.split(",") if origem.strip())

        if isinstance(valor, (list, tuple, set)):
            return tuple(str(origem).strip() for origem in valor if str(origem).strip())

        return valor


def _valor_ambiente(nome: str, padrao: Any | None = None) -> Any | None:
    """Lê uma variável de ambiente preservando o padrão quando ela não existe."""
    return os.getenv(nome, padrao)


def carregar_configuracoes_do_ambiente() -> Configuracoes:
    """Carrega e valida as configurações da aplicação.

    Returns:
        Configurações validadas por Pydantic.
    """
    return Configuracoes(
        app_env=_valor_ambiente("APP_ENV", "development"),
        app_name=_valor_ambiente("APP_NAME", "api-sprints-ia"),
        app_version=_valor_ambiente("APP_VERSION", "0.1.0"),
        log_level=_valor_ambiente("LOG_LEVEL", "INFO"),
        log_file_path=_valor_ambiente("LOG_FILE_PATH", "logs/api.json"),
        auth_enabled=_valor_ambiente("AUTH_ENABLED", True),
        auth_token=_valor_ambiente("AUTH_TOKEN"),
        cors_allowed_origins=_valor_ambiente("CORS_ALLOWED_ORIGINS", ""),
        max_payload_bytes=_valor_ambiente("MAX_PAYLOAD_BYTES", 1_048_576),
        data_dir=_valor_ambiente("DATA_DIR", "data"),
        max_rag_rank=_valor_ambiente("MAX_RAG_RANK", 10),
        max_fragment_size=_valor_ambiente("MAX_FRAGMENT_SIZE", 3000),
        max_message_length=_valor_ambiente("MAX_MESSAGE_LENGTH", 4000),
        max_sprints_per_request=_valor_ambiente("MAX_SPRINTS_PER_REQUEST", 20),
        openai_api_key=_valor_ambiente("OPENAI_API_KEY"),
        openai_llm_model=_valor_ambiente("OPENAI_LLM_MODEL"),
        openai_embedding_model=_valor_ambiente("OPENAI_EMBEDDING_MODEL"),
        openai_timeout_seconds=_valor_ambiente("OPENAI_TIMEOUT_SECONDS", 30.0),
        vector_db_url=_valor_ambiente("VECTOR_DB_URL", "http://localhost:8001"),
        vector_db_collection=_valor_ambiente("VECTOR_DB_COLLECTION", "sprints"),
        embeddings_enabled=_valor_ambiente("EMBEDDINGS_ENABLED", True),
        redis_url=_valor_ambiente("REDIS_URL", "redis://localhost:6379/0"),
        cache_enabled=_valor_ambiente("CACHE_ENABLED", True),
        cache_ttl_seconds=_valor_ambiente("CACHE_TTL_SECONDS", 300),
        rate_limit_enabled=_valor_ambiente("RATE_LIMIT_ENABLED", True),
        rate_limit_max_requests=_valor_ambiente("RATE_LIMIT_MAX_REQUESTS", 60),
        rate_limit_window_seconds=_valor_ambiente("RATE_LIMIT_WINDOW_SECONDS", 60),
        rate_limit_fail_open=_valor_ambiente("RATE_LIMIT_FAIL_OPEN", True),
    )


@lru_cache
def obter_configuracoes() -> Configuracoes:
    """Retorna configurações cacheadas para uso por injeção de dependência."""
    return carregar_configuracoes_do_ambiente()
