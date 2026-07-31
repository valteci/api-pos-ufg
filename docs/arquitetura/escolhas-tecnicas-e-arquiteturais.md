# Escolhas técnicas e arquiteturais

## Objetivo arquitetural

A API deve ser uma aplicação FastAPI organizada em camadas, testável sem chamadas reais à OpenAI e preparada para operar sobre arquivos JSON de sprints armazenados em `data/`.

As decisões abaixo devem orientar a implementação. Quando houver conflito entre uma solução rápida e estas decisões, a solução mais segura, testável e documentável deve prevalecer.

## Camadas da aplicação

A estrutura recomendada para implementação é:

```text
app/
├── main.py
├── api/
│   └── v1/
│       ├── rag.py
│       ├── resumos.py
│       └── health.py
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── security.py
│   └── errors.py
├── domain/
│   ├── sprint.py
│   └── exceptions.py
├── schemas/
│   ├── rag.py
│   ├── resumos.py
│   └── health.py
├── services/
│   ├── sprint_loader.py
│   ├── rag_service.py
│   ├── resumo_service.py
│   ├── chunking_service.py
│   └── prompt_service.py
├── integrations/
│   ├── openai_client.py
│   ├── redis_cache.py
│   └── vector_store.py
└── infrastructure/
    ├── repositories.py
    └── rate_limit.py
```

Decisão: rotas HTTP devem orquestrar dependências, autenticação, schemas e códigos HTTP. Regras de negócio, leitura de dados, geração de prompts, RAG, cache e integrações externas devem ficar em serviços ou integrações próprias.

## Interface web

Decisão: manter uma interface estática em HTML, CSS e JavaScript, servida por
Nginx como serviço separado no Compose. O Nginx encaminha `/api/*` para o
FastAPI, evitando configuração de origem cruzada no fluxo normal do navegador.

Essa abordagem não adiciona uma cadeia de build frontend, mantém o ambiente
reproduzível e preserva a API como fonte única das regras de autenticação,
validação e negócio. O frontend realiza apenas validações de experiência e
apresentação; ele não acessa arquivos em `data/`, OpenAI, Redis ou ChromaDB
diretamente.

O mesmo `AUTH_TOKEN` usado pela API é injetado pelo contêiner em um metadado do
HTML gerado, permitindo que o navegador monte o header Bearer sem entrada
manual. O modelo versionado mantém apenas um marcador e não contém credencial
real. Como a credencial entregue ao navegador pode ser inspecionada, essa
decisão é limitada a ambientes locais ou com usuários confiáveis.

## FastAPI e Pydantic

Decisão: usar FastAPI para rotas e documentação OpenAPI automática, e Pydantic para validações, schemas de entrada e saída e configurações por ambiente.

As configurações devem ser carregadas a partir de variáveis de ambiente por uma camada central, preferencialmente com `pydantic-settings` quando a dependência for adicionada. Segredos não podem ter fallback hardcoded.

## Rotas

Decisão: versionar as rotas de negócio em `/v1`.

Rotas previstas:

- `GET /health`: pública, usada para healthcheck simples.
- `POST /v1/resumos`: autenticada, gera resumo ou resposta consultiva sobre tarefas, subtarefas ou sprints.
- `POST /v1/rag`: autenticada, executa recuperação semântica sobre os dados de sprints.

Rotas adicionais só devem ser criadas se houver justificativa clara, autenticação adequada e documentação.

## Autenticação

Decisão: usar autenticação por Bearer token simples no início do projeto.

Motivos:

- atende ao requisito de proteger rotas de negócio;
- é suficiente para o escopo acadêmico/inicial;
- é fácil de testar com `TestClient`;
- permite evolução futura para OAuth2, JWT ou integração com provedor de identidade.

O token deve vir de `AUTH_TOKEN`. A aplicação não deve aceitar token hardcoded. `GET /health` é a única rota pública prevista.

## Integração com OpenAI

Decisão: encapsular toda chamada à OpenAI em `app/integrations/openai_client.py` ou módulo equivalente.

Nenhum router deve chamar a OpenAI diretamente. Serviços de negócio devem depender de uma interface interna, permitindo mocks em testes.

O modelo de LLM e o modelo de embedding devem ser configuráveis por ambiente:

- `OPENAI_API_KEY`
- `OPENAI_LLM_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_TIMEOUT_SECONDS`

A escolha exata dos modelos deve ser confirmada na documentação oficial da OpenAI no momento da implementação. A arquitetura não deve depender de um modelo específico. A diretriz é usar modelos de custo-benefício adequado, evitando tanto modelos máximos sem justificativa quanto modelos básicos demais para sumarização e RAG.

Chamadas externas devem ter timeout, tratamento de rate limit, autenticação inválida, indisponibilidade e erros inesperados. Mensagens de erro não devem expor chave, prompt completo, stack trace ou payload sensível.

## RAG e banco vetorial

Decisão: implementar RAG com embeddings e banco vetorial ChromaDB em desenvolvimento.

Motivos:

- melhora desempenho quando houver várias sprints;
- separa indexação da consulta;
- permite recuperar fragmentos por similaridade;
- torna o comportamento de RAG mais próximo do requisito de `rank`.

O banco vetorial deve ser acessado por uma interface em `integrations/vector_store.py`, permitindo substituição por fake em testes. A origem da indexação deve ser exclusivamente `data/`.

## Chunking

Decisão: converter tarefas e subtarefas em documentos textuais normalizados antes de gerar embeddings.

Cada fragmento deve preservar metadados mínimos:

- sprint;
- nome do arquivo de origem;
- identificador ou título da tarefa, quando existir;
- identificador ou título da subtarefa, quando existir;
- status, responsável e demais campos relevantes quando disponíveis;
- caminho lógico no JSON.

O tamanho do fragmento solicitado na rota controla o tamanho máximo de cada fragmento retornado, não a quantidade de fragmentos.

## Cache

Decisão: usar Redis para cache e rate limiting quando essas funcionalidades forem implementadas.

O cache deve ser opcional por configuração, ter TTL e usar chaves que não exponham dados sensíveis. A chave deve ser derivada por hash dos parâmetros relevantes, incluindo sprints, mensagem normalizada, rank, tamanho do fragmento e versão do índice ou assinatura dos dados.

## Logs e observabilidade

Decisão: usar logs estruturados em JSON, emitidos para `stdout` e para `logs/api.json`.

Cada requisição deve receber `request_id`. Logs devem conter evento, rota, duração, status, contexto operacional e erro sanitizado quando aplicável.

Não devem ser registrados segredos, tokens, chave da OpenAI, prompts completos nem dados excessivos dos arquivos de sprint.

## Tratamento de erros

Decisão: criar exceções de domínio e handlers HTTP centralizados.

Erros esperados devem virar respostas claras em português, com status HTTP apropriado. Erros internos devem retornar mensagem genérica em produção e registrar diagnóstico sanitizado em log.

## Documentação

Decisão: contratos HTTP devem ser documentados por schemas Pydantic e complementados por Markdown em `docs/`. O `README.md` deve ser atualizado quando as funcionalidades forem implementadas.

Swagger/OpenAPI deve refletir as rotas, exemplos e erros relevantes automaticamente.

## Testabilidade

Decisão: toda integração externa deve ter interface ou wrapper testável por mock.

Testes não devem chamar OpenAI, Redis ou ChromaDB reais por padrão. Casos de integração podem ser marcados separadamente quando forem criados.
