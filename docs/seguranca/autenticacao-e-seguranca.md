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
`POST /v1/resumos` já gera respostas consultivas com base nos dados de sprint.

A interface estática é servida por um contêiner Nginx separado e não constitui
uma rota de negócio FastAPI. O modelo HTML versionado não contém dados de sprint
nem credenciais reais. Toda obtenção de dados continua ocorrendo nas rotas
protegidas sob `/v1`.

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

Para reduzir abuso e custo da OpenAI, a API aplica rate limiting em rotas de
negócio usando Redis. A identidade padrão é o token autenticado, convertido em
chave hasheada antes de ser enviado ao Redis.

Variáveis:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_FAIL_OPEN=true
```

Quando o limite é excedido, a API retorna `429 Too Many Requests` com
`Retry-After`. Se Redis estiver indisponível, `RATE_LIMIT_FAIL_OPEN=true`
permite degradar sem derrubar a API; use `false` quando a política operacional
exigir falha fechada.

## Segredos

Não podem ser expostos em logs, erros, arquivos versionados ou respostas de
negócio:

- `OPENAI_API_KEY`;
- `AUTH_TOKEN`;
- tokens de usuário;
- URLs com credenciais;
- prompts completos quando contiverem dados sensíveis.

Logs e respostas HTTP de negócio devem ser sanitizados. A entrega controlada de
`AUTH_TOKEN` no documento da interface é a exceção operacional descrita abaixo;
por isso, esse token não deve ser considerado secreto para quem puder acessar o
frontend.

## Segurança da interface web

O serviço `frontend` recebe `AUTH_TOKEN` por variável de ambiente. Ao iniciar, um
script codifica o valor em Base64 e o injeta no metadado `api-auth-token` do HTML
gerado dentro do contêiner. O JavaScript decodifica o valor e o usa somente para
montar o header `Authorization`, sem campo de digitação e sem persistência em
`localStorage`, `sessionStorage`, cookies ou parâmetros de URL. Nenhum valor real
é mantido no arquivo versionado.

Base64 protege a estrutura do atributo HTML contra caracteres especiais, mas
não oculta a credencial de quem recebe a página. Portanto, a interface deve ser
restrita a usuários confiáveis. Um ambiente público ou multiusuário deve trocar
esse fluxo por sessão segura, credenciais individuais ou provedor de identidade.

Conteúdo retornado pela API é criado com `textContent` e APIs de nós do DOM, sem
uso de `innerHTML`. Essa decisão impede que texto malicioso presente em uma
sprint seja interpretado como marcação executável.

O Nginx do frontend envia os seguintes controles defensivos:

- Content Security Policy restrita à própria origem;
- bloqueio de incorporação por frames;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`;
- bloqueio de câmera, microfone e geolocalização.

O ambiente do Compose usa HTTP apenas para desenvolvimento local. Em produção,
o frontend e a API devem ser publicados atrás de TLS, o token deve ser
individual e rotacionável, e a autenticação simples pode evoluir para OAuth2 ou
outro provedor de identidade.
