"""Schemas da rota de RAG."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RagRequest(BaseModel):
    """Payload inicial da rota de RAG."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sprints": ["Sprint 75", "Sprint 76"],
                "mensagem": "funcionalidade de permissão de usuários no sistema",
                "rank": 3,
                "tamanho_fragmento": 1000,
            }
        }
    )

    sprints: list[str] = Field(default_factory=list, max_length=20)
    mensagem: str = Field(min_length=1, max_length=4000)
    rank: int = Field(default=3, ge=1, le=10)
    tamanho_fragmento: int = Field(default=1000, ge=1, le=3000)

    @field_validator("mensagem")
    @classmethod
    def validar_mensagem(cls, valor: str) -> str:
        """Rejeita mensagens vazias após remoção de espaços."""
        mensagem = valor.strip()
        if not mensagem:
            raise ValueError("Mensagem não pode ser vazia.")
        return mensagem

    @field_validator("sprints")
    @classmethod
    def validar_sprints(cls, valor: list[str]) -> list[str]:
        """Rejeita identificadores vazios na lista de sprints."""
        sprints = [sprint.strip() for sprint in valor]
        if any(not sprint for sprint in sprints):
            raise ValueError("Lista de sprints não pode conter valores vazios.")
        return sprints

