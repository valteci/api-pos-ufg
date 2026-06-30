# Estratégia de RAG

## Objetivo

O RAG deve recuperar os fragmentos mais relevantes dos dados de sprints a partir de uma mensagem do usuário e de um escopo de sprints.

Ele deve ser rápido o suficiente para uso interativo e testável sem chamadas reais à OpenAI ou ao banco vetorial.

## Fluxo de indexação implementado

O fluxo atual de indexação fica em `app/services/indexacao_vetorial.py`:

1. Ler os arquivos JSON em `data/`.
2. Validar e normalizar sprints, tarefas e subtarefas.
3. Transformar itens normalizados em texto controlado.
4. Quebrar textos em fragmentos com metadados.
5. Gerar embeddings dos fragmentos.
6. Gravar embeddings e metadados no ChromaDB.
7. Registrar assinatura determinística dos dados indexados.

O comando operacional fica em `app/cli/indexar_vetores.py`:

```bash
python -m app.cli.indexar_vetores --reindexar
python -m app.cli.indexar_vetores --sprint sprint-75
python -m app.cli.indexar_vetores --limpar
```

No ambiente Docker Compose, use:

```bash
docker compose exec api python -m app.cli.indexar_vetores --reindexar
```

## Fluxo de consulta

Fluxo proposto para `POST /v1/rag`:

1. Validar autenticação.
2. Validar payload com Pydantic.
3. Resolver escopo de sprints.
4. Rejeitar sprints inexistentes.
5. Gerar embedding da mensagem.
6. Consultar o banco vetorial filtrando pelas sprints solicitadas.
7. Recuperar `rank` fragmentos.
8. Aplicar limite de `tamanho_fragmento` em cada fragmento retornado.
9. Retornar fragmentos com score e metadados.
10. Registrar log estruturado da consulta.

## Chunking implementado

O chunking deve preservar sentido de negócio. Sempre que possível, uma tarefa e suas subtarefas devem ficar próximas no texto, sem misturar dados de sprints diferentes no mesmo fragmento.

Cada fragmento deve conter metadados:

- `sprint`;
- `origem`;
- `tipo`;
- `caminho`;
- `titulo_tarefa`, quando disponível;
- `titulo_subtarefa`, quando disponível;
- `status`, quando disponível;
- `responsavel`, quando disponível.

A implementação cria fragmentos de tarefa e de subtarefa. O fragmento da tarefa
inclui um resumo das subtarefas para preservar contexto de negócio. Subtarefas
também recebem fragmento próprio, com referência ao título da tarefa pai. Campos
extras do JSON são serializados em ordem estável para manter indexação
reproduzível sem quebrar quando exportações trazem campos inesperados.

## Filtros

Quando `sprints` vier vazia, a busca deve considerar todos os documentos indexados.

Quando `sprints` vier preenchida, o banco vetorial deve filtrar apenas essas sprints. A aplicação não deve recuperar dados de sprints fora do escopo solicitado.

## Banco vetorial

O acesso ao banco vetorial fica em `app/integrations/vector_store.py`.

Implementações disponíveis:

- `BancoVetorialChromaDB`: integração HTTP com ChromaDB para desenvolvimento.
- `BancoVetorialFake`: fake em memória para testes unitários e serviços sem
  ChromaDB real.

Variáveis usadas:

```env
VECTOR_DB_URL=http://chromadb:8000
VECTOR_DB_COLLECTION=sprints
EMBEDDINGS_ENABLED=true
```

## Reindexação

Fluxos disponíveis:

- gerar índice inicial: `python -m app.cli.indexar_vetores --reindexar`;
- atualizar sprint específica: `python -m app.cli.indexar_vetores --sprint sprint-75`;
- limpar índice: `python -m app.cli.indexar_vetores --limpar`;
- reconstruir índice completo: `python -m app.cli.indexar_vetores --reindexar`.

Enquanto não houver watcher automático, a reindexação deve ser executada
manualmente sempre que arquivos em `data/` forem criados, alterados ou
removidos.

## Cache

Consultas RAG podem usar Redis para cache quando `CACHE_ENABLED=true`.

A chave de cache deve considerar:

- mensagem normalizada;
- lista de sprints resolvida;
- `rank`;
- `tamanho_fragmento`;
- versão ou assinatura do índice.

O cache deve ter TTL e não pode retornar resposta incompatível com dados reindexados.

## Testabilidade

Testes unitários devem usar fakes para:

- cliente de embeddings;
- banco vetorial;
- cache Redis.

Testes de contrato da rota devem validar payloads, autenticação, erros e resposta sem depender de serviços reais.
