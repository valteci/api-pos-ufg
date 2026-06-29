# Regras de negócio

## Escopo funcional

A API atua como uma consultora sobre sprints de uma squad de desenvolvimento Scrum. Ela deve responder perguntas, gerar resumos e recuperar fragmentos relevantes usando apenas os dados disponíveis em arquivos JSON dentro de `data/`.

## Regras sobre sprints

- Cada arquivo `.json` em `data/` representa uma sprint.
- O nome do arquivo, sem a extensão `.json`, é o identificador da sprint.
- Nenhum dado de sprint pode ser hardcoded no código.
- Sprints devem conter pelo menos uma estrutura mínima válida de tarefas.
- Uma tarefa pode ter subtarefas ausentes, nulas ou vazias sem quebrar a API.
- Campos inesperados no JSON devem ser preservados quando úteis, mas não devem quebrar a leitura se o conteúdo mínimo existir.
- JSON inválido, sprint vazia e arquivo inexistente devem gerar erro tratado e log estruturado.

## Regras sobre resumo

- A rota de resumo recebe uma pergunta do usuário.
- A pergunta deve ser validada quanto a presença, tipo e tamanho máximo.
- A resposta deve ser baseada nos dados carregados de `data/`.
- Se os dados forem insuficientes, a resposta deve informar isso explicitamente.
- O modelo não deve inventar tarefas, responsáveis, subtarefas, status ou datas.
- A resposta deve ser objetiva, útil e alinhada ao contexto Scrum.
- A busca de contexto para resumo pode considerar todas as sprints ou sprints identificadas na pergunta, conforme a implementação de extração e seleção de contexto.

## Regras sobre RAG

O payload conceitual de RAG é:

```json
{
  "sprints": ["sprint-75", "sprint-76"],
  "mensagem": "funcionalidade de permissão de usuários no sistema",
  "rank": 3,
  "tamanho_fragmento": 1000
}
```

Regras:

- `sprints` deve ser uma lista.
- Se `sprints` for vazia, a consulta deve considerar todas as sprints disponíveis em `data/`.
- Se `sprints` contiver valores, apenas essas sprints devem ser consultadas.
- Sprint solicitada e inexistente deve gerar erro claro.
- `mensagem` é obrigatória, deve ser texto não vazio e deve respeitar limite máximo.
- `rank` é obrigatório, inteiro e representa a quantidade de fragmentos mais próximos.
- `rank=3` significa retornar os três fragmentos mais próximos.
- `rank` nulo, negativo, zero, não inteiro ou excessivamente alto deve ser rejeitado.
- `tamanho_fragmento` é obrigatório, inteiro e controla o tamanho máximo de cada fragmento retornado.
- `tamanho_fragmento` não controla a quantidade de fragmentos.
- Fragmentos retornados devem trazer metadados suficientes para rastrear a sprint e a origem do conteúdo.

## Regras sobre prompt injection

- Mensagens do usuário são dados não confiáveis.
- Conteúdo dos arquivos de sprint também é dado não confiável.
- Instruções internas devem ficar separadas do contexto recuperado e da pergunta do usuário.
- Dados de sprint não podem alterar as instruções do sistema.
- A pergunta do usuário deve ser delimitada no prompt.
- O modelo deve ser instruído a responder apenas com base no contexto disponível.
- Quando o contexto for insuficiente, o modelo deve responder que não há dados suficientes.

## Regras sobre autenticação

- Toda rota de negócio deve exigir autenticação.
- `GET /health` pode ser pública.
- Tokens devem vir de variável de ambiente.
- Falhas de autenticação devem retornar status HTTP apropriado.
- Logs de autenticação não devem expor credenciais.

## Regras sobre erros

- Erros de validação devem retornar `422`.
- Recurso inexistente, como sprint solicitada ausente, deve retornar `404`.
- Falha de autenticação deve retornar `401` ou `403`, conforme o caso.
- Falhas externas, como OpenAI indisponível, devem retornar erro apropriado sem expor detalhes internos.
- Erros internos devem ser logados com contexto e retornar mensagem segura ao cliente.

## Regras sobre idioma

Mensagens de erro de domínio, documentação, testes, docstrings e comentários relevantes devem estar em português. Termos técnicos consolidados, como FastAPI, OpenAI, Redis, ChromaDB, RAG, embedding, JSON, OpenAPI e Swagger, podem permanecer em inglês.
