"""Modelos de domínio normalizados para dados de sprints."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


JsonObjeto = dict[str, Any]


@dataclass(frozen=True)
class Subtarefa:
    """Representa uma subtarefa normalizada de uma sprint."""

    indice: int
    caminho: str
    dados: JsonObjeto
    titulo: str | None = None
    descricao: str | None = None
    status: str | None = None
    responsavel: str | None = None


@dataclass(frozen=True)
class Tarefa:
    """Representa uma tarefa normalizada de uma sprint."""

    indice: int
    caminho: str
    dados: JsonObjeto
    titulo: str | None = None
    descricao: str | None = None
    status: str | None = None
    responsavel: str | None = None
    subtarefas: list[Subtarefa] = field(default_factory=list)


@dataclass(frozen=True)
class Sprint:
    """Representa uma sprint carregada a partir de um arquivo JSON."""

    identificador: str
    arquivo_origem: Path
    dados_originais: JsonObjeto | list[Any]
    tarefas: list[Tarefa]

    @property
    def quantidade_subtarefas(self) -> int:
        """Retorna a quantidade total de subtarefas da sprint."""
        return sum(len(tarefa.subtarefas) for tarefa in self.tarefas)
