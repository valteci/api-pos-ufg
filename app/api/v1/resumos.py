"""Rotas de resumos de sprints."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.resumos import ResumoRequest

router = APIRouter(tags=["resumos"])


@router.post(
    "/resumos",
    summary="Gera resumo consultivo sobre sprints",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    responses={
        401: {"description": "Token ausente ou inválido."},
        413: {"description": "Payload acima do limite configurado."},
        422: {"description": "Payload inválido."},
        501: {"description": "Funcionalidade ainda não implementada."},
    },
)
def gerar_resumo(requisicao: ResumoRequest) -> None:
    """Valida o contrato inicial da rota de resumos antes da implementação funcional."""
    _ = requisicao
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidade de resumos ainda não implementada.",
    )

