"""Rotas de resumos de sprints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.exceptions import (
    ConfiguracaoOpenAIError,
    ConsultaResumoInvalidaError,
    DadosSprintInvalidosError,
    DiretorioDadosNaoEncontradoError,
    OpenAIIntegracaoError,
    OpenAITimeoutError,
    SprintNaoEncontradaError,
)
from app.infrastructure.dependencies import obter_servico_resumos
from app.schemas.resumos import FonteResumoResponse, ResumoRequest, ResumoResponse
from app.services.resumo_service import ResultadoResumo, ServicoResumos

router = APIRouter(tags=["resumos"])


@router.post(
    "/resumos",
    summary="Gera resumo consultivo sobre sprints",
    response_model=ResumoResponse,
    responses={
        401: {"description": "Token ausente ou inválido."},
        404: {"description": "Sprint solicitada não encontrada."},
        429: {"description": "Limite de requisições excedido."},
        413: {"description": "Payload acima do limite configurado."},
        422: {"description": "Payload inválido."},
        502: {"description": "Falha tratada na OpenAI."},
        504: {"description": "Timeout em integração externa."},
    },
)
def gerar_resumo(
    requisicao: ResumoRequest,
    servico_resumos: ServicoResumos = Depends(obter_servico_resumos),
) -> ResumoResponse:
    """Gera resposta objetiva baseada nos dados de sprints."""
    try:
        resultado = servico_resumos.gerar_resumo(
            pergunta=requisicao.pergunta,
            sprints=requisicao.sprints,
        )
    except SprintNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=erro.mensagem,
        ) from erro
    except (ConsultaResumoInvalidaError, DadosSprintInvalidosError) as erro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=erro.mensagem,
        ) from erro
    except OpenAITimeoutError as erro:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=erro.mensagem,
        ) from erro
    except (ConfiguracaoOpenAIError, OpenAIIntegracaoError) as erro:
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


def _montar_resposta(resultado: ResultadoResumo) -> ResumoResponse:
    """Converte resultado de serviço para schema HTTP."""
    return ResumoResponse(
        resposta=resultado.resposta,
        sprints_consultadas=resultado.sprints_consultadas,
        fontes=[
            FonteResumoResponse(
                sprint=fonte.sprint,
                origem=fonte.origem,
                tipo=fonte.tipo,
                caminho=fonte.caminho,
                titulo=fonte.titulo,
            )
            for fonte in resultado.fontes
        ],
    )
