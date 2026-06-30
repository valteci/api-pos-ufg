"""Schemas da rota de RAG."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.rag import ValorMetadado


class RagRequest(BaseModel):
    """Payload da rota de RAG."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sprints": ["sprint-75", "sprint-76"],
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


class RagFragmentoResponse(BaseModel):
    """Fragmento recuperado pelo RAG."""

    conteudo: str
    score: float
    sprint: str = Field(min_length=1)
    origem: str = Field(min_length=1)
    metadados: dict[str, ValorMetadado] = Field(default_factory=dict)


class RagResponse(BaseModel):
    """Resposta da rota de RAG com fragmentos relevantes."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mensagem": "funcionalidade de permissão de usuários no sistema",
                "sprints_consultadas": ["sprint-75", "sprint-76"],
                "rank": 3,
                "tamanho_fragmento": 1000,
                "fragmentos": [
                    {
                        "conteudo": "Texto recuperado da tarefa ou subtarefa...",
                        "score": 0.92,
                        "sprint": "sprint-75",
                        "origem": "sprint-75.json",
                        "metadados": {
                            "tipo": "tarefa",
                            "caminho": "tarefas[0]",
                        },
                    }
                ],
            }
        }
    )

    mensagem: str
    sprints_consultadas: list[str]
    rank: int
    tamanho_fragmento: int
    fragmentos: list[RagFragmentoResponse]
