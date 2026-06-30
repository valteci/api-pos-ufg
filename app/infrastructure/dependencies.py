"""Dependências reutilizáveis de infraestrutura."""

from fastapi import Depends

from app.core.config import Configuracoes, obter_configuracoes
from app.integrations.openai_client import ClienteOpenAI
from app.integrations.vector_store import BancoVetorial, BancoVetorialChromaDB
from app.services.chunking_service import ServicoChunkingSprint
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.rag_service import ServicoRag
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


def obter_servico_indexacao_vetorial(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_openai: ClienteOpenAI = Depends(obter_cliente_openai),
    banco_vetorial: BancoVetorial = Depends(obter_banco_vetorial),
) -> ServicoIndexacaoVetorial:
    """Monta serviço de indexação vetorial com dependências reais."""
    return ServicoIndexacaoVetorial(
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        servico_chunking=ServicoChunkingSprint(
            tamanho_maximo_fragmento=configuracoes.max_fragment_size
        ),
        provedor_embeddings=cliente_openai,
        banco_vetorial=banco_vetorial,
    )


def obter_servico_rag(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
    cliente_openai: ClienteOpenAI = Depends(obter_cliente_openai),
    banco_vetorial: BancoVetorial = Depends(obter_banco_vetorial),
) -> ServicoRag:
    """Monta serviço de consulta RAG com dependências reais."""
    return ServicoRag(
        configuracoes=configuracoes,
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        provedor_embeddings=cliente_openai,
        banco_vetorial=banco_vetorial,
    )
