# Backlog de implementação

Este diretório descreve as tarefas necessárias para implementar os requisitos da API.

## Ordem sugerida

1. [Configuração base e estrutura](01-configuracao-base-e-estrutura.md)
2. [Carregamento e validação de sprints](02-carregamento-e-validacao-de-sprints.md)
3. [Autenticação e segurança base](03-autenticacao-e-seguranca-base.md)
4. [Integração com OpenAI](04-integracao-com-openai.md)
5. [Chunking e indexação vetorial](05-chunking-e-indexacao-vetorial.md)
6. [Rota de RAG](06-rota-de-rag.md)
7. [Rota de resumos](07-rota-de-resumos.md)
8. [Cache e rate limiting com Redis](08-cache-e-rate-limiting-com-redis.md)
9. [Logs e tratamento de erros](09-logs-e-tratamento-de-erros.md)
10. [Testes automatizados](10-testes-automatizados.md)
11. [Compose e ambiente local](11-compose-e-ambiente-local.md)
12. [README, OpenAPI e documentação final](12-readme-openapi-e-documentacao-final.md)

## Convenção de status

Cada tarefa deve ser movida para concluída apenas quando:

- código foi implementado;
- testes foram criados ou atualizados;
- testes passaram;
- documentação relacionada foi atualizada;
- nenhum segredo foi adicionado;
- rotas de negócio permanecem autenticadas;
- logs e erros foram tratados quando aplicável.
