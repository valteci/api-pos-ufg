"""Exceções de domínio usadas pela aplicação."""

from typing import Any


class ErroDeDominio(Exception):
    """Erro esperado de regra de negócio ou validação de domínio."""

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        """Inicializa um erro de domínio com código estável.

        Args:
            mensagem: Mensagem em português voltada ao domínio.
            codigo: Código estável para logs, testes e handlers HTTP.
            detalhes: Contexto adicional sem dados sensíveis.
        """
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        self.detalhes = detalhes or {}


class NomeSprintInvalidoError(ErroDeDominio):
    """Erro para identificadores de sprint inválidos."""

    def __init__(self, nome_sprint: str) -> None:
        """Cria erro de nome de sprint inválido."""
        super().__init__(
            "Nome da sprint inválido.",
            codigo="nome_sprint_invalido",
            detalhes={"nome_sprint": nome_sprint},
        )


class DiretorioDadosNaoEncontradoError(ErroDeDominio):
    """Erro para diretório de dados inexistente ou inválido."""

    def __init__(self, caminho: str) -> None:
        """Cria erro de diretório de dados não encontrado."""
        super().__init__(
            "Diretório de dados não encontrado.",
            codigo="diretorio_dados_nao_encontrado",
            detalhes={"caminho": caminho},
        )


class SprintNaoEncontradaError(ErroDeDominio):
    """Erro para sprint solicitada que não existe em `data/`."""

    def __init__(self, nome_sprint: str) -> None:
        """Cria erro de sprint não encontrada."""
        super().__init__(
            "Sprint não encontrada.",
            codigo="sprint_nao_encontrada",
            detalhes={"nome_sprint": nome_sprint},
        )


class DadosSprintInvalidosError(ErroDeDominio):
    """Erro para arquivo de sprint sem formato mínimo válido."""

    def __init__(
        self,
        mensagem: str,
        *,
        nome_sprint: str,
        motivo: str,
        caminho: str | None = None,
    ) -> None:
        """Cria erro de dados inválidos de sprint."""
        detalhes = {"nome_sprint": nome_sprint, "motivo": motivo}
        if caminho:
            detalhes["caminho"] = caminho

        super().__init__(
            mensagem,
            codigo="dados_sprint_invalidos",
            detalhes=detalhes,
        )
