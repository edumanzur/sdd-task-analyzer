"""Módulo de análise de tarefas e produtividade (TaskAnalyzer).

Implementa o contrato definido em ``specs/task_analyzer_spec.md`` e segue as
diretrizes de ``CONTEXT_RULES.md``. O módulo opera inteiramente em memória: não
gerencia o ciclo de vida das tarefas (criação, edição, exclusão) e não persiste
dados em arquivos ou bancos de dados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class Prioridade(str, Enum):
    """Níveis de prioridade aceitos para uma tarefa."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class StatusTarefa(str, Enum):
    """Estados de ciclo de vida aceitos para uma tarefa."""

    CONCLUIDA = "concluida"
    PENDENTE = "pendente"
    CANCELADA = "cancelada"


class TaskValidationError(Exception):
    """Erro específico para dados de tarefa inconsistentes ou inválidos.

    Lançado quando uma tarefa viola uma restrição obrigatória do contrato de
    negócio (ex.: ``data_conclusao`` anterior a ``data_inicio``), impedindo que
    o processamento continue com dados que invalidariam o resultado agregado.
    """


@dataclass(frozen=True)
class Tarefa:
    """Representa uma tarefa a ser analisada pelo TaskAnalyzer.

    Attributes:
        id_tarefa: Identificador único da tarefa (> 0).
        titulo: Título da tarefa. Não pode ser vazio.
        prioridade: Prioridade da tarefa (``baixa``, ``media`` ou ``alta``).
        status: Status atual da tarefa (``concluida``, ``pendente`` ou
            ``cancelada``).
        data_criacao: Data/hora de criação da tarefa (UTC).
        prazo: Data/hora limite para conclusão da tarefa (UTC).
        data_inicio: Data/hora em que a execução começou (UTC), se houver.
        data_conclusao: Data/hora de conclusão (UTC), obrigatória quando
            ``status`` é ``concluida``.
    """

    id_tarefa: int
    titulo: str
    prioridade: Prioridade
    status: StatusTarefa
    data_criacao: datetime
    prazo: datetime
    data_inicio: datetime | None = None
    data_conclusao: datetime | None = None


@dataclass(frozen=True)
class IndicadoresPrioridade:
    """Métricas agregadas para uma única prioridade.

    Attributes:
        quantidade_tarefas: Total de tarefas consideradas nessa prioridade.
        tempo_medio_conclusao_horas: Tempo médio de conclusão em horas.
        taxa_atraso_percentual: Percentual de tarefas em atraso.
    """

    quantidade_tarefas: int
    tempo_medio_conclusao_horas: float
    taxa_atraso_percentual: float


@dataclass(frozen=True)
class TaskAnalysisResult:
    """Resultado agregado da análise de um conjunto de tarefas.

    Attributes:
        total_tarefas: Total de tarefas válidas consideradas na análise.
        total_concluidas: Total de tarefas com status ``concluida``.
        total_pendentes: Total de tarefas com status ``pendente``.
        tempo_medio_conclusao_horas: Tempo médio de conclusão geral, em horas.
        taxa_atraso_percentual: Percentual de tarefas em atraso (geral).
        indicadores_por_prioridade: Métricas segmentadas por prioridade.
    """

    total_tarefas: int
    total_concluidas: int
    total_pendentes: int
    tempo_medio_conclusao_horas: float
    taxa_atraso_percentual: float
    indicadores_por_prioridade: dict[str, IndicadoresPrioridade] = field(
        default_factory=dict
    )


def _validar_tarefa(tarefa: Tarefa) -> None:
    """Valida a consistência de uma tarefa individual.

    Args:
        tarefa: Tarefa a ser validada.

    Raises:
        TaskValidationError: Se o título estiver vazio, se uma tarefa
            concluída não possuir ``data_conclusao``, ou se
            ``data_conclusao`` for anterior a ``data_inicio``.
    """
    if not tarefa.titulo.strip():
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: o título não pode ser vazio."
        )

    if tarefa.status == StatusTarefa.CONCLUIDA and tarefa.data_conclusao is None:
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: tarefas concluídas exigem data_conclusao."
        )

    if (
        tarefa.data_inicio is not None
        and tarefa.data_conclusao is not None
        and tarefa.data_conclusao < tarefa.data_inicio
    ):
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: data_conclusao não pode ser anterior a "
            "data_inicio."
        )


def _esta_em_atraso(tarefa: Tarefa, agora_utc: datetime) -> bool:
    """Determina se uma tarefa está em atraso.

    Uma tarefa concluída está em atraso se foi concluída após o prazo. Uma
    tarefa pendente está em atraso se o prazo já passou.

    Args:
        tarefa: Tarefa a ser avaliada.
        agora_utc: Instante de referência (UTC) usado para tarefas pendentes.

    Returns:
        ``True`` se a tarefa está em atraso, ``False`` caso contrário.
    """
    if tarefa.status == StatusTarefa.CONCLUIDA:
        return tarefa.data_conclusao is not None and tarefa.data_conclusao > tarefa.prazo
    if tarefa.status == StatusTarefa.PENDENTE:
        return agora_utc > tarefa.prazo
    return False


def _calcular_tempo_medio_horas(tarefas: list[Tarefa]) -> float:
    """Calcula o tempo médio de conclusão, em horas, de um grupo de tarefas.

    Considera apenas tarefas concluídas que possuam ``data_inicio`` e
    ``data_conclusao``. Retorna ``0.0`` quando não há tarefas elegíveis,
    nunca lançando exceção por divisão por zero.

    Args:
        tarefas: Tarefas do grupo a ser analisado.

    Returns:
        Tempo médio de conclusão em horas, arredondado para 2 casas decimais.
    """
    duracoes_horas = [
        (tarefa.data_conclusao - tarefa.data_inicio).total_seconds() / 3600
        for tarefa in tarefas
        if tarefa.status == StatusTarefa.CONCLUIDA
        and tarefa.data_inicio is not None
        and tarefa.data_conclusao is not None
    ]

    if not duracoes_horas:
        return 0.0

    return round(sum(duracoes_horas) / len(duracoes_horas), 2)


def _calcular_taxa_atraso_percentual(tarefas: list[Tarefa], agora_utc: datetime) -> float:
    """Calcula o percentual de tarefas em atraso de um grupo de tarefas.

    Considera tarefas concluídas e pendentes (tarefas canceladas já devem ter
    sido filtradas antes de chamar esta função). Retorna ``0.0`` quando o
    grupo está vazio, nunca lançando exceção por divisão por zero.

    Args:
        tarefas: Tarefas do grupo a ser analisado.
        agora_utc: Instante de referência (UTC) usado para tarefas pendentes.

    Returns:
        Percentual de tarefas em atraso, arredondado para 2 casas decimais.
    """
    if not tarefas:
        return 0.0

    total_em_atraso = sum(
        1 for tarefa in tarefas if _esta_em_atraso(tarefa, agora_utc)
    )
    return round((total_em_atraso / len(tarefas)) * 100, 2)


def _construir_indicadores_prioridade(
    tarefas: list[Tarefa], prioridade: Prioridade, agora_utc: datetime
) -> IndicadoresPrioridade:
    """Constrói os indicadores agregados de uma única prioridade.

    Args:
        tarefas: Todas as tarefas válidas (já filtradas de canceladas).
        prioridade: Prioridade para a qual os indicadores serão calculados.
        agora_utc: Instante de referência (UTC) usado para tarefas pendentes.

    Returns:
        Indicadores agregados (quantidade, tempo médio e taxa de atraso) da
        prioridade informada.
    """
    tarefas_da_prioridade = [t for t in tarefas if t.prioridade == prioridade]

    return IndicadoresPrioridade(
        quantidade_tarefas=len(tarefas_da_prioridade),
        tempo_medio_conclusao_horas=_calcular_tempo_medio_horas(tarefas_da_prioridade),
        taxa_atraso_percentual=_calcular_taxa_atraso_percentual(
            tarefas_da_prioridade, agora_utc
        ),
    )


def analyze_tasks(
    tarefas: list[Tarefa], agora_utc: datetime | None = None
) -> TaskAnalysisResult:
    """Analisa um conjunto de tarefas e retorna métricas de produtividade.

    Tarefas com status ``cancelada`` são excluídas de todos os cálculos de
    tempo e atraso, mas cada tarefa (inclusive canceladas) é validada
    individualmente antes do cálculo agregado.

    Args:
        tarefas: Lista de tarefas a serem analisadas. Pode ser vazia.
        agora_utc: Instante de referência (UTC) usado para determinar se
            tarefas pendentes estão em atraso. Se omitido, usa o instante
            atual (``datetime.now(timezone.utc)``).

    Returns:
        Estrutura com as métricas agregadas, geral e por prioridade.

    Raises:
        TaskValidationError: Se alguma tarefa possuir dados inconsistentes
            (ex.: ``data_conclusao`` anterior a ``data_inicio``, título vazio
            ou tarefa concluída sem ``data_conclusao``).
    """
    momento_referencia = agora_utc if agora_utc is not None else datetime.now(timezone.utc)

    for tarefa in tarefas:
        _validar_tarefa(tarefa)

    tarefas_validas = [t for t in tarefas if t.status != StatusTarefa.CANCELADA]

    total_concluidas = sum(
        1 for t in tarefas_validas if t.status == StatusTarefa.CONCLUIDA
    )
    total_pendentes = sum(
        1 for t in tarefas_validas if t.status == StatusTarefa.PENDENTE
    )

    indicadores_por_prioridade = {
        prioridade.value: _construir_indicadores_prioridade(
            tarefas_validas, prioridade, momento_referencia
        )
        for prioridade in Prioridade
    }

    resultado = TaskAnalysisResult(
        total_tarefas=len(tarefas_validas),
        total_concluidas=total_concluidas,
        total_pendentes=total_pendentes,
        tempo_medio_conclusao_horas=_calcular_tempo_medio_horas(tarefas_validas),
        taxa_atraso_percentual=_calcular_taxa_atraso_percentual(
            tarefas_validas, momento_referencia
        ),
        indicadores_por_prioridade=indicadores_por_prioridade,
    )

    logger.info(
        "Análise concluída: %d tarefa(s) válida(s), %.2f%% em atraso.",
        resultado.total_tarefas,
        resultado.taxa_atraso_percentual,
    )

    return resultado
