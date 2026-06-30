# Ambiente de desenvolvimento

## Objetivo

O ambiente local deve ser executável com Docker Compose e conter as dependências gerenciadas pela API.

## Serviços previstos

Serviços declarados ou previstos conforme as decisões arquiteturais:

- `api`: aplicação FastAPI.
- `redis`: cache e rate limiting, quando habilitados.
- `chromadb`: banco vetorial para embeddings e RAG.

## Variáveis de ambiente

Variáveis previstas:

```env
APP_ENV=development
APP_NAME=api-sprints-ia
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/api.json

AUTH_ENABLED=true
AUTH_TOKEN=

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_PAYLOAD_BYTES=1048576

OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
OPENAI_TIMEOUT_SECONDS=30

REDIS_URL=redis://redis:6379/0
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300

VECTOR_DB_URL=http://chromadb:8000
VECTOR_DB_COLLECTION=sprints
EMBEDDINGS_ENABLED=true

DATA_DIR=data
MAX_RAG_RANK=10
MAX_FRAGMENT_SIZE=3000
MAX_MESSAGE_LENGTH=4000
MAX_SPRINTS_PER_REQUEST=20
```

Segredos devem ser preenchidos em `.env` local não versionado. `.env.example` pode existir apenas com valores fictícios.

## Compose

O `docker-compose.yml` carrega variáveis a partir de `.env` com `env_file`. As
variáveis essenciais `AUTH_TOKEN`, `OPENAI_API_KEY`, `OPENAI_LLM_MODEL` e
`OPENAI_EMBEDDING_MODEL` são repassadas explicitamente para o serviço `api` e
não têm fallback hardcoded. Valores não secretos usam defaults seguros. O
diretório `data/` é montado como leitura em `/app/data`, alinhado ao `DATA_DIR`
padrão.

O serviço `chromadb` está declarado para persistir embeddings em volume Docker
nomeado e fica acessível pela API em `http://chromadb:8000`. Para acesso local
do host, a porta exposta é `http://localhost:8001`.

## Swagger e OpenAPI

Em desenvolvimento, a documentação interativa deve ficar disponível em:

```text
http://localhost:8000/docs
```

O OpenAPI JSON deve ficar disponível em:

```text
http://localhost:8000/openapi.json
```

## Comandos previstos

Comandos finais devem ser confirmados após implementação:

```bash
docker compose up --build
docker compose down
poetry install
poetry run python -m unittest discover -s tests
docker compose exec api python -m app.cli.indexar_vetores --reindexar
```

## Gitflow

Mudanças devem seguir nomenclatura Gitflow:

- `feature/adicionar-rota-rag`;
- `feature/gerar-resumo-sprint`;
- `fix/corrigir-validacao-rank`;
- `docs/documentar-openai`;
- `test/cobrir-carregamento-sprints`.

Commits devem ser em português e descrever a mudança de forma objetiva.
