"""Serviço de geração de resumos consultivos sobre sprints."""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.core.config import Configuracoes
from app.domain.exceptions import ConsultaResumoInvalidaError, SprintNaoEncontradaError
from app.domain.sprint import Sprint, Subtarefa, Tarefa
from app.integrations.openai_client import ProvedorLLM
from app.services.sprint_loader import CarregadorSprints

logger = logging.getLogger(__name__)

RESPOSTA_CONTEXTO_INSUFICIENTE = (
    "Não encontrei informações suficientes nos dados disponíveis para responder com segurança."
)

INSTRUCOES_SISTEMA_RESUMO = (
    "Você é uma consultora Scrum para uma squad de desenvolvimento. "
    "Responda em português, de forma objetiva e útil. "
    "Use somente os dados de sprint fornecidos no contexto. "
    "Não invente tarefas, subtarefas, responsáveis, status ou datas. "
    "Quando o contexto não permitir uma resposta segura, diga explicitamente "
    "que não encontrou informações suficientes."
)


@dataclass(frozen=True)
class FonteResumo:
    """Fonte usada para compor o contexto enviado ao LLM."""

    sprint: str
    origem: str
    tipo: str
    caminho: str
    titulo: str | None = None


@dataclass(frozen=True)
class ResultadoResumo:
    """Resultado da geração de resumo."""

    resposta: str
    sprints_consultadas: list[str]
    fontes: list[FonteResumo]


@dataclass(frozen=True)
class ContextoResumo:
    """Contexto textual e fontes correspondentes."""

    texto: str
    fontes: list[FonteResumo]
    truncado: bool


class ServicoResumos:
    """Gera respostas consultivas baseadas em arquivos de sprint."""

    def __init__(
        self,
        *,
        configuracoes: Configuracoes,
        carregador_sprints: CarregadorSprints,
        provedor_llm: ProvedorLLM,
    ) -> None:
        """Inicializa serviço com dependências testáveis."""
        self.configuracoes = configuracoes
        self.carregador_sprints = carregador_sprints
        self.provedor_llm = provedor_llm

    def gerar_resumo(self, *, pergunta: str, sprints: list[str]) -> ResultadoResumo:
        """Gera resumo ou resposta consultiva com base nos dados carregados."""
        pergunta_normalizada = self._validar_pergunta(pergunta)
        sprints_consultadas = self._resolver_sprints(pergunta_normalizada, sprints)
        self._validar_quantidade_sprints(len(sprints_consultadas))

        self._registrar_evento(
            logging.INFO,
            "resumo_consulta_iniciada",
            quantidade_sprints=len(sprints_consultadas),
        )

        if not sprints_consultadas:
            self._registrar_evento(
                logging.INFO,
                "resumo_contexto_insuficiente",
                quantidade_sprints=0,
            )
            return self._resultado_sem_contexto()

        dados_sprints = [
            self.carregador_sprints.carregar_sprint(nome_sprint)
            for nome_sprint in sprints_consultadas
        ]
        contexto = self._montar_contexto(dados_sprints)
        if not contexto.texto.strip() or not contexto.fontes:
            self._registrar_evento(
                logging.INFO,
                "resumo_contexto_insuficiente",
                quantidade_sprints=len(sprints_consultadas),
            )
            return self._resultado_sem_contexto(sprints_consultadas=sprints_consultadas)

        resposta_llm = self.provedor_llm.gerar_resposta(
            instrucoes_sistema=INSTRUCOES_SISTEMA_RESUMO,
            contexto=contexto.texto,
            pergunta=pergunta_normalizada,
        )

        self._registrar_evento(
            logging.INFO,
            "resumo_consulta_executada",
            quantidade_sprints=len(sprints_consultadas),
            quantidade_fontes=len(contexto.fontes),
            contexto_truncado=contexto.truncado,
            modelo=resposta_llm.modelo,
        )
        return ResultadoResumo(
            resposta=resposta_llm.texto,
            sprints_consultadas=sprints_consultadas,
            fontes=contexto.fontes,
        )

    def _resolver_sprints(self, pergunta: str, sprints: list[str]) -> list[str]:
        """Resolve escopo explícito, inferido pela pergunta ou completo."""
        disponiveis = self.carregador_sprints.listar_sprints()
        mapa_aliases = self._mapear_aliases_sprints(disponiveis)

        if sprints:
            resolvidas: list[str] = []
            for sprint in sprints:
                nome_resolvido = mapa_aliases.get(self._normalizar_texto(sprint))
                if nome_resolvido is None:
                    raise SprintNaoEncontradaError(sprint)
                if nome_resolvido not in resolvidas:
                    resolvidas.append(nome_resolvido)
            return resolvidas

        mencionadas = self._identificar_sprints_na_pergunta(pergunta, mapa_aliases)
        if mencionadas:
            return mencionadas

        return disponiveis

    def _validar_pergunta(self, pergunta: str) -> str:
        """Valida pergunta usando limites configuráveis."""
        pergunta_normalizada = pergunta.strip()
        if not pergunta_normalizada:
            raise ConsultaResumoInvalidaError(
                "Pergunta não pode ser vazia.",
                campo="pergunta",
            )
        if len(pergunta_normalizada) > self.configuracoes.max_message_length:
            raise ConsultaResumoInvalidaError(
                "Pergunta excede o limite configurado.",
                campo="pergunta",
                limite=self.configuracoes.max_message_length,
            )
        return pergunta_normalizada

    def _validar_quantidade_sprints(self, quantidade_sprints: int) -> None:
        """Valida quantidade de sprints do escopo resolvido."""
        if quantidade_sprints > self.configuracoes.max_sprints_per_request:
            raise ConsultaResumoInvalidaError(
                "Quantidade de sprints excede o limite configurado.",
                campo="sprints",
                limite=self.configuracoes.max_sprints_per_request,
            )

    def _montar_contexto(self, sprints: list[Sprint]) -> ContextoResumo:
        """Monta contexto compacto e fontes usadas no prompt."""
        limite_contexto = max(1000, min(20_000, self.configuracoes.max_fragment_size * 4))
        linhas: list[str] = []
        fontes: list[FonteResumo] = []
        truncado = False

        for sprint in sprints:
            blocos = self._blocos_sprint(sprint)
            for bloco, fonte in blocos:
                tamanho_estimado = sum(len(linha) + 1 for linha in linhas) + len(bloco) + 1
                if tamanho_estimado > limite_contexto:
                    truncado = True
                    break
                linhas.append(bloco)
                fontes.append(fonte)
            if truncado:
                break

        return ContextoResumo(
            texto="\n\n".join(linhas),
            fontes=fontes,
            truncado=truncado,
        )

    def _blocos_sprint(self, sprint: Sprint) -> list[tuple[str, FonteResumo]]:
        """Gera blocos textuais rastreáveis para uma sprint."""
        origem = sprint.arquivo_origem.name
        blocos: list[tuple[str, FonteResumo]] = [
            (
                (
                    f"Sprint: {sprint.identificador}\n"
                    f"Origem: {origem}\n"
                    f"Quantidade de tarefas: {len(sprint.tarefas)}\n"
                    f"Quantidade de subtarefas: {sprint.quantidade_subtarefas}"
                ),
                FonteResumo(
                    sprint=sprint.identificador,
                    origem=origem,
                    tipo="sprint",
                    caminho="$",
                    titulo=sprint.identificador,
                ),
            )
        ]

        for tarefa in sprint.tarefas:
            blocos.append((self._bloco_tarefa(sprint, tarefa), self._fonte_tarefa(sprint, tarefa)))
            for subtarefa in tarefa.subtarefas:
                blocos.append(
                    (
                        self._bloco_subtarefa(sprint, tarefa, subtarefa),
                        self._fonte_subtarefa(sprint, subtarefa),
                    )
                )

        return blocos

    @staticmethod
    def _bloco_tarefa(sprint: Sprint, tarefa: Tarefa) -> str:
        """Monta texto compacto de uma tarefa."""
        linhas = [
            f"Sprint: {sprint.identificador}",
            f"Tipo: tarefa",
            f"Caminho: {tarefa.caminho}",
        ]
        if tarefa.titulo:
            linhas.append(f"Tarefa: {tarefa.titulo}")
        if tarefa.descricao:
            linhas.append(f"Descrição: {tarefa.descricao}")
        if tarefa.status:
            linhas.append(f"Status: {tarefa.status}")
        if tarefa.responsavel:
            linhas.append(f"Responsável: {tarefa.responsavel}")
        if tarefa.subtarefas:
            linhas.append(f"Subtarefas vinculadas: {len(tarefa.subtarefas)}")
        return "\n".join(linhas)

    @staticmethod
    def _bloco_subtarefa(sprint: Sprint, tarefa: Tarefa, subtarefa: Subtarefa) -> str:
        """Monta texto compacto de uma subtarefa."""
        linhas = [
            f"Sprint: {sprint.identificador}",
            "Tipo: subtarefa",
            f"Caminho: {subtarefa.caminho}",
        ]
        if tarefa.titulo:
            linhas.append(f"Tarefa pai: {tarefa.titulo}")
        if subtarefa.titulo:
            linhas.append(f"Subtarefa: {subtarefa.titulo}")
        if subtarefa.descricao:
            linhas.append(f"Descrição: {subtarefa.descricao}")
        if subtarefa.status:
            linhas.append(f"Status: {subtarefa.status}")
        if subtarefa.responsavel:
            linhas.append(f"Responsável: {subtarefa.responsavel}")
        return "\n".join(linhas)

    @staticmethod
    def _fonte_tarefa(sprint: Sprint, tarefa: Tarefa) -> FonteResumo:
        """Cria fonte de tarefa."""
        return FonteResumo(
            sprint=sprint.identificador,
            origem=sprint.arquivo_origem.name,
            tipo="tarefa",
            caminho=tarefa.caminho,
            titulo=tarefa.titulo,
        )

    @staticmethod
    def _fonte_subtarefa(sprint: Sprint, subtarefa: Subtarefa) -> FonteResumo:
        """Cria fonte de subtarefa."""
        return FonteResumo(
            sprint=sprint.identificador,
            origem=sprint.arquivo_origem.name,
            tipo="subtarefa",
            caminho=subtarefa.caminho,
            titulo=subtarefa.titulo,
        )

    @staticmethod
    def _mapear_aliases_sprints(sprints_disponiveis: list[str]) -> dict[str, str]:
        """Cria aliases seguros para identificar sprints por nome ou número."""
        aliases: dict[str, str] = {}
        for sprint in sprints_disponiveis:
            normalizado = ServicoResumos._normalizar_texto(sprint)
            aliases[normalizado] = sprint

            match = re.search(r"\bsprint\s+(\d+)\b", normalizado)
            if match:
                numero = match.group(1)
                aliases[f"sprint {numero}"] = sprint
                aliases[numero] = sprint

        return aliases

    @staticmethod
    def _identificar_sprints_na_pergunta(
        pergunta: str,
        mapa_aliases: dict[str, str],
    ) -> list[str]:
        """Identifica sprints mencionadas na pergunta por aliases conhecidos."""
        pergunta_normalizada = ServicoResumos._normalizar_texto(pergunta)
        encontradas: list[str] = []
        for alias, sprint in sorted(mapa_aliases.items(), key=lambda item: len(item[0]), reverse=True):
            padrao = rf"(?<!\w){re.escape(alias)}(?!\w)"
            if re.search(padrao, pergunta_normalizada) and sprint not in encontradas:
                encontradas.append(sprint)
        return encontradas

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        """Normaliza texto para comparação de nomes de sprint."""
        sem_acentos = unicodedata.normalize("NFKD", texto)
        ascii_texto = sem_acentos.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", ascii_texto.lower()).strip()

    @staticmethod
    def _resultado_sem_contexto(
        *,
        sprints_consultadas: list[str] | None = None,
    ) -> ResultadoResumo:
        """Retorna resposta explícita quando não há contexto suficiente."""
        return ResultadoResumo(
            resposta=RESPOSTA_CONTEXTO_INSUFICIENTE,
            sprints_consultadas=sprints_consultadas or [],
            fontes=[],
        )

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra eventos de resumo sem expor pergunta ou contexto completo."""
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
