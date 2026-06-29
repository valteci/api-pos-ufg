# Tarefa 05: Chunking e indexação vetorial

## Objetivo

Transformar dados de sprints em fragmentos indexáveis por embeddings.

## Requisitos atendidos

- Embeddings gerados a partir de `data/`.
- Indexação reproduzível.
- Banco vetorial documentado.
- Reindexação clara.
- Testes sem ChromaDB real por padrão.

## Subtarefas

- Criar serviço de chunking.
- Converter tarefas e subtarefas em texto normalizado.
- Preservar metadados de sprint, origem, tipo e caminho.
- Garantir que fragmentos não misturem sprints diferentes.
- Criar interface de banco vetorial.
- Implementar integração com ChromaDB.
- Criar comando ou serviço de indexação.
- Criar estratégia de limpeza do índice.
- Criar estratégia de reindexação.
- Registrar logs de indexação.
- Criar fake de banco vetorial para testes.

## Decisões técnicas

- Usar ChromaDB no ambiente de desenvolvimento.
- Manter interface interna para permitir troca do banco vetorial.
- O índice deve depender exclusivamente de `data/`.

## Testes necessários

- Chunking preserva metadados.
- Chunking aceita tarefa sem subtarefa.
- Indexação chama embeddings com textos esperados.
- Reindexação substitui dados antigos.
- Fake vetorial permite teste sem serviço real.

## Critérios de aceite

- Processo de indexação é reproduzível.
- Mudança em `data/` tem caminho documentado de reindexação.
- Testes não dependem de ChromaDB real por padrão.
