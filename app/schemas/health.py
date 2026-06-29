"""Schemas da rota de saúde."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Resposta pública do healthcheck."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})

    status: str
