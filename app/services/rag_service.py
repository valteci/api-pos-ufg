"""Serviço de consulta RAG sobre dados indexados de sprints."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import Configuracoes
from app.domain.exceptions import ConsultaRagInvalidaError, SprintNaoEncontradaError
from app.domain.rag import ResultadoBuscaVetorial, ValorMetadado
from app.integrations.openai_client import ProvedorEmbeddings
from app.integrations.vector_store import BancoVetorial
from app.services.sprint_loader import CarregadorSprints

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FragmentoRag:
    """Fragmento recuperado e pronto para resposta HTTP."""

    conteudo: str
    score: float
    sprint: str
    origem: str
    metadados: dict[str, ValorMetadado]


@dataclass(frozen=True)
class ResultadoConsultaRag:
    """Resultado de uma consulta RAG."""

    mensagem: str
    sprints_consultadas: list[str]
    rank: int
    tamanho_fragmento: int
    fragmentos: list[FragmentoRag]


class ServicoRag:
    """Executa recuperação semântica de fragmentos de sprints."""

    def __init__(
        self,
        *,
        configuracoes: Configuracoes,
        carregador_sprints: CarregadorSprints,
        provedor_embeddings: ProvedorEmbeddings,
        banco_vetorial: BancoVetorial,
    ) -> None:
        """Inicializa serviço com dependências testáveis."""
        self.configuracoes = configuracoes
        self.carregador_sprints = carregador_sprints
        self.provedor_embeddings = provedor_embeddings
        self.banco_vetorial = banco_vetorial

    def consultar(
        self,
        *,
        sprints: list[str],
        mensagem: str,
        rank: int,
        tamanho_fragmento: int,
    ) -> ResultadoConsultaRag:
        """Recupera fragmentos relevantes respeitando escopo de sprints."""
        mensagem_normalizada = self._validar_mensagem(mensagem)
        self._validar_limites(
            rank=rank,
            tamanho_fragmento=tamanho_fragmento,
            quantidade_sprints=len(sprints),
        )
        sprints_consultadas = self._resolver_sprints(sprints)
        self._validar_quantidade_sprints(len(sprints_consultadas))

        self._registrar_evento(
            logging.INFO,
            "consulta_rag_iniciada",
            quantidade_sprints=len(sprints_consultadas),
            rank=rank,
            tamanho_fragmento=tamanho_fragmento,
        )

        embedding = self.provedor_embeddings.gerar_embedding(mensagem_normalizada)
        resultados = self.banco_vetorial.buscar(
            embedding.vetor,
            sprints=sprints_consultadas,
            rank=rank,
        )
        fragmentos = [
            self._montar_fragmento(resultado, tamanho_fragmento)
            for resultado in resultados[:rank]
        ]

        self._registrar_evento(
            logging.INFO,
            "consulta_rag_executada",
            quantidade_sprints=len(sprints_consultadas),
            quantidade_fragmentos=len(fragmentos),
            rank=rank,
            tamanho_fragmento=tamanho_fragmento,
            modelo_embedding=embedding.modelo,
        )
        return ResultadoConsultaRag(
            mensagem=mensagem_normalizada,
            sprints_consultadas=sprints_consultadas,
            rank=rank,
            tamanho_fragmento=tamanho_fragmento,
            fragmentos=fragmentos,
        )

    def _resolver_sprints(self, sprints: list[str]) -> list[str]:
        """Resolve escopo de sprints e rejeita identificadores inexistentes."""
        disponiveis = self.carregador_sprints.listar_sprints()
        if not sprints:
            return disponiveis

        solicitadas = list(dict.fromkeys(sprints))
        existentes = set(disponiveis)
        for sprint in solicitadas:
            if sprint not in existentes:
                raise SprintNaoEncontradaError(sprint)

        return solicitadas

    def _validar_mensagem(self, mensagem: str) -> str:
        """Aplica validação de mensagem com limite configurável."""
        mensagem_normalizada = mensagem.strip()
        if not mensagem_normalizada:
            raise ConsultaRagInvalidaError(
                "Mensagem não pode ser vazia.",
                campo="mensagem",
            )
        if len(mensagem_normalizada) > self.configuracoes.max_message_length:
            raise ConsultaRagInvalidaError(
                "Mensagem excede o limite configurado.",
                campo="mensagem",
                limite=self.configuracoes.max_message_length,
            )
        return mensagem_normalizada

    def _validar_limites(
        self,
        *,
        rank: int,
        tamanho_fragmento: int,
        quantidade_sprints: int,
    ) -> None:
        """Valida limites configuráveis além do schema Pydantic."""
        if rank < 1:
            raise ConsultaRagInvalidaError("Rank deve ser positivo.", campo="rank")
        if rank > self.configuracoes.max_rag_rank:
            raise ConsultaRagInvalidaError(
                "Rank excede o limite configurado.",
                campo="rank",
                limite=self.configuracoes.max_rag_rank,
            )

        if tamanho_fragmento < 1:
            raise ConsultaRagInvalidaError(
                "Tamanho do fragmento deve ser positivo.",
                campo="tamanho_fragmento",
            )
        if tamanho_fragmento > self.configuracoes.max_fragment_size:
            raise ConsultaRagInvalidaError(
                "Tamanho do fragmento excede o limite configurado.",
                campo="tamanho_fragmento",
                limite=self.configuracoes.max_fragment_size,
            )

        self._validar_quantidade_sprints(quantidade_sprints)

    def _validar_quantidade_sprints(self, quantidade_sprints: int) -> None:
        """Valida quantidade de sprints explícitas ou resolvidas."""
        if quantidade_sprints > self.configuracoes.max_sprints_per_request:
            raise ConsultaRagInvalidaError(
                "Quantidade de sprints excede o limite configurado.",
                campo="sprints",
                limite=self.configuracoes.max_sprints_per_request,
            )

    @staticmethod
    def _montar_fragmento(
        resultado: ResultadoBuscaVetorial,
        tamanho_fragmento: int,
    ) -> FragmentoRag:
        """Converte resultado vetorial para fragmento de resposta."""
        metadados = dict(resultado.metadados)
        sprint = str(metadados.get("sprint") or "")
        origem = str(metadados.get("origem") or "")
        conteudo = resultado.texto[:tamanho_fragmento]
        return FragmentoRag(
            conteudo=conteudo,
            score=resultado.score,
            sprint=sprint,
            origem=origem,
            metadados=metadados,
        )

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra eventos RAG sem expor a mensagem do usuário."""
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
