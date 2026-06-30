"""Testes da rota de resumos com LLM fake."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Configuracoes
from app.infrastructure.dependencies import obter_cliente_openai
from app.integrations.openai_client import RespostaLLM
from app.main import criar_app
from app.services.resumo_service import RESPOSTA_CONTEXTO_INSUFICIENTE

CAMINHO_FIXTURES = Path(__file__).parent / "fixtures"
CAMINHO_SPRINTS_VALIDAS = CAMINHO_FIXTURES / "sprints_validas"
TOKEN_TESTE = "valor-ficticio-sem-uso-real"


class ProvedorLLMFake:
    """Fake de LLM que registra prompt separado por campos."""

    def __init__(self, resposta: str = "Resposta objetiva baseada nos dados.") -> None:
        """Inicializa fake com resposta controlada."""
        self.resposta = resposta
        self.chamadas: list[dict[str, str]] = []

    def gerar_resposta(
        self,
        *,
        instrucoes_sistema: str,
        contexto: str,
        pergunta: str,
    ) -> RespostaLLM:
        """Registra chamada e retorna resposta fake."""
        self.chamadas.append(
            {
                "instrucoes_sistema": instrucoes_sistema,
                "contexto": contexto,
                "pergunta": pergunta,
            }
        )
        return RespostaLLM(texto=self.resposta, modelo="modelo-llm-teste")


def headers_autenticados() -> dict[str, str]:
    """Retorna header Bearer com token fictício."""
    return {"Authorization": f"Bearer {TOKEN_TESTE}"}


def criar_cliente_com_llm_fake(
    *,
    provedor_llm: ProvedorLLMFake | None = None,
    data_dir: Path = CAMINHO_SPRINTS_VALIDAS,
    max_message_length: int = 4000,
    max_sprints_per_request: int = 20,
) -> tuple[TestClient, ProvedorLLMFake]:
    """Cria cliente HTTP com LLM fake e dados controlados."""
    provedor = provedor_llm or ProvedorLLMFake()
    app = criar_app(
        Configuracoes(
            app_env="test",
            auth_enabled=True,
            auth_token=TOKEN_TESTE,
            data_dir=data_dir,
            max_message_length=max_message_length,
            max_sprints_per_request=max_sprints_per_request,
        )
    )
    app.dependency_overrides[obter_cliente_openai] = lambda: provedor
    return TestClient(app), provedor


class RotaResumosTestCase(unittest.TestCase):
    """Cobre contrato HTTP da rota `/v1/resumos`."""

    def test_pergunta_valida_gera_resposta_via_mock(self) -> None:
        """Consulta válida carrega contexto, chama LLM fake e retorna fontes."""
        cliente, provedor = criar_cliente_com_llm_fake()

        with self.assertLogs("app.services.resumo_service", level="INFO") as logs:
            resposta = cliente.post(
                "/v1/resumos",
                json={
                    "pergunta": "Como está o andamento da sprint 75?",
                    "sprints": ["sprint-75"],
                },
                headers=headers_autenticados(),
            )

        corpo = resposta.json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(corpo["resposta"], "Resposta objetiva baseada nos dados.")
        self.assertEqual(corpo["sprints_consultadas"], ["sprint-75"])
        self.assertTrue(any(fonte["titulo"] == "Criar login" for fonte in corpo["fontes"]))
        self.assertEqual(len(provedor.chamadas), 1)
        self.assertIn("Não invente tarefas", provedor.chamadas[0]["instrucoes_sistema"])
        self.assertIn("Criar login", provedor.chamadas[0]["contexto"])
        self.assertEqual(provedor.chamadas[0]["pergunta"], "Como está o andamento da sprint 75?")

        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "resumo_consulta_executada")
        self.assertEqual(evento["metadata"]["quantidade_sprints"], 1)

    def test_identifica_sprint_citada_na_pergunta_quando_escopo_nao_vem_no_payload(self) -> None:
        """Pergunta sem `sprints` usa menção textual para definir escopo."""
        cliente, provedor = criar_cliente_com_llm_fake()

        resposta = cliente.post(
            "/v1/resumos",
            json={
                "pergunta": "Como está a Sprint 76?",
                "sprints": [],
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["sprints_consultadas"], ["sprint-76"])
        self.assertIn("Criar consulta de permissões", provedor.chamadas[0]["contexto"])

    def test_pergunta_vazia_retorna_erro_422(self) -> None:
        """Validação rejeita pergunta vazia após trim."""
        cliente, _ = criar_cliente_com_llm_fake()

        resposta = cliente.post(
            "/v1/resumos",
            json={"pergunta": "   ", "sprints": ["sprint-75"]},
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)

    def test_pergunta_grande_demais_retorna_erro_422(self) -> None:
        """Validação respeita limite configurável de pergunta."""
        cliente, provedor = criar_cliente_com_llm_fake(max_message_length=10)

        resposta = cliente.post(
            "/v1/resumos",
            json={"pergunta": "pergunta maior que limite", "sprints": ["sprint-75"]},
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json()["detail"], "Pergunta excede o limite configurado.")
        self.assertEqual(provedor.chamadas, [])

    def test_sprint_inexistente_retorna_erro_404(self) -> None:
        """Rejeita sprint fora dos arquivos disponíveis."""
        cliente, provedor = criar_cliente_com_llm_fake()

        resposta = cliente.post(
            "/v1/resumos",
            json={"pergunta": "Como está a sprint?", "sprints": ["sprint-999"]},
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json()["detail"], "Sprint não encontrada.")
        self.assertEqual(provedor.chamadas, [])

    def test_contexto_insuficiente_retorna_mensagem_explicita(self) -> None:
        """Sem sprints disponíveis, a rota responde sem chamar o LLM."""
        with tempfile.TemporaryDirectory() as diretorio_temporario:
            cliente, provedor = criar_cliente_com_llm_fake(data_dir=Path(diretorio_temporario))

            resposta = cliente.post(
                "/v1/resumos",
                json={"pergunta": "Como está o andamento?", "sprints": []},
                headers=headers_autenticados(),
            )

        corpo = resposta.json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(corpo["resposta"], RESPOSTA_CONTEXTO_INSUFICIENTE)
        self.assertEqual(corpo["sprints_consultadas"], [])
        self.assertEqual(corpo["fontes"], [])
        self.assertEqual(provedor.chamadas, [])

    def test_prompt_separa_instrucoes_contexto_e_pergunta(self) -> None:
        """Serviço envia instruções, contexto e pergunta como campos separados."""
        cliente, provedor = criar_cliente_com_llm_fake()

        resposta = cliente.post(
            "/v1/resumos",
            json={
                "pergunta": "Quais tarefas estão pendentes?",
                "sprints": ["Sprint 75"],
            },
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 200)
        chamada = provedor.chamadas[0]
        self.assertIn("consultora Scrum", chamada["instrucoes_sistema"])
        self.assertIn("Sprint: sprint-75", chamada["contexto"])
        self.assertEqual(chamada["pergunta"], "Quais tarefas estão pendentes?")

    def test_rota_exige_autenticacao(self) -> None:
        """Rota de resumos permanece protegida por Bearer token."""
        cliente, _ = criar_cliente_com_llm_fake()

        resposta = cliente.post(
            "/v1/resumos",
            json={"pergunta": "Como está a sprint 75?", "sprints": ["sprint-75"]},
        )

        self.assertEqual(resposta.status_code, 401)

    def test_contrato_aparece_no_openapi(self) -> None:
        """Swagger/OpenAPI expõe contrato de request e response."""
        cliente, _ = criar_cliente_com_llm_fake()

        openapi = cliente.app.openapi()
        contrato = openapi["paths"]["/v1/resumos"]["post"]

        self.assertIn("200", contrato["responses"])
        self.assertEqual(
            contrato["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ResumoResponse",
        )


if __name__ == "__main__":
    unittest.main()
