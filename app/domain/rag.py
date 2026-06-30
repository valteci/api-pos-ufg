"""Modelos de domínio para fragmentos e documentos de RAG."""

from dataclasses import dataclass

ValorMetadado = str | int | float | bool


@dataclass(frozen=True)
class FragmentoSprint:
    """Fragmento textual normalizado derivado de uma sprint."""

    id: str
    conteudo: str
    sprint: str
    origem: str
    tipo: str
    caminho: str
    metadados: dict[str, ValorMetadado]


@dataclass(frozen=True)
class DocumentoVetorial:
    """Documento pronto para persistência no banco vetorial."""

    id: str
    texto: str
    embedding: list[float]
    metadados: dict[str, ValorMetadado]


@dataclass(frozen=True)
class ResultadoBuscaVetorial:
    """Resultado recuperado do banco vetorial."""

    id: str
    texto: str
    score: float
    metadados: dict[str, ValorMetadado]
