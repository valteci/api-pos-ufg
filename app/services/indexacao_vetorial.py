"""Serviço de indexação vetorial de dados de sprints."""

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.domain.rag import DocumentoVetorial, FragmentoSprint
from app.integrations.openai_client import ProvedorEmbeddings
from app.integrations.vector_store import BancoVetorial
from app.services.cache_service import CacheRespostas
from app.services.chunking_service import ServicoChunkingSprint
from app.services.sprint_loader import CarregadorSprints

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoIndexacaoVetorial:
    """Resumo da execução de indexação vetorial."""

    sprints: list[str]
    quantidade_fragmentos: int
    modelo_embedding: str | None
    assinatura: str


class ServicoIndexacaoVetorial:
    """Orquestra carregamento, chunking, embeddings e persistência vetorial."""

    def __init__(
        self,
        *,
        carregador_sprints: CarregadorSprints,
        servico_chunking: ServicoChunkingSprint,
        provedor_embeddings: ProvedorEmbeddings,
        banco_vetorial: BancoVetorial,
        cache_respostas: CacheRespostas | None = None,
    ) -> None:
        """Inicializa o serviço com dependências testáveis."""
        self.carregador_sprints = carregador_sprints
        self.servico_chunking = servico_chunking
        self.provedor_embeddings = provedor_embeddings
        self.banco_vetorial = banco_vetorial
        self.cache_respostas = cache_respostas

    def indexar_sprints(
        self,
        nomes_sprints: Sequence[str] | None = None,
    ) -> ResultadoIndexacaoVetorial:
        """Indexa sprints específicas ou todas quando a lista vier vazia.

        Dados antigos das sprints afetadas são removidos antes da nova gravação
        para que exclusões em `data/` não deixem fragmentos obsoletos no índice.
        """
        nomes_resolvidos = self._resolver_nomes_sprints(nomes_sprints)
        self._registrar_evento(
            logging.INFO,
            "indexacao_vetorial_iniciada",
            sprints=nomes_resolvidos,
        )

        sprints = [self.carregador_sprints.carregar_sprint(nome) for nome in nomes_resolvidos]
        fragmentos = self.servico_chunking.fragmentar_sprints(sprints)

        self.banco_vetorial.remover_por_sprints(nomes_resolvidos)
        resultado = self._persistir_fragmentos(nomes_resolvidos, fragmentos)
        self._invalidar_cache_por_reindexacao()

        self._registrar_evento(
            logging.INFO,
            "indexacao_vetorial_concluida",
            sprints=resultado.sprints,
            quantidade_fragmentos=resultado.quantidade_fragmentos,
            modelo_embedding=resultado.modelo_embedding,
            assinatura=resultado.assinatura,
        )
        return resultado

    def reindexar_tudo(self) -> ResultadoIndexacaoVetorial:
        """Limpa o índice completo e recria embeddings a partir de `data/`."""
        nomes_resolvidos = self._resolver_nomes_sprints(None)
        self._registrar_evento(
            logging.INFO,
            "reindexacao_vetorial_iniciada",
            sprints=nomes_resolvidos,
        )

        self.banco_vetorial.limpar_indice()
        sprints = [self.carregador_sprints.carregar_sprint(nome) for nome in nomes_resolvidos]
        fragmentos = self.servico_chunking.fragmentar_sprints(sprints)
        resultado = self._persistir_fragmentos(nomes_resolvidos, fragmentos)
        self._invalidar_cache_por_reindexacao()

        self._registrar_evento(
            logging.INFO,
            "reindexacao_vetorial_concluida",
            sprints=resultado.sprints,
            quantidade_fragmentos=resultado.quantidade_fragmentos,
            modelo_embedding=resultado.modelo_embedding,
            assinatura=resultado.assinatura,
        )
        return resultado

    def limpar_indice(self) -> None:
        """Remove todos os documentos do índice vetorial."""
        self.banco_vetorial.limpar_indice()
        self._invalidar_cache_por_reindexacao()
        self._registrar_evento(logging.INFO, "indice_vetorial_limpo")

    def _persistir_fragmentos(
        self,
        nomes_sprints: list[str],
        fragmentos: list[FragmentoSprint],
    ) -> ResultadoIndexacaoVetorial:
        """Gera embeddings e persiste documentos no banco vetorial."""
        documentos: list[DocumentoVetorial] = []
        modelo_embedding: str | None = None

        for fragmento in fragmentos:
            embedding = self.provedor_embeddings.gerar_embedding(fragmento.conteudo)
            modelo_embedding = embedding.modelo
            documentos.append(
                DocumentoVetorial(
                    id=fragmento.id,
                    texto=fragmento.conteudo,
                    embedding=embedding.vetor,
                    metadados=fragmento.metadados,
                )
            )

        self.banco_vetorial.adicionar_documentos(documentos)
        return ResultadoIndexacaoVetorial(
            sprints=nomes_sprints,
            quantidade_fragmentos=len(fragmentos),
            modelo_embedding=modelo_embedding,
            assinatura=self._calcular_assinatura(fragmentos),
        )

    def _resolver_nomes_sprints(self, nomes_sprints: Sequence[str] | None) -> list[str]:
        """Resolve lista de sprints usando todos os arquivos quando vazia."""
        if nomes_sprints:
            nomes_normalizados = list(
                dict.fromkeys(nome.strip() for nome in nomes_sprints if nome.strip())
            )
            if nomes_normalizados:
                return nomes_normalizados
        return self.carregador_sprints.listar_sprints()

    @staticmethod
    def _calcular_assinatura(fragmentos: Sequence[FragmentoSprint]) -> str:
        """Calcula assinatura determinística do conjunto indexado."""
        hash_indice = hashlib.sha256()
        for fragmento in sorted(fragmentos, key=lambda item: item.id):
            hash_indice.update(fragmento.id.encode("utf-8"))
            hash_indice.update(b"\0")
            hash_indice.update(fragmento.conteudo.encode("utf-8"))
            hash_indice.update(b"\0")
        return hash_indice.hexdigest()

    def _invalidar_cache_por_reindexacao(self) -> None:
        """Invalida respostas cacheadas quando o índice muda."""
        if self.cache_respostas is not None:
            self.cache_respostas.invalidar_por_reindexacao()

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra eventos de indexação em JSON sem textos integrais."""
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
