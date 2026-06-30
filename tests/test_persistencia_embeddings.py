"""Testes de exportação e importação de embeddings entre ChromaDB e disco."""

import json
import tempfile
import unittest
from pathlib import Path

from app.domain.exceptions import PersistenciaEmbeddingsError
from app.domain.rag import DocumentoVetorial
from app.integrations.vector_store import BancoVetorialFake
from app.services.persistencia_embeddings import ServicoPersistenciaEmbeddings


def criar_documentos() -> list[DocumentoVetorial]:
    """Cria documentos fake de duas sprints para os testes."""
    return [
        DocumentoVetorial(
            id="sprint-75:tarefa:aaa",
            texto="funcionalidade de permissões",
            embedding=[1.0, 0.0, 0.5],
            metadados={"sprint": "Sprint 75", "origem": "Sprint 75.json", "tipo": "tarefa"},
        ),
        DocumentoVetorial(
            id="sprint-75:tarefa:bbb",
            texto="fluxo de login",
            embedding=[0.0, 1.0, 0.25],
            metadados={"sprint": "Sprint 75", "origem": "Sprint 75.json", "tipo": "tarefa"},
        ),
        DocumentoVetorial(
            id="sprint-76:tarefa:ccc",
            texto="relatórios da sprint seguinte",
            embedding=[0.5, 0.5, 1.0],
            metadados={"sprint": "Sprint 76", "origem": "Sprint 76.json", "tipo": "tarefa"},
        ),
    ]


def criar_servico(diretorio: Path, banco: BancoVetorialFake) -> ServicoPersistenciaEmbeddings:
    """Cria o serviço de persistência apontando para um diretório temporário."""
    return ServicoPersistenciaEmbeddings(
        banco_vetorial=banco,
        diretorio_embeddings=diretorio,
        colecao="sprints",
    )


class PersistenciaEmbeddingsTestCase(unittest.TestCase):
    """Cobre o ciclo de exportação e importação de embeddings."""

    def setUp(self) -> None:
        """Cria diretório temporário isolado por teste."""
        self._temp = tempfile.TemporaryDirectory()
        self.diretorio = Path(self._temp.name) / "embeddings"

    def tearDown(self) -> None:
        """Remove o diretório temporário."""
        self._temp.cleanup()

    def test_exportacao_gera_arquivo_por_sprint_com_embeddings(self) -> None:
        """Exportação grava um arquivo JSON por sprint com vetores e metadados."""
        banco = BancoVetorialFake()
        banco.adicionar_documentos(criar_documentos())
        servico = criar_servico(self.diretorio, banco)

        resultado = servico.exportar()

        arquivos = sorted(p.name for p in self.diretorio.glob("*.json"))
        self.assertEqual(resultado.quantidade_documentos, 3)
        self.assertEqual(resultado.quantidade_arquivos, 2)
        self.assertEqual(arquivos, ["sprint-75.json", "sprint-76.json"])

        conteudo = json.loads((self.diretorio / "sprint-75.json").read_text(encoding="utf-8"))
        self.assertEqual(conteudo["sprint"], "Sprint 75")
        self.assertEqual(conteudo["colecao"], "sprints")
        self.assertEqual(conteudo["dimensao"], 3)
        self.assertEqual(len(conteudo["documentos"]), 2)
        self.assertEqual(conteudo["documentos"][0]["embedding"], [1.0, 0.0, 0.5])

    def test_exportacao_remove_arquivos_obsoletos(self) -> None:
        """Arquivos antigos são removidos antes de uma nova exportação."""
        self.diretorio.mkdir(parents=True, exist_ok=True)
        (self.diretorio / "sprint-antiga.json").write_text("{}", encoding="utf-8")
        banco = BancoVetorialFake()
        banco.adicionar_documentos(criar_documentos())
        servico = criar_servico(self.diretorio, banco)

        servico.exportar()

        self.assertFalse((self.diretorio / "sprint-antiga.json").exists())

    def test_importacao_carrega_documentos_para_banco_vazio(self) -> None:
        """Importação carrega todos os documentos para uma coleção vazia."""
        banco_origem = BancoVetorialFake()
        banco_origem.adicionar_documentos(criar_documentos())
        criar_servico(self.diretorio, banco_origem).exportar()

        banco_destino = BancoVetorialFake()
        resultado = criar_servico(self.diretorio, banco_destino).importar()

        self.assertTrue(resultado.importado)
        self.assertEqual(resultado.quantidade_documentos, 3)
        self.assertEqual(banco_destino.contar_documentos(), 3)
        self.assertCountEqual(resultado.sprints, ["Sprint 75", "Sprint 76"])

    def test_importacao_ignora_quando_colecao_ja_populada(self) -> None:
        """Importação idempotente não sobrescreve coleção já populada."""
        banco_origem = BancoVetorialFake()
        banco_origem.adicionar_documentos(criar_documentos())
        criar_servico(self.diretorio, banco_origem).exportar()

        banco_destino = BancoVetorialFake()
        banco_destino.adicionar_documentos(
            [
                DocumentoVetorial(
                    id="ja-existe",
                    texto="documento preexistente",
                    embedding=[0.1, 0.2, 0.3],
                    metadados={"sprint": "Sprint 75"},
                )
            ]
        )
        resultado = criar_servico(self.diretorio, banco_destino).importar()

        self.assertFalse(resultado.importado)
        self.assertEqual(resultado.motivo_ignorado, "colecao_ja_populada")
        self.assertEqual(banco_destino.contar_documentos(), 1)

    def test_importacao_forcada_carrega_mesmo_com_documentos(self) -> None:
        """Importação forçada ignora a verificação de coleção vazia."""
        banco_origem = BancoVetorialFake()
        banco_origem.adicionar_documentos(criar_documentos())
        criar_servico(self.diretorio, banco_origem).exportar()

        banco_destino = BancoVetorialFake()
        banco_destino.adicionar_documentos(
            [
                DocumentoVetorial(
                    id="ja-existe",
                    texto="documento preexistente",
                    embedding=[0.1, 0.2, 0.3],
                    metadados={"sprint": "Sprint 75"},
                )
            ]
        )
        resultado = criar_servico(self.diretorio, banco_destino).importar(somente_se_vazio=False)

        self.assertTrue(resultado.importado)
        self.assertEqual(banco_destino.contar_documentos(), 4)

    def test_roundtrip_exportar_importar_preserva_documentos(self) -> None:
        """Exportar e importar preserva id, texto, vetor e metadados."""
        documentos = criar_documentos()
        banco_origem = BancoVetorialFake()
        banco_origem.adicionar_documentos(documentos)
        criar_servico(self.diretorio, banco_origem).exportar()

        banco_destino = BancoVetorialFake()
        criar_servico(self.diretorio, banco_destino).importar()

        importado = {doc.id: doc for doc in banco_destino.exportar_documentos()}
        self.assertEqual(set(importado), {doc.id for doc in documentos})
        original = next(doc for doc in documentos if doc.id == "sprint-75:tarefa:aaa")
        recuperado = importado["sprint-75:tarefa:aaa"]
        self.assertEqual(recuperado.texto, original.texto)
        self.assertEqual(recuperado.embedding, original.embedding)
        self.assertEqual(recuperado.metadados["sprint"], "Sprint 75")

    def test_importacao_diretorio_inexistente_ignora(self) -> None:
        """Importação ignora silenciosamente quando o diretório não existe."""
        banco = BancoVetorialFake()
        resultado = criar_servico(self.diretorio / "inexistente", banco).importar()

        self.assertFalse(resultado.importado)
        self.assertEqual(resultado.motivo_ignorado, "diretorio_inexistente")

    def test_importacao_arquivo_invalido_levanta_erro(self) -> None:
        """Arquivo de embeddings malformado gera erro de domínio."""
        self.diretorio.mkdir(parents=True, exist_ok=True)
        (self.diretorio / "quebrado.json").write_text(
            json.dumps({"sprint": "Sprint 75", "documentos": [{"id": "x"}]}),
            encoding="utf-8",
        )
        banco = BancoVetorialFake()

        with self.assertRaises(PersistenciaEmbeddingsError) as contexto:
            criar_servico(self.diretorio, banco).importar()

        self.assertEqual(contexto.exception.detalhes["motivo"], "texto_invalido")
        self.assertEqual(banco.contar_documentos(), 0)


if __name__ == "__main__":
    unittest.main()
