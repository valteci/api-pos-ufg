# Ambiente de desenvolvimento

## Objetivo

O ambiente local deve ser executável com Docker Compose e conter as dependências gerenciadas pela API.

## Serviços previstos

Serviços declarados ou previstos conforme as decisões arquiteturais:

- `frontend`: Nginx que serve a interface web e encaminha chamadas para a API.
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
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_FAIL_OPEN=true

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

## Base documental versionada

Os 20 documentos de sprint em `data/` são versionados junto com o código-fonte.
Os embeddings exportados em `data/embeddings/` também acompanham o repositório
para permitir a carga automática do ChromaDB. Portanto, depois de clonar o projeto,
o único arquivo que precisa ser recebido separadamente é o `.env`, pois ele contém
as configurações e os segredos usados na demonstração.

Quando os documentos forem modificados, a base e os embeddings reexportados devem
ser versionados na mesma mudança para evitar que a aplicação carregue vetores
antigos.

## Compose

O `docker-compose.yml` carrega variáveis a partir de `.env` com `env_file`. As
variáveis essenciais `AUTH_TOKEN`, `OPENAI_API_KEY`, `OPENAI_LLM_MODEL` e
`OPENAI_EMBEDDING_MODEL` são repassadas explicitamente para o serviço `api` e
não têm fallback hardcoded. `AUTH_TOKEN` também é repassado isoladamente ao
serviço `frontend`; as credenciais da OpenAI não chegam a esse contêiner. Valores
não secretos usam defaults seguros. O diretório versionado `data/` é montado como
leitura em `/app/data`, alinhado ao `DATA_DIR` padrão.

O serviço `chromadb` está declarado para persistir embeddings em volume Docker
nomeado e fica acessível pela API em `http://chromadb:8000`. Para acesso local
do host, a porta exposta é `http://localhost:8001`.

O serviço `redis` está declarado para cache de respostas e rate limiting. Ele
fica acessível pela API em `redis://redis:6379/0` e pelo host em
`localhost:6379`. O cache usa TTL configurável e falha de Redis degrada para
execução normal quando possível. O rate limiting usa token autenticado como
identidade e pode falhar aberto ou fechado conforme `RATE_LIMIT_FAIL_OPEN`.

O serviço `frontend` publica a porta `3000`, monta `index.html` como modelo fora
do document root e gera a cópia servida pelo Nginx com o token de ambiente em um
metadado. O diretório `assets/` fica no document root, enquanto a configuração
do Nginx e o script de preparação são montados separadamente. O proxy reverso
converte chamadas como `/api/v1/resumos` em `/v1/resumos` no serviço `api`, sem
remover a exigência do Bearer token. A pasta também é montada como somente
leitura em `/app/frontend` no contêiner da API para que a suíte completa possa
validar os arquivos estáticos no mesmo ambiente de testes.

## Interface web

Em desenvolvimento, a interface fica disponível em:

```text
http://localhost:3000
```

O frontend não possui etapa de compilação nem gerenciador de pacotes. Alterações
em `frontend/assets/` são refletidas após recarregar a página. Mudanças em
`frontend/index.html` ou em `AUTH_TOKEN` exigem recriar o contêiner `frontend`
para gerar novamente o documento. O Nginx aplica Content Security Policy e
outros cabeçalhos defensivos definidos em `frontend/nginx.conf`.

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
