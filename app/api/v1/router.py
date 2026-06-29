"""Agregador das rotas de negócio da versão 1."""

from fastapi import APIRouter, Depends

from app.api.v1.rag import router as rag_router
from app.api.v1.resumos import router as resumos_router
from app.core.security import exigir_autenticacao

router = APIRouter(prefix="/v1", dependencies=[Depends(exigir_autenticacao)])
router.include_router(rag_router)
router.include_router(resumos_router)
