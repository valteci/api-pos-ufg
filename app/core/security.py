"""Dependências de autenticação e segurança da API."""

import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Configuracoes, obter_configuracoes

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class IdentidadeAutenticada:
    """Representa uma requisição autenticada por Bearer token."""

    metodo: str = "bearer"


def _autenticacao_obrigatoria(configuracoes: Configuracoes) -> bool:
    """Define quando a autenticação deve ser exigida.

    Em produção, `AUTH_ENABLED=false` é ignorado para evitar bypass de rotas de
    negócio por erro de configuração.
    """
    return configuracoes.app_env.lower() == "production" or configuracoes.auth_enabled


def _registrar_evento_autenticacao(
    nivel: int,
    evento: str,
    **metadados: Any,
) -> None:
    """Registra eventos de autenticação sem expor credenciais."""
    logger.log(
        nivel,
        json.dumps(
            {
                "event": evento,
                "metadata": metadados,
            },
            ensure_ascii=False,
            default=str,
        ),
    )


def _erro_nao_autorizado(mensagem: str) -> HTTPException:
    """Cria erro HTTP padronizado para falhas de autenticação."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensagem,
        headers={"WWW-Authenticate": "Bearer"},
    )


def exigir_autenticacao(
    credenciais: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> IdentidadeAutenticada:
    """Exige Bearer token válido para rotas de negócio.

    Args:
        credenciais: Credenciais extraídas do header `Authorization`.
        configuracoes: Configurações carregadas por ambiente.

    Returns:
        Identidade autenticada para uso futuro por rotas e serviços.

    Raises:
        HTTPException: Quando o token está ausente, inválido ou a autenticação
            obrigatória não foi configurada no servidor.
    """
    if not _autenticacao_obrigatoria(configuracoes):
        return IdentidadeAutenticada(metodo="desenvolvimento")

    if not configuracoes.auth_token:
        _registrar_evento_autenticacao(
            logging.ERROR,
            "auth_token_nao_configurado",
            app_env=configuracoes.app_env,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Autenticação da API não está configurada.",
        )

    if credenciais is None:
        _registrar_evento_autenticacao(
            logging.WARNING,
            "autenticacao_token_ausente",
            app_env=configuracoes.app_env,
        )
        raise _erro_nao_autorizado("Token de autenticação ausente.")

    if credenciais.scheme.lower() != "bearer":
        _registrar_evento_autenticacao(
            logging.WARNING,
            "autenticacao_esquema_invalido",
            app_env=configuracoes.app_env,
            esquema=credenciais.scheme,
        )
        raise _erro_nao_autorizado("Esquema de autenticação inválido.")

    if not secrets.compare_digest(credenciais.credentials, configuracoes.auth_token):
        _registrar_evento_autenticacao(
            logging.WARNING,
            "autenticacao_token_invalido",
            app_env=configuracoes.app_env,
        )
        raise _erro_nao_autorizado("Token de autenticação inválido.")

    return IdentidadeAutenticada()

