# Trabalho Final API

Estrutura inicial da API do trabalho final da disciplina de Construção de APIs para Inteligência Artificial.

Nesta etapa a aplicação contém apenas uma base FastAPI executável, sem implementação dos requisitos de negócio ou dos serviços de IA.

## Executar com Docker Compose

```bash
docker compose up --build
```

A API ficará disponível em:

- `http://localhost:8000`
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## Executar localmente com Poetry

```bash
poetry install
poetry run uvicorn app.main:app --reload
```
