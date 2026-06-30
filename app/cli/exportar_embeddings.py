"""Comando para exportar e importar embeddings entre ChromaDB e disco.

Exemplos de uso (dentro do container ``api``):

    # Exporta os embeddings atuais do ChromaDB para data/embeddings
    python -m app.cli.exportar_embeddings

    # Importa os embeddings do disco para o ChromaDB apenas se a coleção
    # estiver vazia
    python -m app.cli.exportar_embeddings --importar

    # Importa forçando, mesmo que a coleção já tenha documentos
    python -m app.cli.exportar_embeddings --importar --forcar
"""

import argparse
import json

from app.core.config import obter_configuracoes
from app.integrations.vector_store import BancoVetorialChromaDB
from app.services.persistencia_embeddings import ServicoPersistenciaEmbeddings


def criar_parser() -> argparse.ArgumentParser:
    """Cria parser do comando de persistência de embeddings."""
    parser = argparse.ArgumentParser(
        description=(
            "Exporta embeddings do ChromaDB para data/embeddings ou importa os "
            "embeddings do disco de volta para o ChromaDB."
        )
    )
    parser.add_argument(
        "--importar",
        action="store_true",
        help="Importa os embeddings do disco para o ChromaDB em vez de exportar.",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Na importação, carrega mesmo que a coleção já tenha documentos.",
    )
    return parser


def criar_servico() -> ServicoPersistenciaEmbeddings:
    """Monta o serviço de persistência com integrações reais."""
    configuracoes = obter_configuracoes()
    banco_vetorial = BancoVetorialChromaDB(
        url=configuracoes.vector_db_url,
        colecao=configuracoes.vector_db_collection,
    )
    return ServicoPersistenciaEmbeddings(
        banco_vetorial=banco_vetorial,
        diretorio_embeddings=configuracoes.embeddings_export_dir,
        colecao=configuracoes.vector_db_collection,
    )


def main() -> None:
    """Executa exportação ou importação de embeddings."""
    argumentos = criar_parser().parse_args()
    servico = criar_servico()

    if argumentos.importar:
        resultado = servico.importar(somente_se_vazio=not argumentos.forcar)
        print(
            json.dumps(
                {
                    "status": "importacao_concluida",
                    "importado": resultado.importado,
                    "motivo_ignorado": resultado.motivo_ignorado,
                    "quantidade_documentos": resultado.quantidade_documentos,
                    "quantidade_arquivos": resultado.quantidade_arquivos,
                    "sprints": resultado.sprints,
                    "diretorio": resultado.diretorio,
                },
                ensure_ascii=False,
            )
        )
        return

    resultado_exportacao = servico.exportar()
    print(
        json.dumps(
            {
                "status": "exportacao_concluida",
                "quantidade_documentos": resultado_exportacao.quantidade_documentos,
                "quantidade_arquivos": resultado_exportacao.quantidade_arquivos,
                "sprints": resultado_exportacao.sprints,
                "diretorio": resultado_exportacao.diretorio,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
