"""Schemas da rota de resumos."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResumoRequest(BaseModel):
    """Payload da rota de resumos."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pergunta": "Como está o andamento da Sprint 75?",
                "sprints": ["Sprint 75"],
            }
        }
    )

    pergunta: str = Field(min_length=1, max_length=4000)
    sprints: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("pergunta")
    @classmethod
    def validar_pergunta(cls, valor: str) -> str:
        """Rejeita perguntas vazias após remoção de espaços."""
        pergunta = valor.strip()
        if not pergunta:
            raise ValueError("Pergunta não pode ser vazia.")
        return pergunta

    @field_validator("sprints")
    @classmethod
    def validar_sprints(cls, valor: list[str]) -> list[str]:
        """Rejeita identificadores vazios na lista de sprints."""
        sprints = [sprint.strip() for sprint in valor]
        if any(not sprint for sprint in sprints):
            raise ValueError("Lista de sprints não pode conter valores vazios.")
        return sprints


class FonteResumoResponse(BaseModel):
    """Fonte consultada para gerar a resposta de resumo."""

    sprint: str = Field(min_length=1)
    origem: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    caminho: str = Field(min_length=1)
    titulo: str | None = None


class ResumoResponse(BaseModel):
    """Resposta consultiva gerada a partir dos dados de sprint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "resposta": "A sprint está em andamento. Há tarefas concluídas e pendências relevantes.",
                "sprints_consultadas": ["sprint-75"],
                "fontes": [
                    {
                        "sprint": "sprint-75",
                        "origem": "sprint-75.json",
                        "tipo": "tarefa",
                        "caminho": "tarefas[0]",
                        "titulo": "Criar login",
                    }
                ],
            }
        }
    )

    resposta: str = Field(min_length=1)
    sprints_consultadas: list[str]
    fontes: list[FonteResumoResponse]
