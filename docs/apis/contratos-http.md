# Contratos HTTP

## Convenções gerais

- Rotas de negócio devem ficar sob `/v1`.
- Rotas de negócio devem exigir Bearer token.
- `GET /health` deve permanecer pública.
- Requisições e respostas devem usar JSON.
- Schemas Pydantic devem alimentar a documentação Swagger/OpenAPI.
- Erros devem usar mensagens em português e códigos HTTP apropriados.

## `GET /health`

Rota pública para healthcheck simples.

Resposta esperada:

```json
{
  "status": "ok"
}
```

Status esperado:

- `200 OK`: aplicação disponível.

## `POST /v1/resumos`

Rota autenticada para perguntas consultivas e resumos sobre sprints, tarefas e subtarefas.

Payload previsto:

```json
{
  "pergunta": "Como está o andamento da sprint 75?",
  "sprints": ["sprint-75"]
}
```

`sprints` pode ser opcional. Quando não informado, a implementação deve identificar o escopo pela pergunta ou consultar o conjunto apropriado de dados.

Resposta prevista:

```json
{
  "resposta": "Não há dados suficientes para responder com segurança.",
  "sprints_consultadas": ["sprint-75"],
  "fontes": [
    {
      "sprint": "sprint-75",
      "origem": "sprint-75.json"
    }
  ]
}
```

Status previstos:

- `200 OK`: resumo gerado.
- `401 Unauthorized`: token ausente ou inválido.
- `404 Not Found`: sprint solicitada não encontrada.
- `422 Unprocessable Entity`: payload inválido.
- `502 Bad Gateway`: falha tratada na OpenAI.
- `504 Gateway Timeout`: timeout em integração externa.

## `POST /v1/rag`

Rota autenticada para recuperação de fragmentos relevantes a partir dos dados de sprint.

Payload previsto:

```json
{
  "sprints": ["sprint-75", "sprint-76"],
  "mensagem": "funcionalidade de permissão de usuários no sistema",
  "rank": 3,
  "tamanho_fragmento": 1000
}
```

Resposta prevista:

```json
{
  "mensagem": "funcionalidade de permissão de usuários no sistema",
  "rank": 3,
  "fragmentos": [
    {
      "conteudo": "Texto recuperado da tarefa ou subtarefa...",
      "score": 0.92,
      "sprint": "sprint-75",
      "origem": "sprint-75.json",
      "metadados": {
        "tipo": "tarefa",
        "caminho": "tarefas[0]"
      }
    }
  ]
}
```

Status previstos:

- `200 OK`: fragmentos recuperados.
- `401 Unauthorized`: token ausente ou inválido.
- `404 Not Found`: sprint solicitada não encontrada.
- `422 Unprocessable Entity`: `rank`, `mensagem`, `sprints` ou `tamanho_fragmento` inválido.
- `502 Bad Gateway`: falha tratada na OpenAI ou no banco vetorial.
- `504 Gateway Timeout`: timeout em integração externa.

## Limites recomendados

Os limites devem ser configuráveis por ambiente, com valores padrão não secretos:

- `MAX_MESSAGE_LENGTH`: limite máximo da pergunta ou mensagem.
- `MAX_RAG_RANK`: maior valor aceito para `rank`.
- `MAX_FRAGMENT_SIZE`: maior tamanho aceito para cada fragmento.
- `MAX_SPRINTS_PER_REQUEST`: maior quantidade de sprints consultáveis em uma requisição.

Valores finais devem ser definidos na implementação e documentados no `README.md`.
