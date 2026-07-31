# Sistema inteligente para consulta e análise de sprints

**Trabalho Prático Final — Opção 2**

**Integrantes:**

- Valteci Marcelino Coelho Junior
- MURILO BENEDITO MARTINS FERREIRA

## 1 Introdução

Este trabalho apresenta uma aplicação que permite consultar informações de sprints
de uma equipe de desenvolvimento usando perguntas em linguagem natural. A ideia
principal é facilitar a procura por tarefas, subtarefas, situações e assuntos que
foram trabalhados pela equipe, sem que o usuário tenha que abrir vários arquivos e
procurar manualmente dentro de cada um deles.

Em um projeto de desenvolvimento de software é comum que uma sprint possua muitas
tarefas. Além disso, uma tarefa pode ter várias subtarefas, descrições grandes,
critérios de aceitação e informações sobre o que foi feito. Com o passar do tempo,
a quantidade de dados cresce e fica cada vez mais difícil lembrar em qual sprint
uma funcionalidade foi desenvolvida. Nesse contexto, uma busca comum por palavras
nem sempre é suficiente, já que o usuário pode fazer uma pergunta usando palavras
diferentes daquelas que foram escritas originalmente na tarefa.

Para tentar resolver esse problema, foi construída uma aplicação web que usa
Inteligência Artificial, embeddings e RAG. O usuário pode escrever, por exemplo,
“Como está o andamento da Sprint 75?” ou procurar por “funcionalidades relacionadas
à devolução de processos”. A aplicação consulta a base de sprints e apresenta uma
resposta ou os fragmentos que possuem maior proximidade com o assunto pesquisado.
Também são mostradas as fontes utilizadas, como o nome da sprint, o arquivo de
origem, a tarefa e o caminho do item dentro dos dados.

O sistema foi feito em Python usando FastAPI. A interface web foi construída com
HTML, CSS e JavaScript e é servida pelo Nginx. Para armazenar e pesquisar os
embeddings foi usado o ChromaDB. A OpenAI é usada tanto na geração dos embeddings
quanto na geração de respostas, enquanto o Redis auxilia no cache e no controle da
quantidade de consultas. Todo o ambiente foi organizado com Docker Compose para
que seja possível executar o trabalho sem instalar cada uma dessas ferramentas
separadamente.

## 2 Objetivo do trabalho

O objetivo principal deste trabalho é construir uma aplicação capaz de receber
perguntas em linguagem natural e consultar uma base documental formada por dados
de sprints. Para que isso fosse possível, o trabalho cobre as principais etapas de
um sistema de IA baseado em documentos:

1. leitura e validação dos arquivos de origem;
2. preparação dos textos das tarefas e subtarefas;
3. divisão dos textos em fragmentos menores;
4. geração de embeddings;
5. armazenamento dos vetores no ChromaDB;
6. recuperação dos fragmentos mais próximos da pergunta;
7. uso de um LLM para produzir respostas com base nos dados disponíveis;
8. apresentação da resposta e das fontes em uma interface web.

Além do funcionamento da IA, também se buscou organizar o projeto de uma forma que
fosse simples de executar e testar. Por isso, as configurações ficam em um arquivo
`.env`, o código foi separado em módulos e as integrações externas possuem
tratamento de erros. A aplicação também tem autenticação, logs e testes
automatizados.

## 3 Contexto dos documentos

A base usada neste trabalho veio de sprints de desenvolvimento do sistema Apolo.
Ela contém informações de trabalho da Sprint 60 até a Sprint 79. Cada sprint foi
exportada para um arquivo dentro da pasta `data/`, possuindo tarefas e subtarefas
com campos como título, descrição, situação, data, complexidade e outras
informações que estavam disponíveis no momento da exportação.

Os 20 documentos estão no formato JSON porque esse formato preserva a relação
entre uma sprint, suas tarefas e suas subtarefas. Suas descrições possuem texto e,
em vários casos, marcações HTML que vieram da ferramenta de gerenciamento do
projeto. Durante a preparação, a aplicação transforma esses dados em textos que
podem ser consultados pela IA.

A base possui os seguintes números:

| Conteúdo | Quantidade |
| --- | ---: |
| Documentos de sprint | 20 |
| Tarefas | 393 |
| Subtarefas | 1.075 |
| Registros de tarefas e subtarefas | 1.468 |

Portanto, a base possui 20 documentos, sendo um arquivo para cada sprint. Dentro
deles existem 1.468 registros de tarefas e subtarefas que podem ser preparados e
consultados pela aplicação. Durante o chunking, algumas descrições grandes ainda
podem ser divididas em mais de uma parte.

O nome do arquivo também possui importância. Ele é usado como identificador da
sprint, por exemplo, o arquivo `Sprint 75.json` representa a `Sprint 75`. Essa
identificação acompanha o texto durante todo o processo e permite que a aplicação
mostre de onde veio cada resultado. Os dados não são escritos diretamente no
código da aplicação, de forma que outras sprints podem ser adicionadas na pasta
`data/` e processadas pelo mesmo fluxo.

## 4 Preparação dos dados

Antes de gerar os embeddings, os arquivos passam por uma etapa de preparação. O
primeiro passo é a leitura automática dos arquivos `.json` presentes diretamente
na pasta `data/`. A aplicação ignora outros tipos de arquivo e também não confunde
os embeddings exportados, que ficam dentro de `data/embeddings`, com os dados
originais das sprints.

Durante a leitura são feitas validações básicas para evitar que um arquivo com
problema seja enviado para a IA. A aplicação verifica se o diretório existe, se o
JSON é válido, se a sprint possui tarefas e se cada tarefa tem uma estrutura que
pode ser lida. Uma tarefa não é obrigada a ter subtarefas. Por isso, subtarefas
ausentes, nulas ou vazias são aceitas sem impedir o carregamento da sprint. Campos
adicionais também são mantidos sempre que possível, pois podem conter informações
úteis para uma consulta futura.

Depois da validação, os nomes dos campos são normalizados. Isso permite reconhecer,
por exemplo, `titulo` ou `title`, `situacao` ou `status`, e `subtarefas` ou
`subtasks`. Essa escolha deixou o carregamento um pouco mais tolerante a arquivos
exportados com pequenas diferenças de estrutura.

Na etapa seguinte, cada tarefa e subtarefa é transformada em um texto controlado.
Esse texto recebe um pequeno cabeçalho com a sprint, o arquivo de origem, o tipo do
item e seu caminho dentro do JSON. Também são acrescentados o título, a descrição,
o status, o responsável e os demais campos úteis. No caso de uma subtarefa, o
título da tarefa principal também é incluído para que ela não perca completamente
o seu contexto.

Um exemplo simplificado do texto preparado é:

```text
Sprint: Sprint 75
Origem: Sprint 75.json
Tipo: subtarefa
Caminho: tarefas[0].subtarefas[1]
Tarefa pai: Devolução de processo na etapa de enviado para o banco
Subtarefa: Criar um tipo de devolução para a etapa de liberação de OP
Status: Concluído
```

Por fim, acontece o chunking. O limite padrão usado na indexação é de 3.000
caracteres. Quando um texto ultrapassa esse valor, ele é dividido em partes menores,
mas cada parte continua levando o cabeçalho com sua origem. Nenhum fragmento
mistura dados de sprints diferentes. Essa decisão é importante porque um resultado
de busca precisa continuar fazendo sentido e também precisa ser rastreável.

É válido diferenciar dois tamanhos que aparecem no projeto. O tamanho usado no
chunking controla como o documento é dividido antes da geração dos embeddings. Já
o campo “tamanho do fragmento”, disponível na busca RAG, controla apenas quantos
caracteres de cada resultado serão apresentados ao usuário. Assim, ele não muda a
quantidade de resultados e nem refaz os embeddings.

## 5 Embeddings e banco vetorial

Embeddings são representações numéricas de textos. De forma simples, o modelo
transforma cada fragmento em uma lista de números que tenta representar o seu
significado. Textos que tratam de assuntos parecidos tendem a ficar próximos nesse
espaço numérico, mesmo quando não usam exatamente as mesmas palavras.

O modelo configurado nesta entrega é o `text-embedding-3-small`, da OpenAI. Ele foi
escolhido por ter um bom equilíbrio entre custo e qualidade para uma base desse
tamanho. Os vetores usados no projeto possuem 1.536 posições. Durante a indexação,
cada fragmento preparado é enviado ao modelo e o vetor retornado é gravado na
coleção `sprints` do ChromaDB, junto com o texto original e seus metadados.

Quando o usuário faz uma busca RAG, a mensagem também é transformada em embedding.
O ChromaDB compara esse vetor com os vetores já armazenados e devolve os mais
próximos. O parâmetro `rank` informa quantos fragmentos devem ser retornados. Um
`rank` igual a 3, por exemplo, pede os três resultados mais próximos. Se uma ou
mais sprints forem informadas, a busca fica limitada a elas; se o campo ficar
vazio, todas as sprints podem ser consideradas.

O ChromaDB foi escolhido porque já é voltado para esse tipo de busca e pode ser
executado em um contêiner. Seus dados ficam em um volume do Docker, portanto não
desaparecem quando os contêineres são apenas parados. A aplicação também permite
exportar os embeddings para `data/embeddings`. Nessa pasta existe um arquivo por
sprint, contendo os textos, vetores e metadados necessários para reconstruir a
coleção.

Essa exportação ajuda na demonstração do trabalho. Gerar todos os embeddings
novamente exige tempo e utiliza créditos da API da OpenAI. Como os arquivos
exportados estão no projeto, a aplicação consegue importá-los automaticamente
quando encontra o ChromaDB vazio. Mesmo assim, o processo completo de geração
continua disponível e pode ser reproduzido usando os comandos descritos mais
adiante.

Sempre que algum arquivo da pasta `data/` for alterado, os embeddings daquela
sprint também precisam ser atualizados. É possível reindexar toda a base ou apenas
uma sprint. Depois disso, recomenda-se exportar os vetores novamente para manter os
arquivos de `data/embeddings` compatíveis com os dados de origem.

## 6 LLM e funcionamento do RAG

O LLM usado na configuração desta entrega é o `gpt-5.4-mini`, acessado pela API da
OpenAI. A escolha de um modelo menor tem relação com o objetivo do trabalho, pois a
tarefa principal é resumir e responder sobre um contexto que já foi fornecido pela
aplicação. Dessa forma, não seria necessário usar o modelo mais pesado disponível,
o que aumentaria o custo das consultas.

A aplicação possui duas formas principais de consulta. A primeira é o “Resumo
consultivo”. Nela o usuário escreve uma pergunta, informa opcionalmente as sprints
e recebe uma resposta produzida pelo LLM. A aplicação monta o contexto com os dados
das sprints selecionadas e envia esse contexto para o modelo junto com a pergunta.
A resposta também informa as sprints consultadas e as fontes usadas.

A segunda forma é a “Busca RAG”. Nesse caso, a pergunta é convertida em embedding
e o ChromaDB recupera os fragmentos mais próximos. Os trechos são mostrados em
ordem de proximidade, acompanhados por score, sprint, arquivo de origem e outros
metadados. Essa visualização permite conferir diretamente por que determinado
resultado foi encontrado.

Os dois modos foram mantidos separados na interface para deixar a demonstração
mais clara: um deles mostra a geração de uma resposta pela IA e o outro permite
observar a etapa de recuperação do RAG. Nos dois casos, os dados das sprints são a
fonte da consulta. O modelo não recebe liberdade para inventar tarefas ou buscar
informações externas.

Como a mensagem do usuário e o conteúdo dos arquivos podem conter instruções, eles
são tratados como dados não confiáveis. As instruções internas, o contexto e a
pergunta são separados no prompt. O modelo é orientado a responder apenas com base
no contexto recebido e a informar quando não houver dados suficientes. Essa
separação não elimina completamente os riscos próprios de um LLM, mas reduz a
possibilidade de uma instrução presente em uma tarefa mudar o comportamento da
aplicação.

O fluxo geral pode ser representado da seguinte forma:

```text
Usuário no navegador
        |
        v
Interface HTML/CSS/JavaScript (Nginx)
        |
        v
API FastAPI
   |          |           |             |
   v          v           v             v
data/      OpenAI      ChromaDB        Redis
sprints    LLM e       embeddings      cache e
           embeddings  e busca         limite de uso
```

## 7 Organização da aplicação

O projeto foi dividido em partes para evitar que toda a regra ficasse concentrada
nas rotas HTTP. A pasta `app/api` possui as rotas, `app/schemas` possui os formatos
de entrada e saída, `app/services` contém as regras de preparação, resumo e RAG, e
`app/integrations` faz a comunicação com OpenAI, ChromaDB e Redis. Os dados ficam
em `data/`, os testes em `tests/` e a documentação complementar em `docs/`.

```text
.
├── app/                    aplicação FastAPI e regras do sistema
├── data/                   sprints e embeddings exportados
├── docs/                   documentação complementar
├── frontend/               interface web e configuração do Nginx
├── logs/                   logs estruturados da aplicação
├── tests/                  testes automatizados
├── .env.sample             exemplo de configuração
├── docker-compose.yml      definição dos serviços
├── Dockerfile              imagem da API
└── README.md               relatório técnico e instruções
```

As rotas principais são `POST /v1/resumos` e `POST /v1/rag`. Elas exigem um token
de acesso, enquanto `GET /health` é público e serve para verificar se a API está
funcionando. Na interface web o token configurado no `.env` é colocado
automaticamente nas requisições, não sendo necessário digitá-lo a cada consulta.
Essa solução foi pensada para a demonstração local do trabalho.

O Redis guarda por alguns minutos o resultado de consultas repetidas e também
limita a quantidade de requisições. Com isso, uma mesma pergunta pode ser
respondida mais rapidamente e há uma proteção básica contra uso excessivo da API
da OpenAI. As configurações de limite e tempo de cache também podem ser alteradas
no `.env`.

## 8 Como executar o projeto com Docker

Esta é a forma recomendada para avaliar o trabalho. É necessário ter Docker e o
comando `docker compose` instalados. Não é necessário instalar Python, FastAPI,
Redis ou ChromaDB separadamente, pois essas dependências serão iniciadas em
contêineres.

### 8.1 Preparar o arquivo `.env`

Na entrega será enviado um arquivo `.env` já preenchido. Esse arquivo deve ser
colocado na raiz do projeto, no mesmo nível do `docker-compose.yml`. Não se deve
renomear o arquivo e nem mover seu conteúdo para o código.

As configurações mais importantes são:

| Variável | Finalidade |
| --- | --- |
| `OPENAI_API_KEY` | Chave usada pela API para acessar a OpenAI. |
| `OPENAI_LLM_MODEL` | Modelo responsável pelas respostas e resumos. |
| `OPENAI_EMBEDDING_MODEL` | Modelo que transforma textos em vetores. |
| `AUTH_TOKEN` | Token usado para proteger as rotas da aplicação. |
| `VECTOR_DB_URL` | Endereço interno do ChromaDB. |
| `REDIS_URL` | Endereço interno do Redis. |
| `EMBEDDINGS_AUTOLOAD_ENABLED` | Permite importar os embeddings automaticamente. |

Os valores de `OPENAI_API_KEY` e `AUTH_TOKEN` são segredos e não devem ser
publicados no Git. O arquivo `.env.sample` mostra todas as opções sem trazer uma
chave real. Caso o `.env` fornecido não esteja disponível, pode-se criar uma cópia
do exemplo e preencher os campos vazios:

```bash
cp .env.sample .env
```

Para esta entrega, os modelos esperados no `.env` são:

```env
OPENAI_LLM_MODEL=gpt-5.4-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### 8.2 Subir todos os serviços

Dentro da raiz do projeto, execute:

```bash
docker compose up --build -d
```

Na primeira execução, o Docker pode demorar um pouco porque precisa baixar as
imagens e montar a imagem da API. O comando inicia quatro serviços:

- `frontend`: interface web executada pelo Nginx;
- `api`: aplicação FastAPI;
- `chromadb`: banco onde ficam os embeddings;
- `redis`: cache e controle de requisições.

Para conferir se todos estão ativos, use:

```bash
docker compose ps
```

Também é possível conferir a API pelo navegador em
`http://localhost:8000/health`. A resposta esperada é:

```json
{"status":"ok"}
```

Se for necessário acompanhar a inicialização ou entender algum erro, use:

```bash
docker compose logs -f api
```

Para sair da visualização dos logs basta pressionar `Ctrl+C`; isso não derruba os
serviços.

### 8.3 Carregamento dos embeddings existentes

O caminho mais rápido para demonstrar a aplicação é usar os embeddings que já
estão em `data/embeddings`. Quando `EMBEDDINGS_AUTOLOAD_ENABLED=true`, a API
verifica a coleção do ChromaDB durante a inicialização. Se a coleção estiver vazia,
os arquivos exportados são importados automaticamente. Se a coleção já possuir
dados, nenhuma duplicação é feita.

Por isso, na execução normal não é necessário gerar todos os embeddings antes de
abrir a interface. Esse comportamento evita uma nova cobrança da OpenAI toda vez
que o professor executar o trabalho.

Caso se queira fazer a importação manual, o comando é:

```bash
docker compose exec api python -m app.cli.exportar_embeddings --importar
```

### 8.4 Gerar novamente os embeddings

Para reproduzir o pipeline completo a partir dos arquivos de sprint, com os
contêineres em funcionamento, execute:

```bash
docker compose exec api python -m app.cli.indexar_vetores --reindexar
```

Esse comando limpa a coleção atual, lê todas as sprints, realiza o chunking, envia
os fragmentos ao modelo `text-embedding-3-small` e grava os novos vetores no
ChromaDB. O processo pode levar alguns minutos e consome créditos da chave da
OpenAI configurada no `.env`.

Depois da geração, os embeddings podem ser exportados novamente para o projeto:

```bash
docker compose exec api python -m app.cli.exportar_embeddings
```

Se somente uma sprint tiver sido alterada, não é necessário processar toda a base.
Por exemplo, para atualizar a Sprint 75, use:

```bash
docker compose exec api python -m app.cli.indexar_vetores --sprint "Sprint 75"
docker compose exec api python -m app.cli.exportar_embeddings
```

Isso representa uma forma de reprocessamento incremental, pois apenas os vetores
da sprint informada são substituídos. O nome deve corresponder ao nome do arquivo
sem a extensão `.json`.

### 8.5 Usar a interface

Com os serviços ativos, abra:

```text
http://localhost:3000
```

Na aba **Resumo consultivo**, pode-se fazer uma pergunta como:

```text
Como está o andamento da Sprint 75?
```

O campo de sprints é opcional. Quando ele for usado, os nomes podem ser separados
por vírgulas. Recomenda-se escrever exatamente como aparecem nos arquivos, por
exemplo, `Sprint 75`.

Na aba **Busca RAG**, um exemplo de mensagem é:

```text
Quais tarefas tratam da devolução de processos?
```

Pode-se escolher a `Sprint 75`, deixar o `rank` em 3 e o tamanho do fragmento em
1.000 caracteres. A interface mostrará os três trechos mais próximos, suas sprints,
os arquivos de origem e os scores da busca. Se o campo de sprints for deixado em
branco, a pesquisa considera toda a base.

### 8.6 Swagger, testes e logs

A documentação automática da API pode ser consultada pelo Swagger em:

```text
http://localhost:8000/docs
```

O contrato OpenAPI em JSON está em `http://localhost:8000/openapi.json`. Essas
páginas permitem visualizar os formatos das requisições e respostas, embora a
interface da porta 3000 seja a forma mais simples de demonstrar o trabalho.

Os testes podem ser executados dentro do mesmo ambiente com:

```bash
docker compose run --rm -T -v ./tests:/app/tests:ro api \
  python -m unittest discover -s tests
```

Os testes não fazem chamadas reais à OpenAI. Eles usam objetos simulados para
verificar o carregamento das sprints, o chunking, a autenticação, a integração com
a OpenAI, o ChromaDB, o Redis, as rotas e a interface.

Os logs são escritos na saída dos contêineres e também no arquivo
`logs/api.json`. Cada linha possui uma estrutura JSON, o que facilita identificar a
rota, o resultado, o tempo da requisição e possíveis erros, sem gravar a chave da
OpenAI ou o token de autenticação.

### 8.7 Encerrar ou reiniciar o ambiente

Para parar e remover os contêineres, mantendo os dados dos volumes, use:

```bash
docker compose down
```

Em uma nova execução, basta usar novamente `docker compose up --build -d`. Para
apagar também os volumes do ChromaDB e do Redis e fazer uma inicialização
completamente limpa, pode-se usar:

```bash
docker compose down -v
```

O último comando apaga o índice armazenado no volume, mas ele poderá ser carregado
ou gerado novamente usando os procedimentos anteriores.

## 9 Tratamento de erros e segurança

A aplicação valida as perguntas, os nomes das sprints, o `rank`, o tamanho dos
fragmentos e o tamanho total das requisições. Uma mensagem vazia, um rank negativo
ou uma sprint que não existe não são enviados para a OpenAI. Erros de autenticação,
timeout, limite de uso, indisponibilidade da OpenAI e falhas no banco vetorial são
convertidos em respostas mais simples, sem mostrar o stack trace ao usuário.

As rotas de negócio exigem um Bearer token. O healthcheck é público porque serve
somente para indicar se a aplicação está disponível. A chave da OpenAI fica apenas
no contêiner da API e não é enviada para a interface. O token usado pela interface
pode ser visto por quem tiver acesso ao navegador, portanto essa forma de
autenticação é apropriada para a demonstração local e não pretende substituir um
sistema completo de usuários em produção.

Também foram colocados limites para reduzir abuso e custo inesperado. Por padrão,
a mensagem pode ter até 4.000 caracteres, o `rank` pode variar de 1 a 10 e cada
consulta pode informar até 20 sprints. O Redis limita a quantidade de requisições e
o cache possui tempo de validade. Os prompts separam as instruções da aplicação,
os documentos e a pergunta do usuário, diminuindo o risco de prompt injection.

## 10 Requisitos atendidos

A relação abaixo resume como os pontos pedidos no Trabalho Prático Final foram
aplicados:

| Requisito | Aplicação no projeto |
| --- | --- |
| Base com pelo menos 20 documentos | A pasta `data/` possui 20 documentos de sprint, da Sprint 60 até a Sprint 79. |
| Extração automática | O carregador lê e valida automaticamente os arquivos da pasta `data/`. |
| Chunking | Tarefas e subtarefas são transformadas em fragmentos de até 3.000 caracteres, preservando a origem. |
| Geração de embeddings | Os fragmentos são enviados ao `text-embedding-3-small`, gerando vetores de 1.536 posições. |
| Banco vetorial | Os vetores, textos e metadados são armazenados no ChromaDB. |
| LLM | O `gpt-5.4-mini` gera respostas e resumos baseados nos dados selecionados. |
| Perguntas em linguagem natural | A interface possui campos de pergunta para resumo e para busca RAG. |
| Recuperação de trechos | A busca vetorial devolve os fragmentos mais próximos de acordo com o `rank`. |
| Resposta baseada no contexto | A rota de resumos monta o contexto a partir das sprints e orienta o LLM a não inventar informações. |
| Exibição das fontes | A interface mostra sprint, origem, tipo, caminho e título quando disponível. |
| Organização em módulos | Rotas, schemas, serviços e integrações ficam em módulos separados. |
| Controle de versão | O projeto é mantido em um repositório Git. |
| Configuração por ambiente | Chaves, modelos, endereços e limites são definidos pelo `.env`. |
| Tratamento de erros | Entradas e integrações são validadas e falhas recebem mensagens controladas. |
| Documentação | Este README funciona como relatório e a pasta `docs/` complementa os detalhes. |
| Interface para consulta | A aplicação web fica disponível na porta 3000. |

O trabalho também apresenta duas funcionalidades que se relacionam aos itens de
bônus. A primeira é o reprocessamento incremental, feito pelo parâmetro `--sprint`,
que permite atualizar somente os documentos modificados. A segunda é a parte de
monitoramento e observabilidade, representada pelo healthcheck, pelos identificadores
de requisição e pelos logs estruturados em JSON. Não foi adicionada uma ferramenta
externa de gráficos, mas os registros já ficam em um formato que pode ser lido por
esse tipo de ferramenta.

## 11 Resultados e considerações finais

Com a aplicação construída, foi possível reunir em um único ambiente a leitura dos
documentos, a geração de embeddings, o armazenamento vetorial, a busca RAG e a
geração de respostas com um LLM. A interface tornou o uso mais simples, já que o
usuário não precisa montar uma requisição HTTP ou conhecer os detalhes internos da
API para fazer uma pergunta.

O uso de embeddings permite encontrar tarefas pelo significado geral da consulta,
e não somente pela ocorrência exata de uma palavra. Já os metadados preservados em
cada fragmento permitem verificar a fonte do resultado. Esse ponto é importante
porque uma resposta gerada por IA não deve ser aceita sem que exista uma forma de
relacioná-la aos documentos usados.

Outro resultado foi a possibilidade de executar todos os componentes com Docker.
O professor precisa apenas colocar o `.env` recebido na raiz do projeto, subir os
serviços e abrir a interface. Os embeddings exportados tornam a primeira execução
mais rápida e econômica, enquanto o comando de reindexação permite demonstrar que
eles foram realmente produzidos a partir dos documentos da pasta `data/`.

Como limitação, as respostas ainda dependem da qualidade das descrições registradas
nas sprints. Se uma tarefa tiver pouco texto ou informações incompletas, a IA não
terá como descobrir aquilo que não está nos dados. O modelo também pode apresentar
as limitações comuns de um LLM, razão pela qual a aplicação orienta respostas
baseadas no contexto e apresenta as fontes utilizadas.

Por fim, este trabalho demonstra uma forma prática de usar IA para consultar um
conjunto documental que faz parte da rotina de uma equipe de software. A mesma
ideia poderia ser aplicada a outros projetos, manuais ou relatórios, desde que os
documentos fossem preparados, divididos e indexados. Dessa forma, a aplicação não
fica limitada às sprints existentes e pode servir como base para outros trabalhos
envolvendo recuperação de informação e modelos de linguagem.

## 12 Documentação complementar

Os detalhes que não foram aprofundados neste relatório podem ser consultados nos
seguintes arquivos:

- [Contratos da API](docs/apis/contratos-http.md)
- [Escolhas técnicas e arquitetura](docs/arquitetura/escolhas-tecnicas-e-arquiteturais.md)
- [Dados das sprints](docs/dados/dados-de-sprints.md)
- [Integração com a OpenAI](docs/integracoes/openai.md)
- [Estratégia de RAG](docs/rag/estrategia-rag.md)
- [Exportação e importação de embeddings](docs/rag/exportacao-e-importacao-de-embeddings.md)
- [Autenticação e segurança](docs/seguranca/autenticacao-e-seguranca.md)
- [Logs e tratamento de erros](docs/observabilidade/logs-e-erros.md)
- [Ambiente de desenvolvimento](docs/deploy/ambiente-de-desenvolvimento.md)
- [Interface web](docs/frontend/interface-web.md)
- [Estratégia de testes](docs/testes/estrategia-de-testes.md)
