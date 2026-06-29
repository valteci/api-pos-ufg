"""Testes do carregamento e validação de arquivos JSON de sprints."""

import json
import unittest
from pathlib import Path

from app.domain.exceptions import (
    DadosSprintInvalidosError,
    DiretorioDadosNaoEncontradoError,
    SprintNaoEncontradaError,
)
from app.services.sprint_loader import CarregadorSprints

CAMINHO_FIXTURES = Path(__file__).parent / "fixtures"
CAMINHO_SPRINTS_VALIDAS = CAMINHO_FIXTURES / "sprints_validas"
CAMINHO_SPRINTS_INVALIDAS = CAMINHO_FIXTURES / "sprints_invalidas"


class CarregamentoSprintsTestCase(unittest.TestCase):
    """Cobre leitura, validação e normalização de sprints."""

    def test_lista_sprints_disponiveis_ignorando_arquivos_nao_json(self) -> None:
        """Lista apenas arquivos `.json` e usa o nome do arquivo como sprint."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprints = carregador.listar_sprints()

        self.assertEqual(
            sprints,
            [
                "sprint-75",
                "sprint-76",
                "sprint-campos-extras",
                "sprint-subtarefa-vazia",
            ],
        )

    def test_carrega_sprint_valida_com_tarefas_e_subtarefas(self) -> None:
        """Normaliza sprint válida preservando tarefas, subtarefas e origem."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprint = carregador.carregar_sprint("sprint-75")

        self.assertEqual(sprint.identificador, "sprint-75")
        self.assertEqual(sprint.arquivo_origem.name, "sprint-75.json")
        self.assertEqual(len(sprint.tarefas), 2)
        self.assertEqual(sprint.quantidade_subtarefas, 1)
        self.assertEqual(sprint.tarefas[0].titulo, "Criar login")
        self.assertEqual(sprint.tarefas[0].responsavel, "Ana")
        self.assertEqual(sprint.tarefas[0].subtarefas[0].titulo, "Criar schema de autenticação")
        self.assertEqual(sprint.tarefas[1].subtarefas, [])

    def test_carrega_todas_as_sprints_validas(self) -> None:
        """Carrega todas as sprints disponíveis em um diretório válido."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprints = carregador.carregar_todas_sprints()

        self.assertEqual(len(sprints), 4)
        self.assertEqual([sprint.identificador for sprint in sprints][0], "sprint-75")

    def test_carrega_sprint_com_campos_em_ingles(self) -> None:
        """Aceita exportações com chaves técnicas comuns em inglês."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprint = carregador.carregar_sprint("sprint-76.json")

        self.assertEqual(sprint.identificador, "sprint-76")
        self.assertEqual(sprint.tarefas[0].titulo, "Criar consulta de permissões")
        self.assertEqual(sprint.tarefas[0].status, "Em revisão")
        self.assertEqual(sprint.tarefas[0].responsavel, "Carla")
        self.assertEqual(sprint.tarefas[0].subtarefas[0].status, "Concluída")

    def test_preserva_campos_extras_sem_quebrar_normalizacao(self) -> None:
        """Mantém dados originais e campos extras para uso posterior em RAG."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprint = carregador.carregar_sprint("sprint-campos-extras")

        self.assertEqual(sprint.dados_originais["metadados_exportacao"]["ferramenta"], "jira")
        self.assertEqual(sprint.tarefas[0].dados["campo_extra_tarefa"], {"valor": 10})
        self.assertEqual(sprint.tarefas[0].subtarefas, [])

    def test_aceita_subtarefas_ausentes_nulas_ou_vazias(self) -> None:
        """Tarefas válidas não dependem da existência de subtarefas."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        sprint_sem_campo = carregador.carregar_sprint("sprint-75")
        sprint_nula = carregador.carregar_sprint("sprint-campos-extras")
        sprint_vazia = carregador.carregar_sprint("sprint-subtarefa-vazia")

        self.assertEqual(sprint_sem_campo.tarefas[1].subtarefas, [])
        self.assertEqual(sprint_nula.tarefas[0].subtarefas, [])
        self.assertEqual(sprint_vazia.tarefas[0].subtarefas, [])

    def test_rejeita_sprint_inexistente(self) -> None:
        """Retorna erro de domínio para arquivo inexistente."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)

        with self.assertLogs("app.services.sprint_loader", level="ERROR"):
            with self.assertRaises(SprintNaoEncontradaError):
                carregador.carregar_sprint("sprint-999")

    def test_rejeita_json_invalido(self) -> None:
        """Retorna erro de domínio para JSON malformado."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_INVALIDAS)

        with self.assertLogs("app.services.sprint_loader", level="ERROR"):
            with self.assertRaises(DadosSprintInvalidosError):
                carregador.carregar_sprint("json-invalido")

    def test_rejeita_sprint_vazia(self) -> None:
        """Retorna erro de domínio quando falta conteúdo mínimo."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_INVALIDAS)

        with self.assertLogs("app.services.sprint_loader", level="ERROR"):
            with self.assertRaises(DadosSprintInvalidosError):
                carregador.carregar_sprint("sprint-vazia")

    def test_rejeita_diretorio_inexistente(self) -> None:
        """Retorna erro de domínio quando o diretório de dados não existe."""
        carregador = CarregadorSprints(CAMINHO_FIXTURES / "nao-existe")

        with self.assertLogs("app.services.sprint_loader", level="ERROR"):
            with self.assertRaises(DiretorioDadosNaoEncontradoError):
                carregador.listar_sprints()

    def test_registra_falhas_em_json_estruturado(self) -> None:
        """Garante que falhas relevantes geram logs JSON."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_INVALIDAS)

        with self.assertLogs("app.services.sprint_loader", level="ERROR") as logs:
            with self.assertRaises(DadosSprintInvalidosError):
                carregador.carregar_sprint("json-invalido")

        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "json_sprint_invalido")
        self.assertEqual(evento["metadata"]["motivo"], "json_invalido")


if __name__ == "__main__":
    unittest.main()
