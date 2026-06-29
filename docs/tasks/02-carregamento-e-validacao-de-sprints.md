# Tarefa 02: Carregamento e validação de sprints

**Status:** concluída

## Objetivo

Implementar leitura, validação e normalização dos arquivos JSON em `data/`.

## Requisitos atendidos

- Cada arquivo `.json` representa uma sprint.
- Nome do arquivo é o identificador da sprint.
- Sprint possui tarefas e subtarefas opcionais.
- Dados não podem ser hardcoded.
- Carregamento deve ser testável.

## Subtarefas

- Criar modelos de domínio para sprint, tarefa e subtarefa.
- Criar serviço de carregamento a partir de `DATA_DIR`.
- Listar sprints disponíveis.
- Carregar sprint por identificador.
- Validar arquivo inexistente.
- Validar JSON inválido.
- Validar sprint vazia.
- Aceitar tarefa sem subtarefa.
- Aceitar subtarefa ausente, nula ou vazia quando a tarefa for válida.
- Preservar campos extras úteis como metadados.
- Registrar logs estruturados de leitura e falha.
- Criar fixtures de dados para testes.

## Decisões técnicas

- O identificador da sprint será derivado do nome do arquivo sem `.json`.
- A normalização deve produzir objetos internos estáveis, mesmo quando os JSON tiverem campos extras.
- Erros de domínio devem ser exceções próprias, convertidas para HTTP nos handlers.

## Testes necessários

- Carrega sprint válida.
- Lista múltiplas sprints.
- Rejeita sprint inexistente.
- Rejeita JSON inválido.
- Rejeita sprint sem conteúdo mínimo.
- Aceita tarefa sem subtarefa.
- Aceita campos extras sem quebrar.

## Critérios de aceite

- Nenhuma regra de leitura fica dentro dos routers.
- Falhas são logadas em JSON.
- Testes cobrem cenários felizes e erros principais.
