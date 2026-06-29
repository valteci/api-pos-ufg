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


class ConfiguracaoOpenAIError(ErroDeDominio):
    """Erro para uso da OpenAI sem configuração essencial."""

    def __init__(self, variavel: str) -> None:
        """Cria erro de configuração ausente sem expor valores sensíveis."""
        super().__init__(
            "Integração com OpenAI não configurada.",
            codigo="openai_configuracao_invalida",
            detalhes={"variavel": variavel},
        )


class OpenAIIntegracaoError(ErroDeDominio):
    """Erro base para falhas tratadas na integração com OpenAI."""

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str,
        operacao: str,
        status_code: int | None = None,
    ) -> None:
        """Cria erro sanitizado da integração com OpenAI."""
        detalhes: dict[str, Any] = {"operacao": operacao}
        if status_code is not None:
            detalhes["status_code"] = status_code

        super().__init__(
            mensagem,
            codigo=codigo,
            detalhes=detalhes,
        )


class OpenAIRateLimitError(OpenAIIntegracaoError):
    """Erro para limite de uso atingido na OpenAI."""

    def __init__(self, *, operacao: str, status_code: int | None = None) -> None:
        """Cria erro de rate limit sanitizado."""
        super().__init__(
            "Limite de uso da OpenAI atingido. Tente novamente mais tarde.",
            codigo="openai_rate_limit",
            operacao=operacao,
            status_code=status_code,
        )


class OpenAIAuthenticationError(OpenAIIntegracaoError):
    """Erro para falha de autenticação na OpenAI."""

    def __init__(self, *, operacao: str, status_code: int | None = None) -> None:
        """Cria erro de autenticação sanitizado."""
        super().__init__(
            "Falha de autenticação na integração com OpenAI.",
            codigo="openai_autenticacao_invalida",
            operacao=operacao,
            status_code=status_code,
        )


class OpenAITimeoutError(OpenAIIntegracaoError):
    """Erro para timeout em chamada à OpenAI."""

    def __init__(self, *, operacao: str, status_code: int | None = None) -> None:
        """Cria erro de timeout sanitizado."""
        super().__init__(
            "Tempo limite excedido ao consultar a OpenAI.",
            codigo="openai_timeout",
            operacao=operacao,
            status_code=status_code,
        )


class OpenAIIndisponivelError(OpenAIIntegracaoError):
    """Erro para indisponibilidade ou falha de conexão com a OpenAI."""

    def __init__(self, *, operacao: str, status_code: int | None = None) -> None:
        """Cria erro de indisponibilidade sanitizado."""
        super().__init__(
            "OpenAI indisponível no momento.",
            codigo="openai_indisponivel",
            operacao=operacao,
            status_code=status_code,
        )


class OpenAIRespostaInvalidaError(OpenAIIntegracaoError):
    """Erro para resposta inesperada ou vazia da OpenAI."""

    def __init__(self, *, operacao: str) -> None:
        """Cria erro de resposta inválida sanitizado."""
        super().__init__(
            "Resposta inválida recebida da OpenAI.",
            codigo="openai_resposta_invalida",
            operacao=operacao,
        )
