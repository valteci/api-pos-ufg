# Autenticação e segurança

## Autenticação

Todas as rotas de negócio devem exigir Bearer token.

Exemplo de header:

```http
Authorization: Bearer <token-de-acesso>
```

O token real deve vir exclusivamente de `AUTH_TOKEN`. Não deve existir token hardcoded no código, testes, documentação operacional, `README.md`, `compose` ou arquivos versionados.

A implementação atual aplica autenticação no router versionado `/v1`.
`POST /v1/rag` já executa recuperação de fragmentos sobre o índice vetorial e
`POST /v1/resumos` segue protegida, retornando `501 Not Implemented` até a
implementação funcional de resumos.

Falhas de autenticação retornam `401 Unauthorized` com `WWW-Authenticate:
Bearer`. O valor recebido no header `Authorization` não é retornado ao cliente
nem registrado em log.

## Rotas públicas

Somente rotas de saúde podem ser públicas:

- `GET /health`;
- `GET /healthz`, se vier a existir;
- `GET /ready`, se vier a existir.

## Configuração por ambiente

`AUTH_ENABLED` pode existir para facilitar testes e desenvolvimento controlado, mas não deve permitir bypass em produção. Em produção, rotas de negócio devem permanecer autenticadas.

Quando `APP_ENV=production`, a aplicação exige autenticação mesmo que
`AUTH_ENABLED=false` seja configurado por engano.

## Validação de entrada

Todos os payloads devem ser validados com Pydantic.

Validações obrigatórias:

- mensagem obrigatória, não vazia e com limite máximo;
- `rank` inteiro, positivo e limitado;
- `tamanho_fragmento` inteiro, positivo e limitado;
- `sprints` como lista;
- limite de quantidade de sprints por requisição;
- rejeição de payloads excessivamente grandes.

## Prompt injection

A aplicação deve separar:

- instruções internas do sistema;
- contexto recuperado dos arquivos;
- pergunta do usuário.

Mensagem do usuário e dados de sprint devem ser tratados como dados não confiáveis. O prompt deve instruir o modelo a responder apenas com base no contexto fornecido.

## CORS

CORS deve ser restritivo por padrão. Origens permitidas devem vir de variável de ambiente, como `CORS_ALLOWED_ORIGINS`.

Não usar `*` em produção.

A configuração atual usa `CORS_ALLOWED_ORIGINS` como lista separada por vírgula.
Quando a variável fica vazia, nenhuma origem de navegador é liberada por padrão.
Em produção, a aplicação rejeita inicialização com `*`.

## Limite de payload

`MAX_PAYLOAD_BYTES` define o maior payload aceito pela API. Requisições com
`Content-Length` acima desse limite retornam `413 Payload Too Large` antes de
chegar aos handlers de negócio.

## Rate limiting

Para reduzir abuso e custo da OpenAI, a implementação deve prever rate limiting por IP ou token. Redis é a opção recomendada quando o recurso for implementado.

## Segredos

Não podem ser expostos:

- `OPENAI_API_KEY`;
- `AUTH_TOKEN`;
- tokens de usuário;
- URLs com credenciais;
- prompts completos quando contiverem dados sensíveis.

Logs e respostas HTTP devem ser sanitizados.
