"""Testes de chunking e indexação vetorial sem ChromaDB real."""

import json
import unittest
from pathlib import Path

from app.domain.rag import DocumentoVetorial
from app.integrations.openai_client import EmbeddingGerado
from app.integrations.vector_store import BancoVetorialFake
from app.services.chunking_service import ServicoChunkingSprint
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.sprint_loader import CarregadorSprints

CAMINHO_FIXTURES = Path(__file__).parent / "fixtures"
CAMINHO_SPRINTS_VALIDAS = CAMINHO_FIXTURES / "sprints_validas"


class ProvedorEmbeddingsFake:
    """Fake de embeddings que registra os textos recebidos."""

    def __init__(self) -> None:
        """Inicializa fake sem chamadas externas."""
        self.textos: list[str] = []

    def gerar_embedding(self, texto: str) -> EmbeddingGerado:
        """Retorna embedding determinístico para o texto informado."""
        self.textos.append(texto)
        indice = float(len(self.textos))
        return EmbeddingGerado(
            vetor=[indice, 1.0],
            modelo="modelo-embedding-teste",
            request_id=f"req-{int(indice)}",
        )


def criar_servico_indexacao(
    banco_vetorial: BancoVetorialFake,
    provedor_embeddings: ProvedorEmbeddingsFake,
) -> ServicoIndexacaoVetorial:
    """Cria serviço de indexação com dependências fake."""
    return ServicoIndexacaoVetorial(
        carregador_sprints=CarregadorSprints(CAMINHO_SPRINTS_VALIDAS),
        servico_chunking=ServicoChunkingSprint(tamanho_maximo_fragmento=3000),
        provedor_embeddings=provedor_embeddings,
        banco_vetorial=banco_vetorial,
    )


class ChunkingIndexacaoVetorialTestCase(unittest.TestCase):
    """Cobre chunking, indexação e fake vetorial."""

    def test_chunking_preserva_metadados_de_tarefa_e_subtarefa(self) -> None:
        """Gera fragmentos rastreáveis por sprint, origem, tipo e caminho."""
        sprint = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS).carregar_sprint("sprint-75")
        servico = ServicoChunkingSprint(tamanho_maximo_fragmento=3000)

        fragmentos = servico.fragmentar_sprint(sprint)

        self.assertEqual(len(fragmentos), 3)

        tarefa_login = next(
            fragmento
            for fragmento in fragmentos
            if fragmento.tipo == "tarefa" and fragmento.caminho == "tarefas[0]"
        )
        self.assertEqual(tarefa_login.sprint, "sprint-75")
        self.assertEqual(tarefa_login.origem, "sprint-75.json")
        self.assertEqual(tarefa_login.metadados["sprint"], "sprint-75")
        self.assertEqual(tarefa_login.metadados["origem"], "sprint-75.json")
        self.assertEqual(tarefa_login.metadados["tipo"], "tarefa")
        self.assertEqual(tarefa_login.metadados["caminho"], "tarefas[0]")
        self.assertEqual(tarefa_login.metadados["titulo_tarefa"], "Criar login")
        self.assertEqual(tarefa_login.metadados["status"], "Em desenvolvimento")
        self.assertIn("Tarefa: Criar login", tarefa_login.conteudo)
        self.assertIn("Subtarefas:", tarefa_login.conteudo)

        subtarefa = next(fragmento for fragmento in fragmentos if fragmento.tipo == "subtarefa")
        self.assertEqual(subtarefa.metadados["titulo_tarefa"], "Criar login")
        self.assertEqual(subtarefa.metadados["titulo_subtarefa"], "Criar schema de autenticação")
        self.assertEqual(subtarefa.metadados["caminho"], "tarefas[0].subtarefas[0]")
        self.assertIn("Subtarefa: Criar schema de autenticação", subtarefa.conteudo)

    def test_chunking_aceita_tarefa_sem_subtarefa(self) -> None:
        """Tarefa sem subtarefas gera fragmento válido sem campos artificiais."""
        sprint = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS).carregar_sprint(
            "sprint-subtarefa-vazia"
        )
        servico = ServicoChunkingSprint(tamanho_maximo_fragmento=3000)

        fragmentos = servico.fragmentar_sprint(sprint)

        self.assertEqual(len(fragmentos), 1)
        self.assertEqual(fragmentos[0].tipo, "tarefa")
        self.assertEqual(fragmentos[0].metadados["sprint"], "sprint-subtarefa-vazia")
        self.assertIn("Subtarefas: nenhuma", fragmentos[0].conteudo)

    def test_fragmentos_nao_misturam_sprints_diferentes(self) -> None:
        """Fragmentos de múltiplas sprints mantêm metadados de origem isolados."""
        carregador = CarregadorSprints(CAMINHO_SPRINTS_VALIDAS)
        sprints = [
            carregador.carregar_sprint("sprint-75"),
            carregador.carregar_sprint("sprint-76"),
        ]
        servico = ServicoChunkingSprint(tamanho_maximo_fragmento=120)

        fragmentos = servico.fragmentar_sprints(sprints)

        self.assertTrue(fragmentos)
        for fragmento in fragmentos:
            self.assertIn(f"Sprint: {fragmento.sprint}", fragmento.conteudo)
            self.assertEqual(fragmento.metadados["sprint"], fragmento.sprint)
            self.assertLessEqual(len(fragmento.conteudo), 120)

    def test_indexacao_chama_embeddings_com_textos_esperados(self) -> None:
        """Indexação usa fragmentos normalizados para gerar embeddings."""
        banco_vetorial = BancoVetorialFake()
        provedor_embeddings = ProvedorEmbeddingsFake()
        servico = criar_servico_indexacao(banco_vetorial, provedor_embeddings)

        with self.assertLogs("app.services.indexacao_vetorial", level="INFO") as logs:
            resultado = servico.indexar_sprints(["sprint-75"])

        self.assertEqual(resultado.sprints, ["sprint-75"])
        self.assertEqual(resultado.quantidade_fragmentos, 3)
        self.assertEqual(resultado.modelo_embedding, "modelo-embedding-teste")
        self.assertEqual(len(resultado.assinatura), 64)
        self.assertEqual(len(provedor_embeddings.textos), 3)
        self.assertIn("Tarefa: Criar login", provedor_embeddings.textos[0])
        self.assertTrue(any("Tarefa: Ajustar permissões" in texto for texto in provedor_embeddings.textos))
        self.assertEqual(len(banco_vetorial.documentos), 3)
        self.assertEqual(banco_vetorial.sprints_removidas, [["sprint-75"]])

        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "indexacao_vetorial_concluida")
        self.assertEqual(evento["metadata"]["quantidade_fragmentos"], 3)

    def test_reindexacao_parcial_substitui_dados_antigos_da_sprint(self) -> None:
        """Indexação parcial remove fragmentos antigos apenas das sprints afetadas."""
        banco_vetorial = BancoVetorialFake()
        banco_vetorial.adicionar_documentos(
            [
                DocumentoVetorial(
                    id="sprint-75-antigo",
                    texto="fragmento obsoleto",
                    embedding=[0.0, 1.0],
                    metadados={"sprint": "sprint-75", "tipo": "tarefa"},
                ),
                DocumentoVetorial(
                    id="sprint-76-existente",
                    texto="fragmento mantido",
                    embedding=[1.0, 0.0],
                    metadados={"sprint": "sprint-76", "tipo": "tarefa"},
                ),
            ]
        )
        provedor_embeddings = ProvedorEmbeddingsFake()
        servico = criar_servico_indexacao(banco_vetorial, provedor_embeddings)

        servico.indexar_sprints(["sprint-75"])

        self.assertNotIn("sprint-75-antigo", banco_vetorial.documentos)
        self.assertIn("sprint-76-existente", banco_vetorial.documentos)
        self.assertEqual(banco_vetorial.sprints_removidas[-1], ["sprint-75"])

    def test_reindexacao_total_limpa_indice_antes_de_recriar(self) -> None:
        """Reindexação completa remove documentos antigos antes da nova carga."""
        banco_vetorial = BancoVetorialFake()
        banco_vetorial.adicionar_documentos(
            [
                DocumentoVetorial(
                    id="antigo",
                    texto="fragmento antigo",
                    embedding=[0.0, 1.0],
                    metadados={"sprint": "sprint-antiga", "tipo": "tarefa"},
                )
            ]
        )
        servico = criar_servico_indexacao(banco_vetorial, ProvedorEmbeddingsFake())

        resultado = servico.reindexar_tudo()

        self.assertEqual(banco_vetorial.quantidade_limpezas, 1)
        self.assertNotIn("antigo", banco_vetorial.documentos)
        self.assertEqual(resultado.sprints[0], "sprint-75")
        self.assertGreater(resultado.quantidade_fragmentos, 0)

    def test_fake_vetorial_permite_busca_sem_servico_real(self) -> None:
        """Fake vetorial filtra por sprint e ordena por similaridade."""
        banco_vetorial = BancoVetorialFake()
        banco_vetorial.adicionar_documentos(
            [
                DocumentoVetorial(
                    id="doc-a",
                    texto="permissões",
                    embedding=[1.0, 0.0],
                    metadados={"sprint": "sprint-75", "tipo": "tarefa"},
                ),
                DocumentoVetorial(
                    id="doc-b",
                    texto="login",
                    embedding=[0.0, 1.0],
                    metadados={"sprint": "sprint-75", "tipo": "tarefa"},
                ),
                DocumentoVetorial(
                    id="doc-c",
                    texto="fora do escopo",
                    embedding=[1.0, 0.0],
                    metadados={"sprint": "sprint-76", "tipo": "tarefa"},
                ),
            ]
        )

        resultados = banco_vetorial.buscar([1.0, 0.0], sprints=["sprint-75"], rank=1)

        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].id, "doc-a")
        self.assertEqual(resultados[0].metadados["sprint"], "sprint-75")


if __name__ == "__main__":
    unittest.main()
