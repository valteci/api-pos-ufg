# Tarefa 06: Rota de RAG

**Status:** concluída

## Objetivo

Implementar `POST /v1/rag` para recuperar fragmentos relevantes das sprints.

## Requisitos atendidos

- Lista de sprints no request.
- Lista vazia consulta todas as sprints.
- `mensagem` validada.
- `rank` validado.
- `tamanho_fragmento` validado.
- Consulta apenas sprints solicitadas.
- Resposta com fragmentos próximos.
- Testável sem OpenAI real.

## Subtarefas

- Criar schemas de request e response.
- Validar `sprints` como lista.
- Resolver todas as sprints quando a lista vier vazia.
- Validar sprints inexistentes.
- Validar `mensagem` não vazia e limite máximo.
- Validar `rank` como inteiro positivo e dentro do limite.
- Validar `tamanho_fragmento` como inteiro positivo e dentro do limite.
- Gerar embedding da mensagem.
- Consultar banco vetorial com filtro de sprints.
- Retornar exatamente até `rank` fragmentos disponíveis.
- Aplicar limite de tamanho por fragmento.
- Incluir score e metadados.
- Registrar log estruturado da consulta.

## Decisões técnicas

- A rota deve retornar fragmentos recuperados, não necessariamente uma resposta sintetizada.
- A síntese com LLM pertence à rota de resumo ou a uma evolução documentada do RAG.
- O filtro de sprints deve ser aplicado antes ou durante a consulta vetorial, nunca apenas depois sem controle.

## Testes necessários

- Payload válido retorna fragmentos.
- Lista vazia consulta todas as sprints.
- Lista preenchida consulta apenas sprints pedidas.
- Sprint inexistente retorna erro.
- `rank` inválido retorna erro.
- `tamanho_fragmento` inválido retorna erro.
- Mensagem vazia retorna erro.
- Rota exige autenticação.

## Critérios de aceite

- Contrato aparece no Swagger.
- Testes cobrem validações e fluxo feliz.
- Nenhuma chamada real à OpenAI ocorre nos testes de rota.
