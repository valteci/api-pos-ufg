"""Interface de banco vetorial e implementação ChromaDB."""

import json
import logging
import math
from collections.abc import Sequence
from typing import Any, Protocol
from urllib.parse import urlparse

from app.domain.exceptions import BancoVetorialError, ConfiguracaoBancoVetorialError
from app.domain.rag import DocumentoVetorial, ResultadoBuscaVetorial, ValorMetadado

logger = logging.getLogger(__name__)


class BancoVetorial(Protocol):
    """Contrato interno para persistência e busca de embeddings."""

    def adicionar_documentos(self, documentos: Sequence[DocumentoVetorial]) -> None:
        """Insere ou atualiza documentos vetoriais."""
        ...

    def remover_por_sprints(self, sprints: Sequence[str]) -> None:
        """Remove documentos associados às sprints informadas."""
        ...

    def limpar_indice(self) -> None:
        """Remove todos os documentos da coleção vetorial."""
        ...

    def buscar(
        self,
        embedding: Sequence[float],
        *,
        sprints: Sequence[str],
        rank: int,
    ) -> list[ResultadoBuscaVetorial]:
        """Busca documentos mais próximos do embedding informado."""
        ...


class BancoVetorialChromaDB:
    """Banco vetorial ChromaDB acessado por HTTP."""

    def __init__(self, *, url: str | None, colecao: str, cliente: Any | None = None) -> None:
        """Inicializa integração com ChromaDB.

        Args:
            url: URL HTTP do ChromaDB, por exemplo `http://chromadb:8000`.
            colecao: Nome da coleção usada para os dados de sprint.
            cliente: Cliente ChromaDB injetável para testes específicos.
        """
        if not url:
            raise ConfiguracaoBancoVetorialError("VECTOR_DB_URL")
        if not colecao.strip():
            raise ConfiguracaoBancoVetorialError("VECTOR_DB_COLLECTION")

        self.url = url
        self.colecao = colecao.strip()
        self._cliente = cliente
        self._colecao_chroma: Any | None = None

    def adicionar_documentos(self, documentos: Sequence[DocumentoVetorial]) -> None:
        """Insere ou atualiza documentos na coleção ChromaDB."""
        if not documentos:
            return

        try:
            colecao = self._obter_colecao()
            colecao.upsert(
                ids=[documento.id for documento in documentos],
                documents=[documento.texto for documento in documentos],
                embeddings=[documento.embedding for documento in documentos],
                metadatas=[self._metadados_chroma(documento.metadados) for documento in documentos],
            )
            self._registrar_evento(
                logging.INFO,
                "banco_vetorial_documentos_adicionados",
                quantidade=len(documentos),
                colecao=self.colecao,
            )
        except ConfiguracaoBancoVetorialError:
            raise
        except Exception as erro:
            raise self._tratar_erro("adicionar_documentos", erro) from erro

    def remover_por_sprints(self, sprints: Sequence[str]) -> None:
        """Remove documentos das sprints informadas."""
        sprints_unicas = sorted({sprint for sprint in sprints if sprint})
        if not sprints_unicas:
            return

        try:
            colecao = self._obter_colecao()
            for sprint in sprints_unicas:
                colecao.delete(where={"sprint": sprint})
            self._registrar_evento(
                logging.INFO,
                "banco_vetorial_sprints_removidas",
                sprints=sprints_unicas,
                colecao=self.colecao,
            )
        except ConfiguracaoBancoVetorialError:
            raise
        except Exception as erro:
            raise self._tratar_erro("remover_por_sprints", erro) from erro

    def limpar_indice(self) -> None:
        """Remove e recria a coleção vetorial para limpeza completa."""
        try:
            cliente = self._obter_cliente()
            try:
                cliente.delete_collection(self.colecao)
            except Exception as erro:
                if "does not exist" not in str(erro).lower() and "not found" not in str(erro).lower():
                    raise
            self._colecao_chroma = cliente.get_or_create_collection(name=self.colecao)
            self._registrar_evento(
                logging.INFO,
                "banco_vetorial_indice_limpo",
                colecao=self.colecao,
            )
        except ConfiguracaoBancoVetorialError:
            raise
        except Exception as erro:
            raise self._tratar_erro("limpar_indice", erro) from erro

    def buscar(
        self,
        embedding: Sequence[float],
        *,
        sprints: Sequence[str],
        rank: int,
    ) -> list[ResultadoBuscaVetorial]:
        """Busca fragmentos próximos no ChromaDB."""
        if rank < 1:
            return []

        where = None
        sprints_unicas = sorted({sprint for sprint in sprints if sprint})
        if len(sprints_unicas) == 1:
            where = {"sprint": sprints_unicas[0]}
        elif len(sprints_unicas) > 1:
            where = {"sprint": {"$in": sprints_unicas}}

        try:
            parametros: dict[str, Any] = {
                "query_embeddings": [list(embedding)],
                "n_results": rank,
                "include": ["documents", "metadatas", "distances"],
            }
            if where is not None:
                parametros["where"] = where
            resultado = self._obter_colecao().query(**parametros)
        except ConfiguracaoBancoVetorialError:
            raise
        except Exception as erro:
            raise self._tratar_erro("buscar", erro) from erro

        return self._normalizar_resultados(resultado)

    def _obter_cliente(self) -> Any:
        """Cria cliente ChromaDB preguiçosamente."""
        if self._cliente is not None:
            return self._cliente

        try:
            import chromadb
        except ImportError as erro:
            raise ConfiguracaoBancoVetorialError("chromadb") from erro

        url = urlparse(self.url)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ConfiguracaoBancoVetorialError("VECTOR_DB_URL")

        self._cliente = chromadb.HttpClient(
            host=url.hostname,
            port=url.port or (443 if url.scheme == "https" else 80),
            ssl=url.scheme == "https",
        )
        return self._cliente

    def _obter_colecao(self) -> Any:
        """Obtém ou cria a coleção configurada."""
        if self._colecao_chroma is None:
            self._colecao_chroma = self._obter_cliente().get_or_create_collection(
                name=self.colecao
            )
        return self._colecao_chroma

    @staticmethod
    def _metadados_chroma(metadados: dict[str, ValorMetadado]) -> dict[str, ValorMetadado]:
        """Remove valores vazios não aceitos pelo ChromaDB."""
        return {
            chave: valor
            for chave, valor in metadados.items()
            if isinstance(valor, (str, int, float, bool)) and valor != ""
        }

    @staticmethod
    def _normalizar_resultados(resultado: Any) -> list[ResultadoBuscaVetorial]:
        """Converte resposta do ChromaDB para modelo interno."""
        ids = resultado.get("ids", [[]]) if isinstance(resultado, dict) else [[]]
        documentos = resultado.get("documents", [[]]) if isinstance(resultado, dict) else [[]]
        metadados = resultado.get("metadatas", [[]]) if isinstance(resultado, dict) else [[]]
        distancias = resultado.get("distances", [[]]) if isinstance(resultado, dict) else [[]]

        resultados: list[ResultadoBuscaVetorial] = []
        for indice, documento_id in enumerate(ids[0] if ids else []):
            distancia = distancias[0][indice] if distancias and distancias[0] else 0.0
            score = 1.0 / (1.0 + float(distancia))
            resultados.append(
                ResultadoBuscaVetorial(
                    id=str(documento_id),
                    texto=str(documentos[0][indice]) if documentos and documentos[0] else "",
                    score=score,
                    metadados=dict(metadados[0][indice]) if metadados and metadados[0] else {},
                )
            )

        return resultados

    def _tratar_erro(self, operacao: str, erro: Exception) -> BancoVetorialError:
        """Registra e converte erro externo para exceção de domínio."""
        erro_dominio = BancoVetorialError(operacao=operacao, erro=erro.__class__.__name__)
        self._registrar_evento(
            logging.ERROR,
            "falha_banco_vetorial",
            operacao=operacao,
            erro=erro.__class__.__name__,
            codigo=erro_dominio.codigo,
        )
        return erro_dominio

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra evento estruturado sem expor conteúdo integral."""
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


class BancoVetorialFake:
    """Banco vetorial em memória para testes unitários."""

    def __init__(self) -> None:
        """Inicializa fake sem dependências externas."""
        self.documentos: dict[str, DocumentoVetorial] = {}
        self.sprints_removidas: list[list[str]] = []
        self.quantidade_limpezas = 0

    def adicionar_documentos(self, documentos: Sequence[DocumentoVetorial]) -> None:
        """Insere documentos em memória com semântica de upsert."""
        for documento in documentos:
            self.documentos[documento.id] = documento

    def remover_por_sprints(self, sprints: Sequence[str]) -> None:
        """Remove documentos por metadado de sprint."""
        sprints_unicas = sorted({sprint for sprint in sprints if sprint})
        self.sprints_removidas.append(sprints_unicas)
        conjunto = set(sprints_unicas)
        ids_removidos = [
            documento_id
            for documento_id, documento in self.documentos.items()
            if documento.metadados.get("sprint") in conjunto
        ]
        for documento_id in ids_removidos:
            del self.documentos[documento_id]

    def limpar_indice(self) -> None:
        """Remove todos os documentos em memória."""
        self.quantidade_limpezas += 1
        self.documentos.clear()

    def buscar(
        self,
        embedding: Sequence[float],
        *,
        sprints: Sequence[str],
        rank: int,
    ) -> list[ResultadoBuscaVetorial]:
        """Busca documentos por similaridade de cosseno em memória."""
        if rank < 1:
            return []

        escopo = {sprint for sprint in sprints if sprint}
        candidatos = [
            documento
            for documento in self.documentos.values()
            if not escopo or documento.metadados.get("sprint") in escopo
        ]
        ordenados = sorted(
            candidatos,
            key=lambda documento: self._similaridade_cosseno(embedding, documento.embedding),
            reverse=True,
        )

        return [
            ResultadoBuscaVetorial(
                id=documento.id,
                texto=documento.texto,
                score=self._similaridade_cosseno(embedding, documento.embedding),
                metadados=documento.metadados,
            )
            for documento in ordenados[:rank]
        ]

    @staticmethod
    def _similaridade_cosseno(a: Sequence[float], b: Sequence[float]) -> float:
        """Calcula similaridade de cosseno sem dependências numéricas."""
        if not a or not b or len(a) != len(b):
            return 0.0

        produto = sum(float(valor_a) * float(valor_b) for valor_a, valor_b in zip(a, b))
        norma_a = math.sqrt(sum(float(valor) ** 2 for valor in a))
        norma_b = math.sqrt(sum(float(valor) ** 2 for valor in b))
        if norma_a == 0.0 or norma_b == 0.0:
            return 0.0

        return produto / (norma_a * norma_b)
