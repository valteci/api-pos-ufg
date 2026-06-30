"""Serviço de exportação e importação de embeddings entre ChromaDB e disco.

Este serviço permite versionar os embeddings já gerados em arquivos JSON dentro
de um diretório (por padrão ``data/embeddings``), evitando regerar embeddings na
OpenAI a cada novo ambiente. O fluxo previsto é:

1. Gerar embeddings uma vez com a indexação vetorial.
2. Exportar os embeddings do ChromaDB para ``data/embeddings`` com este serviço.
3. Versionar esses arquivos.
4. Em uma nova subida da aplicação, carregar automaticamente os embeddings do
   disco para o ChromaDB quando a coleção estiver vazia.

Os arquivos exportados são tratados como dados não confiáveis na importação:
estrutura e tipos são validados antes de qualquer escrita no banco vetorial.
"""

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domain.exceptions import PersistenciaEmbeddingsError
from app.domain.rag import DocumentoVetorial, ValorMetadado
from app.integrations.vector_store import BancoVetorial

logger = logging.getLogger(__name__)

VERSAO_FORMATO_EXPORTACAO = 1
CHAVE_SPRINT_AUSENTE = "sem-sprint"


@dataclass(frozen=True)
class ResultadoExportacaoEmbeddings:
    """Resumo de uma exportação de embeddings para disco."""

    diretorio: str
    quantidade_documentos: int
    quantidade_arquivos: int
    sprints: list[str]


@dataclass(frozen=True)
class ResultadoImportacaoEmbeddings:
    """Resumo de uma importação de embeddings a partir do disco."""

    diretorio: str
    quantidade_documentos: int
    quantidade_arquivos: int
    sprints: list[str]
    importado: bool
    motivo_ignorado: str | None = None


@dataclass
class _GrupoSprint:
    """Acumulador interno de documentos por sprint para exportação."""

    sprint: str
    documentos: list[DocumentoVetorial] = field(default_factory=list)


class ServicoPersistenciaEmbeddings:
    """Exporta e importa embeddings entre o banco vetorial e o disco."""

    def __init__(
        self,
        *,
        banco_vetorial: BancoVetorial,
        diretorio_embeddings: str | Path,
        colecao: str,
    ) -> None:
        """Inicializa o serviço.

        Args:
            banco_vetorial: Banco vetorial de origem/destino dos documentos.
            diretorio_embeddings: Diretório onde os arquivos JSON são gravados e
                lidos, normalmente ``data/embeddings``.
            colecao: Nome da coleção vetorial, registrado no arquivo exportado.
        """
        self.banco_vetorial = banco_vetorial
        self.diretorio_embeddings = Path(diretorio_embeddings)
        self.colecao = colecao

    def exportar(self) -> ResultadoExportacaoEmbeddings:
        """Exporta todos os documentos do banco vetorial para o disco.

        Gera um arquivo JSON por sprint. Arquivos ``.json`` anteriores no
        diretório de exportação são removidos para não deixar embeddings
        obsoletos de sprints que não existem mais.

        Returns:
            Resumo da exportação com contagem de documentos e arquivos.
        """
        documentos = self.banco_vetorial.exportar_documentos()
        grupos = self._agrupar_por_sprint(documentos)

        self.diretorio_embeddings.mkdir(parents=True, exist_ok=True)
        self._remover_arquivos_existentes()

        nomes_usados: set[str] = set()
        for grupo in grupos:
            nome_arquivo = self._nome_arquivo_unico(grupo.sprint, nomes_usados)
            self._escrever_arquivo(self.diretorio_embeddings / nome_arquivo, grupo)

        sprints = [grupo.sprint for grupo in grupos]
        resultado = ResultadoExportacaoEmbeddings(
            diretorio=str(self.diretorio_embeddings),
            quantidade_documentos=len(documentos),
            quantidade_arquivos=len(grupos),
            sprints=sprints,
        )
        self._registrar_evento(
            logging.INFO,
            "embeddings_exportados",
            quantidade_documentos=resultado.quantidade_documentos,
            quantidade_arquivos=resultado.quantidade_arquivos,
            diretorio=resultado.diretorio,
        )
        return resultado

    def importar(self, *, somente_se_vazio: bool = True) -> ResultadoImportacaoEmbeddings:
        """Importa embeddings do disco para o banco vetorial.

        Args:
            somente_se_vazio: Quando ``True``, a importação é ignorada se a
                coleção já tiver documentos, tornando a operação idempotente e
                segura para rodar a cada inicialização.

        Returns:
            Resumo da importação, incluindo se ela de fato ocorreu.

        Raises:
            PersistenciaEmbeddingsError: Quando algum arquivo é inválido.
        """
        if not self.diretorio_embeddings.is_dir():
            return self._importacao_ignorada("diretorio_inexistente")

        arquivos = sorted(self.diretorio_embeddings.glob("*.json"))
        if not arquivos:
            return self._importacao_ignorada("diretorio_vazio")

        if somente_se_vazio and self.banco_vetorial.contar_documentos() > 0:
            return self._importacao_ignorada("colecao_ja_populada")

        documentos: list[DocumentoVetorial] = []
        sprints: list[str] = []
        for arquivo in arquivos:
            sprint, documentos_arquivo = self._ler_arquivo(arquivo)
            documentos.extend(documentos_arquivo)
            if sprint and sprint not in sprints:
                sprints.append(sprint)

        if not documentos:
            return self._importacao_ignorada("sem_documentos")

        self.banco_vetorial.adicionar_documentos(documentos)
        resultado = ResultadoImportacaoEmbeddings(
            diretorio=str(self.diretorio_embeddings),
            quantidade_documentos=len(documentos),
            quantidade_arquivos=len(arquivos),
            sprints=sprints,
            importado=True,
        )
        self._registrar_evento(
            logging.INFO,
            "embeddings_importados",
            quantidade_documentos=resultado.quantidade_documentos,
            quantidade_arquivos=resultado.quantidade_arquivos,
            diretorio=resultado.diretorio,
        )
        return resultado

    def _importacao_ignorada(self, motivo: str) -> ResultadoImportacaoEmbeddings:
        """Cria resultado de importação não realizada e registra o motivo."""
        self._registrar_evento(
            logging.INFO,
            "embeddings_importacao_ignorada",
            motivo=motivo,
            diretorio=str(self.diretorio_embeddings),
        )
        return ResultadoImportacaoEmbeddings(
            diretorio=str(self.diretorio_embeddings),
            quantidade_documentos=0,
            quantidade_arquivos=0,
            sprints=[],
            importado=False,
            motivo_ignorado=motivo,
        )

    @staticmethod
    def _agrupar_por_sprint(documentos: list[DocumentoVetorial]) -> list[_GrupoSprint]:
        """Agrupa documentos por sprint preservando ordem de primeiro contato."""
        grupos: dict[str, _GrupoSprint] = {}
        for documento in documentos:
            sprint = str(documento.metadados.get("sprint") or CHAVE_SPRINT_AUSENTE)
            grupo = grupos.setdefault(sprint, _GrupoSprint(sprint=sprint))
            grupo.documentos.append(documento)
        return list(grupos.values())

    def _remover_arquivos_existentes(self) -> None:
        """Remove arquivos JSON anteriores do diretório de exportação."""
        for arquivo in self.diretorio_embeddings.glob("*.json"):
            if arquivo.is_file():
                arquivo.unlink()

    def _escrever_arquivo(self, caminho: Path, grupo: _GrupoSprint) -> None:
        """Serializa um grupo de sprint em arquivo JSON determinístico."""
        modelo_embedding = self._inferir_modelo(grupo.documentos)
        dimensao = len(grupo.documentos[0].embedding) if grupo.documentos else 0
        conteudo = {
            "versao": VERSAO_FORMATO_EXPORTACAO,
            "colecao": self.colecao,
            "sprint": grupo.sprint,
            "modelo_embedding": modelo_embedding,
            "dimensao": dimensao,
            "quantidade_documentos": len(grupo.documentos),
            "documentos": [
                {
                    "id": documento.id,
                    "texto": documento.texto,
                    "embedding": documento.embedding,
                    "metadados": documento.metadados,
                }
                for documento in grupo.documentos
            ],
        }
        with caminho.open("w", encoding="utf-8") as arquivo:
            json.dump(conteudo, arquivo, ensure_ascii=False, sort_keys=True, indent=2)
            arquivo.write("\n")

    @staticmethod
    def _inferir_modelo(documentos: list[DocumentoVetorial]) -> str | None:
        """Extrai o modelo de embedding dos metadados, quando disponível."""
        for documento in documentos:
            modelo = documento.metadados.get("modelo_embedding")
            if isinstance(modelo, str) and modelo:
                return modelo
        return None

    def _ler_arquivo(self, caminho: Path) -> tuple[str | None, list[DocumentoVetorial]]:
        """Lê e valida um arquivo de embeddings exportado.

        Returns:
            Par com o identificador da sprint e a lista de documentos válidos.

        Raises:
            PersistenciaEmbeddingsError: Quando o arquivo é inválido.
        """
        try:
            with caminho.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise self._erro_invalido(
                "Arquivo de embeddings com JSON inválido.",
                motivo="json_invalido",
                caminho=caminho,
            ) from erro

        if not isinstance(dados, dict):
            raise self._erro_invalido(
                "Arquivo de embeddings deve conter um objeto JSON.",
                motivo="estrutura_invalida",
                caminho=caminho,
            )

        documentos_brutos = dados.get("documentos")
        if not isinstance(documentos_brutos, list):
            raise self._erro_invalido(
                "Arquivo de embeddings sem lista de documentos válida.",
                motivo="documentos_ausentes",
                caminho=caminho,
            )

        sprint = dados.get("sprint")
        documentos = [
            self._documento_de_dict(documento, caminho)
            for documento in documentos_brutos
        ]
        return (str(sprint) if isinstance(sprint, str) else None, documentos)

    def _documento_de_dict(self, dados: Any, caminho: Path) -> DocumentoVetorial:
        """Valida e converte um documento exportado para o modelo de domínio."""
        if not isinstance(dados, dict):
            raise self._erro_invalido(
                "Cada documento exportado deve ser um objeto JSON.",
                motivo="documento_invalido",
                caminho=caminho,
            )

        documento_id = dados.get("id")
        texto = dados.get("texto")
        embedding = dados.get("embedding")
        metadados = dados.get("metadados", {})

        if not isinstance(documento_id, str) or not documento_id:
            raise self._erro_invalido(
                "Documento exportado sem identificador válido.",
                motivo="id_invalido",
                caminho=caminho,
            )
        if not isinstance(texto, str):
            raise self._erro_invalido(
                "Documento exportado sem texto válido.",
                motivo="texto_invalido",
                caminho=caminho,
            )
        if not isinstance(embedding, list) or not embedding or not all(
            isinstance(valor, (int, float)) and not isinstance(valor, bool)
            for valor in embedding
        ):
            raise self._erro_invalido(
                "Documento exportado com vetor de embedding inválido.",
                motivo="embedding_invalido",
                caminho=caminho,
            )
        if not isinstance(metadados, dict):
            raise self._erro_invalido(
                "Documento exportado com metadados inválidos.",
                motivo="metadados_invalidos",
                caminho=caminho,
            )

        metadados_validos: dict[str, ValorMetadado] = {
            str(chave): valor
            for chave, valor in metadados.items()
            if isinstance(valor, (str, int, float, bool))
        }
        return DocumentoVetorial(
            id=documento_id,
            texto=texto,
            embedding=[float(valor) for valor in embedding],
            metadados=metadados_validos,
        )

    @staticmethod
    def _nome_arquivo_unico(sprint: str, nomes_usados: set[str]) -> str:
        """Gera um nome de arquivo seguro e único para a sprint."""
        base = ServicoPersistenciaEmbeddings._slug(sprint)
        nome = f"{base}.json"
        contador = 2
        while nome in nomes_usados:
            nome = f"{base}-{contador}.json"
            contador += 1
        nomes_usados.add(nome)
        return nome

    @staticmethod
    def _slug(texto: str) -> str:
        """Converte um identificador de sprint em nome de arquivo seguro."""
        sem_acentos = unicodedata.normalize("NFKD", texto)
        ascii_texto = sem_acentos.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_texto).strip("-").lower()
        return slug or "sprint"

    @staticmethod
    def _erro_invalido(
        mensagem: str,
        *,
        motivo: str,
        caminho: Path,
    ) -> PersistenciaEmbeddingsError:
        """Cria e registra erro de persistência inválida."""
        erro = PersistenciaEmbeddingsError(
            mensagem,
            motivo=motivo,
            caminho=caminho.name,
        )
        ServicoPersistenciaEmbeddings._registrar_evento(
            logging.ERROR,
            "falha_persistencia_embeddings",
            motivo=motivo,
            arquivo=caminho.name,
        )
        return erro

    @staticmethod
    def _registrar_evento(nivel: int, evento: str, **metadados: Any) -> None:
        """Registra evento estruturado em JSON sem expor conteúdo integral."""
        logger.log(
            nivel,
            json.dumps(
                {"event": evento, "metadata": metadados},
                ensure_ascii=False,
                default=str,
            ),
        )
