# API de sprints com IA

API FastAPI para consulta, sumarização e recuperação de informações sobre
sprints de uma squad de desenvolvimento.

Nesta etapa a aplicação contém a base FastAPI, carregamento validado de arquivos
de sprint, segurança inicial por Bearer token, wrapper interno para OpenAI e
infraestrutura de chunking/indexação vetorial com ChromaDB. A rota `/v1/rag`
recupera fragmentos relevantes das sprints indexadas. A rota `/v1/resumos`
gera respostas consultivas e resumos objetivos com base nos dados carregados de
`data/`.

## Configurar ambiente

Crie um `.env` local a partir de `.env.sample` e preencha os valores essenciais:

```env
AUTH_TOKEN=
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
VECTOR_DB_URL=http://chromadb:8000
VECTOR_DB_COLLECTION=sprints
EMBEDDINGS_EXPORT_DIR=data/embeddings
EMBEDDINGS_AUTOLOAD_ENABLED=true
REDIS_URL=redis://redis:6379/0
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
```

O token real deve ficar apenas no `.env` local ou no ambiente de execução. O
Compose carrega esse arquivo e repassa as variáveis para o container da API.

## Integração com OpenAI

A integração usa o pacote oficial `openai` em uma camada própria:

- `ClienteOpenAI.gerar_resposta`: usa a Responses API para LLM;
- `ClienteOpenAI.gerar_embedding`: usa a API de embeddings para RAG.

Os modelos vêm de `OPENAI_LLM_MODEL` e `OPENAI_EMBEDDING_MODEL`. A chave vem
exclusivamente de `OPENAI_API_KEY`. Falhas como rate limit, autenticação
inválida, indisponibilidade e timeout são convertidas em erros de domínio
sanitizados, sem expor chave, prompt completo ou mensagem original do SDK.

## Cache e rate limiting

Quando `CACHE_ENABLED=true`, consultas repetíveis de `/v1/rag` e `/v1/resumos`
podem ser atendidas por Redis. As chaves usam hash dos parâmetros normalizados,
assinatura dos arquivos consultados e versão do índice; a mensagem do usuário e
o token não aparecem em texto puro. O TTL é definido por `CACHE_TTL_SECONDS`.

Reindexações executadas por `app.cli.indexar_vetores` incrementam a versão do
índice usada nas chaves, evitando respostas antigas após atualização vetorial.
Falhas de Redis no cache degradam para execução normal da consulta.

O rate limiting usa Redis por token autenticado, com limite configurado por
`RATE_LIMIT_MAX_REQUESTS` e `RATE_LIMIT_WINDOW_SECONDS`. Quando o limite é
excedido, a API retorna `429 Too Many Requests`.

## Chunking e índice vetorial

O serviço de chunking converte tarefas e subtarefas carregadas de `data/` em
fragmentos textuais normalizados. Cada fragmento preserva metadados de sprint,
arquivo de origem, tipo, caminho lógico, status, responsável e títulos
disponíveis. Fragmentos não misturam sprints diferentes.

A indexação usa `ClienteOpenAI.gerar_embedding` para gerar embeddings dos
fragmentos e grava os documentos no ChromaDB por meio de uma interface interna
testável. O índice depende exclusivamente dos arquivos `.json` em `data/`.

Com o ambiente do Compose em execução, gere ou atualize o índice com:

```bash
docker compose exec api python -m app.cli.indexar_vetores --reindexar
```

Para reindexar somente uma sprint:

```bash
docker compose exec api python -m app.cli.indexar_vetores --sprint sprint-75
```

Para limpar o índice vetorial:

```bash
docker compose exec api python -m app.cli.indexar_vetores --limpar
```

Execute a reindexação sempre que arquivos em `data/` forem criados, alterados ou
removidos.

## Exportar e importar embeddings (data/embeddings)

Gerar embeddings consome a API da OpenAI. Para evitar regerá-los a cada novo
ambiente, é possível exportar os embeddings já presentes no ChromaDB para
arquivos versionáveis em `data/embeddings/` e recarregá-los depois.

Exportar os embeddings atuais do ChromaDB para o disco (um arquivo `.json` por
sprint):

```bash
docker compose exec api python -m app.cli.exportar_embeddings
```

Importar manualmente os embeddings do disco de volta para o ChromaDB (carrega
apenas quando a coleção está vazia):

```bash
docker compose exec api python -m app.cli.exportar_embeddings --importar
```

Forçar a importação mesmo com a coleção já populada:

```bash
docker compose exec api python -m app.cli.exportar_embeddings --importar --forcar
```

### Carga automática na inicialização

Quando `EMBEDDINGS_AUTOLOAD_ENABLED=true` (default), a API verifica, ao iniciar,
se há arquivos em `EMBEDDINGS_EXPORT_DIR` (default `data/embeddings`). Se houver
e a coleção do ChromaDB estiver vazia, os embeddings são carregados
automaticamente. A operação é idempotente: se a coleção já tiver documentos, a
carga é ignorada. Falhas de conexão ou arquivos ausentes não impedem a subida
da API — o RAG apenas fica sem resultados até a indexação ou a carga.

No Compose, o diretório `data/embeddings` é montado com escrita (`rw`), enquanto
o restante de `data/` permanece somente leitura, preservando os arquivos de
sprint. O formato de cada arquivo exportado inclui versão, coleção, sprint,
modelo de embedding, dimensão e a lista de documentos com `id`, `texto`,
`embedding` e `metadados`. A importação valida estrutura e tipos antes de gravar
no banco vetorial.

Detalhes adicionais em
[`docs/rag/exportacao-e-importacao-de-embeddings.md`](docs/rag/exportacao-e-importacao-de-embeddings.md).

## Consulta RAG

Depois de gerar o índice vetorial, consulte fragmentos relevantes com:

```bash
curl -X POST http://localhost:8000/v1/rag \
  -H "Authorization: Bearer <token-de-acesso>" \
  -H "Content-Type: application/json" \
  -d '{
    "sprints": ["Sprint 75", "Sprint 76"],
    "mensagem": "funcionalidade de permissão de usuários no sistema",
    "rank": 3,
    "tamanho_fragmento": 1000
  }'
```

Quando `sprints` vier vazia, a API consulta todas as sprints disponíveis em
`data/`. A resposta retorna até `rank` fragmentos, cada um limitado por
`tamanho_fragmento`, com `score`, `sprint`, `origem` e metadados de rastreio.

## Resumos

A rota de resumos responde perguntas consultivas usando os dados normalizados de
sprints, tarefas e subtarefas:

```bash
curl -X POST http://localhost:8000/v1/resumos \
  -H "Authorization: Bearer <token-de-acesso>" \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Como está o andamento da Sprint 75?",
    "sprints": ["Sprint 75"]
  }'
```

Quando `sprints` vier vazia, a API tenta identificar sprints mencionadas na
pergunta. Se não encontrar menção clara, consulta todas as sprints disponíveis
dentro do limite configurado. A resposta traz `resposta`, `sprints_consultadas`
e `fontes` rastreáveis.

## Executar com Docker Compose

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
- ChromaDB HTTP em `http://localhost:8001`
- Redis em `localhost:6379`

O `GET /health` é público. Rotas sob `/v1` exigem:

```http
Authorization: Bearer <token-de-acesso>
```

## Executar localmente com Poetry (sem Docker)

É possível rodar a API diretamente na máquina, sem Docker. Nesse modo, o
ChromaDB e o Redis precisam estar rodando localmente, pois a API depende deles
para o índice vetorial, o cache e o rate limiting.

### 1. Instalar dependências da API

```bash
poetry install
```

### 2. Subir o ChromaDB local

O pacote `chromadb` já é instalado como dependência do projeto, então o CLI
`chroma` fica disponível dentro do ambiente do Poetry. Como a API ocupa a porta
`8000`, suba o ChromaDB na porta `8001`:

```bash
poetry run chroma run --host localhost --port 8001 --path ./chroma-data
```

O diretório `./chroma-data` guarda os dados persistidos do índice vetorial.
Deixe esse processo rodando em um terminal próprio.

### 3. Subir o Redis local

Instale o Redis pelo gerenciador de pacotes do seu sistema e inicie o servidor:

```bash
# Debian/Ubuntu
sudo apt-get install redis-server

# macOS (Homebrew)
brew install redis

# Iniciar o servidor (porta padrão 6379)
redis-server
```

Deixe o Redis rodando em um terminal próprio. Para validar a conexão, use
`redis-cli ping`, que deve responder `PONG`.

### 4. Ajustar as variáveis de ambiente para apontar para `localhost`

No Compose, as URLs usam os nomes de serviço `chromadb` e `redis`. Rodando
localmente, ajuste o `.env` para apontar para `localhost` com as portas locais:

```env
VECTOR_DB_URL=http://localhost:8001
REDIS_URL=redis://localhost:6379/0
```

As demais variáveis essenciais (`AUTH_TOKEN`, `OPENAI_API_KEY`,
`OPENAI_LLM_MODEL`, `OPENAI_EMBEDDING_MODEL`) continuam obrigatórias.

### 5. Subir a API

```bash
poetry run uvicorn app.main:app --reload
```

A API ficará disponível em `http://localhost:8000` (`/health`, `/docs` e
`/openapi.json`).

### 6. Gerar o índice vetorial local

Com ChromaDB e Redis no ar, gere o índice a partir dos arquivos de `data/`
(necessário para o `/v1/rag` retornar resultados):

```bash
poetry run python -m app.cli.indexar_vetores --reindexar
```

Caso já existam embeddings exportados em `data/embeddings`, eles são carregados
automaticamente na inicialização quando a coleção do ChromaDB está vazia e
`EMBEDDINGS_AUTOLOAD_ENABLED=true`.

## Testes da base atual

Enquanto a suíte Pytest completa ainda não é adicionada ao projeto, os testes
iniciais podem ser executados com a biblioteca padrão do Python:

```bash
poetry run python -m unittest discover -s tests
```

No container da API, monte `tests/` quando precisar executar a suíte na imagem:

```bash
docker compose run --rm -T -v ./tests:/app/tests:ro api python -m unittest discover -s tests
```

## Dados das sprints

Os arquivos `.json` em `data/` representam as sprints disponíveis. O nome do
arquivo sem `.json` é usado como identificador da sprint. O diretório é
configurado por `DATA_DIR`, com default seguro `data`.
