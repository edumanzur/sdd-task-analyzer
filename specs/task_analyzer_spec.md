# Especificação SDD — TaskAnalyzer

Spec-Driven Development & AI Harness — transposta da Fase 1 (Eduardo Manzur Finotti Seabra).

## 1. Visão Geral e Contrato de Negócio (SDD)

### 1.1 Propósito do Módulo TaskAnalyzer

O `TaskAnalyzer` é um módulo de análise de tarefas e produtividade que recebe um conjunto de
tarefas de um indivíduo ou equipe e calcula métricas objetivas sobre o andamento do trabalho. O
módulo **não** gerencia o ciclo de vida das tarefas (criação, edição, exclusão) — ele apenas
consome uma lista de tarefas já existente e produz indicadores derivados.

Escopo do módulo:

- **Tempo médio de conclusão**: tempo médio decorrido entre o início e a conclusão das tarefas,
  calculado de forma geral e segmentado por prioridade.
- **Taxa de atraso**: percentual de tarefas concluídas após o prazo, ou pendentes com prazo
  vencido, calculado de forma geral e por prioridade.
- **Indicadores por prioridade**: consolidação da quantidade de tarefas e do desempenho (tempo
  médio e taxa de atraso) segmentados pelas prioridades baixa, média e alta.

Fora do escopo: notificações, integrações com calendário, geração de relatórios em PDF/Excel e
qualquer persistência de dados — o módulo opera inteiramente em memória.

### 1.2 Contrato Executável de Interface

#### 1.2.1 Entradas (Inputs)

Lista de objetos `Tarefa`, cada um com os campos:

| Campo | Tipo | Obrigatório | Descrição / Restrições |
|---|---|---|---|
| `id_tarefa` | `int` | Sim | Identificador único da tarefa (> 0). Não pode se repetir na lista. |
| `titulo` | `str` | Sim | Título da tarefa. Não pode ser vazio. |
| `prioridade` | `str` (enum) | Sim | Um dos valores: `"baixa"`, `"media"`, `"alta"`. |
| `status` | `str` (enum) | Sim | Um dos valores: `"concluida"`, `"pendente"`, `"cancelada"`. |
| `data_criacao` | `datetime` | Sim | Data/hora de criação da tarefa (UTC). |
| `data_inicio` | `datetime` | Não | Data/hora de início da execução (UTC). Se ausente, a tarefa é tratada como não iniciada. |
| `data_conclusao` | `datetime` | Não | Data/hora de conclusão (UTC). Obrigatório quando `status = "concluida"`. |
| `prazo` | `datetime` | Sim | Data/hora limite para conclusão (UTC). |

#### 1.2.2 Saídas (Outputs)

Estrutura de métricas (`TaskAnalysisResult`) com:

| Campo | Tipo | Descrição |
|---|---|---|
| `total_tarefas` | `int` | Total de tarefas válidas consideradas na análise. |
| `total_concluidas` | `int` | Total de tarefas com status `"concluida"`. |
| `total_pendentes` | `int` | Total de tarefas com status `"pendente"`. |
| `tempo_medio_conclusao_horas` | `float` (horas) | Tempo médio de conclusão geral, calculado apenas com tarefas `"concluida"` que possuam `data_inicio` e `data_conclusao`. |
| `taxa_atraso_percentual` | `float` (%) | Percentual de tarefas em atraso (geral). |
| `indicadores_por_prioridade` | `dict` | Chaves `"baixa"`, `"media"`, `"alta"`, cada uma com `quantidade_tarefas`, `tempo_medio_conclusao_horas` e `taxa_atraso_percentual` daquela prioridade. |

#### 1.2.3 Regras de Negócio e Restrições

1. Apenas tarefas com status `"concluida"` entram no cálculo de `tempo_medio_conclusao_horas`;
   tarefas `"cancelada"` são excluídas de todos os cálculos de tempo e atraso.
2. Uma tarefa é considerada em atraso quando: `data_conclusao > prazo` (concluídas) ou
   `agora_utc > prazo` (pendentes).
3. Tarefas com campos obrigatórios ausentes ou inconsistentes (ex.: `data_conclusao` anterior a
   `data_inicio`) lançam `TaskValidationError` e interrompem o processamento daquela chamada, com
   mensagem clara indicando a tarefa e o motivo.
4. Divisão por zero (nenhuma tarefa concluída, ou nenhuma tarefa em uma prioridade) retorna `0.0`
   para as métricas numéricas daquele grupo — nunca lança exceção não tratada.
5. Todas as datas são tratadas em UTC; conversões de fuso horário são responsabilidade do sistema
   chamador.
6. Percentuais e tempos médios são arredondados para 2 casas decimais na saída.
7. A ordem das tarefas na lista de entrada não afeta o resultado agregado (cálculo determinístico,
   independente de ordenação).

## 2. Cenários de Aceite (Dado – Quando – Então)

### Cenário 1 — Sucesso

- **Dado** um conjunto de tarefas válidas, com diferentes prioridades, prazos e status
  (concluídas e pendentes),
- **Quando** o `TaskAnalyzer` for executado sobre esse conjunto,
- **Então** deve retornar as métricas corretas de tempo médio de conclusão, taxa de atraso e
  quantidade de tarefas, geral e por prioridade (baixa, média, alta).

### Cenário 2 — Exceção / Erro (Entradas Inválidas)

- **Dado** uma entrada com datas inválidas (ex.: `data_conclusao` anterior a `data_inicio`),
- **Quando** o `TaskAnalyzer` for executado,
- **Então** deve disparar `TaskValidationError` com mensagem clara e objetiva.

### Cenário 3 — Borda (Complementar)

- **Dado** uma lista de tarefas vazia, ou um conjunto apenas com tarefas pendentes (sem nenhuma
  concluída), ou uma prioridade sem nenhuma tarefa,
- **Quando** o `TaskAnalyzer` for executado,
- **Então** deve retornar `0.0` para as médias/percentuais daquele grupo e `0` para as
  quantidades, sem lançar exceção não tratada.

## 3. Planejamento do Test Harness

Fluxo: **Cenários Escritos → Testes Automatizados (pytest) → Validação do Código Gerado por IA.**

Casos de teste derivados (implementados em `tests/test_harness.py`):

- `test_tempo_medio_conclusao_geral`
- `test_tempo_medio_por_prioridade`
- `test_taxa_atraso_tarefa_concluida_apos_prazo`
- `test_taxa_atraso_tarefa_pendente_vencida`
- `test_data_conclusao_anterior_a_inicio_lanca_erro`
- `test_lista_vazia_retorna_zeros`
- `test_prioridade_sem_tarefas_retorna_zero`

## 4. Governança de Contexto

As regras de governança de IA aplicadas a este módulo estão em [`CONTEXT_RULES.md`](../CONTEXT_RULES.md).
