# Tarefa 04: Integração com OpenAI

**Status:** concluída

## Objetivo

Criar camada testável para chamadas de LLM e embeddings da OpenAI.

## Requisitos atendidos

- Uso de LLM para respostas e resumos.
- Uso de embeddings para RAG.
- Chave via variável de ambiente.
- Timeout e tratamento de falhas.
- Integração mockável.
- Prompts controlados.

## Subtarefas

- Adicionar dependência oficial da OpenAI.
- Criar wrapper interno para LLM.
- Criar wrapper interno para embeddings.
- Ler `OPENAI_API_KEY`, `OPENAI_LLM_MODEL`, `OPENAI_EMBEDDING_MODEL` e `OPENAI_TIMEOUT_SECONDS`.
- Impedir execução sem chave quando a funcionalidade depender da OpenAI.
- Definir timeout por chamada.
- Tratar rate limit.
- Tratar erro de autenticação.
- Tratar indisponibilidade.
- Tratar timeout.
- Sanitizar mensagens de erro.
- Criar mocks para testes.

## Decisões técnicas

- Routers não devem chamar OpenAI diretamente.
- Serviços devem depender de interface interna.
- O modelo exato deve ser configurável por ambiente e confirmado na documentação oficial no momento da implementação.
- Prompts devem separar instruções, contexto e pergunta.

## Testes necessários

- Wrapper envia parâmetros esperados para cliente mockado.
- Erro de rate limit vira erro de domínio.
- Erro de autenticação não expõe segredo.
- Timeout é tratado.
- Serviços usam mock sem chamada real.

## Critérios de aceite

- Nenhum teste unitário chama a OpenAI real.
- Nenhuma chave é registrada em log.
- Falhas externas têm resposta e log adequados.
