# Estratégia de RAG

## Objetivo

O RAG deve recuperar os fragmentos mais relevantes dos dados de sprints a partir de uma mensagem do usuário e de um escopo de sprints.

Ele deve ser rápido o suficiente para uso interativo e testável sem chamadas reais à OpenAI ou ao banco vetorial.

## Fluxo de indexação

Fluxo proposto:

1. Ler os arquivos JSON em `data/`.
2. Validar e normalizar sprints, tarefas e subtarefas.
3. Transformar itens normalizados em texto controlado.
4. Quebrar textos em fragmentos com metadados.
5. Gerar embeddings dos fragmentos.
6. Gravar embeddings e metadados no ChromaDB.
7. Registrar versão ou assinatura dos dados indexados.

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

## Chunking

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

## Filtros

Quando `sprints` vier vazia, a busca deve considerar todos os documentos indexados.

Quando `sprints` vier preenchida, o banco vetorial deve filtrar apenas essas sprints. A aplicação não deve recuperar dados de sprints fora do escopo solicitado.

## Reindexação

A implementação deve prever comando ou fluxo documentado para:

- gerar índice inicial;
- atualizar índice quando arquivos em `data/` mudarem;
- limpar índice;
- reconstruir índice completo.

Enquanto a reindexação não for automatizada por watcher, o `README.md` deve explicar quando executar o processo manualmente.

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
