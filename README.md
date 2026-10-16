# sdd-task-analyzer

Implementação do módulo **TaskAnalyzer**, parte da Fase 2 (Entrega Intermediária) do projeto
cumulativo de Spec-Driven Development & AI Harness — Bootcamp III.

O `TaskAnalyzer` recebe uma lista de tarefas e calcula métricas de produtividade: tempo médio de
conclusão, taxa de atraso e quantidade de tarefas, de forma geral e segmentada por prioridade
(baixa, média, alta). O módulo opera inteiramente em memória — não gerencia o ciclo de vida das
tarefas e não persiste dados.

## Status do build

![Testes](https://img.shields.io/badge/pytest-100%25%20passed-brightgreen)

## Estrutura do repositório

```
sdd-task-analyzer/
├── README.md                 # Este arquivo
├── CONTEXT_RULES.md          # Regras de governança de IA (Fase 1)
├── pytest.ini                # Configuração do pytest
├── .gitignore
├── requirements.txt          # Dependências (pytest)
├── specs/
│   └── task_analyzer_spec.md # Especificação SDD / contrato de negócio (Fase 1)
├── tests/
│   └── test_harness.py       # Suíte de testes automatizados (Cenários 1, 2 e bordas)
└── src/
    └── task_analyzer.py      # Implementação de analyze_tasks e TaskValidationError
```

## Como executar

### Pré-requisitos

- Python 3.11+

### Instalação

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Executar os testes

```bash
pytest -v
```

Resultado esperado: **100% dos testes aprovados**, cobrindo os cenários de aceite definidos em
[`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md).

### Relatório de cobertura (opcional)

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

## Uso básico

```python
from datetime import datetime, timedelta, timezone
from src.task_analyzer import Tarefa, Prioridade, StatusTarefa, analyze_tasks

agora = datetime.now(timezone.utc)

tarefas = [
    Tarefa(
        id_tarefa=1,
        titulo="Revisar PR",
        prioridade=Prioridade.ALTA,
        status=StatusTarefa.CONCLUIDA,
        data_criacao=agora - timedelta(days=2),
        prazo=agora + timedelta(days=1),
        data_inicio=agora - timedelta(hours=2),
        data_conclusao=agora,
    ),
]

resultado = analyze_tasks(tarefas)
print(resultado.tempo_medio_conclusao_horas, resultado.taxa_atraso_percentual)
```

## Governança de IA (SDD)

Este código foi gerado por um assistente de IA (Claude), estritamente guiado por:

- [`CONTEXT_RULES.md`](CONTEXT_RULES.md) — regras arquiteturais e proibições explícitas.
- [`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md) — contrato de negócio e cenários
  de aceite da Fase 1.

Todo código gerado passou por homologação humana antes de ser commitado, incluindo execução
completa da suíte de testes automatizados.

## Projeto cumulativo

- **Fase 1** (concluída): Especificação SDD, cenários de aceite, governança de contexto.
- **Fase 2** (esta entrega): Repositório GitHub, código via IA, Test Harness (pytest), versionamento Git/GitHub.
- **Fase 3** (próxima entrega): CI/CD com GitHub Actions, Docker, relatório de governança/segurança.
