"""Testes da integração interna com OpenAI usando mocks."""

import json
import unittest
from types import SimpleNamespace

from app.core.config import Configuracoes
from app.domain.exceptions import (
    ConfiguracaoOpenAIError,
    OpenAIAuthenticationError,
    OpenAIIndisponivelError,
    OpenAIRateLimitError,
    OpenAITimeoutError,
)
from app.integrations.openai_client import ClienteOpenAI


class RecursoOpenAIFake:
    """Recurso fake compatível com `.create` do SDK oficial."""

    def __init__(self, resposta: object | None = None, erro: Exception | None = None) -> None:
        """Inicializa recurso com resposta ou erro controlado pelo teste."""
        self.resposta = resposta
        self.erro = erro
        self.chamadas: list[dict[str, object]] = []

    def create(self, **parametros: object) -> object:
        """Registra parâmetros e retorna resposta fake."""
        self.chamadas.append(parametros)
        if self.erro is not None:
            raise self.erro
        return self.resposta


class ClienteSDKOpenAIFake:
    """Cliente fake com recursos de responses e embeddings."""

    def __init__(
        self,
        *,
        resposta_llm: object | None = None,
        resposta_embedding: object | None = None,
        erro_llm: Exception | None = None,
        erro_embedding: Exception | None = None,
    ) -> None:
        """Inicializa cliente fake sem chamadas externas."""
        self.responses = RecursoOpenAIFake(resposta_llm, erro_llm)
        self.embeddings = RecursoOpenAIFake(resposta_embedding, erro_embedding)
        self.opcoes: list[dict[str, object]] = []

    def with_options(self, **opcoes: object) -> "ClienteSDKOpenAIFake":
        """Registra opções por chamada e retorna o próprio fake."""
        self.opcoes.append(opcoes)
        return self


class RateLimitError(Exception):
    """Erro fake com o mesmo nome usado pelo SDK oficial."""

    status_code = 429


class AuthenticationError(Exception):
    """Erro fake com o mesmo nome usado pelo SDK oficial."""

    status_code = 401


class APITimeoutError(Exception):
    """Erro fake com o mesmo nome usado pelo SDK oficial."""


class APIConnectionError(Exception):
    """Erro fake com o mesmo nome usado pelo SDK oficial."""


def criar_cliente(
    cliente_sdk: ClienteSDKOpenAIFake,
    *,
    api_key: str | None = "sk-ficticia-sem-uso-real",
    llm_model: str | None = "modelo-llm-teste",
    embedding_model: str | None = "modelo-embedding-teste",
    timeout_seconds: float = 7.0,
) -> ClienteOpenAI:
    """Cria wrapper OpenAI com cliente SDK fake."""
    return ClienteOpenAI(
        api_key=api_key,
        llm_model=llm_model,
        embedding_model=embedding_model,
        timeout_seconds=timeout_seconds,
        cliente_sdk=cliente_sdk,
    )


class IntegracaoOpenAITestCase(unittest.TestCase):
    """Cobre wrapper de LLM e embeddings sem chamadas reais à OpenAI."""

    def test_wrapper_llm_envia_parametros_esperados_para_cliente_mockado(self) -> None:
        """Valida modelo, timeout e prompt delimitado enviado ao SDK."""
        sdk = ClienteSDKOpenAIFake(
            resposta_llm=SimpleNamespace(output_text="Resposta objetiva.", _request_id="req-llm")
        )
        cliente = criar_cliente(sdk)

        resposta = cliente.gerar_resposta(
            instrucoes_sistema="Você responde sobre sprints.",
            contexto="Tarefa A concluída.",
            pergunta="Como está a sprint?",
        )

        chamada = sdk.responses.chamadas[0]
        entrada = chamada["input"]

        self.assertEqual(resposta.texto, "Resposta objetiva.")
        self.assertEqual(resposta.modelo, "modelo-llm-teste")
        self.assertEqual(resposta.request_id, "req-llm")
        self.assertEqual(sdk.opcoes[-1], {"timeout": 7.0})
        self.assertEqual(chamada["model"], "modelo-llm-teste")
        self.assertEqual(entrada[0]["role"], "system")
        self.assertEqual(entrada[1]["role"], "developer")
        self.assertIn("<contexto>", entrada[2]["content"])
        self.assertIn("</pergunta>", entrada[2]["content"])

    def test_wrapper_embedding_envia_parametros_esperados_para_cliente_mockado(self) -> None:
        """Valida modelo, texto e formato de embedding enviados ao SDK."""
        sdk = ClienteSDKOpenAIFake(
            resposta_embedding=SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
                _request_id="req-embedding",
            )
        )
        cliente = criar_cliente(sdk, timeout_seconds=3.5)

        embedding = cliente.gerar_embedding("texto normalizado da tarefa")

        chamada = sdk.embeddings.chamadas[0]
        self.assertEqual(embedding.vetor, [0.1, 0.2, 0.3])
        self.assertEqual(embedding.modelo, "modelo-embedding-teste")
        self.assertEqual(embedding.request_id, "req-embedding")
        self.assertEqual(sdk.opcoes[-1], {"timeout": 3.5})
        self.assertEqual(chamada["model"], "modelo-embedding-teste")
        self.assertEqual(chamada["input"], "texto normalizado da tarefa")
        self.assertEqual(chamada["encoding_format"], "float")

    def test_execucao_sem_chave_retorna_erro_de_configuracao(self) -> None:
        """Impede uso de funcionalidade OpenAI sem `OPENAI_API_KEY`."""
        sdk = ClienteSDKOpenAIFake(resposta_embedding={"data": [{"embedding": [0.1]}]})
        cliente = criar_cliente(sdk, api_key=None)

        with self.assertRaises(ConfiguracaoOpenAIError) as contexto:
            cliente.gerar_embedding("texto")

        self.assertEqual(contexto.exception.detalhes["variavel"], "OPENAI_API_KEY")

    def test_rate_limit_vira_erro_de_dominio(self) -> None:
        """Mapeia rate limit da OpenAI para erro de domínio sanitizado."""
        sdk = ClienteSDKOpenAIFake(erro_embedding=RateLimitError("limite atingido"))
        cliente = criar_cliente(sdk)

        with self.assertLogs("app.integrations.openai_client", level="ERROR") as logs:
            with self.assertRaises(OpenAIRateLimitError):
                cliente.gerar_embedding("texto")

        evento = json.loads(logs.records[-1].getMessage())
        self.assertEqual(evento["event"], "falha_openai")
        self.assertEqual(evento["metadata"]["codigo"], "openai_rate_limit")

    def test_erro_de_autenticacao_nao_expoe_segredo(self) -> None:
        """Garante que chave e mensagem original não aparecem em resposta ou log."""
        segredo = "sk-segredo-que-nao-pode-vazar"
        sdk = ClienteSDKOpenAIFake(erro_llm=AuthenticationError(f"chave inválida: {segredo}"))
        cliente = criar_cliente(sdk, api_key=segredo)

        with self.assertLogs("app.integrations.openai_client", level="ERROR") as logs:
            with self.assertRaises(OpenAIAuthenticationError) as contexto:
                cliente.gerar_resposta(
                    instrucoes_sistema="Responda com segurança.",
                    contexto="Contexto.",
                    pergunta="Pergunta.",
                )

        self.assertNotIn(segredo, str(contexto.exception))
        self.assertNotIn(segredo, logs.output[-1])
        self.assertNotIn("chave inválida", logs.output[-1])

    def test_timeout_eh_tratado(self) -> None:
        """Mapeia timeout da OpenAI para erro de domínio."""
        sdk = ClienteSDKOpenAIFake(erro_llm=APITimeoutError("tempo excedido"))
        cliente = criar_cliente(sdk)

        with self.assertRaises(OpenAITimeoutError):
            cliente.gerar_resposta(
                instrucoes_sistema="Responda com segurança.",
                contexto="Contexto.",
                pergunta="Pergunta.",
            )

    def test_indisponibilidade_eh_tratada(self) -> None:
        """Mapeia falha de conexão da OpenAI para erro de domínio."""
        sdk = ClienteSDKOpenAIFake(erro_embedding=APIConnectionError("serviço indisponível"))
        cliente = criar_cliente(sdk)

        with self.assertRaises(OpenAIIndisponivelError):
            cliente.gerar_embedding("texto")

    def test_from_configuracoes_usa_cliente_mock_sem_chamada_real(self) -> None:
        """Garante que serviços futuros podem injetar mock pelo wrapper."""
        sdk = ClienteSDKOpenAIFake(resposta_embedding={"data": [{"embedding": [0.4, 0.5]}]})
        configuracoes = Configuracoes(
            openai_api_key="sk-ficticia-sem-uso-real",
            openai_llm_model="modelo-llm-teste",
            openai_embedding_model="modelo-embedding-teste",
            openai_timeout_seconds=9,
        )

        cliente = ClienteOpenAI.from_configuracoes(configuracoes, cliente_sdk=sdk)
        embedding = cliente.gerar_embedding("texto")

        self.assertEqual(embedding.vetor, [0.4, 0.5])
        self.assertEqual(sdk.opcoes[-1], {"timeout": 9})


if __name__ == "__main__":
    unittest.main()
