# Logs, erros e observabilidade

## Logs estruturados

A API deve emitir logs estruturados em JSON para `stdout` e para `logs/api.json`.

Formato recomendado:

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

## Eventos mínimos

Devem ser registrados eventos para:

- início e fim de requisição;
- falha de autenticação;
- validação rejeitada;
- carregamento de sprints;
- sprint não encontrada;
- JSON inválido;
- consulta RAG executada;
- resumo gerado;
- chamada à OpenAI iniciada e concluída;
- rate limit da OpenAI;
- timeout externo;
- falha no Redis;
- falha no ChromaDB;
- erro interno inesperado.

## Sanitização

Logs não devem conter:

- chave da OpenAI;
- Bearer token;
- prompts completos;
- payloads grandes;
- stack trace enviado ao cliente;
- dados sensíveis dos arquivos de sprint.

Quando necessário, registrar hashes, tamanhos, contagens e identificadores de sprint em vez do conteúdo integral.

## Tratamento de erros

Erros devem ser mapeados por tipo:

- validação de request: `422`;
- autenticação ausente ou inválida: `401`;
- permissão negada, se aplicável: `403`;
- sprint inexistente: `404`;
- falha OpenAI: `502`;
- timeout externo: `504`;
- erro interno inesperado: `500`.

## Request ID

Cada requisição deve ter um `request_id`.

Se o cliente enviar um identificador aceito, a API pode propagá-lo. Caso contrário, deve gerar um UUID. O `request_id` deve aparecer nos logs e pode ser retornado no header de resposta.
