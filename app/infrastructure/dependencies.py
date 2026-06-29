"""Dependências reutilizáveis de infraestrutura."""

from fastapi import Depends

from app.core.config import Configuracoes, obter_configuracoes
from app.integrations.openai_client import ClienteOpenAI


def obter_cliente_openai(
    configuracoes: Configuracoes = Depends(obter_configuracoes),
) -> ClienteOpenAI:
    """Cria o cliente interno da OpenAI a partir das configurações."""
    return ClienteOpenAI.from_configuracoes(configuracoes)
