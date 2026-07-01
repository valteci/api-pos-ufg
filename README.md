# API de sprints com IA

API FastAPI para consulta, sumarização e recuperação de informações sobre
sprints de uma squad de desenvolvimento. A aplicação usa os arquivos JSON em
`data/` como fonte de verdade, valida os dados antes do uso, protege as rotas de
negócio com Bearer token e integra OpenAI, ChromaDB e Redis para entregar
resumos e consultas RAG sobre tarefas e subtarefas.

## Visão geral

A API atende a dois fluxos principais:

- resumos consultivos sobre andamento de sprints, tarefas e subtarefas;
- recuperação semântica de fragmentos relevantes por RAG.

As respostas são geradas com base nos dados carregados do diretório `data/`.
Quando não há informação suficiente para responder com segurança, a API informa
essa limitação em vez de inventar tarefas, responsáveis ou status.

## Recursos principais

- `POST /v1/resumos`: responde perguntas sobre as sprints disponíveis.
- `POST /v1/rag`: retorna fragmentos semanticamente próximos da mensagem do
  usuário.
- `GET /health`: healthcheck público para validação operacional.
- Autenticação por Bearer token nas rotas de negócio.
- Integração com OpenAI para LLM e embeddings.
- Índice vetorial em ChromaDB, derivado exclusivamente dos JSONs em `data/`.
- Cache e rate limiting com Redis.
- Logs estruturados em JSON para `stdout` e `logs/api.json`.
- Documentação automática via Swagger UI e OpenAPI.

## Estrutura do projeto

```text
.
├── app/                    # Aplicação FastAPI, serviços, schemas e integrações
├── data/                   # Arquivos JSON das sprints e embeddings exportados
├── docs/                   # Documentação técnica por tema
├── logs/                   # Arquivos de log estruturado
├── tests/                  # Testes automatizados e fixtures
├── docker-compose.yml      # Ambiente local com API, Redis e ChromaDB
├── Dockerfile
└── README.md
```

O diretório `data/` é a única origem dos dados de sprint usados pela IA. Cada
arquivo `.json` representa uma sprint, e o nome do arquivo sem extensão é usado
como identificador.

## Configuração

Crie um `.env` local a partir de `.env.sample`:

```bash
cp .env.sample .env
```

Preencha os valores sensíveis no `.env` local. Eles não devem ser versionados,
registrados em logs nem expostos em respostas da API.

```env
AUTH_TOKEN=
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
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

Também estão disponíveis configurações de ambiente, CORS, limites de payload,
limites de RAG e caminhos de dados. Consulte `.env.sample` para a lista
completa.

## Execução com Docker Compose

Suba o ambiente local com:

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

Serviços auxiliares:

- ChromaDB HTTP em `http://localhost:8001`
- Redis em `localhost:6379`

Para derrubar o ambiente:

```bash
docker compose down
```

## Execução local com Poetry

Instale as dependências:

```bash
poetry install
```

Suba o ChromaDB em um terminal próprio:

```bash
poetry run chroma run --host localhost --port 8001 --path ./chroma-data
```

Suba o Redis localmente na porta padrão `6379` e ajuste o `.env`:

```env
VECTOR_DB_URL=http://localhost:8001
REDIS_URL=redis://localhost:6379/0
```

Inicie a API:

```bash
poetry run uvicorn app.main:app --reload
```

A aplicação ficará disponível em `http://localhost:8000`.

## Autenticação

O healthcheck é público. Todas as rotas sob `/v1` exigem o token configurado em
`AUTH_TOKEN`:

```http
Authorization: Bearer <token-de-acesso>
```

Falhas de autenticação retornam status HTTP apropriado sem expor o token
recebido.

## Swagger e OpenAPI

Com a API em execução, acesse:

- Swagger UI: `http://localhost:8000/docs`
- Documento OpenAPI: `http://localhost:8000/openapi.json`

Os schemas Pydantic alimentam a documentação automática das rotas, requests,
responses e validações.

## Dados das sprints

Os arquivos em `data/` devem estar em JSON válido. A aplicação valida
existência, formato e conteúdo mínimo antes de usar os dados em resumos ou RAG.

O carregamento trata:

- sprint inexistente;
- JSON inválido;
- sprint vazia;
- tarefas sem subtarefas;
- subtarefas ausentes, nulas ou vazias;
- campos inesperados sem interromper a API desnecessariamente.

O caminho do diretório pode ser alterado por `DATA_DIR`.

## Consulta RAG

Depois que o índice vetorial estiver populado, use:

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

Quando `sprints` vem vazia, a consulta considera todas as sprints disponíveis
dentro dos limites configurados. `rank` define a quantidade máxima de fragmentos
retornados, e `tamanho_fragmento` controla o tamanho de cada fragmento.

## Resumos

A rota de resumos recebe uma pergunta e consulta os dados normalizados de
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

Quando `sprints` vem vazia, a API tenta identificar menções a sprints na
pergunta. Se não houver menção clara, consulta as sprints disponíveis dentro do
limite configurado. A resposta inclui a resposta sintetizada, as sprints
consultadas e fontes rastreáveis.

## Índice vetorial

O chunking converte tarefas e subtarefas em fragmentos textuais normalizados com
metadados de sprint, arquivo de origem, tipo, caminho lógico, status,
responsável e títulos disponíveis. Fragmentos não misturam sprints diferentes.

A indexação gera embeddings com OpenAI e grava os documentos no ChromaDB por
meio de uma camada interna testável. Gere ou atualize o índice com:

```bash
docker compose exec api python -m app.cli.indexar_vetores --reindexar
```

No ambiente local sem Docker, use:

```bash
poetry run python -m app.cli.indexar_vetores --reindexar
```

Para reindexar uma sprint específica:

```bash
docker compose exec api python -m app.cli.indexar_vetores --sprint sprint-75
```

Para limpar o índice:

```bash
docker compose exec api python -m app.cli.indexar_vetores --limpar
```

Execute a reindexação sempre que arquivos em `data/` forem criados, alterados ou
removidos.

## Exportação e importação de embeddings

Embeddings podem ser exportados do ChromaDB para `data/embeddings/`, evitando
novo consumo da API da OpenAI em ambientes já conhecidos.

Exportar:

```bash
docker compose exec api python -m app.cli.exportar_embeddings
```

Importar quando a coleção estiver vazia:

```bash
docker compose exec api python -m app.cli.exportar_embeddings --importar
```

Forçar importação:

```bash
docker compose exec api python -m app.cli.exportar_embeddings --importar --forcar
```

Com `EMBEDDINGS_AUTOLOAD_ENABLED=true`, a API carrega automaticamente os
embeddings exportados quando o ChromaDB inicia com a coleção vazia. O formato
exportado inclui versão, coleção, sprint, modelo, dimensão, documentos,
embeddings e metadados.

Detalhes:
[`docs/rag/exportacao-e-importacao-de-embeddings.md`](docs/rag/exportacao-e-importacao-de-embeddings.md).

## Integração com OpenAI

A integração fica encapsulada em `app/integrations/openai_client.py`:

- `ClienteOpenAI.gerar_resposta`: usa a Responses API para respostas e resumos;
- `ClienteOpenAI.gerar_embedding`: usa embeddings para indexação e RAG.

Os modelos são configurados por `OPENAI_LLM_MODEL` e
`OPENAI_EMBEDDING_MODEL`. A chave vem exclusivamente de `OPENAI_API_KEY`.
Timeout, rate limit, autenticação inválida e indisponibilidade são convertidos
em erros de domínio sanitizados.

Os prompts separam instruções internas, contexto recuperado e mensagem do
usuário para reduzir risco de prompt injection.

## Cache e rate limiting

Quando `CACHE_ENABLED=true`, respostas repetíveis de `/v1/rag` e `/v1/resumos`
podem ser atendidas por Redis. As chaves usam hash dos parâmetros normalizados,
assinatura dos arquivos consultados e versão do índice; mensagens de usuário e
tokens não ficam em texto puro.

O TTL é definido por `CACHE_TTL_SECONDS`. Reindexações incrementam a versão do
índice usada nas chaves, evitando retorno de respostas antigas após atualização
vetorial.

O rate limiting usa Redis por token autenticado, com limite configurado por
`RATE_LIMIT_MAX_REQUESTS` e `RATE_LIMIT_WINDOW_SECONDS`. Ao exceder o limite, a
API retorna `429 Too Many Requests`.

## Logs e erros

Os logs estruturados são enviados para `stdout` e para o arquivo configurado em
`LOG_FILE_PATH`, por padrão `logs/api.json`. Cada linha é registrada em formato
JSON, com contexto suficiente para diagnóstico sem incluir segredos.

Erros de validação, autenticação, dados inválidos, cache, Redis, ChromaDB e
OpenAI são tratados com respostas HTTP apropriadas e mensagens em português.

## Testes

A suíte automatizada fica em `tests/` e pode ser executada com:

```bash
poetry run python -m unittest discover -s tests
```

No container da API:

```bash
docker compose run --rm -T -v ./tests:/app/tests:ro api python -m unittest discover -s tests
```

Os testes cobrem carregamento de sprints, autenticação, segurança, integração
OpenAI por mocks, cache, rate limiting, chunking, indexação vetorial,
persistência de embeddings, rota RAG e rota de resumos.

## Documentação complementar

A documentação técnica fica em `docs/`:

- [`docs/apis/contratos-http.md`](docs/apis/contratos-http.md)
- [`docs/arquitetura/escolhas-tecnicas-e-arquiteturais.md`](docs/arquitetura/escolhas-tecnicas-e-arquiteturais.md)
- [`docs/dados/dados-de-sprints.md`](docs/dados/dados-de-sprints.md)
- [`docs/integracoes/openai.md`](docs/integracoes/openai.md)
- [`docs/observabilidade/logs-e-erros.md`](docs/observabilidade/logs-e-erros.md)
- [`docs/rag/estrategia-rag.md`](docs/rag/estrategia-rag.md)
- [`docs/seguranca/autenticacao-e-seguranca.md`](docs/seguranca/autenticacao-e-seguranca.md)
- [`docs/testes/estrategia-de-testes.md`](docs/testes/estrategia-de-testes.md)
- [`docs/deploy/ambiente-de-desenvolvimento.md`](docs/deploy/ambiente-de-desenvolvimento.md)

## Gitflow

O versionamento segue Gitflow, com branches de funcionalidade, correção,
documentação e testes separadas por escopo. Exemplos:

```text
feature/adicionar-rota-rag
fix/corrigir-validacao-rank
docs/documentar-openai
test/cobrir-carregamento-sprints
```

Mensagens de commit devem ser claras, em português e focadas na alteração
realizada.
