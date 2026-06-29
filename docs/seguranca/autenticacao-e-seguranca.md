# Autenticação e segurança

## Autenticação

Todas as rotas de negócio devem exigir Bearer token.

Exemplo de header:

```http
Authorization: Bearer <token-de-acesso>
```

O token real deve vir exclusivamente de `AUTH_TOKEN`. Não deve existir token hardcoded no código, testes, documentação operacional, `README.md`, `compose` ou arquivos versionados.

## Rotas públicas

Somente rotas de saúde podem ser públicas:

- `GET /health`;
- `GET /healthz`, se vier a existir;
- `GET /ready`, se vier a existir.

## Configuração por ambiente

`AUTH_ENABLED` pode existir para facilitar testes e desenvolvimento controlado, mas não deve permitir bypass em produção. Em produção, rotas de negócio devem permanecer autenticadas.

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
