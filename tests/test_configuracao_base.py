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
            "VECTOR_DB_URL": "http://chromadb:8000",
            "VECTOR_DB_COLLECTION": "sprints-teste",
            "EMBEDDINGS_ENABLED": "false",
            "REDIS_URL": "redis://redis:6379/1",
            "CACHE_ENABLED": "true",
            "CACHE_TTL_SECONDS": "120",
            "RATE_LIMIT_ENABLED": "true",
            "RATE_LIMIT_MAX_REQUESTS": "7",
            "RATE_LIMIT_WINDOW_SECONDS": "30",
            "RATE_LIMIT_FAIL_OPEN": "false",
        }

        with patch.dict(os.environ, ambiente, clear=True):
            configuracoes = carregar_configuracoes_do_ambiente()

        self.assertEqual(configuracoes.app_env, "test")
        self.assertEqual(configuracoes.app_name, "api-teste")
        self.assertEqual(configuracoes.max_rag_rank, 5)
        self.assertEqual(configuracoes.vector_db_url, "http://chromadb:8000")
        self.assertEqual(configuracoes.vector_db_collection, "sprints-teste")
        self.assertFalse(configuracoes.embeddings_enabled)
        self.assertEqual(configuracoes.redis_url, "redis://redis:6379/1")
        self.assertTrue(configuracoes.cache_enabled)
        self.assertEqual(configuracoes.cache_ttl_seconds, 120)
        self.assertTrue(configuracoes.rate_limit_enabled)
        self.assertEqual(configuracoes.rate_limit_max_requests, 7)
        self.assertEqual(configuracoes.rate_limit_window_seconds, 30)
        self.assertFalse(configuracoes.rate_limit_fail_open)
        self.assertIsNone(configuracoes.auth_token)

    def test_healthcheck_esta_registrado_na_aplicacao(self) -> None:
        """Confirma que as rotas públicas esperadas foram incluídas."""
        app = criar_app()

        rotas = {rota.path for rota in app.routes}

        self.assertIn("/health", rotas)


if __name__ == "__main__":
    unittest.main()
