# Dados de sprints

## Origem dos dados

Todos os dados consultados pela IA devem vir da pasta `data/`. Cada arquivo `.json` dentro dessa pasta representa uma sprint.

Exemplo:

```text
data/
├── sprint-75.json
├── sprint-76.json
└── sprint-77.json
```

O identificador lógico de uma sprint deve ser o nome do arquivo sem a extensão `.json`.

## Modelo conceitual

O formato exato dos JSON pode variar, mas a implementação deve reconhecer a estrutura conceitual:

- sprint;
- tarefas;
- subtarefas opcionais.

Campos adicionais podem existir e não devem quebrar a API desnecessariamente.

Na implementação inicial do carregador, uma sprint pode ser representada por:

- um objeto JSON com lista de tarefas em `tarefas`, `tasks`, `issues`, `itens` ou `items`;
- uma lista JSON na raiz, tratada diretamente como lista de tarefas.

Subtarefas opcionais são reconhecidas nas chaves `subtarefas`, `subtasks`, `sub_tasks`, `sub_tarefas` ou `children`. Quando o campo estiver ausente, nulo ou vazio, a tarefa continua válida.

Campos textuais comuns são normalizados quando presentes:

- título: `titulo`, `title`, `nome`, `name`, `summary` ou `resumo`;
- descrição: `descricao`, `description`, `detalhes` ou `body`;
- status: `status`, `estado`, `situacao` ou `state`;
- responsável: `responsavel`, `assignee`, `assigned_to`, `dev` ou `desenvolvedor`.

Os dados originais continuam preservados nos modelos de domínio para permitir uso posterior em RAG, resumo e auditoria.

## Validações obrigatórias

O carregamento dos dados deve tratar:

- diretório `data/` inexistente;
- arquivo solicitado inexistente;
- arquivo com extensão diferente de `.json`;
- JSON inválido;
- JSON vazio;
- sprint sem tarefas;
- tarefa sem subtarefas;
- subtarefas ausentes, nulas ou vazias;
- campos inesperados;
- conteúdo mínimo ausente.

## Normalização

Para uso por resumo e RAG, os dados devem ser normalizados para um modelo interno estável.

Cada item normalizado deve preservar:

- identificador da sprint;
- arquivo de origem;
- tipo do item, como sprint, tarefa ou subtarefa;
- título ou descrição quando disponível;
- status quando disponível;
- responsável quando disponível;
- metadados úteis do JSON original;
- caminho lógico no arquivo.

## Logs

O carregamento deve registrar logs estruturados para:

- início e fim da leitura;
- quantidade de sprints carregadas;
- quantidade de tarefas e subtarefas lidas;
- arquivos ignorados;
- falhas de validação;
- sprint não encontrada;
- JSON inválido.

Logs não devem incluir conteúdo integral das sprints quando isso puder gerar ruído ou expor dados sensíveis.

## Testes esperados

Devem existir fixtures em `tests/fixtures/` cobrindo:

- sprint válida com tarefas e subtarefas;
- sprint válida com tarefa sem subtarefa;
- sprint com subtarefa vazia;
- sprint vazia;
- JSON inválido;
- sprint com campos extras;
- sprint inexistente.
