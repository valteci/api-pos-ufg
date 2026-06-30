"""Comando para indexação vetorial dos arquivos de sprint."""

import argparse
import json

from app.core.config import obter_configuracoes
from app.integrations.openai_client import ClienteOpenAI
from app.integrations.vector_store import BancoVetorialChromaDB
from app.services.chunking_service import ServicoChunkingSprint
from app.services.indexacao_vetorial import ServicoIndexacaoVetorial
from app.services.sprint_loader import CarregadorSprints


def criar_parser() -> argparse.ArgumentParser:
    """Cria parser do comando de indexação vetorial."""
    parser = argparse.ArgumentParser(
        description="Indexa embeddings das sprints a partir dos arquivos em data/."
    )
    parser.add_argument(
        "--sprint",
        action="append",
        dest="sprints",
        help="Identificador de sprint a indexar. Pode ser informado mais de uma vez.",
    )
    parser.add_argument(
        "--reindexar",
        action="store_true",
        help="Limpa o índice completo e recria todos os embeddings a partir de data/.",
    )
    parser.add_argument(
        "--limpar",
        action="store_true",
        help="Limpa o índice vetorial sem gerar novos embeddings.",
    )
    return parser


def criar_servico() -> ServicoIndexacaoVetorial:
    """Monta serviço de indexação com integrações reais configuradas por ambiente."""
    configuracoes = obter_configuracoes()
    if not configuracoes.embeddings_enabled:
        raise RuntimeError("Embeddings estão desabilitados por EMBEDDINGS_ENABLED=false.")

    cliente_openai = ClienteOpenAI.from_configuracoes(configuracoes)
    banco_vetorial = BancoVetorialChromaDB(
        url=configuracoes.vector_db_url,
        colecao=configuracoes.vector_db_collection,
    )
    return ServicoIndexacaoVetorial(
        carregador_sprints=CarregadorSprints(configuracoes.data_dir),
        servico_chunking=ServicoChunkingSprint(
            tamanho_maximo_fragmento=configuracoes.max_fragment_size
        ),
        provedor_embeddings=cliente_openai,
        banco_vetorial=banco_vetorial,
    )


def main() -> None:
    """Executa indexação, reindexação ou limpeza do índice vetorial."""
    argumentos = criar_parser().parse_args()
    servico = criar_servico()

    if argumentos.limpar:
        servico.limpar_indice()
        print(json.dumps({"status": "indice_limpo"}, ensure_ascii=False))
        return

    if argumentos.reindexar:
        resultado = servico.reindexar_tudo()
    else:
        resultado = servico.indexar_sprints(argumentos.sprints)

    print(
        json.dumps(
            {
                "status": "indexacao_concluida",
                "sprints": resultado.sprints,
                "quantidade_fragmentos": resultado.quantidade_fragmentos,
                "modelo_embedding": resultado.modelo_embedding,
                "assinatura": resultado.assinatura,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
