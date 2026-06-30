"""Testes de cache e rate limiting com Redis fake."""

import unittest
from pathlib import Path

from app.core.config import Configuracoes
from app.domain.rag import DocumentoVetorial
from app.integrations.openai_client import EmbeddingGerado, RespostaLLM
from app.integrations.redis_client import RedisFake, RedisIndisponivelFake
from app.integrations.vector_store import BancoVetorialFake
from app.services.cache_service import CacheRespostas, CalculadorAssinaturaDados
from app.services.chunking_service import ServicoChunkingSprint
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.rag_service import ServicoRag
from app.services.rate_limit_service import LimitadorRequisicoes
from app.services.resumo_service import ServicoResumos
from app.services.sprint_loader import CarregadorSprints

CAMINHO_FIXTURES = Path(__file__).parent / "fixtures"
CAMINHO_SPRINTS_VALIDAS = CAMINHO_FIXTURES / "sprints_validas"


class ProvedorEmbeddingsContador:
    """Fake de embeddings que conta chamadas."""

    def __init__(self) -> None:
        """Inicializa contador."""
        self.textos: list[str] = []

    def gerar_embedding(self, texto: str) -> EmbeddingGerado:
        """Retorna embedding determinístico."""
        self.textos.append(texto)
        return EmbeddingGerado(vetor=[1.0, 0.0], modelo="modelo-embedding-teste")


class ProvedorLLMContador:
    """Fake de LLM que conta chamadas."""

    def __init__(self) -> None:
        """Inicializa contador."""
        self.perguntas: list[str] = []

    def gerar_resposta(
        self,
        *,
        instrucoes_sistema: str,
        contexto: str,
        pergunta: str,
    ) -> RespostaLLM:
        """Retorna resposta com contador de chamada."""
        _ = instrucoes_sistema, contexto
        self.perguntas.append(pergunta)
        return RespostaLLM(
            texto=f"Resposta gerada {len(self.perguntas)}",
            modelo="modelo-llm-teste",
        )


class BancoVetorialContador(BancoVetorialFake):
    """Banco vetorial fake com contador de buscas."""

    def __init__(self) -> None:
        """Inicializa banco com contador."""
        super().__init__()
        self.quantidade_buscas = 0

    def buscar(self, embedding, *, sprints, rank):
        """Conta buscas antes de delegar para o fake."""
        self.quantidade_buscas += 1
        return super().buscar(embedding, sprints=sprints, rank=rank)


def criar_cache(redis_fake: RedisFake | RedisIndisponivelFake, ttl: int = 123) -> CacheRespostas:
    """Cria cache habilitado com cliente fake."""
    return CacheRespostas(cliente_redis=redis_fake, habilitado=True, ttl_seconds=ttl)


def criar_servico_rag(
    cache: CacheRespostas,
    provedor: ProvedorEmbeddingsContador,
    banco: BancoVetorialContador,
) -> ServicoRag:
    """Cria serviço RAG com cache fake."""
    return ServicoRag(
        configuracoes=Configuracoes(
            data_dir=CAMINHO_SPRINTS_VALIDAS,
            rate_limit_enabled=False,
        ),
        carregador_sprints=CarregadorSprints(CAMINHO_SPRINTS_VALIDAS),
        provedor_embeddings=provedor,
        banco_vetorial=banco,
        cache_respostas=cache,
        calculador_assinatura=CalculadorAssinaturaDados(CAMINHO_SPRINTS_VALIDAS),
    )


def criar_servico_resumos(cache: CacheRespostas, provedor: ProvedorLLMContador) -> ServicoResumos:
    """Cria serviço de resumos com cache fake."""
    return ServicoResumos(
        configuracoes=Configuracoes(
            data_dir=CAMINHO_SPRINTS_VALIDAS,
            rate_limit_enabled=False,
        ),
        carregador_sprints=CarregadorSprints(CAMINHO_SPRINTS_VALIDAS),
        provedor_llm=provedor,
        cache_respostas=cache,
        calculador_assinatura=CalculadorAssinaturaDados(CAMINHO_SPRINTS_VALIDAS),
    )


def popular_banco(banco: BancoVetorialContador) -> None:
    """Adiciona documento vetorial fake."""
    banco.adicionar_documentos(
        [
            DocumentoVetorial(
                id="frag-permissoes",
                texto="funcionalidade de permissões",
                embedding=[1.0, 0.0],
                metadados={
                    "sprint": "sprint-75",
                    "origem": "sprint-75.json",
                    "tipo": "tarefa",
                    "caminho": "tarefas[1]",
                },
            )
        ]
    )


class CacheRateLimitRedisTestCase(unittest.TestCase):
    """Cobre cache e rate limiting com Redis fake."""

    def test_cache_hit_rag_evita_chamada_externa(self) -> None:
        """Segunda consulta RAG usa cache e não chama embeddings ou banco."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake)
        provedor = ProvedorEmbeddingsContador()
        banco = BancoVetorialContador()
        popular_banco(banco)
        servico = criar_servico_rag(cache, provedor, banco)

        primeira = servico.consultar(
            sprints=["sprint-75"],
            mensagem="segredo de permissões",
            rank=1,
            tamanho_fragmento=1000,
        )
        segunda = servico.consultar(
            sprints=["sprint-75"],
            mensagem="segredo de permissões",
            rank=1,
            tamanho_fragmento=1000,
        )

        self.assertEqual(primeira.fragmentos[0].conteudo, segunda.fragmentos[0].conteudo)
        self.assertEqual(len(provedor.textos), 1)
        self.assertEqual(banco.quantidade_buscas, 1)

    def test_cache_miss_executa_servico_e_aplica_ttl(self) -> None:
        """Cache miss executa consulta e grava resposta com TTL configurado."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake, ttl=77)
        provedor = ProvedorEmbeddingsContador()
        banco = BancoVetorialContador()
        popular_banco(banco)
        servico = criar_servico_rag(cache, provedor, banco)

        servico.consultar(
            sprints=["sprint-75"],
            mensagem="permissões",
            rank=1,
            tamanho_fragmento=1000,
        )

        chaves_cache = [chave for chave in redis_fake.dados if ":cache:rag:" in chave]
        self.assertEqual(len(chaves_cache), 1)
        self.assertEqual(redis_fake.ttls[chaves_cache[0]], 77)
        self.assertEqual(len(provedor.textos), 1)

    def test_chave_cache_nao_contem_mensagem_em_texto_puro(self) -> None:
        """Chave de cache usa hash e não expõe a mensagem do usuário."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake)
        provedor = ProvedorEmbeddingsContador()
        banco = BancoVetorialContador()
        popular_banco(banco)
        servico = criar_servico_rag(cache, provedor, banco)

        servico.consultar(
            sprints=["sprint-75"],
            mensagem="segredo de permissões",
            rank=1,
            tamanho_fragmento=1000,
        )

        chaves = " ".join(redis_fake.dados)
        self.assertNotIn("segredo", chaves)
        self.assertNotIn("permiss", chaves)

    def test_mudanca_de_versao_do_indice_evitar_resposta_antiga(self) -> None:
        """Invalidação por reindexação muda a chave e evita cache antigo."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake)
        provedor = ProvedorEmbeddingsContador()
        banco = BancoVetorialContador()
        popular_banco(banco)
        servico = criar_servico_rag(cache, provedor, banco)

        servico.consultar(
            sprints=["sprint-75"],
            mensagem="permissões",
            rank=1,
            tamanho_fragmento=1000,
        )
        cache.invalidar_por_reindexacao()
        servico.consultar(
            sprints=["sprint-75"],
            mensagem="permissões",
            rank=1,
            tamanho_fragmento=1000,
        )

        self.assertEqual(len(provedor.textos), 2)
        self.assertEqual(banco.quantidade_buscas, 2)

    def test_reindexacao_invalida_versao_do_cache(self) -> None:
        """Serviço de indexação incrementa versão usada nas chaves de cache."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake)
        servico = ServicoIndexacaoVetorial(
            carregador_sprints=CarregadorSprints(CAMINHO_SPRINTS_VALIDAS),
            servico_chunking=ServicoChunkingSprint(),
            provedor_embeddings=ProvedorEmbeddingsContador(),
            banco_vetorial=BancoVetorialFake(),
            cache_respostas=cache,
        )

        self.assertEqual(cache.obter_versao_indice(), "0")
        servico.limpar_indice()

        self.assertEqual(cache.obter_versao_indice(), "1")

    def test_redis_indisponivel_degrada_para_execucao_normal(self) -> None:
        """Falha de Redis não impede execução da consulta cacheável."""
        cache = criar_cache(RedisIndisponivelFake())
        provedor = ProvedorEmbeddingsContador()
        banco = BancoVetorialContador()
        popular_banco(banco)
        servico = criar_servico_rag(cache, provedor, banco)

        resultado = servico.consultar(
            sprints=["sprint-75"],
            mensagem="permissões",
            rank=1,
            tamanho_fragmento=1000,
        )

        self.assertEqual(len(resultado.fragmentos), 1)
        self.assertEqual(len(provedor.textos), 1)
        self.assertEqual(banco.quantidade_buscas, 1)

    def test_cache_hit_resumos_evita_chamada_llm(self) -> None:
        """Segunda consulta de resumo usa cache e não chama o LLM."""
        redis_fake = RedisFake()
        cache = criar_cache(redis_fake)
        provedor = ProvedorLLMContador()
        servico = criar_servico_resumos(cache, provedor)

        primeira = servico.gerar_resumo(
            pergunta="Como está a sprint 75?",
            sprints=["sprint-75"],
        )
        segunda = servico.gerar_resumo(
            pergunta="Como está a sprint 75?",
            sprints=["sprint-75"],
        )

        self.assertEqual(primeira.resposta, segunda.resposta)
        self.assertEqual(len(provedor.perguntas), 1)

    def test_rate_limit_bloqueia_excesso(self) -> None:
        """Rate limit bloqueia requisições acima do limite configurado."""
        redis_fake = RedisFake()
        limitador = LimitadorRequisicoes(
            cliente_redis=redis_fake,
            habilitado=True,
            max_requisicoes=2,
            janela_segundos=60,
            falhar_aberto=True,
        )

        primeira = limitador.verificar("token:valor-secreto")
        segunda = limitador.verificar("token:valor-secreto")
        terceira = limitador.verificar("token:valor-secreto")

        self.assertTrue(primeira.permitido)
        self.assertTrue(segunda.permitido)
        self.assertFalse(terceira.permitido)
        self.assertEqual(terceira.motivo, "limite_excedido")
        chaves = " ".join(redis_fake.dados)
        self.assertNotIn("valor-secreto", chaves)


if __name__ == "__main__":
    unittest.main()
