# Tarefa 03: Autenticação e segurança base

## Objetivo

Proteger rotas de negócio e aplicar validações iniciais de segurança.

## Requisitos atendidos

- Rotas de negócio autenticadas.
- Healthcheck público.
- Tokens por variável de ambiente.
- Sem exposição de credenciais.
- CORS restritivo.
- Limites contra payloads abusivos.

## Subtarefas

- Implementar dependência de autenticação Bearer token.
- Ler `AUTH_TOKEN` de variável de ambiente.
- Bloquear rotas de negócio sem token.
- Bloquear token inválido.
- Manter `GET /health` sem autenticação.
- Configurar CORS por lista de origens permitidas.
- Definir limites de tamanho de payload e campos textuais.
- Garantir que logs não exibam tokens.
- Criar testes de autenticação.

## Decisões técnicas

- Começar com Bearer token simples.
- Não permitir bypass de autenticação em produção.
- Evolução futura para OAuth2 ou JWT pode ocorrer sem alterar regras de negócio.

## Testes necessários

- Healthcheck sem token retorna sucesso.
- RAG sem token retorna erro.
- Resumos sem token retorna erro.
- Token inválido retorna erro.
- Token válido permite acesso.

## Critérios de aceite

- Não existe rota de negócio pública.
- Credenciais não aparecem em logs nem respostas.
- Validações de segurança estão cobertas por testes.
