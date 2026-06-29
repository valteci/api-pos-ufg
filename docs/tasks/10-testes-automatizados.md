# Tarefa 10: Testes automatizados

## Objetivo

Criar suíte de testes para regras de negócio, rotas, validações e integrações mockadas.

## Requisitos atendidos

- Toda funcionalidade testável.
- Integrações externas isoladas por mocks.
- Carregamento de dados testado.
- RAG testado.
- Resumo testado.
- Autenticação testada.
- Healthcheck público testado.

## Subtarefas

- Configurar Pytest.
- Criar estrutura `tests/`.
- Criar fixtures de sprints.
- Criar fixtures de configuração.
- Criar mocks da OpenAI.
- Criar fake de Redis.
- Criar fake de banco vetorial.
- Testar carregamento de dados.
- Testar serviços de RAG.
- Testar serviços de resumo.
- Testar rotas com `TestClient`.
- Testar autenticação.
- Testar erros e validações.
- Configurar marcador para testes de integração.

## Decisões técnicas

- Testes unitários devem ser padrão.
- Testes com serviços reais devem ser marcados como integração.
- Nenhum teste padrão deve depender de internet ou OpenAI real.

## Critérios de aceite

- `poetry run pytest` executa a suíte padrão.
- Falhas comuns dos requisitos estão cobertas.
- Fixtures não contêm segredos reais.
