# Tarefa 08: Cache e rate limiting com Redis

## Objetivo

Reduzir custo, latência e abuso da API usando Redis quando aplicável.

## Requisitos atendidos

- Cache opcional com Redis.
- TTL configurável.
- Chaves sem dados sensíveis.
- Invalidação compatível com atualização de dados.
- Rate limiting para reduzir abuso.

## Subtarefas

- Adicionar dependência de cliente Redis.
- Criar wrapper interno para Redis.
- Ler `REDIS_URL`, `CACHE_ENABLED` e `CACHE_TTL_SECONDS`.
- Implementar cache para consultas repetíveis de RAG e resumos quando seguro.
- Usar hash nos parâmetros da chave.
- Incluir versão do índice ou assinatura dos dados na chave.
- Implementar invalidação por reindexação.
- Implementar rate limiting por IP ou token.
- Tratar Redis indisponível sem derrubar a API quando cache for opcional.
- Criar fake Redis para testes.

## Decisões técnicas

- Cache não deve ser fonte de verdade.
- Falha de cache deve degradar para execução normal quando possível.
- Rate limiting pode falhar fechado ou aberto conforme configuração documentada.

## Testes necessários

- Cache hit evita chamada externa.
- Cache miss executa serviço e grava resultado.
- TTL é aplicado.
- Chave não contém mensagem em texto puro.
- Mudança de versão do índice evita resposta antiga.
- Redis indisponível é tratado.
- Rate limit bloqueia excesso.

## Critérios de aceite

- Cache tem documentação operacional.
- Não há dados sensíveis nas chaves.
- Testes cobrem hit, miss, falha e rate limit.
