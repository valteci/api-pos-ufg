# API de sprints com IA

API FastAPI para consulta, sumarização e recuperação de informações sobre
sprints de uma squad de desenvolvimento.

Nesta etapa a aplicação contém a base FastAPI, carregamento validado de arquivos
de sprint, segurança inicial por Bearer token, wrapper interno para OpenAI e
infraestrutura de chunking/indexação vetorial com ChromaDB. As rotas `/v1/rag`
e `/v1/resumos` já estão protegidas, mas ainda retornam `501 Not Implemented`
até as tarefas funcionais de RAG e resumos serem concluídas.

## Configurar ambiente

Crie um `.env` local a partir de `.env.sample` e preencha os valores essenciais:

```env
AUTH_TOKEN=
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
VECTOR_DB_URL=http://chromadb:8000
VECTOR_DB_COLLECTION=sprints
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

## Executar com Docker Compose

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
- ChromaDB HTTP em `http://localhost:8001`

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
