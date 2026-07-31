# Exportação e importação de embeddings

Este documento descreve como persistir os embeddings gerados pelo RAG em
arquivos versionados e como recarregá-los para o ChromaDB, inclusive de forma
automática na inicialização da API.

## Motivação

Gerar embeddings depende de chamadas à OpenAI, que têm custo e latência. Depois
de indexar as sprints uma vez, é útil guardar os embeddings resultantes em disco
para:

- evitar regerá-los a cada novo ambiente ou recriação do volume do ChromaDB;
- versionar o índice junto ao restante do projeto;
- subir um ambiente funcional sem depender da OpenAI no primeiro boot.

A origem lógica dos dados continua sendo `data/`. Tanto os 20 documentos de
sprint quanto os arquivos exportados em `data/embeddings/` fazem parte do
repositório. Os arquivos de embeddings são um artefato derivado da indexação, não
uma fonte de verdade independente.

## Diretório e formato

Os arquivos ficam em `EMBEDDINGS_EXPORT_DIR` (default `data/embeddings`). A
exportação gera um arquivo `.json` por sprint, com o seguinte formato:

```json
{
  "versao": 1,
  "colecao": "sprints",
  "sprint": "Sprint 75",
  "modelo_embedding": "text-embedding-3-small",
  "dimensao": 1536,
  "quantidade_documentos": 42,
  "documentos": [
    {
      "id": "Sprint 75:tarefa:abcdef0123456789",
      "texto": "Sprint: Sprint 75\nTipo: tarefa\n...",
      "embedding": [0.0123, -0.0456, "..."],
      "metadados": {
        "sprint": "Sprint 75",
        "origem": "Sprint 75.json",
        "tipo": "tarefa",
        "caminho": "tarefas[0]"
      }
    }
  ]
}
```

O nome do arquivo é um *slug* seguro derivado do identificador da sprint (por
exemplo, `sprint-75.json`). O identificador real da sprint é preservado no campo
`sprint` dentro do arquivo, então o nome do arquivo é apenas cosmético: a
importação lê todos os `*.json` do diretório independentemente do nome.

## Exportar

Com o ambiente do Compose em execução e o índice já gerado:

```bash
docker compose exec api python -m app.cli.exportar_embeddings
```

A exportação remove arquivos `.json` anteriores do diretório antes de gravar os
novos, evitando deixar embeddings obsoletos de sprints que não existem mais. O
comando imprime um resumo em JSON com a quantidade de documentos, de arquivos e
as sprints exportadas.

## Importar manualmente

```bash
# Importa apenas se a coleção estiver vazia (idempotente)
docker compose exec api python -m app.cli.exportar_embeddings --importar

# Força a importação mesmo com a coleção já populada
docker compose exec api python -m app.cli.exportar_embeddings --importar --forcar
```

A importação trata os arquivos como dados não confiáveis: valida estrutura,
tipos e o vetor de embedding antes de gravar no banco vetorial. Arquivos
malformados geram erro de domínio sem gravação parcial.

## Carga automática na inicialização

Quando `EMBEDDINGS_AUTOLOAD_ENABLED=true` (default), a API tenta carregar os
embeddings do disco ao iniciar:

1. Se o diretório não existir ou não tiver arquivos, a carga é ignorada.
2. Se a coleção do ChromaDB já tiver documentos, a carga é ignorada
   (idempotência).
3. Caso contrário, os documentos são carregados para o ChromaDB.

A carga é resiliente: qualquer falha (ChromaDB indisponível, arquivo inválido)
é registrada em log estruturado e **não** impede a subida da API. Nesse caso, o
RAG fica sem resultados até uma indexação ou carga bem-sucedida.

A carga automática é desativada quando `APP_ENV=test`, para não acoplar a subida
da aplicação a um ChromaDB real durante os testes.

## Montagem de volume no Compose

Para permitir a escrita dos arquivos exportados sem abrir mão da proteção dos
arquivos de sprint, o Compose monta:

- `./data:/app/data:ro` — sprints em somente leitura;
- `./data/embeddings:/app/data/embeddings` — diretório de embeddings com escrita.

O mount mais específico de `data/embeddings` tem precedência sobre o mount
somente leitura de `data`, então a exportação consegue gravar apenas nesse
subdiretório.

## Estratégia de reindexação

Os arquivos de embeddings refletem o estado de `data/` no momento da exportação.
Quando os arquivos de sprint mudarem, o fluxo recomendado é:

1. Reindexar: `python -m app.cli.indexar_vetores --reindexar`.
2. Reexportar: `python -m app.cli.exportar_embeddings`.
3. Versionar os documentos alterados e os arquivos atualizados em
   `data/embeddings` na mesma mudança.

Assim, o índice persistido permanece consistente com os dados das sprints. Um
clone novo do repositório recebe a base e os embeddings necessários para a carga
automática, ficando de fora apenas configurações locais e segredos do `.env`.

## Variáveis de ambiente

| Variável | Default | Descrição |
| --- | --- | --- |
| `EMBEDDINGS_EXPORT_DIR` | `data/embeddings` | Diretório dos arquivos de embeddings. |
| `EMBEDDINGS_AUTOLOAD_ENABLED` | `true` | Habilita a carga automática na inicialização. |
