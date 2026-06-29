# Estratégia de testes

## Objetivo

Os testes devem garantir que regras de negócio, validações, autenticação, leitura de dados, RAG, resumo, erros e integrações estejam cobertos sem depender de serviços externos reais por padrão.

## Organização recomendada

```text
tests/
├── fixtures/
├── unit/
├── services/
├── routes/
└── integration/
```

## Testes unitários

Devem cobrir:

- carregamento de sprints;
- validação de JSON;
- normalização de tarefas e subtarefas;
- chunking;
- montagem segura de prompts;
- validação de limites de RAG;
- seleção de sprints;
- tratamento de erros de domínio;
- cache com fake Redis;
- cliente OpenAI com mocks;
- banco vetorial com fake.

## Testes de rotas

Devem cobrir:

- `GET /health` público;
- `POST /v1/resumos` autenticado;
- `POST /v1/rag` autenticado;
- ausência de token;
- token inválido;
- payload válido;
- payload inválido;
- sprint não encontrada;
- resposta de erro sem stack trace;
- exemplos compatíveis com OpenAPI.

## Testes de integração

Testes que dependem de Redis ou ChromaDB reais devem ser marcados explicitamente e não devem ser obrigatórios no fluxo unitário padrão.

Chamadas reais à OpenAI não devem ocorrer por padrão.

## Fixtures

Fixtures devem representar:

- sprint válida com tarefas e subtarefas;
- sprint válida com tarefa sem subtarefa;
- sprint com campos extras;
- sprint vazia;
- JSON inválido;
- conjunto com múltiplas sprints;
- resposta simulada da OpenAI;
- resultados simulados do banco vetorial.

## Critério de aceite

Uma mudança funcional só deve ser considerada pronta quando os testes relacionados forem criados ou atualizados e passarem localmente.
