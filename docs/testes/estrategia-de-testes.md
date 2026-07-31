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

## Testes da interface web

`tests/test_interface_web.py` valida sem navegador ou serviços externos:

- presença dos formulários de resumo e RAG;
- unicidade dos identificadores HTML;
- chamadas aos endpoints corretos com header Bearer;
- injeção codificada do token de ambiente no metadado;
- ausência do campo de digitação do token e da marca visual;
- ausência de persistência do token no navegador;
- renderização sem `innerHTML`;
- cabeçalhos defensivos e proxy reverso do Nginx;
- publicação segura dos arquivos estáticos no Compose.

A sintaxe do JavaScript também pode ser verificada com `node --check
frontend/assets/app.js` quando Node.js estiver disponível. Testes ponta a ponta
em navegador podem ser adicionados no futuro caso o projeto adote uma
ferramenta específica para esse fim.

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
