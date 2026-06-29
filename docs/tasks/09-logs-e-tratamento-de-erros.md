# Tarefa 09: Logs e tratamento de erros

## Objetivo

Padronizar logs estruturados, request ID e respostas de erro seguras.

## Requisitos atendidos

- Logs em JSON.
- Logs em `stdout` e `logs/api.json`.
- Logs sem segredos.
- Tratamento robusto de erros.
- Respostas sem stack trace em produção.

## Subtarefas

- Configurar logger estruturado.
- Garantir criação ou montagem de `logs/api.json`.
- Implementar middleware de request ID.
- Logar início e fim de requisições.
- Criar exceções de domínio.
- Criar handlers HTTP centralizados.
- Mapear erros de validação, autenticação, dados, OpenAI, Redis e ChromaDB.
- Sanitizar mensagens de erro.
- Testar que stack trace não aparece na resposta.
- Testar logs principais quando viável.

## Decisões técnicas

- Cada evento relevante deve ter nome estável em português técnico.
- Dados sensíveis devem ser substituídos por identificadores, contagens, tamanhos ou hashes.
- O cliente deve receber mensagem clara, mas sem detalhes internos.

## Testes necessários

- Erro de domínio vira status correto.
- Erro interno vira `500` seguro.
- Erro externo vira `502` ou `504`.
- Falha de validação retorna `422`.
- Resposta contém `request_id` quando definido.

## Critérios de aceite

- Logs são JSON válidos.
- Erros principais têm cobertura.
- Nenhum segredo é logado.
