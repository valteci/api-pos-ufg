# Tarefa 07: Rota de resumos

## Objetivo

Implementar `POST /v1/resumos` para responder perguntas e gerar resumos sobre sprints, tarefas e subtarefas.

## Requisitos atendidos

- Recebe pergunta do usuário.
- Identifica onde pesquisar.
- Consulta dados corretos.
- Gera resposta objetiva.
- Responde com base nos dados.
- Informa quando dados são insuficientes.
- Testável por mocks.

## Subtarefas

- Criar schemas de request e response.
- Validar pergunta obrigatória, não vazia e limitada.
- Permitir escopo opcional de sprints.
- Identificar sprints citadas na pergunta quando possível.
- Carregar contexto relevante.
- Usar RAG ou seleção estruturada para reduzir contexto.
- Montar prompt seguro com instruções, contexto e pergunta separados.
- Chamar serviço de LLM por interface mockável.
- Retornar resposta, sprints consultadas e fontes.
- Tratar contexto insuficiente.
- Registrar log estruturado.

## Decisões técnicas

- A rota deve usar o mesmo carregamento e normalização de dados da rota de RAG.
- A resposta deve priorizar objetividade e evidência dos dados.
- O modelo deve ser instruído a não inventar informações ausentes.

## Testes necessários

- Pergunta válida gera resposta via mock.
- Pergunta vazia retorna erro.
- Pergunta grande demais retorna erro.
- Sprint inexistente retorna erro.
- Contexto insuficiente retorna mensagem explícita.
- Prompt separa instruções, contexto e pergunta.
- Rota exige autenticação.

## Critérios de aceite

- Respostas são rastreáveis por fontes.
- Router não contém regra de negócio de resumo.
- Swagger mostra contrato e exemplos.
