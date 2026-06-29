# API de sprints com IA

API FastAPI para consulta, sumarização e recuperação de informações sobre
sprints de uma squad de desenvolvimento.

Nesta etapa a aplicação contém a base FastAPI, carregamento validado de arquivos
de sprint e segurança inicial por Bearer token. As rotas `/v1/rag` e
`/v1/resumos` já estão protegidas, mas ainda retornam `501 Not Implemented` até
as tarefas funcionais de RAG e resumos serem concluídas.

## Configurar ambiente

Crie um `.env` local a partir de `.env.sample` e preencha os valores essenciais:

```env
AUTH_TOKEN=
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
```

O token real deve ficar apenas no `.env` local ou no ambiente de execução. O
Compose carrega esse arquivo e repassa as variáveis para o container da API.

## Executar com Docker Compose

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

O `GET /health` é público. Rotas sob `/v1` exigem:

```http
Authorization: Bearer <token-de-acesso>
```

## Executar localmente com Poetry

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

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
