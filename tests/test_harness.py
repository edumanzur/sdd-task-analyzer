"""Test Harness do TaskAnalyzer.

Traduz os cenários de aceite definidos em ``specs/task_analyzer_spec.md``
(seção 2) em testes automatizados com pytest.

- Cenário 1 (Sucesso): cálculos corretos de métricas gerais e por prioridade.
- Cenário 2 (Exceção/Erro): datas inconsistentes disparam TaskValidationError.
- Cenário 3 (Borda): entradas vazias ou sem tarefas concluídas retornam 0.0,
  sem lançar exceção.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.task_analyzer import (
    Prioridade,
    StatusTarefa,
    Tarefa,
    TaskValidationError,
    analyze_tasks,
)

UTC = timezone.utc
AGORA = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def _tarefa(
    id_tarefa: int,
    prioridade: Prioridade,
    status: StatusTarefa,
    prazo: datetime,
    data_inicio: datetime | None = None,
    data_conclusao: datetime | None = None,
    titulo: str = "Tarefa de teste",
) -> Tarefa:
    """Cria uma Tarefa de teste com data_criacao fixa, 1 dia antes do prazo."""
    return Tarefa(
        id_tarefa=id_tarefa,
        titulo=titulo,
        prioridade=prioridade,
        status=status,
        data_criacao=prazo - timedelta(days=1),
        prazo=prazo,
        data_inicio=data_inicio,
        data_conclusao=data_conclusao,
    )


@pytest.fixture
def tarefas_validas_mistas() -> list[Tarefa]:
    """Cenário 1: conjunto válido com prioridades, prazos e status variados."""
    return [
        # Alta prioridade, concluída dentro do prazo, 2h de duração.
        _tarefa(
            id_tarefa=1,
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.CONCLUIDA,
            prazo=AGORA + timedelta(days=1),
            data_inicio=AGORA - timedelta(hours=2),
            data_conclusao=AGORA,
        ),
        # Alta prioridade, concluída após o prazo (em atraso), 4h de duração.
        _tarefa(
            id_tarefa=2,
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.CONCLUIDA,
            prazo=AGORA - timedelta(hours=1),
            data_inicio=AGORA - timedelta(hours=4),
            data_conclusao=AGORA,
        ),
        # Média prioridade, pendente, prazo ainda não vencido.
        _tarefa(
            id_tarefa=3,
            prioridade=Prioridade.MEDIA,
            status=StatusTarefa.PENDENTE,
            prazo=AGORA + timedelta(days=2),
        ),
        # Média prioridade, pendente, prazo vencido (em atraso).
        _tarefa(
            id_tarefa=4,
            prioridade=Prioridade.MEDIA,
            status=StatusTarefa.PENDENTE,
            prazo=AGORA - timedelta(days=1),
        ),
        # Baixa prioridade, cancelada — deve ser excluída de todos os cálculos.
        _tarefa(
            id_tarefa=5,
            prioridade=Prioridade.BAIXA,
            status=StatusTarefa.CANCELADA,
            prazo=AGORA + timedelta(days=1),
        ),
    ]


class TestCenario1Sucesso:
    """Cenário 1 — conjunto de tarefas válidas produz métricas corretas."""

    def test_tempo_medio_conclusao_geral(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        # Duas tarefas concluídas: 2h e 4h -> média de 3h.
        assert resultado.tempo_medio_conclusao_horas == 3.0

    def test_tempo_medio_por_prioridade(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        indicadores_alta = resultado.indicadores_por_prioridade["alta"]
        assert indicadores_alta.tempo_medio_conclusao_horas == 3.0
        assert indicadores_alta.quantidade_tarefas == 2

        indicadores_media = resultado.indicadores_por_prioridade["media"]
        # Nenhuma tarefa de média prioridade está concluída.
        assert indicadores_media.tempo_medio_conclusao_horas == 0.0
        assert indicadores_media.quantidade_tarefas == 2

    def test_taxa_atraso_tarefa_concluida_apos_prazo(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        indicadores_alta = resultado.indicadores_por_prioridade["alta"]
        # 1 de 2 tarefas de alta prioridade está em atraso -> 50%.
        assert indicadores_alta.taxa_atraso_percentual == 50.0

    def test_taxa_atraso_tarefa_pendente_vencida(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        indicadores_media = resultado.indicadores_por_prioridade["media"]
        # 1 de 2 tarefas de média prioridade está pendente e vencida -> 50%.
        assert indicadores_media.taxa_atraso_percentual == 50.0

    def test_quantidade_tarefas_exclui_canceladas(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        # 5 tarefas no total, 1 cancelada -> 4 tarefas válidas.
        assert resultado.total_tarefas == 4
        assert resultado.total_concluidas == 2
        assert resultado.total_pendentes == 2
        # Prioridade baixa só tinha a tarefa cancelada -> 0 tarefas válidas.
        assert resultado.indicadores_por_prioridade["baixa"].quantidade_tarefas == 0


class TestCenario2ExcecaoErro:
    """Cenário 2 — entradas inválidas disparam TaskValidationError."""

    def test_data_conclusao_anterior_a_inicio_lanca_erro(self) -> None:
        tarefa_invalida = _tarefa(
            id_tarefa=1,
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.CONCLUIDA,
            prazo=AGORA + timedelta(days=1),
            data_inicio=AGORA,
            data_conclusao=AGORA - timedelta(hours=1),
        )
        with pytest.raises(TaskValidationError):
            analyze_tasks([tarefa_invalida], agora_utc=AGORA)

    def test_tarefa_concluida_sem_data_conclusao_lanca_erro(self) -> None:
        tarefa_invalida = _tarefa(
            id_tarefa=1,
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.CONCLUIDA,
            prazo=AGORA + timedelta(days=1),
            data_inicio=AGORA - timedelta(hours=1),
            data_conclusao=None,
        )
        with pytest.raises(TaskValidationError):
            analyze_tasks([tarefa_invalida], agora_utc=AGORA)

    def test_titulo_vazio_lanca_erro(self) -> None:
        tarefa_invalida = _tarefa(
            id_tarefa=1,
            prioridade=Prioridade.ALTA,
            status=StatusTarefa.PENDENTE,
            prazo=AGORA + timedelta(days=1),
            titulo="   ",
        )
        with pytest.raises(TaskValidationError):
            analyze_tasks([tarefa_invalida], agora_utc=AGORA)


class TestCenario3Borda:
    """Cenário 3 — entradas vazias ou sem conclusões retornam 0.0, sem erro."""

    def test_lista_vazia_retorna_zeros(self) -> None:
        resultado = analyze_tasks([], agora_utc=AGORA)
        assert resultado.total_tarefas == 0
        assert resultado.total_concluidas == 0
        assert resultado.total_pendentes == 0
        assert resultado.tempo_medio_conclusao_horas == 0.0
        assert resultado.taxa_atraso_percentual == 0.0
        for indicadores in resultado.indicadores_por_prioridade.values():
            assert indicadores.quantidade_tarefas == 0
            assert indicadores.tempo_medio_conclusao_horas == 0.0
            assert indicadores.taxa_atraso_percentual == 0.0

    def test_somente_tarefas_pendentes_sem_erro(self) -> None:
        tarefas = [
            _tarefa(
                id_tarefa=1,
                prioridade=Prioridade.BAIXA,
                status=StatusTarefa.PENDENTE,
                prazo=AGORA + timedelta(days=1),
            )
        ]
        resultado = analyze_tasks(tarefas, agora_utc=AGORA)
        # Nenhuma tarefa concluída -> média de tempo é 0.0, sem lançar exceção.
        assert resultado.tempo_medio_conclusao_horas == 0.0
        assert resultado.taxa_atraso_percentual == 0.0

    def test_prioridade_sem_tarefas_retorna_zero(
        self, tarefas_validas_mistas: list[Tarefa]
    ) -> None:
        resultado = analyze_tasks(tarefas_validas_mistas, agora_utc=AGORA)
        # Prioridade "baixa" só tinha a tarefa cancelada -> grupo vazio.
        indicadores_baixa = resultado.indicadores_por_prioridade["baixa"]
        assert indicadores_baixa.quantidade_tarefas == 0
        assert indicadores_baixa.tempo_medio_conclusao_horas == 0.0
        assert indicadores_baixa.taxa_atraso_percentual == 0.0
