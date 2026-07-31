# Interface web

## Objetivo

A interface web permite usar as rotas de resumo e RAG pelo navegador. Ela não
duplica regras de negócio: todos os dados, validações definitivas, autenticação,
rate limiting e integrações continuam sob responsabilidade do FastAPI.

## Acesso

Com o ambiente iniciado por `docker compose up --build`, acesse:

```text
http://localhost:3000
```

O healthcheck exibido no cabeçalho consulta `GET /health` por meio do proxy. O
estado disponível confirma conectividade com a API, mas não valida o Bearer
token. A credencial é validada ao executar uma consulta de negócio.

## Fluxos disponíveis

### Resumo consultivo

O formulário envia para `POST /v1/resumos`:

- pergunta, obrigatória e limitada a 4000 caracteres;
- lista opcional de sprints, separadas por vírgula.

A resposta exibe a síntese, as sprints consultadas e as fontes rastreáveis
retornadas pela API.

### Busca RAG

O formulário envia para `POST /v1/rag`:

- mensagem, obrigatória e limitada a 4000 caracteres;
- lista opcional de sprints, separadas por vírgula;
- `rank`, entre 1 e 10;
- tamanho de cada fragmento, entre 1 e 3000 caracteres.

A resposta exibe os fragmentos na ordem recebida, o `score`, a origem e os
metadados associados. O frontend não interpreta o `score` como porcentagem.

## Arquitetura

```text
Navegador :3000
      |
      | HTML, CSS e JavaScript
      v
Nginx (frontend)
      |
      | /api/* por proxy reverso
      v
FastAPI (api:8000)
      |
      +-- OpenAI
      +-- ChromaDB
      +-- Redis
      +-- data/*.json
```

O documento define `/api` como base de comunicação. O Nginx remove esse prefixo
ao encaminhar a chamada na rede interna. Por exemplo,
`http://localhost:3000/api/v1/rag` chega ao FastAPI como `/v1/rag`.
O hostname do serviço é resolvido dinamicamente pelo DNS interno do Docker, de
forma que a recriação do contêiner da API não exija reiniciar o frontend.

Na inicialização, `frontend/preparar-index.sh` lê `AUTH_TOKEN`, codifica o valor
em Base64 e substitui o marcador do metadado `api-auth-token` no modelo HTML. O
arquivo versionado continua sem credencial real e somente o documento gerado
dentro do contêiner é servido pelo Nginx.

Arquivos principais:

- `frontend/index.html`: estrutura semântica, formulários e regiões de resposta;
- `frontend/assets/estilos.css`: layout responsivo e estados visuais;
- `frontend/assets/app.js`: validação, chamadas HTTP e renderização;
- `frontend/preparar-index.sh`: injeção da credencial no HTML gerado;
- `frontend/nginx.conf`: arquivos estáticos, proxy e cabeçalhos de segurança.

## Autenticação

O Compose repassa `AUTH_TOKEN` exclusivamente aos serviços `api` e `frontend`.
O navegador recebe o valor no metadado gerado e o JavaScript cria o header
abaixo em cada chamada de negócio:

```http
Authorization: Bearer <token-configurado>
```

Não há campo de token e o valor não é incluído no código versionado, nos
logs, na URL, em cookies ou em mecanismos persistentes do navegador. Como o
metadado faz parte do documento entregue ao cliente, qualquer pessoa com acesso
à interface pode inspecionar a credencial. Base64 evita problemas de injeção
no atributo, mas não é criptografia. Esse modelo deve ficar restrito ao ambiente
local ou a usuários confiáveis; para acesso público, use sessão segura ou um
provedor de identidade.

## Validação e erros

O frontend valida campos obrigatórios, tamanho de texto, quantidade de sprints,
`rank` e tamanho do fragmento antes da chamada. Isso reduz requisições inválidas,
mas não substitui Pydantic: manipular o JavaScript não permite contornar as
regras do backend.

Erros `401`, `404`, `413`, `422`, `429`, `502` e `504` são apresentados perto
do formulário. A interface cancela uma chamada que ultrapassar 60 segundos e
libera novamente o botão de envio em qualquer resultado.

## Segurança no navegador

- nenhuma credencial real é gravada nos arquivos versionados;
- o `AUTH_TOKEN` injetado fica somente no documento gerado pelo contêiner e não
  usa armazenamento persistente do navegador;
- credenciais são enviadas somente no header e com `credentials: omit`;
- dados retornados são renderizados como texto, sem `innerHTML`;
- a Content Security Policy aceita scripts, estilos e conexões apenas da mesma
  origem;
- a página não depende de scripts, fontes ou estilos de terceiros;
- câmera, microfone, geolocalização, frames e detecção flexível de MIME ficam
  bloqueados.

O proxy local usa HTTP. TLS deve ser encerrado por um proxy ou balanceador na
publicação de produção.

## Acessibilidade e responsividade

A interface inclui labels explícitos, regiões de status, mensagens de erro com
`role=alert`, navegação das abas por setas, link para pular ao conteúdo, foco no
resultado e respeito a `prefers-reduced-motion`. O layout se adapta a telas
menores sem remover nenhuma funcionalidade.

## Manutenção

Não há etapa de compilação. Em desenvolvimento, edite os arquivos dentro de
`frontend/` e recarregue o navegador. Alterações em endpoints, limites ou
schemas devem ser refletidas no JavaScript, nos testes e nesta documentação.

Execute os testes relacionados com:

```bash
poetry run python -m unittest tests.test_interface_web -v
```
