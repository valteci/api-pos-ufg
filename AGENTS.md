# AGENTS.md

## Objetivo deste projeto

Este projeto é uma API em **FastAPI** voltada para consulta, sumarização e recuperação de informações sobre **sprints de uma squad de desenvolvimento** usando IA.

A API deve operar sobre arquivos `.json` armazenados em `data/`, onde cada arquivo representa uma sprint. Cada sprint contém tarefas e, opcionalmente, subtarefas. A metodologia de referência é **Scrum**.

A IA deve atuar como uma consultora sobre os dados das sprints, respondendo perguntas, gerando resumos e executando consultas do tipo RAG sobre os dados disponíveis.

---

## Regras obrigatórias para agentes

Antes de modificar, criar ou remover qualquer arquivo neste projeto, siga estas regras:

1. Respeite todos os requisitos funcionais e não funcionais descritos neste arquivo.
2. Não implemente atalhos que removam autenticação, validação, testes, logs ou tratamento de erros.
3. Não coloque segredos, chaves de API, tokens ou senhas no código, nos testes, no README, nos arquivos de documentação ou no `compose`.
4. Todo código, teste, documentação e mensagem de commit deve estar em **português**, exceto nomes técnicos que não façam sentido traduzir, como `FastAPI`, `OpenAI`, `Redis`, `ChromaDB`, `Docker`, `RAG`, `embedding`, `healthcheck`, `JSON`, `OpenAPI`, `Swagger`, etc.
5. O projeto deve seguir terminologia e fluxo de versionamento baseados em **Gitflow**.
6. Qualquer mudança funcional deve vir acompanhada de testes.
7. Qualquer mudança relevante deve atualizar o `README.md` e/ou a documentação em `docs/`.
8. O projeto deve permanecer executável em ambiente de desenvolvimento via `compose`, incluindo dependências gerenciadas pela API.

---

## Stack esperada

A implementação deve ser compatível com um projeto FastAPI moderno.

Tecnologias esperadas ou permitidas:

- **FastAPI** para API HTTP.
- **Pydantic** para schemas, validações e configurações.
- **OpenAI API** para uso de modelos GPT e embeddings.
- **ChromaDB** ou banco vetorial equivalente para armazenar embeddings, se necessário.
- **Redis** para cache, se houver cache de respostas ou consultas.
- **Docker Compose** para ambiente de desenvolvimento.
- **Pytest** para testes.
- Logging estruturado em JSON.
- Geração automática de documentação OpenAPI/Swagger.

---

## Estrutura de diretórios

A estrutura pode variar, mas deve preservar obrigatoriamente os diretórios abaixo:

```text
.
├── AGENTS.md
├── README.md
├── compose.yml ou docker-compose.yml
├── data/
│   ├── sprint-75.json
│   ├── sprint-76.json
│   └── ...
├── docs/
│   ├── apis/
│   ├── integracoes/
│   ├── modelos/
│   ├── seguranca/
│   ├── observabilidade/
│   └── ...
├── logs/
│   └── api.json
├── tests/
└── app/ ou src/
```

Regras de estrutura:

- `data/` deve conter os arquivos `.json` das sprints.
- Cada arquivo `.json` em `data/` representa uma sprint.
- O nome do arquivo deve ser tratado como o nome ou identificador da sprint.
- `docs/` deve ficar na raiz do projeto.
- A documentação em `docs/` deve ser organizada em subpastas por tema.
- Os arquivos de documentação dentro de `docs/` devem usar formato `.md`.
- `logs/` deve armazenar arquivos de log estruturado.
- O arquivo de log preferencial deve ter extensão `.json`.

---

## Documentação obrigatória

A API deve possuir documentação completa em dois lugares:

1. `README.md`
2. Diretório `docs/`

O `README.md` deve explicar, no mínimo:

- Objetivo da API.
- Como rodar o projeto localmente.
- Como configurar variáveis de ambiente.
- Como rodar testes.
- Como gerar ou acessar Swagger/OpenAPI.
- Como usar as principais rotas.
- Como funciona o uso de dados em `data/`.
- Como funciona a integração com OpenAI.
- Como funciona o RAG.
- Como funciona autenticação.
- Como funcionam logs e tratamento de erros.
- Como o projeto aplica Gitflow.

A pasta `docs/` deve conter subpastas temáticas, por exemplo:

```text
docs/
├── apis/
├── integracoes/
├── modelos/
├── dados/
├── rag/
├── seguranca/
├── testes/
├── observabilidade/
└── deploy/
```

Toda funcionalidade criada ou alterada deve ter documentação correspondente quando houver impacto relevante.

---

## Dados das sprints

Os dados usados pela IA devem estar na pasta `data/`.

Regras obrigatórias:

1. Cada arquivo `.json` em `data/` representa uma sprint.
2. O nome do arquivo representa o nome da sprint.
3. Uma sprint pode conter várias tarefas.
4. Uma tarefa pode ou não conter várias subtarefas.
5. O modelo de IA deve operar sobre esses dados, total ou parcialmente.
6. Nenhum dado de sprint deve ser hardcoded no código da aplicação.
7. O carregamento dos dados deve ser testável.
8. A aplicação deve validar existência, formato e conteúdo mínimo dos arquivos `.json`.

Ao implementar leitura dos dados:

- Trate arquivo inexistente.
- Trate JSON inválido.
- Trate sprint vazia.
- Trate tarefa sem subtarefa.
- Trate subtarefa ausente, nula ou vazia.
- Trate campos inesperados sem quebrar a API desnecessariamente.
- Registre logs estruturados sobre carregamento e falhas.

---

## Integração com OpenAI

A API deve se integrar com a **OpenAI API** para:

1. Uso de modelos LLM/GPT para geração de respostas e resumos.
2. Uso de modelos de embeddings para RAG ou indexação semântica.

Regras obrigatórias:

- A chave da OpenAI deve vir exclusivamente de variável de ambiente.
- Nunca versionar API keys.
- Nunca expor API keys em logs, respostas HTTP, documentação pública ou mensagens de erro.
- O modelo deve ser escolhido com foco em **custo-benefício**.
- Não usar o modelo mais pesado sem justificativa.
- Não usar um modelo extremamente básico caso ele comprometa a qualidade esperada.
- A integração deve ser encapsulada em camada própria, testável por mocks.
- Falhas da OpenAI devem ser tratadas com mensagens adequadas e logs estruturados.
- Chamadas para OpenAI devem possuir timeout.
- Chamadas para OpenAI devem tratar rate limit, indisponibilidade e erros de autenticação.
- Prompts devem ser montados de forma controlada para reduzir risco de prompt injection.

Variáveis de ambiente esperadas, ajustáveis conforme implementação:

```env
OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
OPENAI_TIMEOUT_SECONDS=
```

Quando possível, forneça valores padrão seguros para parâmetros não secretos. Segredos não devem ter fallback hardcoded.

---

## RAG

Uma das rotas principais da API deve implementar RAG.

A requisição de RAG deve permitir:

- Informar uma lista de sprints.
- Informar a mensagem do usuário.
- Informar `rank`.
- Informar o tamanho do fragmento retornado.

Contrato conceitual esperado:

```json
{
  "sprints": ["sprint-75", "sprint-76"],
  "mensagem": "funcionalidade de permissão de usuários no sistema",
  "rank": 3,
  "tamanho_fragmento": 1000
}
```

Regras obrigatórias do RAG:

1. `sprints` deve ser uma lista.
2. Se `sprints` vier vazia, a consulta deve considerar todas as sprints disponíveis em `data/`.
3. `rank` deve ser um inteiro.
4. `rank` representa a quantidade de fragmentos mais próximos a serem retornados.
5. `rank=3` significa retornar os 3 fragmentos mais próximos.
6. Deve haver validação para `rank` inválido, nulo, negativo ou excessivamente alto.
7. `mensagem` deve ser validada.
8. Mensagem vazia, nula ou grande demais deve ser rejeitada.
9. O tamanho do fragmento deve ser validado.
10. O tamanho do fragmento controla o tamanho de cada fragmento retornado, não a quantidade de fragmentos.
11. A rota deve consultar apenas as sprints solicitadas, exceto quando a lista estiver vazia.
12. A resposta deve ser rápida o suficiente para uso interativo.
13. O uso de banco vetorial é permitido e recomendado se melhorar desempenho.
14. O uso de cache é permitido para reduzir custo e latência.
15. O RAG deve ser testável sem chamar a API real da OpenAI.

Se embeddings forem usados:

- Os embeddings devem ser gerados a partir dos dados em `data/`.
- Os embeddings podem ser armazenados em banco vetorial, como ChromaDB.
- A indexação deve ser reproduzível.
- Deve haver documentação sobre como gerar, atualizar e limpar o índice vetorial.
- Mudanças nos arquivos de `data/` devem ter estratégia clara de reindexação.

---

## Rota de resumo de tarefas e sprints

A API deve possuir uma rota principal para resumo de tarefas, subtarefas e/ou sprints.

Essa rota deve permitir perguntas como:

> Como está o andamento da sprint 75?

A resposta esperada deve sintetizar informações relevantes, por exemplo:

> A sprint está quase no fim. A maioria das tarefas foi desenvolvida. Faltam as tarefas X, Y e Z. Os devs A e B estão trabalhando nas tarefas C e D.

Regras obrigatórias:

1. A rota deve receber uma pergunta do usuário.
2. A rota deve identificar onde pesquisar dentro dos dados disponíveis.
3. A rota deve consultar os dados corretos.
4. A rota deve gerar uma resposta útil e objetiva.
5. A rota deve responder em tempo hábil.
6. Não é necessário usar o modelo mais potente para essa tarefa.
7. A resposta deve ser baseada nos dados das sprints, não em invenções do modelo.
8. Quando não houver dados suficientes, a API deve responder explicitamente que não encontrou informações suficientes.
9. A rota deve ser testável com mocks.
10. A rota deve validar parâmetros de entrada de forma rigorosa.

---

## Rotas principais

A API deve ter pelo menos duas rotas principais:

1. Uma rota para resumos de tarefas, subtarefas e sprints.
2. Uma rota para RAG.

Os nomes exatos das rotas podem variar, mas devem ser claros, documentados e cobertos por testes.

Sugestão de nomes:

```text
POST /v1/resumos
POST /v1/rag
GET  /health
```

Regras:

- Todas as rotas devem exigir autenticação, exceto healthcheck.
- Rotas de healthcheck, se existirem, podem ser públicas.
- As rotas devem possuir schemas claros de request e response.
- As rotas devem aparecer na documentação Swagger/OpenAPI.
- As rotas devem possuir exemplos documentados.
- As rotas devem retornar códigos HTTP apropriados.

---

## Autenticação

Toda rota da API deve possuir autenticação, exceto rotas de healthcheck.

Regras obrigatórias:

- Não criar rotas de negócio sem autenticação.
- Não permitir bypass de autenticação em produção.
- O mecanismo de autenticação deve ser documentado.
- Tokens, chaves ou credenciais devem vir por variável de ambiente ou mecanismo seguro equivalente.
- Falhas de autenticação devem retornar status HTTP apropriado.
- Logs de autenticação não devem expor credenciais.

Exceção permitida:

```text
GET /health
GET /healthz
GET /ready
```

Somente rotas de saúde podem ser públicas.

---

## Segurança

A API deve seguir altos padrões de segurança.

A implementação deve mitigar, sempre que aplicável:

- DDoS.
- Injeção de SQL.
- Prompt injection.
- CSRF.
- XSS.
- Exposição de segredos.
- Abuso de consumo da API da OpenAI.
- Entrada de dados maliciosa.
- Payloads excessivamente grandes.

Regras práticas:

1. Validar todos os parâmetros de entrada com Pydantic.
2. Definir limites de tamanho para textos enviados pelo usuário.
3. Definir limites para `rank`.
4. Definir limites para tamanho de fragmento.
5. Definir limites para quantidade de sprints consultadas.
6. Evitar interpolação insegura em consultas, filtros ou comandos.
7. Sanitizar ou neutralizar conteúdo de usuário antes de montar prompts.
8. Separar instruções do sistema, contexto recuperado e mensagem do usuário.
9. Não permitir que dados vindos do usuário sobrescrevam instruções internas do prompt.
10. Configurar CORS de forma restritiva.
11. Evitar logs com dados sensíveis.
12. Usar rate limiting quando aplicável.
13. Usar timeouts em chamadas externas.
14. Tratar erros sem vazar stack trace em produção.
15. Usar dependências atualizadas e evitar bibliotecas abandonadas.

---

## Prompt injection

Como a API usa LLMs, toda implementação deve considerar risco de prompt injection.

Regras obrigatórias:

- Tratar a mensagem do usuário como dado não confiável.
- Tratar o conteúdo dos arquivos de sprint como dado não confiável.
- Não permitir que instruções dentro dos dados das sprints alterem o comportamento do sistema.
- Não inserir a mensagem do usuário diretamente em prompts sem delimitação.
- Separar claramente:
  - instruções do sistema;
  - contexto recuperado;
  - pergunta do usuário.
- Instruir o modelo a responder apenas com base no contexto disponível.
- Quando o contexto for insuficiente, responder que não há dados suficientes.

---

## Cache

A API pode implementar cache para reduzir chamadas ao modelo de IA.

Se houver cache:

- Deve usar **Redis**.
- Redis deve estar declarado no `compose` para desenvolvimento.
- Chaves de cache devem evitar expor dados sensíveis.
- Deve existir TTL.
- Deve haver forma documentada de invalidar cache.
- O cache não pode retornar respostas incompatíveis com os dados atualizados.
- O comportamento com cache deve ser testado.

Variáveis de ambiente sugeridas:

```env
REDIS_URL=
CACHE_TTL_SECONDS=
CACHE_ENABLED=
```

---

## Banco vetorial

Se a API usar embeddings persistidos, deve ser usado um banco vetorial, como **ChromaDB**.

Regras:

- O banco vetorial deve estar declarado no `compose` em desenvolvimento.
- A origem dos dados vetorizados deve ser sempre `data/`.
- O processo de indexação deve ser documentado.
- O processo de reindexação deve ser documentado.
- Os testes não devem depender de um ChromaDB real, salvo testes de integração explicitamente marcados.

Variáveis de ambiente sugeridas:

```env
VECTOR_DB_URL=
VECTOR_DB_COLLECTION=
EMBEDDINGS_ENABLED=
```

---

## Compose de desenvolvimento

Em desenvolvimento, todas as dependências de serviços gerenciados pela API devem estar declaradas no `compose`.

Exemplos de serviços que devem estar no `compose` quando usados:

- Redis.
- ChromaDB ou banco vetorial equivalente.
- Banco relacional, se a API vier a usar um.
- Outros serviços necessários para rodar a API localmente.

Regras:

- O projeto deve ser inicializável localmente com `compose`.
- O `compose` não deve conter segredos reais.
- Segredos devem vir de `.env` local não versionado ou variáveis do ambiente.
- O `.env.example` pode existir, mas apenas com valores fictícios.
- A documentação deve explicar como subir e derrubar o ambiente.

---

## Logs estruturados

A API deve emitir logs estruturados de todas as ações relevantes.

Regras obrigatórias:

1. Logs devem ser estruturados.
2. Preferencialmente, cada linha de log deve ser um JSON válido.
3. Logs devem ir para `stdout`.
4. Logs também devem ser gravados em arquivo dentro de `logs/`.
5. O arquivo de log deve preferencialmente ser `.json`.
6. Logs devem permitir ingestão em ferramentas como Elastic, Grafana, Loki ou equivalentes.
7. Não está no escopo configurar ferramenta de observabilidade externa.
8. Logs não devem conter segredos.
9. Logs de erro devem conter contexto suficiente para diagnóstico.
10. Logs devem registrar ações relevantes da API, validações, falhas externas e decisões de fluxo.

Campos recomendados:

```json
{
  "timestamp": "2026-01-01T12:00:00Z",
  "level": "INFO",
  "event": "consulta_rag_executada",
  "request_id": "uuid",
  "route": "/v1/rag",
  "status_code": 200,
  "duration_ms": 123,
  "metadata": {}
}
```

---

## Tratamento de erros e validações

A API deve possuir tratamento de erros robusto e validação pesada de parâmetros.

Regras:

- Validar todos os requests com schemas Pydantic.
- Definir mensagens de erro claras.
- Retornar códigos HTTP apropriados.
- Tratar JSON inválido.
- Tratar sprint não encontrada.
- Tratar lista de sprints inválida.
- Tratar `rank` inválido.
- Tratar tamanho de fragmento inválido.
- Tratar mensagem vazia.
- Tratar mensagem grande demais.
- Tratar falhas na OpenAI.
- Tratar falhas no Redis.
- Tratar falhas no banco vetorial.
- Tratar timeout.
- Tratar erro interno sem expor stack trace ao cliente em produção.
- Cobrir cenários de erro com testes.

---

## Swagger e OpenAPI

A API deve gerar documentação Swagger/OpenAPI de forma automatizada.

Em FastAPI:

- A documentação interativa deve estar disponível via Swagger UI, salvo decisão explícita de segurança para ambientes produtivos.
- Os schemas Pydantic devem alimentar a documentação automaticamente.
- Deve existir documentação sobre como acessar ou exportar o OpenAPI.
- Se houver comando para exportar `openapi.json`, ele deve estar documentado.

Regras:

- Toda rota deve ter descrição clara.
- Toda rota deve ter request/response model quando aplicável.
- Toda rota deve declarar possíveis erros relevantes.
- Exemplos de payload devem ser fornecidos quando útil.
- Mudanças de contrato devem atualizar documentação e testes.

---

## Testes

Todas as funcionalidades da API devem ser testadas e testáveis.

Regras obrigatórias:

1. Toda regra de negócio deve ter teste.
2. Toda rota principal deve ter teste.
3. Toda validação relevante deve ter teste.
4. Todo tratamento de erro relevante deve ter teste.
5. Integrações externas devem ser isoladas por mocks em testes unitários.
6. A integração com OpenAI deve ser testável sem chamada real à OpenAI.
7. A integração com Redis deve ser testável.
8. A integração com banco vetorial deve ser testável.
9. O carregamento dos arquivos em `data/` deve ser testado.
10. A geração de resumo deve ser testada.
11. O RAG deve ser testado.
12. Autenticação deve ser testada.
13. Healthcheck público deve ser testado, se existir.

Organização sugerida:

```text
tests/
├── unit/
├── integration/
├── routes/
├── services/
└── fixtures/
```

Use fixtures para representar arquivos de sprint em JSON.

---

## Documentação de código Python

Código e testes devem ser documentados seguindo padrão moderno de documentação Python.

Regras:

- Usar type hints.
- Usar docstrings em módulos, classes, funções e métodos relevantes.
- Preferir docstrings em estilo Google, NumPy ou outro padrão moderno, desde que o projeto use um padrão consistente.
- Documentar regras de negócio não óbvias.
- Documentar decisões importantes de prompt, RAG, chunking, cache e embeddings.
- Não documentar obviedades de forma ruidosa.

Exemplo de docstring aceitável:

```python
def carregar_sprint(nome_sprint: str) -> Sprint:
    """Carrega os dados de uma sprint a partir da pasta data/.

    Args:
        nome_sprint: Nome da sprint, normalmente derivado do nome do arquivo JSON.

    Returns:
        Objeto de domínio representando a sprint carregada.

    Raises:
        SprintNaoEncontradaError: Quando o arquivo da sprint não existe.
        DadosInvalidosError: Quando o JSON não possui estrutura válida.
    """
```

---

## Variáveis de ambiente e configurações

Todas as configurações que podem mudar por ambiente devem ser injetadas por variáveis de ambiente.

Segredos devem sempre vir de variáveis de ambiente ou mecanismo seguro equivalente.

Regras:

- Nunca hardcodar segredos.
- Nunca criar fallback hardcoded para segredo.
- Parâmetros não secretos podem ter fallback seguro.
- Criar documentação das variáveis necessárias.
- Manter `.env.example` sem valores reais.
- Não versionar `.env`.

Exemplos de variáveis:

```env
APP_ENV=development
APP_NAME=api-sprints-ia
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/api.json

AUTH_ENABLED=true
AUTH_TOKEN=

OPENAI_API_KEY=
OPENAI_LLM_MODEL=
OPENAI_EMBEDDING_MODEL=
OPENAI_TIMEOUT_SECONDS=30

REDIS_URL=redis://redis:6379/0
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300

VECTOR_DB_URL=http://chromadb:8000
VECTOR_DB_COLLECTION=sprints

DATA_DIR=data
MAX_RAG_RANK=10
MAX_FRAGMENT_SIZE=3000
MAX_MESSAGE_LENGTH=4000
```

---

## Versionamento e Gitflow

O projeto deve adotar terminologia Gitflow.

Regras:

- Usar nomes e descrições compatíveis com Gitflow.
- Commits devem estar em português.
- Mensagens de commit devem ser claras.
- Branches devem seguir uma convenção compreensível.
- Mudanças devem ser pequenas o suficiente para revisão.
- Não misturar refatorações grandes com mudanças funcionais sem necessidade.

Exemplos de branches:

```text
feature/adicionar-rota-rag
feature/gerar-resumo-sprint
fix/corrigir-validacao-rank
docs/documentar-openai
test/cobrir-carregamento-sprints
```

Exemplos de commits:

```text
adiciona rota de rag para consulta de sprints
corrige validação de rank na consulta rag
documenta integração com openai
adiciona testes para carregamento de sprints
```

---

## Restrições de idioma

Devem estar em português:

- Mensagens de commit.
- Testes.
- Documentação.
- Comentários relevantes.
- Docstrings.
- Nomes de regras de negócio quando possível.
- Mensagens de erro voltadas ao domínio da aplicação.

Podem permanecer em inglês:

- Nomes de bibliotecas.
- Termos técnicos consolidados.
- Nomes de classes de frameworks.
- Métodos exigidos por bibliotecas.
- Convenções técnicas amplamente usadas.

Exemplos:

- Use `rank`, pois é parâmetro exigido.
- Use `RAG`, `embedding`, `OpenAI`, `FastAPI`, `Redis`, `ChromaDB`.
- Prefira mensagens de erro em português.

---

## Regras para respostas da IA

As respostas geradas pela API devem seguir estas regras:

1. Responder com base nos dados disponíveis.
2. Não inventar tarefas, subtarefas, responsáveis ou estados.
3. Informar quando os dados forem insuficientes.
4. Ser objetiva, mas útil.
5. Considerar o contexto Scrum.
6. Evitar expor detalhes internos de prompt.
7. Evitar retornar dados sensíveis desnecessários.
8. Manter tempo de resposta adequado para uso interativo.

---

## Restrições de implementação

Não faça:

- Não criar rotas de negócio sem autenticação.
- Não chamar OpenAI diretamente dentro de controllers/routers sem camada de serviço.
- Não deixar regra de negócio espalhada em handlers HTTP.
- Não hardcodar dados de sprint.
- Não hardcodar segredos.
- Não ignorar erros de leitura dos arquivos `.json`.
- Não ignorar falhas externas.
- Não retornar stack trace em produção.
- Não criar logs em texto solto quando o requisito pede logs estruturados.
- Não adicionar Redis se não houver uso real ou documentação.
- Não adicionar ChromaDB se não houver uso real ou documentação.
- Não fazer testes que dependam da API real da OpenAI por padrão.
- Não gerar documentação fora do padrão `.md` em `docs/`.
- Não escrever commits, documentação ou mensagens de erro de domínio em inglês sem necessidade.

Faça:

- Use camadas separadas para rotas, schemas, serviços, integrações e infraestrutura.
- Use injeção de dependência do FastAPI quando fizer sentido.
- Use mocks para OpenAI, Redis e banco vetorial nos testes.
- Use validação forte com Pydantic.
- Use logs estruturados.
- Use variáveis de ambiente.
- Atualize documentação junto com código.
- Cubra comportamento feliz e cenários de erro.

---

## Critérios de pronto

Uma tarefa só deve ser considerada concluída quando:

1. Código implementado.
2. Testes criados ou atualizados.
3. Testes passando.
4. Documentação atualizada.
5. Swagger/OpenAPI refletindo a mudança.
6. Logs relevantes implementados.
7. Tratamento de erros implementado.
8. Validações implementadas.
9. Nenhum segredo hardcoded.
10. Rotas de negócio protegidas por autenticação.
11. Mensagens, testes e documentação em português.
12. Mudança compatível com Gitflow.

---

## Observações finais para agentes

Este arquivo é uma fonte de restrições do projeto. Em caso de conflito entre uma implementação sugerida e este documento, este documento deve prevalecer, salvo instrução explícita posterior do responsável pelo projeto.

Quando um requisito estiver ambíguo:

1. Prefira a solução mais segura.
2. Prefira a solução mais testável.
3. Prefira a solução mais documentável.
4. Não invente comportamento de negócio sem registrar a suposição.
5. Se a implementação depender de decisão externa, registre a pendência em documentação ou comentário técnico adequado.