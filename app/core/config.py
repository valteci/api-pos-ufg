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

    data_dir: Path = Field(default=Path("data"))
    max_rag_rank: int = Field(default=10, ge=1, le=100)
    max_fragment_size: int = Field(default=3000, ge=1, le=100_000)
    max_message_length: int = Field(default=4000, ge=1, le=100_000)
    max_sprints_per_request: int = Field(default=20, ge=1, le=1000)

    openai_api_key: str | None = None
    openai_llm_model: str | None = None
    openai_embedding_model: str | None = None
    openai_timeout_seconds: float = Field(default=30.0, gt=0)

    @field_validator("auth_token", "openai_api_key", mode="before")
    @classmethod
    def normalizar_segredo_vazio(cls, valor: Any) -> Any:
        """Converte segredos vazios em ausentes para evitar falsos positivos."""
        if isinstance(valor, str) and not valor.strip():
            return None
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
        data_dir=_valor_ambiente("DATA_DIR", "data"),
        max_rag_rank=_valor_ambiente("MAX_RAG_RANK", 10),
        max_fragment_size=_valor_ambiente("MAX_FRAGMENT_SIZE", 3000),
        max_message_length=_valor_ambiente("MAX_MESSAGE_LENGTH", 4000),
        max_sprints_per_request=_valor_ambiente("MAX_SPRINTS_PER_REQUEST", 20),
        openai_api_key=_valor_ambiente("OPENAI_API_KEY"),
        openai_llm_model=_valor_ambiente("OPENAI_LLM_MODEL"),
        openai_embedding_model=_valor_ambiente("OPENAI_EMBEDDING_MODEL"),
        openai_timeout_seconds=_valor_ambiente("OPENAI_TIMEOUT_SECONDS", 30.0),
    )


@lru_cache
def obter_configuracoes() -> Configuracoes:
    """Retorna configurações cacheadas para uso por injeção de dependência."""
    return carregar_configuracoes_do_ambiente()
