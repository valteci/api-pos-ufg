"""Cliente Redis interno e fake para testes."""

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


class ClienteRedis(Protocol):
    """Contrato mínimo usado por cache e rate limiting."""

    def get(self, chave: str) -> str | None:
        """Obtém valor textual por chave."""
        ...

    def setex(self, chave: str, ttl_seconds: int, valor: str) -> None:
        """Grava valor textual com TTL."""
        ...

    def incr(self, chave: str) -> int:
        """Incrementa contador e retorna o valor atual."""
        ...

    def expire(self, chave: str, ttl_seconds: int) -> None:
        """Define TTL para uma chave existente."""
        ...

    def delete(self, *chaves: str) -> int:
        """Remove chaves e retorna quantidade removida."""
        ...

    def scan_iter(self, match: str) -> Iterator[str]:
        """Itera por chaves compatíveis com o padrão informado."""
        ...


class ClienteRedisReal:
    """Adaptador do cliente oficial Redis."""

    def __init__(self, redis_url: str) -> None:
        """Inicializa cliente Redis a partir da URL configurada."""
        self.redis_url = redis_url
        self._cliente = None

    def get(self, chave: str) -> str | None:
        """Obtém valor textual por chave."""
        valor = self._obter_cliente().get(chave)
        if valor is None:
            return None
        if isinstance(valor, bytes):
            return valor.decode("utf-8")
        return str(valor)

    def setex(self, chave: str, ttl_seconds: int, valor: str) -> None:
        """Grava valor textual com TTL."""
        self._obter_cliente().set(chave, valor, ex=ttl_seconds)

    def incr(self, chave: str) -> int:
        """Incrementa contador e retorna o valor atual."""
        return int(self._obter_cliente().incr(chave))

    def expire(self, chave: str, ttl_seconds: int) -> None:
        """Define TTL para uma chave existente."""
        self._obter_cliente().expire(chave, ttl_seconds)

    def delete(self, *chaves: str) -> int:
        """Remove chaves e retorna quantidade removida."""
        if not chaves:
            return 0
        return int(self._obter_cliente().delete(*chaves))

    def scan_iter(self, match: str) -> Iterator[str]:
        """Itera por chaves compatíveis com o padrão informado."""
        for chave in self._obter_cliente().scan_iter(match=match):
            if isinstance(chave, bytes):
                yield chave.decode("utf-8")
            else:
                yield str(chave)

    def _obter_cliente(self):
        """Cria cliente Redis preguiçosamente."""
        if self._cliente is None:
            from redis import Redis

            self._cliente = Redis.from_url(
                self.redis_url,
                decode_responses=False,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
        return self._cliente


@dataclass
class _EntradaRedisFake:
    """Valor armazenado pelo Redis fake."""

    valor: str
    expira_em: float | None = None


class RedisFake:
    """Implementação Redis em memória para testes."""

    def __init__(self) -> None:
        """Inicializa armazenamento em memória."""
        self.dados: dict[str, _EntradaRedisFake] = {}
        self.ttls: dict[str, int] = {}

    def get(self, chave: str) -> str | None:
        """Obtém valor quando a chave existe e não expirou."""
        self._remover_expirada(chave)
        entrada = self.dados.get(chave)
        return entrada.valor if entrada else None

    def setex(self, chave: str, ttl_seconds: int, valor: str) -> None:
        """Grava valor com TTL."""
        self.dados[chave] = _EntradaRedisFake(
            valor=valor,
            expira_em=time.monotonic() + ttl_seconds,
        )
        self.ttls[chave] = ttl_seconds

    def incr(self, chave: str) -> int:
        """Incrementa contador textual."""
        self._remover_expirada(chave)
        valor_atual = self.dados.get(chave)
        novo_valor = int(valor_atual.valor) + 1 if valor_atual else 1
        self.dados[chave] = _EntradaRedisFake(valor=str(novo_valor))
        return novo_valor

    def expire(self, chave: str, ttl_seconds: int) -> None:
        """Define TTL para chave existente."""
        if chave in self.dados:
            self.dados[chave].expira_em = time.monotonic() + ttl_seconds
            self.ttls[chave] = ttl_seconds

    def delete(self, *chaves: str) -> int:
        """Remove chaves."""
        removidas = 0
        for chave in chaves:
            if chave in self.dados:
                removidas += 1
                del self.dados[chave]
            self.ttls.pop(chave, None)
        return removidas

    def scan_iter(self, match: str) -> Iterator[str]:
        """Itera chaves por prefixo simples com `*` no final."""
        prefixo = match[:-1] if match.endswith("*") else match
        for chave in list(self.dados):
            self._remover_expirada(chave)
            if chave in self.dados and chave.startswith(prefixo):
                yield chave

    def _remover_expirada(self, chave: str) -> None:
        """Remove chave expirada."""
        entrada = self.dados.get(chave)
        if entrada and entrada.expira_em is not None and entrada.expira_em <= time.monotonic():
            del self.dados[chave]
            self.ttls.pop(chave, None)


class RedisIndisponivelFake:
    """Fake que simula Redis indisponível."""

    def get(self, chave: str) -> str | None:
        """Simula falha de leitura."""
        raise ConnectionError("Redis indisponível")

    def setex(self, chave: str, ttl_seconds: int, valor: str) -> None:
        """Simula falha de escrita."""
        raise ConnectionError("Redis indisponível")

    def incr(self, chave: str) -> int:
        """Simula falha de contador."""
        raise ConnectionError("Redis indisponível")

    def expire(self, chave: str, ttl_seconds: int) -> None:
        """Simula falha de TTL."""
        raise ConnectionError("Redis indisponível")

    def delete(self, *chaves: str) -> int:
        """Simula falha de remoção."""
        raise ConnectionError("Redis indisponível")

    def scan_iter(self, match: str) -> Iterator[str]:
        """Simula falha de varredura."""
        raise ConnectionError("Redis indisponível")
