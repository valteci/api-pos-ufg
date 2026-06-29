# Integração com OpenAI

## Objetivo

A aplicação usa a OpenAI por meio de uma camada interna em
`app/integrations/openai_client.py`. Routers e serviços de negócio não devem
chamar o SDK oficial diretamente.

## Dependência

O projeto usa o pacote oficial `openai`, declarado no `pyproject.toml` e travado
no `poetry.lock`.

## Configuração

Variáveis essenciais:

```env
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
OPENAI_TIMEOUT_SECONDS=30
```

`OPENAI_API_KEY` não possui fallback no código. Os modelos também são lidos do
ambiente para permitir troca por custo, qualidade e disponibilidade sem mudar
código.

O `docker-compose.yml` repassa essas variáveis para o serviço `api`. Valores
reais devem ficar no `.env` local, que não é versionado.

## LLM

O método `gerar_resposta` usa a Responses API do SDK oficial. A chamada recebe:

- `OPENAI_LLM_MODEL` como modelo;
- instruções de sistema controladas pela aplicação;
- instruções internas para responder apenas com base no contexto;
- contexto e pergunta delimitados como dados não confiáveis.

Essa separação reduz risco de prompt injection e evita que dados das sprints ou
mensagens do usuário sobrescrevam instruções internas.

## Embeddings

O método `gerar_embedding` usa `embeddings.create` com
`OPENAI_EMBEDDING_MODEL` e `encoding_format="float"`. Esse wrapper será usado
pelas tarefas de chunking, indexação e RAG.

## Timeout

Cada chamada usa `with_options(timeout=OPENAI_TIMEOUT_SECONDS)` quando o SDK
disponibiliza essa API. O cliente oficial também é criado com o mesmo timeout e
`max_retries=0`, deixando retentativas explícitas para camadas futuras caso
sejam necessárias.

## Erros tratados

Falhas do SDK são convertidas para erros de domínio sanitizados:

- rate limit: `OpenAIRateLimitError`;
- autenticação inválida: `OpenAIAuthenticationError`;
- timeout: `OpenAITimeoutError`;
- indisponibilidade ou falha de conexão: `OpenAIIndisponivelError`;
- resposta vazia ou inesperada: `OpenAIRespostaInvalidaError`;
- erro externo genérico: `OpenAIIntegracaoError`.

Mensagens originais do SDK não são repassadas ao cliente nem registradas em log,
pois podem conter dados sensíveis.

## Logs

O wrapper registra eventos JSON para:

- `chamada_openai_iniciada`;
- `chamada_openai_concluida`;
- `falha_openai`.

Os logs incluem operação, modelo, código de erro e status HTTP quando existir,
mas não incluem `OPENAI_API_KEY`, prompts completos, contexto integral ou
mensagem original de exceção.

## Testes

Os testes em `tests/test_integracao_openai.py` usam um cliente fake compatível
com o SDK oficial. A suíte padrão não faz chamada real à OpenAI.

## Referências oficiais

- Responses API: https://platform.openai.com/docs/api-reference/responses/create
- Embeddings: https://platform.openai.com/docs/guides/embeddings
- SDK oficial Python: https://github.com/openai/openai-python
