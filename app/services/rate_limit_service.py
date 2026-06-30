"""Rate limiting baseado em Redis."""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

from app.integrations.redis_client import ClienteRedis

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoRateLimit:
    """Resultado da verificação de rate limiting."""

    permitido: bool
    limite: int
    restante: int
    janela_segundos: int
    motivo: str | None = None


class LimitadorRequisicoes:
    """Aplica limite de requisições por identidade."""

    def __init__(
        self,
        *,
        cliente_redis: ClienteRedis,
        habilitado: bool,
        max_requisicoes: int,
        janela_segundos: int,
        falhar_aberto: bool,
        prefixo: str = "api-sprints-ia",
    ) -> None:
        """Inicializa limitador com Redis e política de falha."""
        self.cliente_redis = cliente_redis
        self.habilitado = habilitado
        self.max_requisicoes = max_requisicoes
        self.janela_segundos = janela_segundos
        self.falhar_aberto = falhar_aberto
        self.prefixo = prefixo

    def verificar(self, identidade: str) -> ResultadoRateLimit:
        """Verifica se uma identidade pode executar nova requisição."""
        if not self.habilitado:
            return ResultadoRateLimit(
                permitido=True,
                limite=self.max_requisicoes,
                restante=self.max_requisicoes,
                janela_segundos=self.janela_segundos,
            )

        chave = self._criar_chave(identidade)
        try:
            quantidade = self.cliente_redis.incr(chave)
            if quantidade == 1:
                self.cliente_redis.expire(chave, self.janela_segundos)
        except Exception as erro:
            self._registrar_evento(
                logging.WARNING,
                "falha_redis_rate_limit",
                erro=erro.__class__.__name__,
                falhar_aberto=self.falhar_aberto,
            )
            return ResultadoRateLimit(
                permitido=self.falhar_aberto,
                limite=self.max_requisicoes,
                restante=0 if not self.falhar_aberto else self.max_requisicoes,
                janela_segundos=self.janela_segundos,
                motivo="redis_indisponivel",
            )

        restante = max(self.max_requisicoes - quantidade, 0)
        permitido = quantidade <= self.max_requisicoes
        if not permitido:
            self._registrar_evento(
                logging.WARNING,
                "rate_limit_bloqueado",
                chave_hash=self._hash_chave(chave),
                limite=self.max_requisicoes,
                janela_segundos=self.janela_segundos,
            )

        return ResultadoRateLimit(
            permitido=permitido,
            limite=self.max_requisicoes,
            restante=restante,
            janela_segundos=self.janela_segundos,
            motivo=None if permitido else "limite_excedido",
        )

    def _criar_chave(self, identidade: str) -> str:
        """Cria chave hasheada sem token/IP em texto puro."""
        digest = hashlib.sha256(identidade.encode("utf-8")).hexdigest()
        return f"{self.prefixo}:rate_limit:{digest}"

    @staticmethod
    def _hash_chave(chave: str) -> str:
        """Hash curto para logs."""
        return hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra evento estruturado de rate limiting."""
        logger.log(
            nivel,
            json.dumps(
                {"event": evento, "metadata": metadados},
                ensure_ascii=False,
                default=str,
            ),
        )
