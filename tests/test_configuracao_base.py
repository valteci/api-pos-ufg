"""Testes da configuração base e composição da aplicação."""

import os
import unittest
from unittest.mock import patch

from app.api.health import health_check
from app.core.config import Configuracoes, carregar_configuracoes_do_ambiente
from app.main import criar_app


class ConfiguracaoBaseTestCase(unittest.TestCase):
    """Cobre o bootstrap mínimo da API."""

    def test_healthcheck_publico_retorna_status_ok(self) -> None:
        """Garante que o healthcheck público continua disponível."""
        resposta = health_check(Configuracoes())

        self.assertEqual(resposta.model_dump(), {"status": "ok"})

    def test_swagger_e_openapi_permanecem_disponiveis(self) -> None:
        """Garante que a documentação automática do FastAPI está ativa."""
        app = criar_app()
        openapi = app.openapi()

        self.assertEqual(app.docs_url, "/docs")
        self.assertEqual(app.openapi_url, "/openapi.json")
        self.assertEqual(openapi["info"]["title"], "api-sprints-ia")

    def test_configuracoes_sao_carregadas_do_ambiente(self) -> None:
        """Valida leitura de variáveis de ambiente sem segredos hardcoded."""
        ambiente = {
            "APP_ENV": "test",
            "APP_NAME": "api-teste",
            "AUTH_TOKEN": "",
            "MAX_RAG_RANK": "5",
        }

        with patch.dict(os.environ, ambiente, clear=True):
            configuracoes = carregar_configuracoes_do_ambiente()

        self.assertEqual(configuracoes.app_env, "test")
        self.assertEqual(configuracoes.app_name, "api-teste")
        self.assertEqual(configuracoes.max_rag_rank, 5)
        self.assertIsNone(configuracoes.auth_token)

    def test_healthcheck_esta_registrado_na_aplicacao(self) -> None:
        """Confirma que as rotas públicas esperadas foram incluídas."""
        app = criar_app()

        rotas = {rota.path for rota in app.routes}

        self.assertIn("/health", rotas)


if __name__ == "__main__":
    unittest.main()
