"""Testes de autenticação e segurança base da API."""

import json
import unittest

from fastapi.testclient import TestClient

from app.core.config import Configuracoes
from app.infrastructure.dependencies import obter_limitador_requisicoes
from app.integrations.redis_client import RedisFake
from app.main import criar_app
from app.services.rate_limit_service import LimitadorRequisicoes

VALOR_AUTORIZACAO_TESTE = "valor-ficticio-sem-uso-real"
VALOR_INVALIDO_TESTE = "valor-invalido-sem-uso-real"

PAYLOAD_RAG = {
    "sprints": ["Sprint 75"],
    "mensagem": "funcionalidade de permissão de usuários no sistema",
    "rank": 3,
    "tamanho_fragmento": 1000,
}

PAYLOAD_RESUMO = {
    "pergunta": "Como está o andamento da Sprint 75?",
    "sprints": ["Sprint 75"],
}


def criar_cliente(
    *,
    app_env: str = "test",
    auth_enabled: bool = True,
    max_payload_bytes: int = 1_048_576,
) -> TestClient:
    """Cria cliente HTTP com configurações isoladas para testes."""
    app = criar_app(
        Configuracoes(
            app_env=app_env,
            auth_enabled=auth_enabled,
            auth_token=VALOR_AUTORIZACAO_TESTE,
            cors_allowed_origins=("http://cliente.local",),
            max_payload_bytes=max_payload_bytes,
            cache_enabled=False,
            rate_limit_enabled=False,
        )
    )
    return TestClient(app)


def headers_autenticados() -> dict[str, str]:
    """Retorna header Bearer com valor fictício de teste."""
    return {"Authorization": f"Bearer {VALOR_AUTORIZACAO_TESTE}"}


class AutenticacaoSegurancaTestCase(unittest.TestCase):
    """Cobre a segurança mínima exigida para rotas de negócio."""

    def test_healthcheck_sem_token_retorna_sucesso(self) -> None:
        """Garante que a rota de saúde permanece pública."""
        cliente = criar_cliente()

        resposta = cliente.get("/health")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})

    def test_rag_sem_token_retorna_erro(self) -> None:
        """Bloqueia rota de RAG quando o Bearer token não é enviado."""
        cliente = criar_cliente()

        resposta = cliente.post("/v1/rag", json=PAYLOAD_RAG)

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["detail"], "Token de autenticação ausente.")

    def test_resumos_sem_token_retorna_erro(self) -> None:
        """Bloqueia rota de resumos quando o Bearer token não é enviado."""
        cliente = criar_cliente()

        resposta = cliente.post("/v1/resumos", json=PAYLOAD_RESUMO)

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["detail"], "Token de autenticação ausente.")

    def test_token_invalido_retorna_erro_sem_expor_credencial(self) -> None:
        """Bloqueia token inválido sem registrar ou responder o valor recebido."""
        cliente = criar_cliente()

        with self.assertLogs("app.core.security", level="WARNING") as logs:
            resposta = cliente.post(
                "/v1/rag",
                json=PAYLOAD_RAG,
                headers={"Authorization": f"Bearer {VALOR_INVALIDO_TESTE}"},
            )

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["detail"], "Token de autenticação inválido.")
        self.assertNotIn(VALOR_INVALIDO_TESTE, resposta.text)
        self.assertNotIn(VALOR_INVALIDO_TESTE, logs.output[-1])

        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "autenticacao_token_invalido")

    def test_token_valido_permite_alcancar_rota_protegida(self) -> None:
        """Permite chegar à rota protegida quando o Bearer token é válido."""
        cliente = criar_cliente()
        payload_sprint_inexistente = {**PAYLOAD_RAG, "sprints": ["sprint-inexistente"]}

        resposta = cliente.post(
            "/v1/rag",
            json=payload_sprint_inexistente,
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            resposta.json()["detail"],
            "Sprint não encontrada.",
        )

    def test_auth_disabled_nao_desativa_autenticacao_em_producao(self) -> None:
        """Impede bypass de autenticação em ambiente produtivo."""
        cliente = criar_cliente(app_env="production", auth_enabled=False)

        resposta = cliente.post("/v1/resumos", json=PAYLOAD_RESUMO)

        self.assertEqual(resposta.status_code, 401)

    def test_cors_permite_apenas_origem_configurada(self) -> None:
        """Valida que CORS usa a lista configurada por ambiente."""
        cliente = criar_cliente()

        resposta = cliente.options(
            "/v1/rag",
            headers={
                "Origin": "http://cliente.local",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.headers["access-control-allow-origin"],
            "http://cliente.local",
        )

    def test_payload_acima_do_limite_retorna_erro(self) -> None:
        """Rejeita requisições com payload maior que o limite configurado."""
        cliente = criar_cliente(max_payload_bytes=16)

        resposta = cliente.post(
            "/v1/rag",
            json=PAYLOAD_RAG,
            headers=headers_autenticados(),
        )

        self.assertEqual(resposta.status_code, 413)
        self.assertIn("Payload excede o limite configurado", resposta.json()["detail"])

    def test_rate_limit_bloqueia_excesso_de_requisicoes_autenticadas(self) -> None:
        """Bloqueia excesso de requisições por token autenticado."""
        app = criar_app(
            Configuracoes(
                app_env="test",
                auth_enabled=True,
                auth_token=VALOR_AUTORIZACAO_TESTE,
                rate_limit_enabled=True,
                rate_limit_max_requests=1,
                rate_limit_window_seconds=60,
            )
        )
        limitador = LimitadorRequisicoes(
            cliente_redis=RedisFake(),
            habilitado=True,
            max_requisicoes=1,
            janela_segundos=60,
            falhar_aberto=True,
        )
        app.dependency_overrides[obter_limitador_requisicoes] = lambda: limitador
        cliente = TestClient(app)
        payload = {**PAYLOAD_RAG, "sprints": ["sprint-inexistente"]}

        primeira = cliente.post("/v1/rag", json=payload, headers=headers_autenticados())
        segunda = cliente.post("/v1/rag", json=payload, headers=headers_autenticados())

        self.assertEqual(primeira.status_code, 404)
        self.assertEqual(segunda.status_code, 429)
        self.assertEqual(
            segunda.json()["detail"],
            "Limite de requisições excedido. Tente novamente mais tarde.",
        )


if __name__ == "__main__":
    unittest.main()
