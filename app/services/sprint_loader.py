"""Serviço de carregamento e normalização de arquivos JSON de sprints."""

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.exceptions import (
    DadosSprintInvalidosError,
    DiretorioDadosNaoEncontradoError,
    NomeSprintInvalidoError,
    SprintNaoEncontradaError,
)
from app.domain.sprint import JsonObjeto, Sprint, Subtarefa, Tarefa

logger = logging.getLogger(__name__)

CHAVES_TAREFAS = ("tarefas", "tasks", "issues", "itens", "items")
CHAVES_SUBTAREFAS = ("subtarefas", "subtasks", "sub_tasks", "sub_tarefas", "children")
CHAVES_TITULO = ("titulo", "title", "nome", "name", "summary", "resumo")
CHAVES_DESCRICAO = ("descricao", "description", "detalhes", "body")
CHAVES_STATUS = ("status", "estado", "situacao", "state")
CHAVES_RESPONSAVEL = (
    "responsavel",
    "assignee",
    "assigned_to",
    "dev",
    "desenvolvedor",
)


class CarregadorSprints:
    """Carrega e normaliza sprints a partir de arquivos JSON."""

    def __init__(self, diretorio_dados: str | Path) -> None:
        """Inicializa o carregador com o diretório de dados.

        Args:
            diretorio_dados: Caminho para a pasta que contém os arquivos `.json`.
        """
        self.diretorio_dados = Path(diretorio_dados)

    def listar_sprints(self) -> list[str]:
        """Lista os identificadores de sprints disponíveis no diretório de dados.

        Returns:
            Lista ordenada de identificadores derivados dos nomes dos arquivos.

        Raises:
            DiretorioDadosNaoEncontradoError: Quando `data/` não existe.
        """
        self._validar_diretorio()
        identificadores: list[str] = []

        for caminho in sorted(self.diretorio_dados.iterdir()):
            if not caminho.is_file():
                continue

            if caminho.suffix != ".json":
                self._registrar_log(
                    logging.INFO,
                    "arquivo_dados_ignorado",
                    caminho=str(caminho),
                    motivo="extensao_nao_json",
                )
                continue

            identificadores.append(caminho.stem)

        self._registrar_log(
            logging.INFO,
            "sprints_listadas",
            quantidade=len(identificadores),
            diretorio=str(self.diretorio_dados),
        )
        return identificadores

    def carregar_sprint(self, nome_sprint: str) -> Sprint:
        """Carrega uma sprint específica a partir de `data/`.

        Args:
            nome_sprint: Identificador da sprint, normalmente sem `.json`.

        Returns:
            Sprint normalizada.

        Raises:
            NomeSprintInvalidoError: Quando o identificador é inseguro ou vazio.
            DiretorioDadosNaoEncontradoError: Quando o diretório não existe.
            SprintNaoEncontradaError: Quando o arquivo da sprint não existe.
            DadosSprintInvalidosError: Quando o JSON é inválido ou sem conteúdo mínimo.
        """
        identificador = self._normalizar_nome_sprint(nome_sprint)
        self._validar_diretorio()
        caminho = self.diretorio_dados / f"{identificador}.json"

        self._registrar_log(
            logging.INFO,
            "carregamento_sprint_iniciado",
            nome_sprint=identificador,
            caminho=str(caminho),
        )

        if not caminho.is_file():
            erro = SprintNaoEncontradaError(identificador)
            self._registrar_erro("sprint_nao_encontrada", erro)
            raise erro

        dados = self._ler_json(caminho, identificador)
        sprint = self._normalizar_sprint(identificador, caminho, dados)

        self._registrar_log(
            logging.INFO,
            "carregamento_sprint_concluido",
            nome_sprint=sprint.identificador,
            quantidade_tarefas=len(sprint.tarefas),
            quantidade_subtarefas=sprint.quantidade_subtarefas,
        )
        return sprint

    def carregar_todas_sprints(self) -> list[Sprint]:
        """Carrega todas as sprints JSON disponíveis no diretório de dados."""
        return [self.carregar_sprint(nome_sprint) for nome_sprint in self.listar_sprints()]

    def _validar_diretorio(self) -> None:
        """Garante que o diretório de dados existe."""
        if not self.diretorio_dados.is_dir():
            erro = DiretorioDadosNaoEncontradoError(str(self.diretorio_dados))
            self._registrar_erro("diretorio_dados_nao_encontrado", erro)
            raise erro

    def _ler_json(self, caminho: Path, identificador: str) -> JsonObjeto | list[Any]:
        """Lê e valida a sintaxe JSON de um arquivo de sprint."""
        try:
            with caminho.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as exc:
            erro = DadosSprintInvalidosError(
                "Arquivo JSON da sprint é inválido.",
                nome_sprint=identificador,
                motivo="json_invalido",
                caminho=str(caminho),
            )
            self._registrar_erro("json_sprint_invalido", erro, posicao=exc.pos)
            raise erro from exc

        if dados in ({}, []):
            erro = DadosSprintInvalidosError(
                "Sprint vazia ou sem conteúdo mínimo.",
                nome_sprint=identificador,
                motivo="sprint_vazia",
                caminho=str(caminho),
            )
            self._registrar_erro("sprint_vazia", erro)
            raise erro

        return dados

    def _normalizar_sprint(
        self,
        identificador: str,
        caminho: Path,
        dados: JsonObjeto | list[Any],
    ) -> Sprint:
        """Normaliza o JSON bruto para o modelo interno de sprint."""
        tarefas_brutas, caminho_tarefas = self._extrair_tarefas(dados, identificador, caminho)
        tarefas = [
            self._normalizar_tarefa(tarefa, indice, caminho_tarefas, identificador)
            for indice, tarefa in enumerate(tarefas_brutas)
        ]

        return Sprint(
            identificador=identificador,
            arquivo_origem=caminho,
            dados_originais=dados,
            tarefas=tarefas,
        )

    def _extrair_tarefas(
        self,
        dados: JsonObjeto | list[Any],
        identificador: str,
        caminho: Path,
    ) -> tuple[list[Any], str]:
        """Extrai a lista bruta de tarefas do JSON."""
        if isinstance(dados, list):
            tarefas = dados
            caminho_tarefas = "$"
        elif isinstance(dados, dict):
            chave_tarefas = next((chave for chave in CHAVES_TAREFAS if chave in dados), None)
            if chave_tarefas is None:
                raise self._erro_dados_invalidos(
                    identificador,
                    "Sprint sem lista de tarefas em campo reconhecido.",
                    "lista_tarefas_ausente",
                    caminho,
                )
            tarefas = dados[chave_tarefas]
            caminho_tarefas = chave_tarefas
        else:
            raise self._erro_dados_invalidos(
                identificador,
                "JSON da sprint deve ser um objeto ou uma lista de tarefas.",
                "estrutura_raiz_invalida",
                caminho,
            )

        if not isinstance(tarefas, list):
            raise self._erro_dados_invalidos(
                identificador,
                "Campo de tarefas deve ser uma lista.",
                "lista_tarefas_invalida",
                caminho,
            )

        if not tarefas:
            raise self._erro_dados_invalidos(
                identificador,
                "Sprint sem tarefas.",
                "sprint_sem_tarefas",
                caminho,
            )

        return tarefas, caminho_tarefas

    def _normalizar_tarefa(
        self,
        tarefa: Any,
        indice: int,
        caminho_tarefas: str,
        identificador: str,
    ) -> Tarefa:
        """Normaliza uma tarefa bruta e suas subtarefas."""
        caminho = f"{caminho_tarefas}[{indice}]"
        if not isinstance(tarefa, dict):
            raise self._erro_dados_invalidos(
                nome_sprint=identificador,
                mensagem="Cada tarefa deve ser um objeto JSON.",
                motivo="tarefa_invalida",
                caminho=caminho,
            )

        subtarefas = self._normalizar_subtarefas(tarefa, caminho, identificador)

        return Tarefa(
            indice=indice,
            caminho=caminho,
            dados=tarefa,
            titulo=self._primeiro_texto(tarefa, CHAVES_TITULO),
            descricao=self._primeiro_texto(tarefa, CHAVES_DESCRICAO),
            status=self._primeiro_texto(tarefa, CHAVES_STATUS),
            responsavel=self._primeiro_texto(tarefa, CHAVES_RESPONSAVEL),
            subtarefas=subtarefas,
        )

    def _normalizar_subtarefas(
        self,
        tarefa: JsonObjeto,
        caminho_tarefa: str,
        identificador: str,
    ) -> list[Subtarefa]:
        """Normaliza subtarefas aceitando campo ausente, nulo ou vazio."""
        chave_subtarefas = next(
            (chave for chave in CHAVES_SUBTAREFAS if chave in tarefa),
            None,
        )
        if chave_subtarefas is None or tarefa[chave_subtarefas] is None:
            return []

        subtarefas_brutas = tarefa[chave_subtarefas]
        if not subtarefas_brutas:
            return []

        if not isinstance(subtarefas_brutas, list):
            raise self._erro_dados_invalidos(
                nome_sprint=identificador,
                mensagem="Campo de subtarefas deve ser uma lista.",
                motivo="lista_subtarefas_invalida",
                caminho=caminho_tarefa,
            )

        subtarefas: list[Subtarefa] = []
        for indice, subtarefa in enumerate(subtarefas_brutas):
            caminho = f"{caminho_tarefa}.{chave_subtarefas}[{indice}]"
            if not isinstance(subtarefa, dict):
                raise self._erro_dados_invalidos(
                    nome_sprint=identificador,
                    mensagem="Cada subtarefa deve ser um objeto JSON.",
                    motivo="subtarefa_invalida",
                    caminho=caminho,
                )

            subtarefas.append(
                Subtarefa(
                    indice=indice,
                    caminho=caminho,
                    dados=subtarefa,
                    titulo=self._primeiro_texto(subtarefa, CHAVES_TITULO),
                    descricao=self._primeiro_texto(subtarefa, CHAVES_DESCRICAO),
                    status=self._primeiro_texto(subtarefa, CHAVES_STATUS),
                    responsavel=self._primeiro_texto(subtarefa, CHAVES_RESPONSAVEL),
                )
            )

        return subtarefas

    def _erro_dados_invalidos(
        self,
        nome_sprint: str,
        mensagem: str,
        motivo: str,
        caminho: str | Path,
    ) -> DadosSprintInvalidosError:
        """Cria e registra erro de dados inválidos."""
        erro = DadosSprintInvalidosError(
            mensagem,
            nome_sprint=nome_sprint,
            motivo=motivo,
            caminho=str(caminho),
        )
        self._registrar_erro("dados_sprint_invalidos", erro)
        return erro

    @staticmethod
    def _normalizar_nome_sprint(nome_sprint: str) -> str:
        """Normaliza o identificador da sprint evitando path traversal."""
        nome = nome_sprint.strip()
        if nome.endswith(".json"):
            nome = nome[:-5]

        if not nome or Path(nome).name != nome or "/" in nome or "\\" in nome:
            raise NomeSprintInvalidoError(nome_sprint)

        return nome

    @staticmethod
    def _primeiro_texto(dados: JsonObjeto, chaves: tuple[str, ...]) -> str | None:
        """Extrai o primeiro campo textual não vazio dentre as chaves conhecidas."""
        for chave in chaves:
            valor = dados.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
        return None

    def _registrar_erro(
        self,
        evento: str,
        erro: Exception,
        **metadados: Any,
    ) -> None:
        """Registra erro de forma estruturada em JSON."""
        if hasattr(erro, "detalhes"):
            metadados.update(getattr(erro, "detalhes"))

        self._registrar_log(
            logging.ERROR,
            evento,
            erro=erro.__class__.__name__,
            mensagem=str(erro),
            **metadados,
        )

    @staticmethod
    def _registrar_log(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra evento estruturado como JSON."""
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
