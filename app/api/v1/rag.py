"""Rotas de RAG."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.rag import RagRequest

router = APIRouter(tags=["RAG"])


@router.post(
    "/rag",
    summary="Executa consulta RAG sobre sprints",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    responses={
        401: {"description": "Token ausente ou inválido."},
        413: {"description": "Payload acima do limite configurado."},
        422: {"description": "Payload inválido."},
        501: {"description": "Funcionalidade ainda não implementada."},
    },
)
def consultar_rag(requisicao: RagRequest) -> None:
    """Valida o contrato inicial da rota de RAG antes da implementação funcional."""
    _ = requisicao
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidade de RAG ainda não implementada.",
    )

