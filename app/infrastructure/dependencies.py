"""Dependências reutilizáveis de infraestrutura."""

from fastapi import Depends

from app.core.config import Configuracoes, obter_configuracoes
from app.integrations.openai_client import ClienteOpenAI
from app.integrations.redis_client import ClienteRedis, ClienteRedisReal
from app.integrations.vector_store import BancoVetorial, BancoVetorialChromaDB
from app.services.cache_service import CacheRespostas, CalculadorAssinaturaDados
from app.services.chunking_service import ServicoChunkingSprint
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.rag_service import ServicoRag
from app.services.rate_limit_service import LimitadorRequisicoes
from app.services.resumo_service import ServicoResumos
from app.services.sprint_loader import CarregadorSprints


def obter_cliente_openai(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> ClienteOpenAI:
    """Cria o cliente interno da OpenAI a partir das configurações."""
    return ClienteOpenAI.from_configuracoes(configuracoes)


def obter_banco_vetorial(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> BancoVetorial:
    """Cria banco vetorial ChromaDB a partir das configurações."""
    return BancoVetorialChromaDB(
        url=configuracoes.vector_db_url,
        colecao=configuracoes.vector_db_collection,
    )


def obter_cliente_redis(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> ClienteRedis:
    """Cria cliente Redis real a partir das configurações."""
    return ClienteRedisReal(configuracoes.redis_url)


def obter_cache_respostas(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_redis: ClienteRedis = Depends(obter_cliente_redis),
) -> CacheRespostas:
    """Cria cache de respostas com Redis."""
    return CacheRespostas(
        cliente_redis=cliente_redis,
        habilitado=configuracoes.cache_enabled,
        ttl_seconds=configuracoes.cache_ttl_seconds,
    )


def obter_calculador_assinatura_dados(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> CalculadorAssinaturaDados:
    """Cria calculador de assinatura dos arquivos de sprint."""
    return CalculadorAssinaturaDados(configuracoes.data_dir)


def obter_limitador_requisicoes(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_redis: ClienteRedis = Depends(obter_cliente_redis),
) -> LimitadorRequisicoes:
    """Cria limitador de requisições com Redis."""
    return LimitadorRequisicoes(
        cliente_redis=cliente_redis,
        habilitado=configuracoes.rate_limit_enabled,
        max_requisicoes=configuracoes.rate_limit_max_requests,
        janela_segundos=configuracoes.rate_limit_window_seconds,
        falhar_aberto=configuracoes.rate_limit_fail_open,
    )


def obter_servico_indexacao_vetorial(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_openai: ClienteOpenAI = Depends(obter_cliente_openai),
    banco_vetorial: BancoVetorial = Depends(obter_banco_vetorial),
    cache_respostas: CacheRespostas = Depends(obter_cache_respostas),
) -> ServicoIndexacaoVetorial:
    """Monta serviço de indexação vetorial com dependências reais."""
    return ServicoIndexacaoVetorial(
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        servico_chunking=ServicoChunkingSprint(
            tamanho_maximo_fragmento=configuracoes.max_fragment_size
        ),
        provedor_embeddings=cliente_openai,
        banco_vetorial=banco_vetorial,
        cache_respostas=cache_respostas,
    )


def obter_servico_rag(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_openai: ClienteOpenAI = Depends(obter_cliente_openai),
    banco_vetorial: BancoVetorial = Depends(obter_banco_vetorial),
    cache_respostas: CacheRespostas = Depends(obter_cache_respostas),
    calculador_assinatura: CalculadorAssinaturaDados = Depends(
        obter_calculador_assinatura_dados
    ),
) -> ServicoRag:
    """Monta serviço de consulta RAG com dependências reais."""
    return ServicoRag(
        configuracoes=configuracoes,
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        provedor_embeddings=cliente_openai,
        banco_vetorial=banco_vetorial,
        cache_respostas=cache_respostas,
        calculador_assinatura=calculador_assinatura,
    )


def obter_servico_resumos(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_openai: ClienteOpenAI = Depends(obter_cliente_openai),
    cache_respostas: CacheRespostas = Depends(obter_cache_respostas),
    calculador_assinatura: CalculadorAssinaturaDados = Depends(
        obter_calculador_assinatura_dados
    ),
) -> ServicoResumos:
    """Monta serviço de resumos com dependências reais."""
    return ServicoResumos(
        configuracoes=configuracoes,
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        provedor_llm=cliente_openai,
        cache_respostas=cache_respostas,
        calculador_assinatura=calculador_assinatura,
    )
