# CONTEXT_RULES.md — Governança de Contexto para Agentes de IA

Fonte de verdade fornecida a qualquer assistente de IA (Gemini, ChatGPT, GitHub Copilot, Claude)
antes de qualquer geração ou alteração de código neste repositório. Transposto da Fase 1
(`specs/task_analyzer_spec.md`, seção 3).

## 1. Diretrizes Arquiteturais (Obrigatórias)

- Utilizar Python 3.11+ como versão mínima obrigatória.
- Utilizar type hints (anotações de tipo) em 100% das funções e métodos.
- Seguir o princípio Single Responsibility (SRP) e código limpo (PEP 8).
- Documentação formal no padrão Google style docstrings para módulos, classes, funções e parâmetros.
- Funções devem ser pequenas, coesas e com um único propósito.
- Tratamento de exceções específico e com mensagens claras (nunca usar `except Exception` genérico
  sem re-tratamento).
- Logs estruturados utilizando o módulo padrão `logging`.
- Código deve ser legível, manutenível e com nomes de variáveis e funções descritivos.
- Separar responsabilidades (SRP) e evitar lógica em scripts soltos — organizar em módulos coesos
  dentro de `src/`.

## 2. Proibições Explícitas (Regras Restritivas)

- Não utilizar bibliotecas externas não autorizadas (apenas biblioteca padrão do Python, salvo
  autorização explícita).
- Não alterar, remover ou adaptar os cenários de teste fornecidos na especificação.
- Não modificar a estrutura de pastas definida na especificação.
- Não persistir dados em arquivos ou bancos de dados.
- Não alterar a assinatura (nome e parâmetros) das funções públicas sem autorização explícita.
- Não gerar código sem testes correspondentes para as novas funcionalidades.
- Não inserir código duplicado ou sem necessidade (evitar redundância).
- Não assumir comportamentos não especificados no contrato de negócio — em caso de dúvida,
  sinalizar e não implementar.

## 3. Regras de Interação com IA

- Fornecer sempre o contexto completo da especificação (`specs/task_analyzer_spec.md`) antes de
  solicitar geração de código.
- Validar se a IA compreendeu o contrato de negócio e os cenários de aceite antes de aceitar a
  resposta.
- Solicitar explicações quando houver dúvidas sobre a solução proposta pela IA.
- Revisar criticamente todo código gerado antes de qualquer commit.
- Rejeitar respostas que violem as proibições explícitas da seção 2 ou o contrato de negócio.

## 4. Como estas regras evitaram "alucinações" nesta implementação

- O nome da exceção customizada (`TaskValidationError`) e a assinatura de `analyze_tasks` foram
  fixados a partir do contrato, impedindo que a IA inventasse nomes alternativos (ex.:
  `DadosInvalidosError`, mencionado em rascunho anterior, foi descartado por divergir do nome
  exigido na entrega da Fase 2).
- A regra de "divisão por zero retorna 0.0, nunca exceção" impediu que a IA lançasse
  `ZeroDivisionError` ou similar em grupos sem tarefas concluídas.
- A proibição de bibliotecas externas manteve a implementação apenas com `dataclasses`, `enum`,
  `datetime` e `logging` da biblioteca padrão.
- A exigência de type hints em 100% das funções obrigou a tipagem explícita de parâmetros,
  retornos e estruturas de dados (dataclasses), evitando funções com assinaturas ambíguas.
