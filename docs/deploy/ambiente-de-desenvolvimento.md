# Ambiente de desenvolvimento

## Objetivo

O ambiente local deve ser executável com Docker Compose e conter as dependências gerenciadas pela API.

## Serviços previstos

Serviços esperados conforme as decisões arquiteturais:

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

O `docker-compose.yml` deve ser atualizado quando Redis e ChromaDB forem integrados de fato. Não adicionar serviços sem uso real na aplicação.

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
poetry run pytest
```

## Gitflow

Mudanças devem seguir nomenclatura Gitflow:

- `feature/adicionar-rota-rag`;
- `feature/gerar-resumo-sprint`;
- `fix/corrigir-validacao-rank`;
- `docs/documentar-openai`;
- `test/cobrir-carregamento-sprints`.

Commits devem ser em português e descrever a mudança de forma objetiva.
