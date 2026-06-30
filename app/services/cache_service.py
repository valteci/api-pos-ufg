"""Serviços de cache de respostas usando Redis."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from app.integrations.redis_client import ClienteRedis

logger = logging.getLogger(__name__)


class CalculadorAssinaturaDados:
    """Calcula assinatura dos arquivos de sprint usados por uma consulta."""

    def __init__(self, diretorio_dados: str | Path) -> None:
        """Inicializa calculador com diretório de dados."""
        self.diretorio_dados = Path(diretorio_dados)

    def assinar_sprints(self, sprints: list[str]) -> str:
        """Gera assinatura estável baseada nos arquivos consultados."""
        hash_dados = hashlib.sha256()
        for sprint in sorted(sprints):
            caminho = self.diretorio_dados / f"{sprint}.json"
            hash_dados.update(sprint.encode("utf-8"))
            hash_dados.update(b"\0")
            if caminho.is_file():
                estatistica = caminho.stat()
                hash_dados.update(str(estatistica.st_size).encode("utf-8"))
                hash_dados.update(b"\0")
                hash_dados.update(str(estatistica.st_mtime_ns).encode("utf-8"))
            else:
                hash_dados.update(b"ausente")
            hash_dados.update(b"\0")
        return hash_dados.hexdigest()


class CacheRespostas:
    """Cache opcional de respostas RAG e resumos."""

    def __init__(
        self,
        *,
        cliente_redis: ClienteRedis,
        habilitado: bool,
        ttl_seconds: int,
        prefixo: str = "api-sprints-ia",
    ) -> None:
        """Inicializa cache com cliente Redis e TTL."""
        self.cliente_redis = cliente_redis
        self.habilitado = habilitado
        self.ttl_seconds = ttl_seconds
        self.prefixo = prefixo

    def criar_chave(
        self,
        *,
        tipo: str,
        parametros: dict[str, Any],
        assinatura_dados: str,
    ) -> str:
        """Cria chave sem dados sensíveis em texto puro."""
        versao_indice = self.obter_versao_indice()
        payload = json.dumps(
            {
                "assinatura_dados": assinatura_dados,
                "parametros": parametros,
                "tipo": tipo,
                "versao_indice": versao_indice,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{self.prefixo}:cache:{tipo}:{digest}"

    def obter_json(self, chave: str) -> dict[str, Any] | None:
        """Obtém valor JSON do cache degradando em caso de falha."""
        if not self.habilitado:
            return None
        try:
            valor = self.cliente_redis.get(chave)
        except Exception as erro:
            self._registrar_falha("cache_obter", erro)
            return None

        if not valor:
            return None

        try:
            dado = json.loads(valor)
        except json.JSONDecodeError as erro:
            self._registrar_falha("cache_decodificar", erro)
            return None

        if isinstance(dado, dict):
            self._registrar_evento(logging.INFO, "cache_hit", chave_hash=self._hash_chave(chave))
            return dado
        return None

    def salvar_json(self, chave: str, valor: dict[str, Any]) -> None:
        """Salva valor JSON com TTL configurado."""
        if not self.habilitado:
            return
        try:
            self.cliente_redis.setex(
                chave,
                self.ttl_seconds,
                json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str),
            )
            self._registrar_evento(
                logging.INFO,
                "cache_miss_gravado",
                chave_hash=self._hash_chave(chave),
                ttl_seconds=self.ttl_seconds,
            )
        except Exception as erro:
            self._registrar_falha("cache_salvar", erro)

    def obter_versao_indice(self) -> str:
        """Obtém versão de invalidação global do índice."""
        chave = self._chave_versao_indice()
        if not self.habilitado:
            return "0"
        try:
            valor = self.cliente_redis.get(chave)
        except Exception as erro:
            self._registrar_falha("cache_obter_versao_indice", erro)
            return "0"
        return valor or "0"

    def invalidar_por_reindexacao(self) -> None:
        """Incrementa versão global usada nas chaves de cache."""
        if not self.habilitado:
            return
        try:
            versao = self.cliente_redis.incr(self._chave_versao_indice())
            self._registrar_evento(logging.INFO, "cache_invalidado_reindexacao", versao=versao)
        except Exception as erro:
            self._registrar_falha("cache_invalidar_reindexacao", erro)

    def limpar_cache_respostas(self) -> int:
        """Remove chaves de respostas cacheadas."""
        if not self.habilitado:
            return 0
        padrao = f"{self.prefixo}:cache:*"
        try:
            chaves = list(self.cliente_redis.scan_iter(match=padrao))
            if not chaves:
                return 0
            removidas = self.cliente_redis.delete(*chaves)
            self._registrar_evento(logging.INFO, "cache_respostas_removidas", quantidade=removidas)
            return removidas
        except Exception as erro:
            self._registrar_falha("cache_limpar_respostas", erro)
            return 0

    def _chave_versao_indice(self) -> str:
        """Retorna chave da versão global do índice."""
        return f"{self.prefixo}:cache:versao_indice"

    @staticmethod
    def _hash_chave(chave: str) -> str:
        """Hash curto para logs sem expor a chave."""
        return hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra evento estruturado de cache."""
        logger.log(
            nivel,
            json.dumps(
                {"event": evento, "metadata": metadados},
                ensure_ascii=False,
                default=str,
            ),
        )

    def _registrar_falha(self, operacao: str, erro: Exception) -> None:
        """Registra falha de Redis sem impedir execução normal."""
        self._registrar_evento(
            logging.WARNING,
            "falha_redis_cache",
            operacao=operacao,
            erro=erro.__class__.__name__,
        )
