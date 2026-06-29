# Tarefa 01: Configuração base e estrutura

**Status:** concluída

## Objetivo

Preparar a base da aplicação FastAPI para receber as funcionalidades de sprints, OpenAI, RAG, autenticação, logs e testes.

## Requisitos atendidos

- Organização em camadas.
- Configuração por variáveis de ambiente.
- Documentação OpenAPI automática.
- Base testável.

## Subtarefas

- Criar módulos de `api`, `core`, `domain`, `schemas`, `services`, `integrations` e `infrastructure`.
- Implementar configuração central com variáveis de ambiente.
- Definir valores padrão apenas para parâmetros não secretos.
- Garantir que segredos não tenham fallback hardcoded.
- Versionar rotas de negócio sob `/v1`.
- Manter `GET /health` público.
- Preparar injeção de dependências do FastAPI.
- Adicionar dependências necessárias no `pyproject.toml`.

## Decisões técnicas

- Usar FastAPI como framework HTTP.
- Usar Pydantic para schemas e configuração.
- Separar handlers HTTP das regras de negócio.
- Manter `app/main.py` apenas como composição da aplicação.

## Critérios de aceite

- Aplicação inicia localmente.
- Swagger/OpenAPI continua disponível em desenvolvimento.
- Configurações são carregadas por ambiente.
- Nenhum segredo é codificado.
- Estrutura criada permite testes isolados.
