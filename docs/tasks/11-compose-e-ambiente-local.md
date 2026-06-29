# Tarefa 11: Compose e ambiente local

## Objetivo

Garantir que a aplicação e suas dependências possam rodar localmente via Docker Compose.

## Requisitos atendidos

- Projeto executável via compose.
- Dependências gerenciadas declaradas no compose.
- Sem segredos reais no compose.
- `.env.example` com valores fictícios.

## Subtarefas

- Atualizar `docker-compose.yml` para serviços realmente usados.
- Adicionar Redis quando cache ou rate limiting forem implementados.
- Adicionar ChromaDB quando banco vetorial for implementado.
- Montar `data/` no container da API.
- Montar `logs/` no container da API.
- Documentar variáveis em `.env.example`.
- Garantir que `.env` não seja versionado.
- Documentar comandos de subida e derrubada.
- Validar healthcheck em ambiente local.

## Decisões técnicas

- Não adicionar serviço ao compose antes de haver uso real na aplicação.
- Segredos devem vir do ambiente local.
- Volumes devem permitir desenvolvimento sem rebuild para código e dados quando adequado.

## Testes ou verificações necessárias

- `docker compose up --build` inicia a API.
- `/health` responde.
- Swagger fica acessível.
- Redis e ChromaDB sobem quando integrados.

## Critérios de aceite

- Ambiente local é reproduzível.
- Compose não contém segredo real.
- Documentação operacional está atualizada.
