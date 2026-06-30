"""Rotas de RAG."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.exceptions import (
    BancoVetorialError,
    ConfiguracaoBancoVetorialError,
    ConfiguracaoOpenAIError,
    ConsultaRagInvalidaError,
    DadosSprintInvalidosError,
    DiretorioDadosNaoEncontradoError,
    OpenAIIntegracaoError,
    OpenAITimeoutError,
    SprintNaoEncontradaError,
)
from app.infrastructure.dependencies import obter_servico_rag
from app.schemas.rag import RagFragmentoResponse, RagRequest, RagResponse
from app.services.rag_service import ResultadoConsultaRag, ServicoRag

router = APIRouter(tags=["RAG"])


@router.post(
    "/rag",
    summary="Executa consulta RAG sobre sprints",
    response_model=RagResponse,
    responses={
        401: {"description": "Token ausente ou inválido."},
        404: {"description": "Sprint solicitada não encontrada."},
        413: {"description": "Payload acima do limite configurado."},
        422: {"description": "Payload inválido."},
        502: {"description": "Falha tratada em integração externa."},
        504: {"description": "Timeout em integração externa."},
    },
)
def consultar_rag(
    requisicao: RagRequest,
    servico_rag: ServicoRag = Depends(obter_servico_rag),
) -> RagResponse:
    """Recupera fragmentos relevantes das sprints indexadas."""
    try:
        resultado = servico_rag.consultar(
            sprints=requisicao.sprints,
            mensagem=requisicao.mensagem,
            rank=requisicao.rank,
            tamanho_fragmento=requisicao.tamanho_fragmento,
        )
    except SprintNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=erro.mensagem,
        ) from erro
    except (ConsultaRagInvalidaError, DadosSprintInvalidosError) as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=erro.mensagem,
        ) from erro
    except OpenAITimeoutError as erro:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=erro.mensagem,
        ) from erro
    except (
        ConfiguracaoOpenAIError,
        OpenAIIntegracaoError,
        ConfiguracaoBancoVetorialError,
        BancoVetorialError,
    ) as erro:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=erro.mensagem,
        ) from erro
    except DiretorioDadosNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=erro.mensagem,
        ) from erro

    return _montar_resposta(resultado)


def _montar_resposta(resultado: ResultadoConsultaRag) -> RagResponse:
    """Converte resultado de serviço para schema HTTP."""
    return RagResponse(
        mensagem=resultado.mensagem,
        sprints_consultadas=resultado.sprints_consultadas,
        rank=resultado.rank,
        tamanho_fragmento=resultado.tamanho_fragmento,
        fragmentos=[
            RagFragmentoResponse(
                conteudo=fragmento.conteudo,
                score=fragmento.score,
                sprint=fragmento.sprint,
                origem=fragmento.origem,
                metadados=fragmento.metadados,
            )
            for fragmento in resultado.fragmentos
        ],
    )
