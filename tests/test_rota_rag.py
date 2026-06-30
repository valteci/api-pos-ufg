"""Testes da rota de RAG com integrações fake."""

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Configuracoes
from app.domain.rag import DocumentoVetorial
from app.integrations.openai_client import EmbeddingGerado
from app.integrations.vector_store import BancoVetorialFake
from app.infrastructure.dependencies import obter_banco_vetorial, obter_cliente_openai
from app.main import criar_app

CAMINHO_FIXTURES = Path(__file__).parent / "fixtures"
CAMINHO_SPRINTS_VALIDAS = CAMINHO_FIXTURES / "sprints_validas"
TOKEN_TESTE = "valor-ficticio-sem-uso-real"


class ProvedorEmbeddingsRagFake:
    """Fake de embeddings usado pelos testes da rota RAG."""

    def __init__(self) -> None:
        """Inicializa fake registrando textos consultados."""
        self.textos: list[str] = []

    def gerar_embedding(self, texto: str) -> EmbeddingGerado:
        """Retorna vetor determinístico sem chamada externa."""
        self.textos.append(texto)
        if "permiss" in texto.lower():
            vetor = [1.0, 0.0]
        else:
            vetor = [0.0, 1.0]
        return EmbeddingGerado(vetor=vetor, modelo="modelo-embedding-teste")


class BancoVetorialRagFake(BancoVetorialFake):
    """Fake vetorial que registra parâmetros da última busca."""

    def __init__(self) -> None:
        """Inicializa fake com histórico de buscas."""
        super().__init__()
        self.buscas: list[dict[str, object]] = []

    def buscar(
        self,
        embedding: list[float],
        *,
        sprints: list[str],
        rank: int,
    ):
        """Registra filtro antes de delegar para busca em memória."""
        self.buscas.append({"embedding": embedding, "sprints": list(sprints), "rank": rank})
        return super().buscar(embedding, sprints=sprints, rank=rank)


def headers_autenticados() -> dict[str, str]:
    """Retorna header Bearer com token fictício."""
    return {"Authorization": f"Bearer {TOKEN_TESTE}"}


def criar_cliente_com_fakes(
    *,
    banco_vetorial: BancoVetorialRagFake | None = None,
    provedor_embeddings: ProvedorEmbeddingsRagFake | None = None,
    max_rag_rank: int = 10,
    max_fragment_size: int = 3000,
    max_sprints_per_request: int = 20,
) -> tuple[TestClient, BancoVetorialRagFake, ProvedorEmbeddingsRagFake]:
    """Cria cliente HTTP com OpenAI e banco vetorial fake."""
    banco = banco_vetorial or BancoVetorialRagFake()
    provedor = provedor_embeddings or ProvedorEmbeddingsRagFake()
    app = criar_app(
        Configuracoes(
            app_env="test",
            auth_enabled=True,
            auth_token=TOKEN_TESTE,
            data_dir=CAMINHO_SPRINTS_VALIDAS,
            max_rag_rank=max_rag_rank,
            max_fragment_size=max_fragment_size,
            max_sprints_per_request=max_sprints_per_request,
        )
    )
    app.dependency_overrides[obter_cliente_openai] = lambda: provedor
    app.dependency_overrides[obter_banco_vetorial] = lambda: banco
    return TestClient(app), banco, provedor


def popular_banco_vetorial(banco: BancoVetorialRagFake) -> None:
    """Adiciona documentos fake para consultas RAG."""
    banco.adicionar_documentos(
        [
            DocumentoVetorial(
                id="frag-permissoes",
                texto="funcionalidade de permissões com conteúdo detalhado",
                embedding=[1.0, 0.0],
                metadados={
                    "sprint": "sprint-75",
                    "origem": "sprint-75.json",
                    "tipo": "tarefa",
                    "caminho": "tarefas[1]",
                },
            ),
            DocumentoVetorial(
                id="frag-login",
                texto="fluxo de login e autenticação",
                embedding=[0.0, 1.0],
                metadados={
                    "sprint": "sprint-75",
                    "origem": "sprint-75.json",
                    "tipo": "tarefa",
                    "caminho": "tarefas[0]",
                },
            ),
            DocumentoVetorial(
                id="frag-sprint-76",
                texto="consulta de permissões da sprint seguinte",
                embedding=[1.0, 0.0],
                metadados={
                    "sprint": "sprint-76",
                    "origem": "sprint-76.json",
                    "tipo": "tarefa",
                    "caminho": "tasks[0]",
                },
            ),
        ]
    )


class RotaRagTestCase(unittest.TestCase):
    """Cobre contrato HTTP da rota `/v1/rag`."""

    def test_payload_valido_retorna_fragmentos_com_limite_de_tamanho(self) -> None:
        """Consulta válida retorna até `rank` fragmentos com metadados."""
        banco = BancoVetorialRagFake()
        popular_banco_vetorial(banco)
        cliente, _, provedor = criar_cliente_com_fakes(banco_vetorial=banco)

        with self.assertLogs("app.services.rag_service", level="INFO") as logs:
            resposta = cliente.post(
                "/v1/rag",
                json={
                    "sprints": ["sprint-75"],
                    "mensagem": "permissões",
                    "rank": 1,
                    "tamanho_fragmento": 20,
                },
                headers=headers_autenticados(),
            )

        corpo = resposta.json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(corpo["mensagem"], "permissões")
        self.assertEqual(corpo["sprints_consultadas"], ["sprint-75"])
        self.assertEqual(corpo["rank"], 1)
        self.assertEqual(corpo["tamanho_fragmento"], 20)
        self.assertEqual(len(corpo["fragmentos"]), 1)
        self.assertEqual(corpo["fragmentos"][0]["sprint"], "sprint-75")
        self.assertEqual(corpo["fragmentos"][0]["origem"], "sprint-75.json")
        self.assertEqual(corpo["fragmentos"][0]["metadados"]["tipo"], "tarefa")
        self.assertLessEqual(len(corpo["fragmentos"][0]["conteudo"]), 20)
        self.assertEqual(provedor.textos, ["permissões"])
        self.assertEqual(banco.buscas[-1]["sprints"], ["sprint-75"])
        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "consulta_rag_executada")
        self.assertEqual(evento["metadata"]["quantidade_fragmentos"], 1)

    def test_lista_vazia_consulta_todas_as_sprints_disponiveis(self) -> None:
        """Lista vazia resolve todas as sprints presentes em `data/`."""
        banco = BancoVetorialRagFake()
        popular_banco_vetorial(banco)
        cliente, _, _ = criar_cliente_com_fakes(banco_vetorial=banco)

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": [],
                "mensagem": "permissões",
                "rank": 2,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            banco.buscas[-1]["sprints"],
            [
                "sprint-75",
                "sprint-76",
                "sprint-campos-extras",
                "sprint-subtarefa-vazia",
            ],
        )
        self.assertEqual(len(resposta.json()["fragmentos"]), 2)

    def test_lista_preenchida_consulta_apenas_sprints_pedidas(self) -> None:
        """Filtro de sprint é enviado ao banco vetorial antes da resposta."""
        banco = BancoVetorialRagFake()
        popular_banco_vetorial(banco)
        cliente, _, _ = criar_cliente_com_fakes(banco_vetorial=banco)

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-76"],
                "mensagem": "permissões",
                "rank": 3,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        corpo = resposta.json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(banco.buscas[-1]["sprints"], ["sprint-76"])
        self.assertEqual(len(corpo["fragmentos"]), 1)
        self.assertEqual(corpo["fragmentos"][0]["sprint"], "sprint-76")

    def test_sprint_inexistente_retorna_erro_404(self) -> None:
        """Rejeita sprint fora dos arquivos disponíveis em `data/`."""
        cliente, banco, provedor = criar_cliente_com_fakes()

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-999"],
                "mensagem": "permissões",
                "rank": 1,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json()["detail"], "Sprint não encontrada.")
        self.assertEqual(banco.buscas, [])
        self.assertEqual(provedor.textos, [])

    def test_rank_invalido_retorna_erro_422(self) -> None:
        """Validação rejeita rank nulo ou negativo."""
        cliente, _, _ = criar_cliente_com_fakes()

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-75"],
                "mensagem": "permissões",
                "rank": 0,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)

    def test_rank_acima_do_limite_configurado_retorna_erro_422(self) -> None:
        """Validação respeita limite configurado por ambiente."""
        cliente, _, _ = criar_cliente_com_fakes(max_rag_rank=1)

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-75"],
                "mensagem": "permissões",
                "rank": 2,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["detail"], "Rank excede o limite configurado.")

    def test_tamanho_fragmento_invalido_retorna_erro_422(self) -> None:
        """Validação rejeita tamanho de fragmento inválido."""
        cliente, _, _ = criar_cliente_com_fakes()

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-75"],
                "mensagem": "permissões",
                "rank": 1,
                "tamanho_fragmento": 0,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)

    def test_mensagem_vazia_retorna_erro_422(self) -> None:
        """Validação rejeita mensagem vazia após trim."""
        cliente, _, _ = criar_cliente_com_fakes()

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-75"],
                "mensagem": "   ",
                "rank": 1,
                "tamanho_fragmento": 1000,
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)

    def test_rota_exige_autenticacao(self) -> None:
        """Rota de RAG permanece protegida por Bearer token."""
        cliente, _, _ = criar_cliente_com_fakes()

        resposta = cliente.post(
            "/v1/rag",
            json={
                "sprints": ["sprint-75"],
                "mensagem": "permissões",
                "rank": 1,
                "tamanho_fragmento": 1000,
            },
        )

        self.assertEqual(resposta.status_code, 401)

    def test_contrato_aparece_no_openapi(self) -> None:
        """Swagger/OpenAPI expõe contrato de request e response."""
        cliente, _, _ = criar_cliente_com_fakes()

        openapi = cliente.app.openapi()
        contrato = openapi["paths"]["/v1/rag"]["post"]

        self.assertIn("200", contrato["responses"])
        self.assertEqual(
            contrato["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/RagResponse",
        )


if __name__ == "__main__":
    unittest.main()
