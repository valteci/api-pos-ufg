"""Dependências de autenticação e segurança da API."""

import json
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Configuracoes, obter_configuracoes
from app.infrastructure.dependencies import obter_limitador_requisicoes
from app.services.rate_limit_service import LimitadorRequisicoes

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
    request: Request,
    credenciais: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    limitador: LimitadorRequisicoes = Depends(obter_limitador_requisicoes),
) -> IdentidadeAutenticada:
    """Exige Bearer token válido para rotas de negócio.

    Args:
        request: Requisição atual, usada para fallback de identidade por IP.
        credenciais: Credenciais extraídas do header `Authorization`.
        configuracoes: Configurações carregadas por ambiente.
        limitador: Serviço de rate limiting configurado por ambiente.

    Returns:
        Identidade autenticada para uso futuro por rotas e serviços.

    Raises:
        HTTPException: Quando o token está ausente, inválido ou a autenticação
            obrigatória não foi configurada no servidor.
    """
    if not _autenticacao_obrigatoria(configuracoes):
        _aplicar_rate_limit(
            limitador,
            identidade=f"desenvolvimento:{request.client.host if request.client else 'desconhecido'}",
        )
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

    _aplicar_rate_limit(limitador, identidade=f"token:{credenciais.credentials}")
    return IdentidadeAutenticada()


def _aplicar_rate_limit(limitador: LimitadorRequisicoes, *, identidade: str) -> None:
    """Aplica rate limiting para identidade autenticada."""
    resultado = limitador.verificar(identidade)
    if resultado.permitido:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Limite de requisições excedido. Tente novamente mais tarde.",
        headers={
            "Retry-After": str(resultado.janela_segundos),
            "X-RateLimit-Limit": str(resultado.limite),
            "X-RateLimit-Remaining": str(resultado.restante),
        },
    )
